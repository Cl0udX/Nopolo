"""
Mixin para recarga en caliente del motor TTS (solo modo dev).
Permite aplicar cambios en core/tts_engine.py, core/tts/* y
core/advanced_processor.py sin reiniciar la aplicación.
"""
from PySide6.QtWidgets import QMessageBox


class TTSHotReloadMixin:
    """Mixin para MainWindow. Añade la recarga en caliente del motor TTS."""

    def _reload_tts_engine_hot(self):
        """
        Recarga en caliente los módulos del motor TTS (core/tts_engine.py,
        core/tts/* y core/advanced_processor.py) y reemplaza las instancias
        en uso, sin necesidad de reiniciar la aplicación.

        Solo disponible en modo dev — es una herramienta para desarrolladores.

        Hay DOS pipelines de síntesis independientes que pueden estar activos
        en cualquier momento: la cola simple (self.audio_queue, ver
        core/audio_queue.py) y la cola multi-voz (self._mv_queue /
        self._mv_worker_loop, ver playback_mixin.py), cada una con su propio
        worker thread. Antes de recargar hay que asegurarse de que NINGUNA
        de las dos esté (ni pueda quedar) sintetizando, porque construir un
        provider (ej. Google TTS) concurrentemente con otra construcción es
        lo que _PROVIDER_CREATION_LOCK existe para evitar.
        """
        # Asegurar que el guard multi-voz exista aunque ese pipeline nunca
        # se haya usado todavía (se crea de forma perezosa).
        if hasattr(self, '_ensure_mv_reload_guard'):
            self._ensure_mv_reload_guard()
        mv_guard = getattr(self, '_mv_reload_guard', None)

        # 1) Chequeo rápido, NO atómico, solo para dar un mensaje amigable
        #    sin intentar nada todavía. La exclusión mutua REAL viene del
        #    acquire() no bloqueante del paso 2.
        mv_idle = self.is_mv_idle() if hasattr(self, 'is_mv_idle') else True
        if not self.audio_queue.is_idle() or not mv_idle:
            QMessageBox.warning(
                self,
                "Motor TTS ocupado",
                "No se puede recargar el motor TTS mientras hay audio "
                "procesándose o en cola (incluido el modo multi-voz). "
                "Espera a que termine e inténtalo de nuevo."
            )
            return

        # 2) Exclusión mutua real: adquirir (no bloqueante) los mismos locks
        #    que cada worker mantiene mientras procesa un ítem. Si un worker
        #    ganó la carrera entre el chequeo de arriba y este punto, el
        #    acquire() fallará aquí y abortamos sin tocar nada -- se cierra
        #    la ventana TOCTOU del chequeo puntual de is_idle()/is_mv_idle().
        #    Los locks se mantienen tomados durante TODA la recarga (reload
        #    de módulos + construcción del nuevo engine), así que ningún
        #    worker puede empezar a procesar (ni por tanto construir un
        #    provider) mientras dure.
        if not self.audio_queue._reload_guard.acquire(blocking=False):
            QMessageBox.warning(
                self,
                "Motor TTS ocupado",
                "El motor TTS empezó a procesar audio justo ahora. "
                "Inténtalo de nuevo en unos segundos."
            )
            return

        if mv_guard is not None and not mv_guard.acquire(blocking=False):
            self.audio_queue._reload_guard.release()
            QMessageBox.warning(
                self,
                "Motor TTS ocupado",
                "El pipeline multi-voz empezó a procesar audio justo ahora. "
                "Inténtalo de nuevo en unos segundos."
            )
            return

        try:
            self._do_reload_tts_engine_hot()
        finally:
            if mv_guard is not None:
                mv_guard.release()
            self.audio_queue._reload_guard.release()

    def _do_reload_tts_engine_hot(self):
        """
        Hace el trabajo real de la recarga. Se llama SIEMPRE con los guards
        de ambos workers ya tomados (ver _reload_tts_engine_hot), así que
        aquí es seguro reejecutar los módulos y construir el nuevo engine.
        """
        try:
            import importlib
            import core.tts.base_provider
            import core.tts.edge_provider
            import core.tts.provider_factory
            import core.tts
            import core.tts_engine
            import core.advanced_processor

            # Recargar en orden de dependencias.
            # NOTA: core.tts_lock (dueño de _PROVIDER_CREATION_LOCK) NUNCA
            # se recarga a propósito -- si se recargara, el lock se
            # reemplazaría por un objeto nuevo y código en vuelo sincronizado
            # con el lock viejo dejaría de estar realmente serializado con
            # código posterior (ver core/tts_lock.py).
            importlib.reload(core.tts.base_provider)
            importlib.reload(core.tts.edge_provider)

            try:
                import core.tts.google_provider
                importlib.reload(core.tts.google_provider)
            except ImportError:
                pass

            try:
                import core.tts.azure_provider
                importlib.reload(core.tts.azure_provider)
            except ImportError:
                pass

            importlib.reload(core.tts.provider_factory)
            importlib.reload(core.tts)
            importlib.reload(core.tts_engine)
            importlib.reload(core.advanced_processor)

            new_engine = core.tts_engine.TTSEngine(config=self.tts_engine.config)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error al recargar motor TTS",
                f"No se pudo recargar el motor TTS. La aplicación sigue "
                f"funcionando con el motor anterior.\n\nError: {e}"
            )
            return

        self.tts_engine = new_engine
        self.audio_queue.tts_engine = new_engine
        self.advanced_processor.tts_engine = new_engine
        self.advanced_processor._tts_engines.clear()

        self.log_to_console("🔄 Motor TTS recargado en caliente")
        QMessageBox.information(
            self,
            "Motor TTS recargado",
            "El motor TTS se recargó correctamente con los últimos cambios."
        )
