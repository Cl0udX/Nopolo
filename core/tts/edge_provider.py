"""
Proveedor de Edge TTS (Microsoft Azure).
Implementa BaseTTSProvider usando edge-tts.
"""
import asyncio
import edge_tts
import tempfile
import os
from pydub import AudioSegment
from typing import Optional

from .base_provider import BaseTTSProvider
from ..models import EdgeTTSConfig


class EdgeTTSProvider(BaseTTSProvider):
    """Proveedor de Microsoft Edge TTS (gratuito)"""
    
    def __init__(self, config: Optional[EdgeTTSConfig] = None):
        """
        Args:
            config: Configuración de Edge TTS. Si es None, usa valores por defecto.
        """
        if config is None:
            config = EdgeTTSConfig()
        
        super().__init__(config)
        print("Usando Edge TTS")
    
    async def synthesize_async(self, text: str) -> str:
        """
        Sintetiza texto usando Edge TTS.
        
        Args:
            text: Texto a convertir
            
        Returns:
            Ruta al archivo WAV generado
        """
        # Crear archivos temporales
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3_tmp:
            mp3_path = mp3_tmp.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_tmp:
            wav_path = wav_tmp.name

        # Crear comunicador con configuración
        communicate = edge_tts.Communicate(
            text, 
            self.config.voice_id,
            rate=self.config.rate,
            volume=self.config.volume_str,
            pitch=f"{self.config.pitch:+d}Hz" if self.config.pitch != 0 else "+0Hz"
        )
        
        # Generar audio
        await communicate.save(mp3_path)

        # Convertir MP3 → WAV
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_channels(1).set_frame_rate(self.config.sample_rate)
        audio.export(wav_path, format="wav")

        # Limpiar archivo temporal
        os.unlink(mp3_path)
        
        return wav_path
    
    def get_available_voices(self) -> list[dict]:
        """
        Obtiene lista de voces disponibles de Edge TTS.
        
        Returns:
            Lista de voces con formato:
            [
                {"id": "es-MX-DaliaNeural", "name": "Dalia", "language": "es-MX", "gender": "Female"},
                ...
            ]
        """
        async def _get_voices():
            voices = await edge_tts.list_voices()
            return [
                {
                    "id": v["ShortName"],
                    "name": v["FriendlyName"],
                    "language": v["Locale"],
                    "gender": v["Gender"]
                }
                for v in voices
            ]
        
        return asyncio.run(_get_voices())
    
    def validate_config(self) -> bool:
        """Valida que la voz exista en Edge TTS"""
        try:
            voices = self.get_available_voices()
            voice_ids = [v["id"] for v in voices]
            return self.config.voice_id in voice_ids
        except Exception:
            return False