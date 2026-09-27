import threading
import queue
import gc
import collections
import time
from typing import Optional
from .tts_engine import TTSEngine
from .rvc_engine import RVCEngine
from .audio_player import play_wav, play_wav_with_peaks, stop_audio
from .models import VoiceProfile
from .overlay_manager import get_overlay_manager

# ── Reintento automático de mensajes que fallaron por completo ────────────
# Si un mensaje falla en absolutamente todo (Google/Azure + refresh + Edge,
# ver TTSEngine._synthesize_with_resilience), en vez de perderlo se guarda
# en un backlog de pendientes para reintentarlo automáticamente cuando el
# corte se recupere, sin bloquear ni perder los mensajes nuevos que sigan
# llegando mientras tanto.
_MAX_PENDING_MESSAGES = 30          # tope del backlog; si se excede se descarta el más viejo
_MAX_PENDING_ATTEMPTS = 5           # reintentos máximos para un mismo mensaje pendiente
_PENDING_RETRY_COOLDOWN_SECONDS = 15.0  # tiempo mínimo entre reintentos de pendientes
_QUEUE_POLL_TIMEOUT_SECONDS = 5.0   # el worker despierta periódicamente para revisar pendientes


class AudioQueue:
    """
    Cola de procesamiento de audio con soporte para voces configurables.
    """

    def __init__(self, tts_engine: TTSEngine, rvc_engine: RVCEngine):
        self.tts_engine = tts_engine
        self.rvc_engine = rvc_engine
        self.queue = queue.Queue()
        self._processing = False
        # Lock que el worker mantiene mientras procesa un ítem. La recarga
        # en caliente del motor TTS lo adquiere (no bloqueante) para tener
        # exclusión mutua REAL con el worker -- no solo un chequeo de
        # is_idle() puntual (TOCTOU) -- durante toda la recarga.
        self._reload_guard = threading.Lock()
        # Backlog de mensajes que fallaron por completo (ver
        # _enqueue_pending / _maybe_retry_one_pending) y esperan a que el
        # corte se recupere para reintentarse automáticamente.
        # `_pending_lock` protege TODO acceso a `_pending_messages` /
        # `_pending_generation`, porque `clear_queue()` puede ser llamado
        # desde otro hilo (p.ej. el hilo de uvicorn en api/rest_server.py)
        # mientras el worker está leyendo/escribiendo el mismo deque.
        self._pending_messages = collections.deque()
        self._pending_lock = threading.Lock()
        # Se incrementa cada vez que clear_queue() vacía el backlog. Un
        # reintento en curso lo captura al sacar su entrada del deque; si al
        # terminar el número cambió, significa que el usuario pidió limpiar
        # la cola mientras ese mensaje se reintentaba, así que no se
        # reencola (ver _maybe_retry_one_pending).
        self._pending_generation = 0
        self._last_pending_attempt_at = 0.0
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        print("Cola de audio iniciada")
    
    def add(self, text: str, voice_profile: Optional[VoiceProfile] = None, voice_name: str = "", main_window=None, author: str = None):
        """
        Agrega texto a la cola para procesamiento.
        
        Args:
            text: Texto a sintetizar
            voice_profile: Perfil de voz a usar (opcional)
            voice_name: Nombre de la voz para el overlay
            main_window: Referencia a la ventana principal para enviar eventos overlay
            author: Nombre del usuario que envió el mensaje (opcional, se muestra en overlay)
        """
        self.queue.put((text, voice_profile, voice_name, main_window, author))
    
    def stop_current(self):
        """Detiene el audio que está sonando actualmente"""
        stop_audio()
    
    def skip_to_next(self):
        """Salta al siguiente en la cola (detiene el actual)"""
        stop_audio()
    
    def clear_queue(self):
        """Limpia toda la cola de audios pendientes"""
        # Vaciar la cola
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except queue.Empty:
                break
        # Vaciar también el backlog de reintentos pendientes, para que un
        # "limpiar cola" explícito del usuario no deje mensajes fallidos
        # viejos esperando para reproducirse sorpresivamente minutos después.
        # Bajo el mismo lock que _enqueue_pending/_maybe_retry_one_pending
        # usan, para que esto sea atómico frente al worker thread (que corre
        # en un hilo distinto de quien llama a clear_queue(), p.ej. el hilo
        # de uvicorn en api/rest_server.py). El generation++ hace que un
        # reintento que ya estaba en curso al momento del clear no se
        # reencole cuando termine (ver _maybe_retry_one_pending).
        with self._pending_lock:
            self._pending_messages.clear()
            self._pending_generation += 1
        # Detener el actual
        stop_audio()

    def get_queue_size(self):
        """Retorna el número de items en la cola"""
        return self.queue.qsize()

    def get_pending_count(self) -> int:
        """
        Retorna cuántos mensajes hay en el backlog de reintentos pendientes
        (mensajes que fallaron por completo y esperan a que el corte se
        recupere). No incluye lo que haya en self.queue.
        """
        return len(self._pending_messages)

    def is_idle(self) -> bool:
        """
        Retorna True si la cola está vacía, no hay nada procesándose ahora
        mismo y tampoco quedan mensajes en el backlog de reintentos
        pendientes. Es un chequeo rápido y NO atómico (puede haber un ítem
        nuevo justo después) -- para exclusión mutua real (p.ej. antes de
        una recarga en caliente) hay que adquirir además `_reload_guard`.
        """
        return (self.queue.empty() and not self._processing
                and len(self._pending_messages) == 0)

    def _process_queued_item(self, text, voice_profile, voice_name, main_window, author):
        """
        Procesa un único ítem: TTS + RVC + reproducción. No maneja el guard
        de recarga ni la bandera `_processing` -- eso lo hace
        `_run_with_guard`, que envuelve tanto un mensaje nuevo como uno
        reintentado desde el backlog de pendientes con el mismo mecanismo.

        Si algo falla, se re-lanza la excepción (después de la limpieza de
        overlay/GC) para que el llamador decida si el mensaje debe quedar
        en el backlog de reintentos automáticos.
        """
        try:
            # Si viene author, usarlo en lugar del nombre de voz
            display_name = author if author else voice_name
            print(f"[Audio Queue] Procesando modo normal con voz: {display_name}")

            # Obtener imágenes del avatar si el perfil tiene RVC configurado
            _img_idle    = None
            _img_talking = None
            if voice_profile and voice_profile.rvc_config:
                _img_idle    = voice_profile.rvc_config.image_idle
                _img_talking = voice_profile.rvc_config.image_talking

            # ── Protección GC ─────────────────────────────────────────────
            # Desactivar GC durante las operaciones nativas (TTS/RVC).
            # Evita que el recolector de Python dispare finalizadores de
            # objetos nativos (gRPC, PyTorch, FAISS) en mal momento,
            # reduciendo la frecuencia de heap corruption (0xc0000374).
            gc.disable()
            try:
                # Paso 1: TTS (voz neutral)
                if voice_profile and voice_profile.tts_config:
                    # update_config puede crear un nuevo provider (ej. Google TTS).
                    # El lock en TTSEngine serializa la inicialización de gRPC.
                    self.tts_engine.update_config(voice_profile.tts_config)

                neutral_wav = self.tts_engine.synthesize(text)

                # Paso 2: RVC (transformación opcional)
                if voice_profile and voice_profile.is_transformer_voice():
                    # Cargar modelo si es diferente
                    if (not self.rvc_engine.model_loaded or
                        self.rvc_engine.config.model_id != voice_profile.rvc_config.model_id):
                        self.rvc_engine.load_model(voice_profile.rvc_config)

                    # Usar el nuevo método con recuperación automática
                    try:
                        converted_wav = self.rvc_engine.convert_with_recovery(neutral_wav)
                    except Exception as e:
                        print(f"Error crítico en RVC después de reintentos: {e}")
                        # Como último recurso, usar el audio original sin transformación
                        import scipy.io.wavfile as wavfile
                        rate, data = wavfile.read(neutral_wav)
                        converted_wav = (data.astype('float32') / 32768.0, rate)
                        print("Usando audio original sin transformación RVC")
                else:
                    # Sin transformación, leer el WAV generado
                    import scipy.io.wavfile as wavfile
                    rate, data = wavfile.read(neutral_wav)
                    converted_wav = (data.astype('float32') / 32768.0, rate)
                    import os
                    os.unlink(neutral_wav)  # Limpiar temporal

            finally:
                # Re-activar GC y hacer collect mientras no hay operaciones nativas
                gc.enable()
                gc.collect()
            # ── Fin protección GC ──────────────────────────────────────────

            # Paso 3: Reproducir (con detección de peaks para avatar)
            # overlay.show() y overlay.hide() se pasan como callbacks para
            # que ocurran DENTRO del _playback_lock → sin race conditions
            # cuando AudioQueue y el worker multi-voz están activos a la vez.
            _overlay = get_overlay_manager()
            _text_snap    = text
            _name_snap    = display_name
            _idle_snap    = _img_idle
            _talking_snap = _img_talking

            def _on_before():
                _overlay.show(_text_snap, _name_snap, is_nopolo=False,
                              image_idle=_idle_snap, image_talking=_talking_snap)

            def _on_after():
                _overlay.hide()

            _has_avatar = bool(
                voice_profile and voice_profile.rvc_config
                and (voice_profile.rvc_config.image_idle
                     or voice_profile.rvc_config.image_talking)
            )
            if _has_avatar:
                def _on_peak(talking: bool):
                    get_overlay_manager().avatar_peak(talking)
                play_wav_with_peaks(converted_wav, on_peak=_on_peak,
                                    on_before_play=_on_before,
                                    on_after_play=_on_after)
            else:
                play_wav(converted_wav,
                         on_before_play=_on_before,
                         on_after_play=_on_after)

        except Exception as e:
            print(f"Error en cola de audio: {e}")
            import traceback
            traceback.print_exc()
            try:
                get_overlay_manager().hide()
            except Exception:
                pass
            # Re-activar GC si quedó desactivado por un crash
            if not gc.isenabled():
                gc.enable()
            # Re-lanzar para que el llamador (_run_with_guard / _worker)
            # decida si este mensaje debe quedar en el backlog de reintentos.
            raise

    def _run_with_guard(self, text, voice_profile, voice_name, main_window, author):
        """
        Envuelve `_process_queued_item` con el mismo acquire/release de
        `_reload_guard` y la misma bandera `_processing` que antes vivían
        directamente en `_worker`. Se usa tanto para un mensaje recién
        sacado de la cola como para un reintento de un mensaje pendiente,
        de modo que la recarga en caliente del motor TTS siga teniendo
        exclusión mutua real sobre el 100% del procesamiento TTS/RVC, sin
        importar de dónde vino el mensaje.

        Solo se llama desde el hilo único del worker, nunca de forma
        concurrente consigo mismo, así que un acquire bloqueante es seguro.
        """
        self._reload_guard.acquire()
        self._processing = True
        try:
            self._process_queued_item(text, voice_profile, voice_name, main_window, author)
        finally:
            self._processing = False
            self._reload_guard.release()

    def _enqueue_pending(self, text, voice_profile, voice_name, main_window, author, error):
        """
        Guarda un mensaje que falló por completo (Google/Azure + refresh +
        Edge, ver TTSEngine) en el backlog de reintentos automáticos, para
        que no se pierda y se reintente solo cuando el corte se recupere.

        Todo el acceso al deque va bajo `_pending_lock`: `clear_queue()`
        puede correr en otro hilo (p.ej. el hilo de uvicorn) al mismo
        tiempo que este worker thread.
        """
        with self._pending_lock:
            if len(self._pending_messages) >= _MAX_PENDING_MESSAGES:
                dropped = self._pending_messages.popleft()
                dropped_text = dropped['item'][0]
                print(
                    f"[Audio Queue] Backlog de pendientes lleno ({_MAX_PENDING_MESSAGES}); "
                    f"se descarta el más antiguo: \"{dropped_text[:60]}\"; "
                    f"quedan {len(self._pending_messages)} en backlog"
                )
            self._pending_messages.append({
                'item': (text, voice_profile, voice_name, main_window, author),
                'attempts': 0,
            })
            pending_count = len(self._pending_messages)
        print(
            f"[Audio Queue] Mensaje falló por completo ({error}); "
            f"se encola para reintento automático: \"{text[:60]}\" "
            f"(pendientes en backlog: {pending_count})"
        )

    def _maybe_retry_one_pending(self):
        """
        Si hay mensajes pendientes y ya pasó el cooldown desde el último
        intento, reintenta UNO solo (no todos de una vez), para no convertir
        un corte sostenido en un bucle de reintentos apretado que satura el
        servicio caído y le roba tiempo a los mensajes nuevos.

        El chequeo-y-pop del backlog va bajo `_pending_lock` para que sea
        atómico frente a `clear_queue()` (otro hilo). Se recuerda además la
        "generación" del backlog al sacar la entrada: si `clear_queue()`
        limpió el backlog mientras este mensaje se reintentaba, la
        generación habrá cambiado y no se reencola aunque el reintento haya
        fallado -- honra un "limpiar cola" explícito del usuario.

        IMPORTANTE: solo debe llamarse desde `_worker()` en los puntos donde
        el `_run_with_guard()` anterior ya retornó/lanzó y su `finally` ya
        liberó el guard -- nunca desde dentro de `_process_queued_item` o
        `_run_with_guard` mismos.
        """
        now = time.monotonic()
        with self._pending_lock:
            if not self._pending_messages:
                return
            if now - self._last_pending_attempt_at < _PENDING_RETRY_COOLDOWN_SECONDS:
                return
            self._last_pending_attempt_at = now
            entry = self._pending_messages.popleft()
            generation = self._pending_generation

        entry['attempts'] += 1
        text, voice_profile, voice_name, main_window, author = entry['item']
        print(
            f"[Audio Queue] Reintentando mensaje pendiente (intento "
            f"{entry['attempts']}/{_MAX_PENDING_ATTEMPTS}): \"{text[:60]}\""
        )
        try:
            self._run_with_guard(text, voice_profile, voice_name, main_window, author)
        except Exception as e:
            if entry['attempts'] >= _MAX_PENDING_ATTEMPTS:
                print(
                    f"[Audio Queue] Mensaje pendiente descartado definitivamente "
                    f"tras {entry['attempts']} intentos: \"{text[:60]}\" ({e})"
                )
                return
            with self._pending_lock:
                if self._pending_generation == generation:
                    # Se reencola al final para darle su turno a otros pendientes.
                    self._pending_messages.append(entry)
                else:
                    print(
                        f"[Audio Queue] Mensaje pendiente descartado: la cola "
                        f"fue limpiada mientras se reintentaba: \"{text[:60]}\""
                    )
        else:
            print(f"[Audio Queue] Mensaje pendiente recuperado con éxito: \"{text[:60]}\"")

    def _worker(self):
        """Worker thread que procesa la cola"""
        while True:
            try:
                text, voice_profile, voice_name, main_window, author = \
                    self.queue.get(timeout=_QUEUE_POLL_TIMEOUT_SECONDS)
            except queue.Empty:
                # Nada nuevo llegó -- aprovechar para revisar si toca
                # reintentar algún mensaje pendiente del backlog. Envuelto
                # en try/except para que un bug en la gestión de pendientes
                # nunca pueda matar este hilo de worker (solo se pierde ese
                # ciclo de reintento).
                try:
                    self._maybe_retry_one_pending()
                except Exception as e:
                    print(f"[Audio Queue] Error inesperado revisando pendientes (se ignora este ciclo): {e}")
                continue

            try:
                self._run_with_guard(text, voice_profile, voice_name, main_window, author)
            except Exception as e:
                try:
                    self._enqueue_pending(text, voice_profile, voice_name, main_window, author, e)
                except Exception as e2:
                    print(f"[Audio Queue] Error inesperado encolando mensaje pendiente (se pierde este mensaje): {e2}")
            finally:
                self.queue.task_done()

            try:
                self._maybe_retry_one_pending()
            except Exception as e:
                print(f"[Audio Queue] Error inesperado revisando pendientes (se ignora este ciclo): {e}")