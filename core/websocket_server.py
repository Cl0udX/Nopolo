"""
Servidor WebSocket para Nopolo TTS
Envía eventos en tiempo real para integración con OBS Browser Source
"""

import asyncio
import json
import logging
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
        
        # Configurar rutas
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_get('/overlay', self.overlay_handler)
        self.app.router.add_static('/static', './overlay', name='static')
    
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
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.clients.add(ws)
        logger.info(f"🔌 Cliente conectado. Total: {len(self.clients)}")
        
        # Enviar estado actual si está hablando
        if self.is_speaking:
            await ws.send_json({
                'type': 'tts_start',
                'text': self.current_text,
                'voice': self.current_voice
            })
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # Procesar mensajes del cliente si es necesario
                    pass
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        finally:
            self.clients.discard(ws)
            logger.info(f"🔌 Cliente desconectado. Total: {len(self.clients)}")
        
        return ws
    
    async def overlay_handler(self, request):
        """Sirve la página HTML del overlay"""
        try:
            with open('./overlay/overlay.html', 'r', encoding='utf-8') as f:
                html_content = f.read()
            return web.Response(text=html_content, content_type='text/html')
        except FileNotFoundError:
            return web.Response(text="Overlay no encontrado", status=404)
    
    async def send_tts_start(self, text: str, voice: str = "", is_nopolo: bool = False):
        """
        Envía evento cuando inicia el TTS
        
        Args:
            text: Texto que se está reproduciendo
            voice: Nombre de la voz
            is_nopolo: True si es modo Nopolo (multi-voz), False si es modo normal (API/voz única)
        """
        self.current_text = text
        self.current_voice = voice
        self.is_speaking = True
        
        message = {
            'type': 'tts_start',
            'text': text,
            'voice': voice,
            'is_nopolo': is_nopolo
        }
        
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
        
        for ws in self.clients:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error enviando mensaje a cliente: {e}")
                disconnected.add(ws)
        
        # Limpiar clientes desconectados
        self.clients -= disconnected


# Instancia global
_websocket_server = None


def get_websocket_server() -> WebSocketServer:
    """Obtiene la instancia del servidor WebSocket"""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = WebSocketServer()
    return _websocket_server
