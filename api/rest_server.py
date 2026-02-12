
"""
API REST para integración con Streamer.bot y otras aplicaciones.
Permite enviar texto a sintetizar mediante HTTP requests.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import uvicorn
import threading
from datetime import datetime

from core.voice_manager import VoiceManager
from core.audio_queue import AudioQueue
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine


# ==================== Modelos Pydantic ====================

class TTSRequest(BaseModel):
    """Request para sintetizar texto"""
    text: str = Field(..., description="Texto a sintetizar", min_length=1, max_length=5000)
    voice_id: Optional[str] = Field(None, description="ID del perfil de voz (usa default si no se especifica)")
    priority: Optional[int] = Field(0, description="Prioridad en la cola (mayor = más prioritario)")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hola, soy Goku y estoy listo para pelear",
                "voice_id": "goku_mx",
                "priority": 0
            }
        }


class VoiceProfileResponse(BaseModel):
    """Respuesta con información de perfil de voz"""
    profile_id: str
    display_name: str
    enabled: bool
    is_transformer: bool
    tags: List[str]


class QueueStatus(BaseModel):
    """Estado de la cola de audio"""
    queue_size: int
    processing: bool


class TTSResponse(BaseModel):
    """Respuesta de solicitud TTS"""
    success: bool
    message: str
    queue_position: int
    voice_used: str


# ==================== API Server ====================

class TTSAPIServer:
    """Servidor REST API para TTS"""
    
    def __init__(self, voice_manager: VoiceManager, audio_queue: AudioQueue, 
                 host: str = "0.0.0.0", port: int = 8000):
        self.voice_manager = voice_manager
        self.audio_queue = audio_queue
        self.host = host
        self.port = port
        
        # Crear app FastAPI
        self.app = FastAPI(
            title="Nopolo TTS API",
            description="API REST para Text-to-Speech con transformadores de voz RVC",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Configurar CORS para permitir requests desde Streamer.bot
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # En producción, especificar dominios
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Registrar rutas
        self._setup_routes()
        
        # Thread del server
        self.server_thread = None
        self.is_running = False
    
    def _setup_routes(self):
        """Configura todas las rutas de la API"""
        
        @self.app.get("/")
        async def root():
            """Endpoint raíz con información del servicio"""
            return {
                "service": "Nopolo TTS API",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "tts": "/api/tts",
                    "voices": "/api/voices",
                    "queue": "/api/queue",
                    "docs": "/docs"
                }
            }
        
        @self.app.get("/health")
        async def health_check():
            """Health check para monitoreo"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "queue_size": self.audio_queue.queue.qsize()
            }
        
        @self.app.post("/api/tts", response_model=TTSResponse)
        async def synthesize_text(request: TTSRequest, background_tasks: BackgroundTasks):
            """
            Sintetiza texto con la voz especificada.
            
            - **text**: Texto a sintetizar (requerido)
            - **voice_id**: ID del perfil de voz (opcional, usa default)
            - **priority**: Prioridad en cola (opcional, default=0)
            """
            try:
                # Obtener perfil de voz
                if request.voice_id:
                    profile = self.voice_manager.get_profile(request.voice_id)
                    if not profile:
                        raise HTTPException(
                            status_code=404, 
                            detail=f"Voice profile '{request.voice_id}' not found"
                        )
                    if not profile.enabled:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Voice profile '{request.voice_id}' is disabled"
                        )
                else:
                    profile = self.voice_manager.get_default_profile()
                    if not profile:
                        raise HTTPException(
                            status_code=500,
                            detail="No default voice profile configured"
                        )
                
                # Agregar a la cola
                self.audio_queue.add(request.text, profile)
                queue_pos = self.audio_queue.queue.qsize()
                
                return TTSResponse(
                    success=True,
                    message="Text queued for synthesis",
                    queue_position=queue_pos,
                    voice_used=profile.display_name
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/voices", response_model=List[VoiceProfileResponse])
        async def list_voices():
            """Lista todos los perfiles de voz disponibles"""
            profiles = []
            for profile_id, profile in self.voice_manager.profiles.items():
                profiles.append(VoiceProfileResponse(
                    profile_id=profile.profile_id,
                    display_name=profile.display_name,
                    enabled=profile.enabled,
                    is_transformer=profile.is_transformer_voice(),
                    tags=profile.tags
                ))
            return profiles
        
        @self.app.get("/api/voices/{voice_id}", response_model=VoiceProfileResponse)
        async def get_voice(voice_id: str):
            """Obtiene información de un perfil de voz específico"""
            profile = self.voice_manager.get_profile(voice_id)
            if not profile:
                raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")
            
            return VoiceProfileResponse(
                profile_id=profile.profile_id,
                display_name=profile.display_name,
                enabled=profile.enabled,
                is_transformer=profile.is_transformer_voice(),
                tags=profile.tags
            )
        
        @self.app.get("/api/queue", response_model=QueueStatus)
        async def queue_status():
            """Obtiene el estado actual de la cola de procesamiento"""
            return QueueStatus(
                queue_size=self.audio_queue.queue.qsize(),
                processing=not self.audio_queue.queue.empty()
            )
        
        @self.app.delete("/api/queue")
        async def clear_queue():
            """Limpia la cola de audio (cancela trabajos pendientes)"""
            # Vaciar la cola
            while not self.audio_queue.queue.empty():
                try:
                    self.audio_queue.queue.get_nowait()
                    self.audio_queue.queue.task_done()
                except:
                    break
            
            return {"success": True, "message": "Queue cleared"}
    
    def start(self):
        """Inicia el servidor en un thread separado"""
        if self.is_running:
            print("API Server ya está corriendo")
            return
        
        def run_server():
            self.is_running = True
            print(f"API REST iniciada en http://{self.host}:{self.port}")
            print(f"Documentación: http://{self.host}:{self.port}/docs")
            uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
    
    def stop(self):
        """Detiene el servidor"""
        self.is_running = False
        print("API REST detenida")