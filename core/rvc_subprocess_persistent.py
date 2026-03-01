"""
Procesador multi-voz con subprocess PERSISTENTE.

A diferencia de SubprocessProcessor (que arranca un proceso Python nuevo
por cada mensaje), este procesador inicia el worker UNA SOLA VEZ y lo
reutiliza para todos los mensajes siguientes.

Ventajas:
- Los modelos (Hubert, RMVPE, RVC) se cargan una sola vez (~30s al inicio)
- Cada mensaje subsiguiente tarda sólo TTS + RVC (~3-8s)
- Si el worker crashea (heap corruption), se reinicia automáticamente
- El proceso padre NUNCA toca RVC/CUDA directamente → sin heap corruption

Protocolo stdin/stdout:
  - Padre → Hijo: una línea JSON por mensaje: {"text":"...", "output_file":"..."}
  - Hijo → Padre: líneas de log (ignoradas o mostradas)
                  líneas de protocolo con prefijo "NOPOLO_PROTO|"
    NOPOLO_PROTO|READY              - worker listo para recibir mensajes
    NOPOLO_PROTO|SUCCESS|<ruta>     - audio escrito en <ruta>
    NOPOLO_PROTO|ERROR|<mensaje>    - error procesando mensaje
    NOPOLO_PROTO|FATAL|<mensaje>    - error fatal, worker va a morir
"""

import subprocess
import sys
import os
import json
import tempfile
import threading
import time
import queue
import numpy as np
import soundfile as sf
from typing import Tuple, Optional

# Capturar los streams REALES antes de que la GUI los redirija a widgets Qt.
# Los relay threads DEBEN usar estos — llamar a sys.stdout desde un thread
# de background cuando sys.stdout apunta a un QTextEdit causa heap corruption
# (0xc0000374) porque los métodos Qt no son thread-safe.
_REAL_STDOUT = sys.__stdout__
_REAL_STDERR = sys.__stderr__


def _tprint(*args, **kwargs):
    """print() thread-safe: escribe en el stdout original, nunca en el widget Qt."""
    try:
        print(*args, **kwargs, file=_REAL_STDOUT)
        _REAL_STDOUT.flush()
    except Exception:
        pass


# Prefijo único para mensajes de protocolo (improbable en logs normales)
PROTO_PREFIX = "NOPOLO_PROTO|"

# ============================================================
# Script del worker persistente (se embebe como string)
# ============================================================
PERSISTENT_WORKER_SCRIPT = r'''
import sys
import os
import json
import gc
import io

# ── Encoding seguro en Windows ────────────────────────────────────────────────
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                   errors="replace", line_buffering=True)
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                                   errors="replace", line_buffering=True)

PROTO = "NOPOLO_PROTO|"

def proto(msg: str):
    """Escribe mensaje de protocolo garantizando que llega al padre."""
    sys.stdout.write(PROTO + msg + "\n")
    sys.stdout.flush()

def log(msg: str):
    """Log normal (va a stderr para no mezclar con protocolo)."""
    sys.stderr.write(f"[Worker] {msg}\n")
    sys.stderr.flush()

# ── Setup del entorno ─────────────────────────────────────────────────────────
base_dir = sys.argv[1]
sys.path.insert(0, base_dir)
os.chdir(base_dir)

os.environ["index_root"]  = os.path.join(base_dir, "voices")
os.environ["weight_root"] = os.path.join(base_dir, "voices")
os.environ["hubert_path"] = os.path.join(base_dir, "models", "hubert_base.pt")
os.environ["rmvpe_root"]  = os.path.join(base_dir, "models")

proto("INITIALIZING")
log("Cargando dependencias (torch, RVC, TTS)...")

try:
    from core.voice_manager import VoiceManager
    from core.tts_engine import TTSEngine
    from core.rvc_engine import RVCEngine
    from core.advanced_processor import AdvancedAudioProcessor
    from core.models import EdgeTTSConfig
    import soundfile as sf_w
    import numpy as np_w

    log("Inicializando componentes...")
    voice_manager = VoiceManager()
    edge_config   = EdgeTTSConfig()
    tts_engine    = TTSEngine(config=edge_config, provider_name="edge_tts")
    rvc_engine    = RVCEngine()
    processor     = AdvancedAudioProcessor(
        voice_manager=voice_manager,
        tts_engine=tts_engine,
        rvc_engine=rvc_engine,
    )

    log("Worker listo para procesar mensajes.")
    proto("READY")

    # ── Bucle principal ───────────────────────────────────────────────────────
    while True:
        raw = sys.stdin.readline()
        if not raw:
            log("stdin cerrado, saliendo.")
            break
        raw = raw.strip()
        if not raw:
            continue

        try:
            req         = json.loads(raw)
            text        = req["text"]
            output_file = req["output_file"]
        except Exception as parse_err:
            proto(f"ERROR|JSON invalido: {parse_err}")
            continue

        log(f"Procesando: {text[:60]}...")
        try:
            audio_data, sample_rate = processor.process_message(text)
            sf_w.write(output_file, audio_data, sample_rate)
            del audio_data
            gc.collect()
            log(f"OK → {output_file}")
            proto(f"SUCCESS|{output_file}")
        except Exception as proc_err:
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Sanitizar mensaje de error (no puede contener "|" sin escape)
            err_msg = str(proc_err).replace("|", ";").replace("\n", " ")
            proto(f"ERROR|{err_msg}")

except Exception as fatal_err:
    import traceback
    traceback.print_exc(file=sys.stderr)
    err_msg = str(fatal_err).replace("|", ";").replace("\n", " ")
    proto(f"FATAL|{err_msg}")
    sys.exit(1)
'''


