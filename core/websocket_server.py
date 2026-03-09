"""
Servidor WebSocket para Nopolo TTS
Envía eventos en tiempo real para integración con OBS Browser Source
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Set
from aiohttp import web
import aiohttp

logger = logging.getLogger(__name__)


class WebSocketServer:
    """Servidor WebSocket para enviar eventos de TTS a navegadores (OBS)"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.clients: Set[web.WebSocketResponse] = set()
        self.current_text = ""
        self.current_voice = ""
        self.is_speaking = False

        # Rutas absolutas para servir archivos estáticos
        from core.paths import get_app_base_dir, get_overlay_dir
        overlay_dir = get_overlay_dir()
        assets_dir  = get_app_base_dir() / "assets"

        # Configurar rutas
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_get('/overlay', self.overlay_handler)
        self.app.router.add_static('/static', str(overlay_dir), name='static')
        self.app.router.add_static('/assets', str(assets_dir), name='assets')
    
    async def start(self):
        """Inicia el servidor WebSocket"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, self.host, self.port)
            await site.start()
            logger.info(f"✅ WebSocket server iniciado en ws://{self.host}:{self.port}")
            logger.info(f"📺 Overlay disponible en http://localhost:{self.port}/overlay")
        except Exception as e:
            logger.error(f"❌ Error al iniciar WebSocket server: {e}")
            raise
    
    async def stop(self):
        """Detiene el servidor WebSocket"""
        try:
            # Cerrar todas las conexiones
            for ws in list(self.clients):
                await ws.close()
            self.clients.clear()
            
            # Detener el servidor
            if self.runner:
                await self.runner.cleanup()
            logger.info("🛑 WebSocket server detenido")
        except Exception as e:
            logger.error(f"❌ Error al detener WebSocket server: {e}")
    
    async def websocket_handler(self, request):
        """Maneja las conexiones WebSocket"""
        ws = web.WebSocketResponse(heartbeat=30)  # Ping cada 30 segundos
        await ws.prepare(request)
        
        self.clients.add(ws)
        logger.info(f"🔌 Cliente conectado. Total: {len(self.clients)}")
        
        # Enviar estado actual si está hablando
        if self.is_speaking:
            try:
                await ws.send_json({
                    'type': 'tts_start',
                    'text': self.current_text,
                    'voice': self.current_voice
                })
            except Exception as e:
                logger.error(f"Error enviando estado inicial: {e}")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Procesar mensajes del cliente
                    try:
                        data = json.loads(msg.data)
                        if data.get('type') == 'ping':
                            # Responder al ping del cliente
                            await ws.send_json({'type': 'pong'})
                    except json.JSONDecodeError:
                        pass  # Ignorar mensajes mal formados
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    break
        except Exception as e:
            logger.error(f"Error en WebSocket handler: {e}")
        finally:
            self.clients.discard(ws)
            logger.info(f"🔌 Cliente desconectado. Total: {len(self.clients)}")
            try:
                await ws.close()
            except:
                pass
        
        return ws
    
    async def overlay_handler(self, request):
        """Sirve la página HTML del overlay"""
        try:
            from core.paths import get_overlay_html
            overlay_path = get_overlay_html()
            with open(str(overlay_path), 'r', encoding='utf-8') as f:
                html_content = f.read()
            return web.Response(text=html_content, content_type='text/html')
        except FileNotFoundError:
            return web.Response(text="Overlay no encontrado", status=404)
    
    async def send_tts_start(self, text: str, voice: str = "", is_nopolo: bool = False,
                             image_idle_b64: str = None, image_talking_b64: str = None):
        """
        Envía evento cuando inicia el TTS.

        Args:
            text: Texto que se está reproduciendo
            voice: Nombre de la voz
            is_nopolo: True si es modo Nopolo (multi-voz), False si es modo normal
            image_idle_b64: Data URL base64 del PNG boca cerrada (opcional)
            image_talking_b64: Data URL base64 del PNG boca abierta (opcional)
        """
        self.current_text = text
        self.current_voice = voice
        self.is_speaking = True

        message = {
            'type': 'tts_start',
            'text': text,
            'voice': voice,
            'is_nopolo': is_nopolo,
        }
        if image_idle_b64:
            message['image_idle'] = image_idle_b64
        if image_talking_b64:
            message['image_talking'] = image_talking_b64

        await self._broadcast(message)

    async def send_avatar_frame(self, talking: bool):
        """Alterna la imagen del avatar entre boca abierta/cerrada."""
        await self._broadcast({'type': 'avatar_frame', 'talking': talking})

    async def send_avatar_change(self, voice: str,
                                 image_idle_b64: str = None,
                                 image_talking_b64: str = None,
                                 sound_indicator: bool = False):
        """
        Cambia el avatar activo (modo multi-voz, transición entre personajes).
        sound_indicator=True: mostrar emoji 🔊 en lugar de personaje.
        """
        message = {'type': 'avatar_change', 'voice': voice,
                   'sound_indicator': sound_indicator}
        if image_idle_b64:
            message['image_idle'] = image_idle_b64
        if image_talking_b64:
            message['image_talking'] = image_talking_b64
        await self._broadcast(message)

    async def send_tts_stop(self):
        """Envía evento cuando termina el TTS"""
        self.is_speaking = False
        self.current_text = ""
        self.current_voice = ""

        message = {'type': 'tts_stop'}

        await self._broadcast(message)
    
    async def _broadcast(self, message: dict):
        """Envía un mensaje a todos los clientes conectados"""
        if not self.clients:
            return
        
        disconnected = set()
        
        for ws in list(self.clients):  # Copiar lista para evitar modificación durante iteración
            try:
                if ws.closed:
                    disconnected.add(ws)
                else:
                    await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error enviando mensaje a cliente: {e}")
                disconnected.add(ws)
        
        # Limpiar clientes desconectados
        if disconnected:
            self.clients -= disconnected
            logger.info(f"🧹 Limpiados {len(disconnected)} clientes desconectados. Total activos: {len(self.clients)}")


# Instancia global
_websocket_server = None


def get_websocket_server() -> WebSocketServer:
    """Obtiene la instancia del servidor WebSocket"""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = WebSocketServer()
    return _websocket_server
