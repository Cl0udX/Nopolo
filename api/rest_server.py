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
from core.advanced_processor import AdvancedAudioProcessor
from core.overlay_manager import get_overlay_manager


# ==================== Modelos Pydantic ====================

class TTSRequest(BaseModel):
    """Request para sintetizar texto"""
    text: str = Field(..., description="Texto a sintetizar", min_length=1, max_length=5000)
    voice_id: Optional[str] = Field(None, description="ID del perfil de voz (usa default si no se especifica)")
    priority: Optional[int] = Field(0, description="Prioridad en la cola (mayor = más prioritario)")
    author: Optional[str] = Field(None, description="Nombre del usuario que envió el mensaje (se muestra en overlay)")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "texto",
                "voice_id": "voice",
                "priority": 0,
                "author": "user"
            }
        }


class AdvancedTTSRequest(BaseModel):
    """Request para sintetizar mensajes multi-voz con efectos"""
    message: str = Field(..., description="Mensaje con formato Mopolo (multi-voz + efectos)", min_length=1, max_length=10000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "goku: hola amigos (disparo) homero: doh! reportero.fa: estamos en vivo"
            }
        }


class AdvancedTTSResponse(BaseModel):
    """Respuesta de síntesis avanzada"""
    success: bool
    message: str
    audio_duration: float
    segments_processed: int


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
                 tts_engine: TTSEngine = None, rvc_engine: RVCEngine = None,
                 host: str = "0.0.0.0", port: int = 8000, main_window = None):
        self.voice_manager = voice_manager
        self.audio_queue = audio_queue
        self.tts_engine = tts_engine or TTSEngine()
        self.rvc_engine = rvc_engine or RVCEngine()
        self.host = host
        self.port = port
        self.main_window = main_window
        
        # Crear procesador avanzado para mensajes multi-voz
        self.advanced_processor = AdvancedAudioProcessor(
            voice_manager=self.voice_manager,
            tts_engine=self.tts_engine,
            rvc_engine=self.rvc_engine
        )
        
        # Cola dedicada para mensajes multi-voz (evita cancelar audio anterior)
        import queue as queue_module
        self.multivoice_queue = queue_module.Queue()
        self._start_multivoice_worker()
        
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
    
    def _get_random_tts_only_voice(self):
        """
        Obtiene una voz aleatoria que solo usa TTS (sin RVC).
        
        Returns:
            VoiceProfile o None si no hay voces disponibles
        """
        import random
        
        # Filtrar voces que NO tienen RVC (solo TTS)
        tts_only_voices = [
            profile for profile in self.voice_manager.profiles.values()
            if profile.enabled and profile.rvc_config is None
        ]
        
        if not tts_only_voices:
            print("No hay voces solo-TTS disponibles")
            return None
        
        # Seleccionar una aleatoria
        selected = random.choice(tts_only_voices)
        print(f"Voz aleatoria seleccionada: {selected.display_name} (ID: {selected.profile_id})")
        return selected
    
    def _start_multivoice_worker(self):
        """Inicia el worker thread para procesar cola multi-voz secuencialmente"""

        def multivoice_worker():
            from core.audio_player import play_wav
            from core.rvc_subprocess_persistent import PersistentSubprocessProcessor

            # PROCESADOR PERSISTENTE:
            # El subprocess hijo carga los modelos (Hubert, RMVPE, RVC) UNA SOLA VEZ
            # y luego procesa mensajes en loop → sin overhead de arranque por mensaje.
            # Si crashea (segfault / heap corruption), se reinicia automáticamente.
            processor = PersistentSubprocessProcessor(voice_manager=self.voice_manager)
            # Arrancar el subprocess AHORA en background, sin esperar la primera solicitud.
            # Así el worker ya está caliente cuando llega el primer mensaje.
            processor.warmup()

            request_count = 0
            while True:
                text = None
                try:
                    text, author = self.multivoice_queue.get()
                    request_count += 1
                    print(f"\n{'='*60}")
                    print(f"[Worker Nopolo] Solicitud #{request_count}: {text[:60]}...")
                    print(f"{'='*60}")

                    # Todo el procesamiento (TTS + RVC + filtros) ocurre en el
                    # subprocess persistente → proceso principal nunca toca CUDA
                    audio_data, sample_rate = processor.process_message(text)

                    # Mostrar overlay ANTES de reproducir (audio ya está listo)
                    display_name = author if author else "Multi-Voz (API)"
                    overlay_mgr = get_overlay_manager()
                    overlay_mgr.show(text, display_name, is_nopolo=True)

                    # Reproducir (bloqueante hasta que termina)
                    play_wav((audio_data, sample_rate))
                    del audio_data

                    overlay_mgr.hide()
                    print(f"[Worker Nopolo] Solicitud #{request_count} completada")

                except Exception as e:
                    import traceback
                    print(f"[Worker Nopolo] ERROR en solicitud #{request_count}: {e}")
                    traceback.print_exc()
                    try:
                        get_overlay_manager().hide()
                    except Exception:
                        pass

                finally:
                    self.multivoice_queue.task_done()

        # Iniciar worker thread
        worker_thread = threading.Thread(target=multivoice_worker, daemon=True)
        worker_thread.start()
        print("Worker multi-voz iniciado (subprocess persistente)")
    
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
            - **author**: Nombre del usuario que envió el mensaje (opcional, se muestra en overlay)
            
            Si la voz no existe o se especifica "random"/"aleatorio", 
            se usa una voz aleatoria sin RVC (solo TTS).
            """
            try:
                profile = None
                
                # Obtener perfil de voz
                if request.voice_id:
                    # Caso especial: voz aleatoria sin RVC
                    if request.voice_id.lower() in ["random", "aleatorio", "aleatoria"]:
                        profile = self._get_random_tts_only_voice()
                        if not profile:
                            raise HTTPException(
                                status_code=500,
                                detail="No hay voces solo-TTS disponibles para selección aleatoria"
                            )
                    else:
                        # Intentar obtener la voz especificada (por ID o nombre)
                        profile = self.voice_manager.get_profile_by_name_or_id(request.voice_id)
                        
                        # Si no existe, usar voz aleatoria sin RVC como fallback
                        if not profile:
                            print(f"⚠️ Voz '{request.voice_id}' no encontrada, usando voz aleatoria sin RVC")
                            profile = self._get_random_tts_only_voice()
                            if not profile:
                                raise HTTPException(
                                    status_code=404,
                                    detail=f"Voice profile '{request.voice_id}' not found y no hay voces solo-TTS disponibles"
                                )
                        elif not profile.enabled:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Voice profile '{request.voice_id}' is disabled"
                            )
                else:
                    # Si no se especifica, usar voz por defecto
                    profile = self.voice_manager.get_default_profile()
                    if not profile:
                        raise HTTPException(
                            status_code=500,
                            detail="No default voice profile configured"
                        )
                
                # Agregar a la cola
                # Usar author si está disponible, sino el nombre de la voz
                voice_name = profile.display_name
                self.audio_queue.add(request.text, profile, voice_name, self.main_window, request.author)
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
        
        @self.app.post("/api/tts/multivoice", response_model=TTSResponse)
        async def synthesize_multivoice(request: TTSRequest):
            """
            Sintetiza mensajes con múltiples voces usando sintaxis Mopolo.
            
            Soporta:
            - **Voces**: `nombre: texto` o `id: texto`
            - **Sonidos**: `(nombre)` o `(id)`
            - **Filtros**: `nombre.filtro: texto` (r, p, pu, pd, m, a, l)
            - **Fondos**: `nombre.fondo: texto` (fa, fb, fc, fd, fe)
            - **author**: Nombre del usuario que envió el mensaje (opcional, se muestra en overlay)
            
            Ejemplo: `"dross: hola (disparo) homero: doh! reportero.fa: en vivo"`
            """
            try:
                # Agregar a la cola dedicada de multi-voz (procesamiento secuencial)
                # Guardar texto y autor (opcional)
                self.multivoice_queue.put((request.text, request.author))
                queue_pos = self.multivoice_queue.qsize()
                
                return TTSResponse(
                    success=True,
                    message=f"Multi-voice message queued (position {queue_pos})",
                    queue_position=queue_pos,
                    voice_used="multi-voice"
                )
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Error queueing multi-voice: {str(e)}")
        
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
        
        @self.app.post("/api/audio/stop")
        async def stop_audio():
            """Detiene el audio que está sonando actualmente"""
            self.audio_queue.stop_current()
            return {"success": True, "message": "Audio stopped"}
        
        @self.app.post("/api/audio/skip")
        async def skip_audio():
            """Salta al siguiente en la cola"""
            self.audio_queue.skip_to_next()
            queue_size = self.audio_queue.get_queue_size()
            return {
                "success": True, 
                "message": "Skipped to next",
                "queue_size": queue_size
            }
        
        @self.app.delete("/api/audio/clear")
        async def clear_all_audio():
            """Detiene el audio actual y limpia toda la cola"""
            self.audio_queue.clear_queue()
            return {"success": True, "message": "Audio stopped and queue cleared"}
        
        @self.app.post("/api/synthesize/advanced")
        async def synthesize_advanced(request: AdvancedTTSRequest):
            """
            Sintetiza mensajes complejos con múltiples voces, efectos de sonido y filtros.
            
            Soporta sintaxis Mopolo:
            - **Voces**: `nombre: texto` o `id: texto`
            - **Sonidos**: `(nombre)` o `(id)`
            - **Filtros**: `nombre.filtro: texto` (r, p, pu, pd, m, a, l)
            - **Fondos**: `nombre.fa: texto` (fa, fb, fc, fd, fe)
            
            Ejemplo: `"dross: hola (disparo) homero: doh! reportero.fa: en vivo"`
            
            Retorna el archivo de audio WAV directamente.
            """
            try:
                import tempfile
                import soundfile as sf
                from fastapi.responses import FileResponse
                import os
                
                # Procesar mensaje con el procesador avanzado
                audio_data, sample_rate = self.advanced_processor.process_message(request.message)
                
                # Guardar audio temporalmente
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_file.close()
                
                sf.write(temp_file.name, audio_data, sample_rate)
                
                # Retornar archivo de audio
                return FileResponse(
                    temp_file.name,
                    media_type="audio/wav",
                    filename="advanced_audio.wav",
                    headers={
                        "X-Audio-Duration": str(len(audio_data) / sample_rate),
                        "X-Segments-Processed": str(len(self.advanced_processor.parser.parse(request.message)))
                    }
                )
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")
    
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