class PersistentSubprocessProcessor:
    """
    Mantiene un subproceso Python vivo entre llamadas, con restart proactivo.

    Problema resuelto: después de ~25-30 conversiones RVC, el CUDA state del
    subprocess se degrada. Si crashea, puede corromper el contexto CUDA del
    proceso padre → access violation en threads nativos del padre.

    Solución: Restart PROACTIVO cada MAX_REQUESTS_PER_WORKER requests, ANTES
    de que el subprocess llegue a un estado degradado. Al mismo tiempo se
    pre-calienta el reemplazo en background para minimizar downtime.

    Ciclo de vida:
        request 1 → N-5:   subprocess activo, prewarm inicia en background al llegar a N-5
        request N:          swap al subprocess pre-calentado (si está listo) o espera
        request N+1 → 2N-5: segundo subprocess activo, tercero empieza a calentar
        ...

    Si el subprocess crashea inesperadamente → auto-restart (crash restart).
    Los crash-restarts se cuentan separadamente de los proactivos.
    """

    # ── Configuración ──────────────────────────────────────────────────────────
    # Restart proactivo cada N requests para evitar degradación CUDA.
    # Con 2 voces/request promedio: 15 requests ≈ 30 conversiones RVC
    # (el valor original max_conversions_before_restart era 5 en el mismo proceso)
    MAX_REQUESTS_PER_WORKER = 15

    # Pre-calentamiento: iniciar N requests antes del límite para poder hacer
    # swap instantáneo cuando se llegue al límite
    PREWARM_AHEAD   = 5      # iniciar prewarm cuando resten 5 requests
    STARTUP_TIMEOUT = 180    # segundos para que el worker cargue modelos
    REQUEST_TIMEOUT = 120    # segundos por mensaje
    MAX_CRASH_RESTARTS = 5   # crash-restarts máximos antes de rendirse

    def __init__(self, voice_manager=None):
        self.voice_manager = voice_manager
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self._lock = threading.Lock()   # un request a la vez

        # Worker activo
        self._process:     Optional[subprocess.Popen] = None
        self._proto_queue: queue.Queue                = queue.Queue()
        self._ready        = False
        self._req_count    = 0   # requests procesados en este subprocess

        # Worker pre-calentado (preparándose para relevar al activo)
        self._next_process:     Optional[subprocess.Popen] = None
        self._next_proto_queue: queue.Queue                = queue.Queue()
        self._next_ready        = threading.Event()   # se activa cuando READY
        self._prewarm_lock      = threading.Lock()    # evita pre-warms paralelos
        self._prewarming        = False

        # Conteo de crash-restarts
        self._crash_count = 0

    # ── Arranque de workers ────────────────────────────────────────────────────

    def _launch_process(self, proto_q: queue.Queue) -> subprocess.Popen:
        """
        Lanza un subproceso nuevo y arranca sus relay threads.
        Retorna el Popen inmediatamente (sin esperar READY).
        """
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        process = subprocess.Popen(
            [sys.executable, "-c", PERSISTENT_WORKER_SCRIPT, self.base_dir],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=1,
        )

        # Relay stdout → proto_q
        def stdout_relay():
            try:
                for raw in process.stdout:
                    try:
                        line = raw.decode("utf-8", errors="replace").rstrip("\n\r")
                    except Exception:
                        continue
                    if line.startswith(PROTO_PREFIX):
                        proto_q.put(line[len(PROTO_PREFIX):])
                    else:
                        if line:
                            _tprint(f"[Worker-log] {line}")
            except Exception:
                pass
            finally:
                proto_q.put("DIED|")

        # Relay stderr → stdout del padre (solo logs)
        def stderr_relay():
            try:
                for raw in process.stderr:
                    try:
                        line = raw.decode("utf-8", errors="replace").rstrip("\n\r")
                        if line:
                            _tprint(f"[Worker-err] {line}")
                    except Exception:
                        pass
            except Exception:
                pass

        threading.Thread(target=stdout_relay, daemon=True,
                         name=f"w{process.pid}-stdout").start()
        threading.Thread(target=stderr_relay, daemon=True,
                         name=f"w{process.pid}-stderr").start()

        return process

    def _wait_for_ready(self, process: subprocess.Popen,
                        proto_q: queue.Queue) -> bool:
        """
        Espera hasta que el subprocess envíe READY.
        Retorna True si listo, False si falló.
        """
        deadline = time.time() + self.STARTUP_TIMEOUT
        while time.time() < deadline:
            if process.poll() is not None:
                return False   # murió
            try:
                msg = proto_q.get(timeout=2.0)
            except queue.Empty:
                continue

            kind = msg.split("|", 1)[0]
            if kind == "READY":
                return True
            elif kind in ("FATAL", "DIED"):
                return False
            elif kind == "INITIALIZING":
                _tprint("[PersistentProcessor] Worker inicializando modelos...")
        return False   # timeout

    def _kill_process(self, process: Optional[subprocess.Popen]):
        """Mata un proceso de forma limpia."""
        if process is None:
            return
        try:
            if process.poll() is None:
                # Intento limpio: cerrar stdin
                try:
                    process.stdin.close()
                except Exception:
                    pass
                # Esperar brevemente
                try:
                    process.wait(timeout=3)
                except Exception:
                    pass
            # Forzar kill si sigue vivo
            if process.poll() is None:
                process.kill()
                try:
                    process.wait(timeout=3)
                except Exception:
                    pass
        except Exception:
            pass

    # ── Pre-calentamiento ──────────────────────────────────────────────────────

    def _start_prewarming(self):
        """
        Inicia el pre-calentamiento del próximo worker en background.
        Solo un pre-warm simultáneo (protegido por _prewarm_lock).
        """
        with self._prewarm_lock:
            if self._prewarming:
                return
            if self._next_process is not None:
                return   # ya hay uno listo
            self._prewarming = True

        pid_act = self._process.pid if self._process else "?"
        _tprint(f"[PersistentProcessor] Iniciando pre-calentamiento (worker actual PID {pid_act})...")

        def _warm():
            try:
                q = queue.Queue()
                p = self._launch_process(q)
                _tprint(f"[PersistentProcessor] Pre-warm PID {p.pid} arrancado, cargando modelos...")
                ok = self._wait_for_ready(p, q)
                if ok:
                    self._next_process     = p
                    self._next_proto_queue = q
                    self._next_ready.set()
                    _tprint(f"[PersistentProcessor] Pre-warm PID {p.pid} LISTO.")
                else:
                    _tprint(f"[PersistentProcessor] Pre-warm falló, se tratará de nuevo cuando haga falta.")
                    self._kill_process(p)
            finally:
                with self._prewarm_lock:
                    self._prewarming = False

        threading.Thread(target=_warm, daemon=True, name="prewarm").start()

    # ── Swap / Ensure ──────────────────────────────────────────────────────────

    def _swap_to_next_worker(self):
        """
        Rota al worker pre-calentado.
        Si el pre-warm no terminó, espera (máx STARTUP_TIMEOUT).
        """
        _tprint("[PersistentProcessor] Rotando a worker pre-calentado...")

        # Si no hay next_process, arrancar prewarm ahora y esperar
        if self._next_process is None:
            _tprint("[PersistentProcessor] No había pre-warm listo — arrancando y esperando...")
            self._next_ready.clear()
            q = queue.Queue()
            p = self._launch_process(q)
            if self._wait_for_ready(p, q):
                self._next_process     = p
                self._next_proto_queue = q
                self._next_ready.set()
            else:
                self._kill_process(p)
                raise RuntimeError("No se pudo arrancar next worker para el swap")
        else:
            # Esperar hasta que esté listo (puede estar en proceso de loading)
            if not self._next_ready.is_set():
                _tprint("[PersistentProcessor] Esperando que pre-warm termine...")
                self._next_ready.wait(timeout=self.STARTUP_TIMEOUT)
                if not self._next_ready.is_set():
                    raise RuntimeError("Pre-warm tardó demasiado")

        # Matar worker viejo
        old = self._process
        _tprint(f"[PersistentProcessor] Matando worker viejo (PID {old.pid if old else '?'})...")
        self._kill_process(old)

        # Promover next → current
        self._process     = self._next_process
        self._proto_queue = self._next_proto_queue
        self._ready       = True
        self._req_count   = 0

        # Limpiar estado next
        self._next_process     = None
        self._next_proto_queue = queue.Queue()
        self._next_ready.clear()

        _tprint(f"[PersistentProcessor] Swap completado. Nuevo worker PID {self._process.pid}.")

    def _ensure_worker(self):
        """
        Garantiza que hay un worker vivo y listo.
        Lógica:
          1. Si activo y sano → decidir si hay que hacer swap proactivo
          2. Si muerto → crash-restart
        """
        alive = (self._process is not None and
                 self._process.poll() is None and
                 self._ready)

        if alive:
            # ¿Hay que iniciar pre-warm?
            remaining = self.MAX_REQUESTS_PER_WORKER - self._req_count
            if (remaining <= self.PREWARM_AHEAD
                    and not self._prewarming
                    and self._next_process is None):
                self._start_prewarming()

            # ¿Llegamos al límite? → swap
            if self._req_count >= self.MAX_REQUESTS_PER_WORKER:
                _tprint(f"[PersistentProcessor] Límite proactivo alcanzado "
                      f"({self._req_count} requests). Rotando subprocess...")
                self._swap_to_next_worker()
            return

        # Worker muerto → crash restart
        self._ready = False
        self._crash_count += 1
        if self._crash_count > self.MAX_CRASH_RESTARTS:
            raise RuntimeError(
                f"Worker crasheó {self._crash_count} veces consecutivas. Abortando."
            )

        _tprint(f"[PersistentProcessor] Worker muerto. Crash-restart #{self._crash_count}...")

        # Intentar usar el pre-calentado si está listo
        if self._next_process is not None and self._next_ready.is_set():
            _tprint("[PersistentProcessor] Usando worker pre-calentado para crash recovery.")
            self._process     = self._next_process
            self._proto_queue = self._next_proto_queue
            self._ready       = True
            self._req_count   = 0
            self._next_process     = None
            self._next_proto_queue = queue.Queue()
            self._next_ready.clear()
            return

        # Arranque frío
        q = queue.Queue()
        p = self._launch_process(q)
        _tprint(f"[PersistentProcessor] Esperando arranque frío (PID {p.pid})...")
        if not self._wait_for_ready(p, q):
            self._kill_process(p)
            raise RuntimeError("Worker no arrancó tras crash-restart")

        self._process     = p
        self._proto_queue = q
        self._ready       = True
        self._req_count   = 0

    # ── API Pública ────────────────────────────────────────────────────────────

    def process_message(self, message: str) -> Tuple[np.ndarray, int]:
        """
        Procesa un mensaje multi-voz en el subprocess persistente.

        Primera llamada: espera READY (~30-60s para cargar modelos).
        Llamadas posteriores: sólo TTS + RVC (~3-8s).
        Cada MAX_REQUESTS_PER_WORKER requests, el subprocess se rota de forma
        limpia para evitar degradación CUDA (crash del proceso padre).
        Si crashea inesperadamente, se reinicia automáticamente.

        Returns:
            (audio_data, sample_rate)
        """
        with self._lock:
            self._ensure_worker()

            fd, output_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

            try:
                # Enviar request al worker
                req_json = json.dumps({"text": message, "output_file": output_path}) + "\n"
                self._process.stdin.write(req_json.encode("utf-8"))
                self._process.stdin.flush()

                # Esperar respuesta de protocolo
                deadline = time.time() + self.REQUEST_TIMEOUT
                while time.time() < deadline:
                    if self._process.poll() is not None:
                        self._ready = False
                        raise RuntimeError("Worker crasheó durante el procesamiento")

                    try:
                        msg = self._proto_queue.get(timeout=2.0)
                    except queue.Empty:
                        continue

                    kind, *rest = msg.split("|", 1)
                    payload = rest[0] if rest else ""

                    if kind == "SUCCESS":
                        audio_data, sample_rate = sf.read(output_path, dtype="float32")
                        dur = len(audio_data) / sample_rate
                        self._req_count += 1
                        # Reset crash counter en éxito
                        self._crash_count = 0
                        _tprint(f"[PersistentProcessor] Audio: {dur:.2f}s "
                              f"(req #{self._req_count}/{self.MAX_REQUESTS_PER_WORKER} "
                              f"en worker PID {self._process.pid})")
                        return (audio_data, sample_rate)

                    elif kind == "ERROR":
                        raise RuntimeError(f"Worker error: {payload}")

                    elif kind == "DIED":
                        self._ready = False
                        raise RuntimeError("Worker subprocess murió durante el procesamiento")

                raise TimeoutError(f"Request no completado en {self.REQUEST_TIMEOUT}s")

            except (RuntimeError, TimeoutError):
                self._ready = False
                raise

            finally:
                try:
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                except Exception:
                    pass

    def shutdown(self):
        """Apaga todos los workers de forma limpia."""
        self._kill_process(self._process)
        self._kill_process(self._next_process)
        self._process      = None
        self._next_process = None
        self._ready        = False
        _tprint("[PersistentProcessor] Shutdown completado.")

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass

