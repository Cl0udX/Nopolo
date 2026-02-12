import asyncio
import edge_tts
import tempfile
import os
from pydub import AudioSegment
from typing import Optional
from .models import EdgeTTSConfig


class TTSEngine:
    """
    Motor TTS configurable que soporta múltiples voces de Edge TTS.
    Puede recibir una configuración específica o usar valores por defecto.
    """
    
    def __init__(self, config: Optional[EdgeTTSConfig] = None):
        """
        Inicializa el engine con una configuración opcional.
        
        Args:
            config: Configuración de Edge TTS. Si es None, usa valores por defecto.
        """
        self.config = config or EdgeTTSConfig()
        print(f"TTS Engine: {self.config.voice_id} (speed={self.config.speed}x, pitch={self.config.pitch:+d})")
    
    def update_config(self, config: EdgeTTSConfig):
        """Actualiza la configuración del engine"""
        self.config = config
        print(f"TTS actualizado: {self.config.voice_id}")
    
    def synthesize(self, text: str, config_override: Optional[EdgeTTSConfig] = None) -> str:
        """
        Sintetiza texto a audio.
        
        Args:
            text: Texto a convertir
            config_override: Configuración temporal para esta síntesis (opcional)
        
        Returns:
            Ruta al archivo WAV generado
        """
        config = config_override or self.config
        return asyncio.run(self._generate(text, config))
    
    async def _generate(self, text: str, config: EdgeTTSConfig) -> str:
        """Genera audio usando Edge TTS de forma asíncrona"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3_tmp:
            mp3_path = mp3_tmp.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_tmp:
            wav_path = wav_tmp.name

        # Crear comunicador con configuración
        communicate = edge_tts.Communicate(
            text, 
            config.voice_id,
            rate=config.rate,
            volume=config.volume_str,
            pitch=f"{config.pitch:+d}Hz" if config.pitch != 0 else "+0Hz"
        )
        await communicate.save(mp3_path)

        # Convertir a WAV
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_channels(1).set_frame_rate(config.sample_rate)
        audio.export(wav_path, format="wav")

        os.unlink(mp3_path)
        return wav_path