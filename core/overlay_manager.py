"""
Overlay Manager - Manejo centralizado de eventos del overlay

Este módulo centraliza TODO el manejo del overlay, evitando llamadas dispersas
y solapamiento de eventos.
"""

import asyncio
import base64
import os
from typing import Optional


def _encode_image(path: Optional[str]) -> Optional[str]:
    """
    Lee un PNG/JPG y devuelve una data URL base64.
    Retorna None si path es None/vacío o el archivo no existe.
    """
    if not path:
        return None
    try:
        if not os.path.exists(path):
            return None
        ext = os.path.splitext(path)[1].lower()
        mime = 'image/png' if ext == '.png' else 'image/jpeg'
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        return f'data:{mime};base64,{data}'
    except Exception as e:
        print(f"[OverlayManager] Error leyendo imagen '{path}': {e}")
        return None


class OverlayManager:
    """
    Gestor centralizado para el overlay.
    
    Maneja:
    - Control de eventos (un solo evento activo a la vez)
    - Timing y sincronización
    - Comunicación con WebSocket server
    """
    
    def __init__(self, ws_server=None, event_loop=None):
        self.ws_server = ws_server
        self.event_loop = event_loop
        self.server_running = False
        
        # Control de eventos
        self.current_event_active = False
        self._lock = asyncio.Lock() if event_loop else None
        
        # Filtros de modo (GUI settings)
        self.show_nopolo_mode = True
        self.show_normal_mode = True
    
    def set_websocket(self, ws_server, event_loop):
        """Configura el WebSocket server y event loop"""
        self.ws_server = ws_server
        self.event_loop = event_loop
        if event_loop:
            self._lock = asyncio.Lock()
    
    def set_server_running(self, running: bool):
        """Marca si el servidor está corriendo"""
        self.server_running = running
    
    def set_filters(self, show_nopolo: bool, show_normal: bool):
        """Configura los filtros de visualización"""
        self.show_nopolo_mode = show_nopolo
        self.show_normal_mode = show_normal
    
    def show(self, text: str, voice: str = "", is_nopolo: bool = False,
             image_idle: Optional[str] = None, image_talking: Optional[str] = None):
        """
        Muestra texto en el overlay.

        Args:
            text: Texto a mostrar
            voice: Nombre de voz o usuario
            is_nopolo: True para modo multi-voz (con colores), False para modo normal
            image_idle: Ruta al PNG boca cerrada del personaje (opcional)
            image_talking: Ruta al PNG boca abierta del personaje (opcional)
        """
        if not self._should_show(is_nopolo):
            return

        if not self.ws_server or not self.event_loop or not self.server_running:
            return

        # Marcar que hay un evento activo
        self.current_event_active = True

        # Codificar imágenes si se proporcionaron
        idle_b64    = _encode_image(image_idle)
        talking_b64 = _encode_image(image_talking)

        # Enviar al WebSocket
        asyncio.run_coroutine_threadsafe(
            self.ws_server.send_tts_start(text, voice, is_nopolo, idle_b64, talking_b64),
            self.event_loop
        )
    
    def hide(self):
        """Oculta el overlay"""
        if not self.ws_server or not self.event_loop or not self.server_running:
            return

        print(f"[OverlayManager] Ocultando overlay")

        # Marcar que no hay evento activo
        self.current_event_active = False

        # Enviar al WebSocket
        asyncio.run_coroutine_threadsafe(
            self.ws_server.send_tts_stop(),
            self.event_loop
        )

    def avatar_peak(self, talking: bool):
        """
        Alterna la imagen del avatar entre boca abierta/cerrada.
        Debe llamarse desde el hilo de reproducción cada ~80ms.
        """
        if not self.ws_server or not self.event_loop or not self.server_running:
            return
        asyncio.run_coroutine_threadsafe(
            self.ws_server.send_avatar_frame(talking),
            self.event_loop
        )

    def avatar_change(self, voice: str,
                      image_idle: Optional[str] = None,
                      image_talking: Optional[str] = None,
                      sound_indicator: bool = False):
        """
        Cambia el personaje activo (usado en modo multi-voz al cambiar de voz).

        Args:
            voice: Nombre del nuevo personaje
            image_idle: Ruta al PNG boca cerrada (opcional)
            image_talking: Ruta al PNG boca abierta (opcional)
            sound_indicator: True cuando el segmento es un efecto de sonido (muestra 🔊)
        """
        if not self.ws_server or not self.event_loop or not self.server_running:
            return
        idle_b64    = _encode_image(image_idle)
        talking_b64 = _encode_image(image_talking)
        asyncio.run_coroutine_threadsafe(
            self.ws_server.send_avatar_change(voice, idle_b64, talking_b64,
                                              sound_indicator=sound_indicator),
            self.event_loop
        )
    
    def _should_show(self, is_nopolo: bool) -> bool:
        """Verifica si se debe mostrar según filtros configurados"""
        if is_nopolo and not self.show_nopolo_mode:
            return False
        if not is_nopolo and not self.show_normal_mode:
            return False
        return True


# Instancia global (singleton)
_overlay_manager = None


def get_overlay_manager() -> OverlayManager:
    """Obtiene la instancia global del OverlayManager"""
    global _overlay_manager
    if _overlay_manager is None:
        _overlay_manager = OverlayManager()
    return _overlay_manager
