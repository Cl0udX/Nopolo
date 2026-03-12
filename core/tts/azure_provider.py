"""
Proveedor de Azure Cognitive Services Text-to-Speech.
Requiere una clave de suscripción de Azure y una región.
"""
import os
import ssl
import tempfile
from dataclasses import dataclass
from typing import Optional

from .base_provider import BaseTTSProvider

# Importación condicional
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_TTS_AVAILABLE = True
except ImportError:
    AZURE_TTS_AVAILABLE = False


@dataclass
class AzureTTSConfig:
    """Configuración para Azure Cognitive Services TTS"""
    provider_name: str = "azure_tts"
    voice_id: str = "es-MX-JorgeNeural"
    language_code: str = "es-MX"
    speed: float = 1.0          # 0.5 – 2.0
    pitch: int = 0              # semitonos -12 a +12
    volume: float = 1.0         # 0.0 – 1.0
    sample_rate: int = 24000
    subscription_key: Optional[str] = None
    region: str = "eastus"

    def to_dict(self) -> dict:
        return {
            "provider_name": self.provider_name,
            "voice_id": self.voice_id,
            "language_code": self.language_code,
            "speed": self.speed,
            "pitch": self.pitch,
            "volume": self.volume,
            "sample_rate": self.sample_rate,
            "subscription_key": self.subscription_key,
            "region": self.region,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AzureTTSConfig":
        return cls(
            voice_id=data.get("voice_id", "es-MX-JorgeNeural"),
            language_code=data.get("language_code", "es-MX"),
            speed=data.get("speed", 1.0),
            pitch=data.get("pitch", 0),
            volume=data.get("volume", 1.0),
            sample_rate=data.get("sample_rate", 24000),
            subscription_key=data.get("subscription_key"),
            region=data.get("region", "eastus"),
        )

    # ── helpers de conversión ──────────────────────────────────────────────

    @property
    def rate_str(self) -> str:
        """Convierte speed (0.5–2.0) a porcentaje SSML: "+50%", "-20%", etc."""
        pct = int((self.speed - 1.0) * 100)
        return f"{pct:+d}%"

    @property
    def pitch_str(self) -> str:
        """Convierte pitch (semitonos) a Hz-offset aproximado para SSML.
        Azure usa strings como "+5Hz" o "-10Hz"."""
        # Aproximación: 1 semitono ≈ 6 Hz en voz media
        hz = self.pitch * 6
        return f"{hz:+d}Hz"

    @property
    def volume_str(self) -> str:
        """Convierte volume (0.0–1.0) a porcentaje SSML."""
        pct = int((self.volume - 1.0) * 100)
        return f"{pct:+d}%"


class AzureTTSProvider(BaseTTSProvider):
    """Proveedor de Azure Cognitive Services TTS"""

    def __init__(self, config: Optional[AzureTTSConfig] = None):
        if not AZURE_TTS_AVAILABLE:
            raise ImportError(
                "Azure Cognitive Services Speech SDK no está instalado.\n"
                "Instala con: pip install azure-cognitiveservices-speech"
            )

        if config is None:
            config = AzureTTSConfig()

        super().__init__(config)

        key = config.subscription_key or os.getenv("AZURE_SPEECH_KEY")
        region = config.region or os.getenv("AZURE_SPEECH_REGION", "eastus")

        if not key:
            raise ValueError(
                "Azure TTS requiere una clave de suscripción.\n"
                "Configúrala en los ajustes del proveedor o como variable de entorno AZURE_SPEECH_KEY."
            )

        self._speech_config = speechsdk.SpeechConfig(
            subscription=key,
            region=region,
        )
        self._speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
        )
        print(f"Azure TTS inicializado — región: {region}")

    # ── síntesis ──────────────────────────────────────────────────────────

    async def synthesize_async(self, text: str) -> str:
        """Sintetiza usando Azure Cognitive Services TTS vía SSML."""
        ssml = self._build_ssml(text)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            wav_path = f.name

        # Azure SDK es síncrono internamente; lo envolvemos para compatibilidad
        audio_cfg = speechsdk.audio.AudioOutputConfig(filename=wav_path)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self._speech_config,
            audio_config=audio_cfg,
        )

        result = synthesizer.speak_ssml(ssml)

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return wav_path
        elif result.reason == speechsdk.ResultReason.Canceled:
            details = speechsdk.SpeechSynthesisCancellationDetails(result)
            raise RuntimeError(
                f"Azure TTS cancelado: {details.reason}\n"
                f"Detalles: {details.error_details}"
            )
        else:
            raise RuntimeError(f"Azure TTS falló con razón: {result.reason}")

    def _build_ssml(self, text: str) -> str:
        """Construye el SSML para Azure con los parámetros de la config."""
        cfg = self.config
        # Escapar caracteres especiales XML básicos en el texto
        safe_text = (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
        )
        return (
            f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xml:lang="{cfg.language_code}">'
            f'<voice name="{cfg.voice_id}">'
            f'<prosody rate="{cfg.rate_str}" pitch="{cfg.pitch_str}" volume="{cfg.volume_str}">'
            f"{safe_text}"
            f"</prosody>"
            f"</voice>"
            f"</speak>"
        )

    # ── voces disponibles ─────────────────────────────────────────────────

    def get_available_voices(self) -> list[dict]:
        """Obtiene voces disponibles de Azure para la región configurada."""
        try:
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self._speech_config,
                audio_config=None,
            )
            result = synthesizer.get_voices_async().get()

            if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
                return [
                    {
                        "id": v.short_name,
                        "name": v.local_name or v.short_name,
                        "language": v.locale,
                        "gender": v.gender.name,
                    }
                    for v in result.voices
                ]
            return []
        except Exception as e:
            print(f"Error obteniendo voces de Azure: {e}")
            return []

    def validate_config(self) -> bool:
        """Prueba la conexión con Azure."""
        try:
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self._speech_config,
                audio_config=None,
            )
            result = synthesizer.get_voices_async().get()
            return result.reason == speechsdk.ResultReason.VoicesListRetrieved
        except Exception:
            return False
