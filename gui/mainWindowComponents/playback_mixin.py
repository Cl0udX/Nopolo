"""
Mixin para reproducción de audio (TTS + RVC).
Contiene los métodos principales de síntesis y reproducción.
"""
import queue
import threading

from core.overlay_manager import get_overlay_manager


class PlaybackMixin:
    """Mixin para reproducción de audio"""

    # ── Cola multi-voz ────────────────────────────────────────────────────────

    def _get_mv_queue(self) -> queue.Queue:
        """
        Devuelve la cola multi-voz. Si aún no existe, la crea junto con
        su worker thread (arranca una sola vez, daemon=True).
        """
        if not hasattr(self, '_mv_queue') or self._mv_queue is None:
            self._mv_queue: queue.Queue = queue.Queue()
            t = threading.Thread(target=self._mv_worker_loop, daemon=True)
            t.start()
        return self._mv_queue

    def _mv_worker_loop(self):
        """
        Worker único que procesa mensajes multi-voz en orden FIFO.
        Corre en un daemon thread → la GUI nunca se bloquea.
        """
        import sounddevice as sd
        import core.audio_player as player

        while True:
            text = self._mv_queue.get()
            if text is None:  # señal de cierre
                break
            try:
                audio_data, sample_rate = self.advanced_processor.process_message(text)

                # Aplicar volumen global
                vol = getattr(player, '_volume', 1.0)
                if vol != 1.0:
                    audio_data = audio_data * vol

                overlay_mgr = get_overlay_manager()
                overlay_mgr.show(text, "Multi-Voz (GUI)", is_nopolo=True)

                sd.play(audio_data, sample_rate)
                sd.wait()

                overlay_mgr.hide()

            except Exception as e:
                print(f"Error en multi-voz: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self._mv_queue.task_done()

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
