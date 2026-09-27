"""
Mixin para reproducción de audio (TTS + RVC).
Contiene los métodos principales de síntesis y reproducción.
"""
import queue
import threading
import time
import collections

from core.overlay_manager import get_overlay_manager

# ── Reintento automático de mensajes que fallaron por completo ────────────
# Mismo mecanismo que en core/audio_queue.py, adaptado a la cola multi-voz
# (que solo transporta el texto, sin tupla). Si un mensaje falla en
# absolutamente todo (TTS+RVC de todas las voces del mensaje), en vez de
# perderlo se guarda en un backlog para reintentarlo automáticamente
# cuando el corte se recupere, sin bloquear ni perder los mensajes nuevos.
_MV_MAX_PENDING_MESSAGES = 30          # tope del backlog; si se excede se descarta el más viejo
_MV_MAX_PENDING_ATTEMPTS = 5           # reintentos máximos para un mismo mensaje pendiente
_MV_PENDING_RETRY_COOLDOWN_SECONDS = 15.0  # tiempo mínimo entre reintentos de pendientes
_MV_QUEUE_POLL_TIMEOUT_SECONDS = 5.0   # el worker despierta periódicamente para revisar pendientes


class PlaybackMixin:
    """Mixin para reproducción de audio"""

    # ── Cola multi-voz ────────────────────────────────────────────────────────

    def _get_mv_queue(self) -> queue.Queue:
        """
        Devuelve la cola multi-voz. Si aún no existe, la crea junto con
        su worker thread (arranca una sola vez, daemon=True).
        """
        self._ensure_mv_reload_guard()
        if not hasattr(self, '_mv_queue') or self._mv_queue is None:
            self._mv_queue: queue.Queue = queue.Queue()
            t = threading.Thread(target=self._mv_worker_loop, daemon=True)
            t.start()
        return self._mv_queue

    def _ensure_mv_reload_guard(self):
        """
        Crea (de forma perezosa e idempotente, igual que la cola multi-voz)
        el flag/lock que coordinan la recarga en caliente del motor TTS con
        este worker. Así existen aunque el pipeline multi-voz nunca se haya
        usado todavía.
        """
        if not hasattr(self, '_mv_processing'):
            self._mv_processing = False
        if not hasattr(self, '_mv_reload_guard'):
            self._mv_reload_guard = threading.Lock()
        # Backlog de mensajes que fallaron por completo y esperan a que el
        # corte se recupere para reintentarse automáticamente.
        if not hasattr(self, '_mv_pending_messages'):
            self._mv_pending_messages = collections.deque()
        # Protege TODO acceso a `_mv_pending_messages` / `_mv_pending_generation`.
        # Hoy nada limpia este backlog desde otro hilo, pero se protege igual
        # (mismo patrón que core/audio_queue.py) para que una futura función de
        # "limpiar cola multi-voz" no reintroduzca la misma condición de
        # carrera ya corregida allá.
        if not hasattr(self, '_mv_pending_lock'):
            self._mv_pending_lock = threading.Lock()
        if not hasattr(self, '_mv_pending_generation'):
            self._mv_pending_generation = 0
        if not hasattr(self, '_mv_last_pending_attempt_at'):
            self._mv_last_pending_attempt_at = 0.0

    def is_mv_idle(self) -> bool:
        """
        Retorna True si el pipeline multi-voz está inactivo (o si nunca se
        ha usado). Chequeo rápido y NO atómico -- usado por la recarga en
        caliente del motor TTS junto con `_mv_reload_guard` para exclusión
        mutua real.
        """
        if not hasattr(self, '_mv_queue') or self._mv_queue is None:
            return True
        return (self._mv_queue.empty() and not getattr(self, '_mv_processing', False)
                and len(getattr(self, '_mv_pending_messages', ())) == 0)

    def get_mv_pending_count(self) -> int:
        """
        Retorna cuántos mensajes multi-voz hay en el backlog de reintentos
        pendientes (mensajes que fallaron por completo y esperan a que el
        corte se recupere). No incluye lo que haya en self._mv_queue.
        """
        return len(getattr(self, '_mv_pending_messages', ()))

    def _mv_worker_loop(self):
        """
        Worker único que procesa mensajes multi-voz en orden FIFO.
        Corre en un daemon thread → la GUI nunca se bloquea.

        Usa `queue.get(timeout=...)` para despertar periódicamente aunque
        no llegue ningún mensaje nuevo, y así poder reintentar mensajes del
        backlog de pendientes (ver `_maybe_retry_one_mv_pending`).
        """
        import sounddevice as sd
        import core.audio_player as player

        while True:
            try:
                text = self._mv_queue.get(timeout=_MV_QUEUE_POLL_TIMEOUT_SECONDS)
            except queue.Empty:
                # Nada nuevo llegó -- aprovechar para revisar si toca
                # reintentar algún mensaje pendiente del backlog. Envuelto en
                # try/except para que un bug en la gestión de pendientes
                # nunca pueda matar este hilo de worker.
                try:
                    self._maybe_retry_one_mv_pending()
                except Exception as e:
                    print(f"[Multi-Voz] Error inesperado revisando pendientes (se ignora este ciclo): {e}")
                continue

            if text is None:  # señal de cierre
                break

            try:
                self._run_mv_with_guard(text, sd, player)
            except Exception as e:
                try:
                    self._enqueue_mv_pending(text, e)
                except Exception as e2:
                    print(f"[Multi-Voz] Error inesperado encolando mensaje pendiente (se pierde este mensaje): {e2}")
            finally:
                self._mv_queue.task_done()

            try:
                self._maybe_retry_one_mv_pending()
            except Exception as e:
                print(f"[Multi-Voz] Error inesperado revisando pendientes (se ignora este ciclo): {e}")

    def _process_mv_text(self, text, sd, player):
        """
        Procesa un único mensaje multi-voz: TTS+RVC (potencialmente varias
        voces) + reproducción con timeline de avatares. No maneja el guard
        de recarga ni la bandera `_mv_processing` -- eso lo hace
        `_run_mv_with_guard`, que envuelve tanto un mensaje nuevo como uno
        reintentado desde el backlog de pendientes con el mismo mecanismo.

        Si algo falla, se re-lanza la excepción (después de la limpieza de
        overlay) para que el llamador decida si el mensaje debe quedar en
        el backlog de reintentos automáticos.
        """
        try:
            audio_data, sample_rate, avatar_timeline = \
                self.advanced_processor.process_message(text, return_timeline=True)

            # Aplicar volumen global
            vol = getattr(player, '_volume', 1.0)
            if vol != 1.0:
                audio_data = audio_data * vol

            overlay_mgr = get_overlay_manager()
            overlay_mgr.show(text, "Multi-Voz (GUI)", is_nopolo=True)

            sd.play(audio_data, sample_rate)
            play_start = time.time()

            # Hilo de avatares: recorre el timeline y dispara eventos
            if avatar_timeline:
                def _drive_avatars(timeline=avatar_timeline,
                                   t0=play_start,
                                   mgr=overlay_mgr):
                    for entry in timeline:
                        profile    = entry['profile']
                        start_sec  = entry['start_sec']
                        peaks      = entry['peaks']
                        is_sound   = entry.get('is_sound', False)

                        # Esperar al inicio de este segmento
                        wait = start_sec - (time.time() - t0)
                        if wait > 0:
                            time.sleep(wait)

                        if is_sound:
                            # Segmento de sonido: ocultar personaje y mostrar 🔊
                            mgr.avatar_change('🔊', None, None, sound_indicator=True)
                        else:
                            # Cambiar personaje
                            img_idle    = None
                            img_talking = None
                            if profile and profile.rvc_config:
                                img_idle    = profile.rvc_config.image_idle
                                img_talking = profile.rvc_config.image_talking
                            mgr.avatar_change(
                                profile.display_name if profile else '',
                                img_idle,
                                img_talking,
                            )

                            # Disparar peaks del segmento
                            for offset_sec, is_talking in peaks:
                                target_t = t0 + start_sec + offset_sec
                                sleep_t  = target_t - time.time()
                                if sleep_t > 0.005:
                                    time.sleep(sleep_t)
                                mgr.avatar_peak(is_talking)

                    mgr.avatar_peak(False)

                threading.Thread(target=_drive_avatars, daemon=True).start()

            sd.wait()

            overlay_mgr.hide()

        except Exception as e:
            print(f"Error en multi-voz: {e}")
            import traceback
            traceback.print_exc()
            # Re-lanzar para que el llamador (_run_mv_with_guard / worker)
            # decida si este mensaje debe quedar en el backlog de reintentos.
            raise

    def _run_mv_with_guard(self, text, sd, player):
        """
        Envuelve `_process_mv_text` con el mismo acquire/release de
        `_mv_reload_guard` y la misma bandera `_mv_processing` que antes
        vivían directamente en `_mv_worker_loop`. Se usa tanto para un
        mensaje recién sacado de la cola como para un reintento de un
        mensaje pendiente, de modo que la recarga en caliente del motor
        TTS siga teniendo exclusión mutua real sobre el 100% del
        procesamiento TTS/RVC, sin importar de dónde vino el mensaje.

        Solo se llama desde el hilo único del worker multi-voz, nunca de
        forma concurrente consigo mismo, así que un acquire bloqueante es
        seguro.
        """
        self._mv_reload_guard.acquire()
        self._mv_processing = True
        try:
            self._process_mv_text(text, sd, player)
        finally:
            self._mv_processing = False
            self._mv_reload_guard.release()

    def _enqueue_mv_pending(self, text, error):
        """
        Guarda un mensaje multi-voz que falló por completo en el backlog de
        reintentos automáticos, para que no se pierda y se reintente solo
        cuando el corte se recupere.

        Todo el acceso al deque va bajo `_mv_pending_lock` (mismo patrón que
        core/audio_queue.py), por si en el futuro algo llega a limpiar este
        backlog desde otro hilo.
        """
        with self._mv_pending_lock:
            if len(self._mv_pending_messages) >= _MV_MAX_PENDING_MESSAGES:
                dropped = self._mv_pending_messages.popleft()
                print(
                    f"[Multi-Voz] Backlog de pendientes lleno ({_MV_MAX_PENDING_MESSAGES}); "
                    f"se descarta el más antiguo: \"{dropped['text'][:60]}\"; "
                    f"quedan {len(self._mv_pending_messages)} en backlog"
                )
            self._mv_pending_messages.append({'text': text, 'attempts': 0})
            pending_count = len(self._mv_pending_messages)
        print(
            f"[Multi-Voz] Mensaje falló por completo ({error}); "
            f"se encola para reintento automático: \"{text[:60]}\" "
            f"(pendientes en backlog: {pending_count})"
        )

    def _maybe_retry_one_mv_pending(self):
        """
        Si hay mensajes multi-voz pendientes y ya pasó el cooldown desde el
        último intento, reintenta UNO solo (no todos de una vez), para no
        convertir un corte sostenido en un bucle de reintentos apretado que
        satura el servicio caído y le roba tiempo a los mensajes nuevos.

        El chequeo-y-pop va bajo `_mv_pending_lock` (mismo patrón que
        core/audio_queue.py) para que sea atómico frente a cualquier acceso
        concurrente al backlog, y se recuerda la "generación" del backlog al
        sacar la entrada para no reencolarla si algo la limpió mientras se
        reintentaba.

        IMPORTANTE: solo debe llamarse desde `_mv_worker_loop()` en los
        puntos donde el `_run_mv_with_guard()` anterior ya retornó/lanzó y
        su `finally` ya liberó el guard -- nunca desde dentro de
        `_process_mv_text` o `_run_mv_with_guard` mismos.
        """
        now = time.monotonic()
        with self._mv_pending_lock:
            if not self._mv_pending_messages:
                return
            if now - self._mv_last_pending_attempt_at < _MV_PENDING_RETRY_COOLDOWN_SECONDS:
                return
            self._mv_last_pending_attempt_at = now
            entry = self._mv_pending_messages.popleft()
            generation = self._mv_pending_generation

        entry['attempts'] += 1
        text = entry['text']
        print(
            f"[Multi-Voz] Reintentando mensaje pendiente (intento "
            f"{entry['attempts']}/{_MV_MAX_PENDING_ATTEMPTS}): \"{text[:60]}\""
        )
        import sounddevice as sd
        import core.audio_player as player
        try:
            self._run_mv_with_guard(text, sd, player)
        except Exception as e:
            if entry['attempts'] >= _MV_MAX_PENDING_ATTEMPTS:
                print(
                    f"[Multi-Voz] Mensaje pendiente descartado definitivamente "
                    f"tras {entry['attempts']} intentos: \"{text[:60]}\" ({e})"
                )
                return
            with self._mv_pending_lock:
                if self._mv_pending_generation == generation:
                    # Se reencola al final para darle su turno a otros pendientes.
                    self._mv_pending_messages.append(entry)
                else:
                    print(
                        f"[Multi-Voz] Mensaje pendiente descartado: el backlog "
                        f"fue limpiado mientras se reintentaba: \"{text[:60]}\""
                    )
        else:
            print(f"[Multi-Voz] Mensaje pendiente recuperado con éxito: \"{text[:60]}\"")

    # ── Punto de entrada principal ────────────────────────────────────────────

    def play_text(self):
        """Reproduce el texto con la voz seleccionada o modo multi-voz"""
        text = self.input.text().strip()
        if not text:
            return

        if self.multivoice_check.isChecked():
            # Modo multi-voz: encolar sin bloquear la GUI
            mv_q = self._get_mv_queue()
            mv_q.put(text)
            pending = mv_q.qsize()
            if pending > 1:
                self.log_to_console(f"[Cola multi-voz] {pending} mensajes pendientes")
        else:
            # Modo normal: audio_queue ya es no bloqueante
            profile_id = self.voice_combo.currentData()
            profile = self.voice_manager.get_profile(profile_id)
            voice_name = profile.display_name if profile else ""
            self.audio_queue.add(text, profile, voice_name, self, author=None)

    def _play_multivoice(self, text: str):
        """Mantener por compatibilidad — delega en la cola."""
        self._get_mv_queue().put(text)
