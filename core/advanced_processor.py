"""
Procesador avanzado de mensajes multi-voz + efectos.

Orquesta el parser, TTS, RVC, filtros y sonidos para generar
audio complejo con múltiples voces y efectos.
"""

import os
import tempfile
import numpy as np
from typing import List, Tuple, Optional
import soundfile as sf

from .message_parser import MessageParser, MessageSegment, SegmentType, AudioFilter
from .sound_manager import SoundManager
from .background_manager import BackgroundManager
from .audio_filters import AudioFilters
from .tts_engine import TTSEngine
from .rvc_engine import RVCEngine
from .voice_manager import VoiceManager


class AdvancedAudioProcessor:
    """
    Procesador avanzado para mensajes multi-voz con efectos.
    
    Pipeline:
    1. Parser → Segmentos (voces, sonidos)
    2. Para cada segmento de voz:
       a. TTS → Audio neutral
       b. RVC → Conversión de voz
       c. Filtros → Efectos de audio
    3. Para cada segmento de sonido:
       a. Cargar archivo de sonido
    4. Concatenar todo el audio
    5. Retornar audio final
    """
    
    def __init__(self, 
                 voice_manager: VoiceManager,
                 tts_engine: TTSEngine,
                 rvc_engine: RVCEngine,
                 sound_manager: Optional[SoundManager] = None,
                 background_manager: Optional[BackgroundManager] = None):
        """
        Inicializa el procesador avanzado.
        
        Args:
            voice_manager: Gestor de voces configuradas
            tts_engine: Motor TTS
            rvc_engine: Motor RVC
            sound_manager: Gestor de sonidos (opcional)
            background_manager: Gestor de fondos (opcional)
        """
        self.voice_manager = voice_manager
        self.tts_engine = tts_engine
        self.rvc_engine = rvc_engine
        self.sound_manager = sound_manager or SoundManager()
        self.background_manager = background_manager or BackgroundManager()
        
        self.parser = MessageParser(default_voice="base_male")
        self.filters = AudioFilters()
    
    def process_message(self, message: str, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
        """
        Procesa un mensaje complejo y genera audio.
        
        Args:
            message: Mensaje con formato Mopolo
            target_sr: Sample rate de salida
            
        Returns:
            Tupla (audio_data, sample_rate)
            
        Ejemplo:
            >>> processor = AdvancedAudioProcessor(...)
            >>> audio, sr = processor.process_message("dross: hola (disparo) homero: doh!")
        """
        print(f"Procesando mensaje: '{message}'")
        
        # 1. Parsear mensaje
        segments = self.parser.parse(message)
        print(f"{len(segments)} segmentos detectados")
        
        # Detectar filtros de fondo globales
        background_filters = set()
        for segment in segments:
            for f in segment.filters:
                if f.value.startswith('f'):  # fa, fb, fc, fd, fe
                    background_filters.add(f)
        
        # 2. Procesar cada segmento
        audio_chunks = []
        
        for i, segment in enumerate(segments):
            print(f"\n{'='*50}")
            print(f"Segmento {i+1}/{len(segments)}: {segment.type.value}")
            print(f"{'='*50}")
            
            try:
                if segment.type == SegmentType.VOICE:
                    chunk = self._process_voice_segment(segment, target_sr, apply_background=False)
                elif segment.type == SegmentType.SOUND:
                    chunk = self._process_sound_segment(segment, target_sr, apply_background=False)
                else:
                    print(f"Tipo de segmento desconocido: {segment.type}")
                    continue
                
                if chunk is not None:
                    audio_chunks.append(chunk)
                    # Liberar referencia del chunk original para ayudar al GC
                    del chunk
                    
                # Limpieza de memoria AGRESIVA después de cada segmento
                # Esto previene acumulación que causa segfaults
                import gc
                gc.collect()
                    
            except MemoryError as e:
                print(f"⚠️ Error de memoria en segmento {i+1}: {e}")
                print(f"Audio demasiado largo o complejo - saltando segmento")
                # Liberar memoria y continuar
                import gc
                gc.collect()
                continue
            except RuntimeError as e:
                # RuntimeError puede indicar problemas de CUDA/GPU
                print(f"⚠️ Error de runtime en segmento {i+1}: {e}")
                print(f"Posible problema de GPU - saltando segmento")
                import gc
                gc.collect()
                continue
            except Exception as e:
                print(f"⚠️ Error procesando segmento {i+1}: {e}")
                import traceback
                traceback.print_exc()
                # Continuar con siguiente segmento
                import gc
                gc.collect()
        
        # 3. Concatenar todos los chunks
        if not audio_chunks:
            print("No se generó audio")
            # Retornar silencio de 1 segundo
            return (np.zeros(target_sr, dtype=np.float32), target_sr)
        
        print(f"\nConcatenando {len(audio_chunks)} chunks de audio...")
        final_audio = np.concatenate(audio_chunks)
        
        # 4. Aplicar fondos globales al audio completo
        if background_filters:
            print(f"Aplicando {len(background_filters)} fondo(s) al audio completo...")
            for bg_filter in background_filters:
                bg_id = bg_filter.value
                print(f"   Fondo global: {bg_id}")
                
                bg_data = self.background_manager.load_background_audio(bg_id)
                if bg_data:
                    bg_audio, bg_sr, bg_volume = bg_data
                    final_audio = self.filters.apply_background(
                        final_audio, target_sr, bg_audio, bg_sr, bg_volume
                    )
                else:
                    print(f"   Fondo '{bg_id}' no encontrado")
        
        # 5. Normalizar audio final
        max_val = np.max(np.abs(final_audio))
        if max_val > 0:
            final_audio = final_audio / max_val * 0.9
        
        # Validar que el audio final sea válido (sin NaN o infinitos)
        if not np.isfinite(final_audio).all():
            print("Advertencia: Audio final contiene valores inválidos, limpiando...")
            final_audio = np.nan_to_num(final_audio, nan=0.0, posinf=0.9, neginf=-0.9)
        
        print(f"Audio final generado: {len(final_audio)/target_sr:.2f}s")
        
        return (final_audio, target_sr)
    
    def _process_voice_segment(self, segment: MessageSegment, target_sr: int, apply_background: bool = True) -> Optional[np.ndarray]:
        """
        Procesa un segmento de voz (TTS + RVC + Filtros).
        
        Args:
            segment: Segmento de voz
            target_sr: Sample rate objetivo
            apply_background: Si debe aplicar filtros de fondo (False para aplicación global)
            
        Returns:
            Audio procesado o None si falla
        """
        text = segment.content.strip()
        voice_id = segment.voice
        filters = segment.filters
        
        print(f"Voz: '{voice_id}' | Texto: '{text[:50]}...'")
        if filters:
            print(f"Filtros: {[f.value for f in filters]}")
        
        # Obtener configuración de voz (buscar por ID o nombre)
        voice_config = self.voice_manager.get_profile_by_name_or_id(voice_id)
        if not voice_config:
            print(f"Voz no encontrada: '{voice_id}', usando default")
            voice_config = self.voice_manager.get_profile("base_male")
        
        # Verificar si la voz está habilitada
        if not voice_config.enabled:
            print(f"Voz deshabilitada: {voice_id}")
            return None
        
        try:
            # 1. TTS → Audio neutral
            print("Generando TTS...")
            
            # Debug: verificar tipo de tts_config
            # Actualizar config y sintetizar
            self.tts_engine.update_config(voice_config.tts_config)
            
            # synthesize() retorna la ruta del archivo WAV
            tts_file_path = self.tts_engine.synthesize(text)
            
            # Cargar audio TTS
            tts_audio, tts_sr = sf.read(tts_file_path, dtype='float32')
            os.unlink(tts_file_path)  # Limpiar archivo temporal
            
            # 2. RVC → Conversión de voz (si está habilitada)
            if voice_config.rvc_config and voice_config.rvc_config.enabled:
                print("  2. Aplicando RVC...")
                
                try:
                    # Guardar TTS temporalmente para RVC
                    rvc_input_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                    rvc_input_file.close()
                    sf.write(rvc_input_file.name, tts_audio, tts_sr)
                    
                    # Cargar modelo RVC si es necesario
                    self.rvc_engine.load_model(voice_config.rvc_config)
                    
                    # Convertir con protección contra segfaults
                    rvc_audio, rvc_sr = self.rvc_engine.convert(rvc_input_file.name)
                    
                    # Limpiar (puede que RVC ya lo haya eliminado)
                    try:
                        os.unlink(rvc_input_file.name)
                    except FileNotFoundError:
                        pass  # Ya fue eliminado
                    
                    # Usar audio RVC
                    final_audio = rvc_audio
                    final_sr = rvc_sr
                    
                except Exception as rvc_error:
                    # Si RVC falla, usar TTS sin conversión
                    print(f"⚠️ Error en RVC (usando TTS sin conversión): {rvc_error}")
                    final_audio = tts_audio
                    final_sr = tts_sr
                    
                    # Limpiar archivo temporal si quedó
                    try:
                        if 'rvc_input_file' in locals():
                            os.unlink(rvc_input_file.name)
                    except:
                        pass
            else:
                print("  2. RVC deshabilitado, usando TTS directo")
                final_audio = tts_audio
                final_sr = tts_sr
            
            # 3. Aplicar filtros
            if filters:
                # Separar filtros normales de filtros de fondo
                normal_filters = []
                background_filters = []
                
                for audio_filter in filters:
                    if audio_filter.value.startswith('f'):  # fa, fb, fc, fd, fe
                        background_filters.append(audio_filter)
                    else:
                        normal_filters.append(audio_filter)
                
                # Aplicar filtros normales
                if normal_filters:
                    print(f"  3. Aplicando {len(normal_filters)} filtro(s) de audio...")
                    for audio_filter in normal_filters:
                        print(f"     Filtro: {audio_filter.value}")
                        final_audio = self.filters.apply_filter(
                            final_audio, 
                            final_sr, 
                            audio_filter.value
                        )
                
                # Aplicar filtros de fondo solo si apply_background=True
                if background_filters and apply_background:
                    print(f"  3. Aplicando {len(background_filters)} fondo(s)...")
                    for audio_filter in background_filters:
                        bg_id = audio_filter.value  # fa, fb, fc, etc.
                        print(f"     Fondo: {bg_id}")
                        
                        # Cargar audio de fondo
                        bg_data = self.background_manager.load_background_audio(bg_id)
                        if bg_data:
                            bg_audio, bg_sr, bg_volume = bg_data
                            final_audio = self.filters.apply_background(
                                final_audio,
                                final_sr,
                                bg_audio,
                                bg_sr,
                                bg_volume
                            )
                        else:
                            print(f"       Fondo '{bg_id}' no encontrado")
                elif background_filters and not apply_background:
                    print(f"  3. Fondos detectados (se aplicarán globalmente al final)")
            
            # 4. Resample si es necesario
            if final_sr != target_sr:
                print(f"  4. Resampling {final_sr} → {target_sr} Hz")
                from scipy import signal
                num_samples = int(len(final_audio) * target_sr / final_sr)
                final_audio = signal.resample(final_audio, num_samples)
            
            # Asegurar mono
            if len(final_audio.shape) > 1:
                final_audio = final_audio.mean(axis=1)
            
            # Agregar pequeña pausa al final (0.1s)
            pause = np.zeros(int(target_sr * 0.1), dtype=np.float32)
            final_audio = np.concatenate([final_audio, pause])
            
            print(f"Segmento procesado: {len(final_audio)/target_sr:.2f}s")
            
            return final_audio.astype(np.float32)
            
        except Exception as e:
            print(f"Error procesando voz: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _process_sound_segment(self, segment: MessageSegment, target_sr: int, apply_background: bool = True) -> Optional[np.ndarray]:
        """
        Procesa un segmento de sonido.
        
        Args:
            segment: Segmento de sonido
            target_sr: Sample rate objetivo
            apply_background: Si debe aplicar filtros de fondo (False para aplicación global)
            
        Returns:
            Audio del sonido o None si no existe
        """
        sound_id = segment.content
        filters_str = f".{'.'.join([f.value for f in segment.filters])}" if segment.filters else ""
        print(f"Sonido: '{sound_id}{filters_str}'")
        if segment.filters:
            print(f"Filtros: {[f.value for f in segment.filters]}")
        
        # Cargar audio del sonido
        sound_data = self.sound_manager.load_sound_audio(sound_id)
        if not sound_data:
            print(f"  Sonido no encontrado: {sound_id}")
            # Retornar silencio breve
            return np.zeros(int(target_sr * 0.5), dtype=np.float32)
        
        audio, sr = sound_data
        
        # Asegurar mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # Resample si es necesario
        if sr != target_sr:
            from scipy import signal
            num_samples = int(len(audio) * target_sr / sr)
            audio = signal.resample(audio, num_samples)
        
        # Aplicar filtros si existen
        if segment.filters:
            # Separar filtros normales de filtros de fondo
            normal_filters = []
            background_filters = []
            
            for audio_filter in segment.filters:
                if audio_filter.value.startswith('f'):  # fa, fb, fc, fd, fe
                    background_filters.append(audio_filter)
                else:
                    normal_filters.append(audio_filter)
            
            # Aplicar filtros normales
            if normal_filters:
                print(f"  Aplicando {len(normal_filters)} filtro(s) de audio...")
                for audio_filter in normal_filters:
                    print(f"     Filtro: {audio_filter.value}")
                    audio = self.filters.apply_filter(audio, target_sr, audio_filter.value)
            
            # Aplicar filtros de fondo solo si apply_background=True
            if background_filters and apply_background:
                print(f"  Aplicando {len(background_filters)} fondo(s)...")
                for audio_filter in background_filters:
                    bg_id = audio_filter.value
                    print(f"     Fondo: {bg_id}")
                    
                    bg_data = self.background_manager.load_background_audio(bg_id)
                    if bg_data:
                        bg_audio, bg_sr, bg_volume = bg_data
                        audio = self.filters.apply_background(
                            audio, target_sr, bg_audio, bg_sr, bg_volume
                        )
                    else:
                        print(f"       Fondo '{bg_id}' no encontrado")
            elif background_filters and not apply_background:
                print(f"  Fondos detectados (se aplicarán globalmente al final)")
        
        # NO agregar pausa al final (se eliminan las micro pausas)
        # El fondo global creará la separación natural
        
        print(f"  Sonido procesado: {len(audio)/target_sr:.2f}s")
        
        return audio.astype(np.float32)


# Ejemplo de uso
if __name__ == "__main__":
    from .voice_manager import VoiceManager
    from .tts_engine import TTSEngine
    from .rvc_engine import RVCEngine
    
    # Inicializar componentes
    voice_mgr = VoiceManager()
    tts = TTSEngine()
    rvc = RVCEngine()
    
    # Crear procesador
    processor = AdvancedAudioProcessor(voice_mgr, tts, rvc)
    
    # Mensaje de prueba
    test_message = "enrique: hola amigos (disparo) homero: doh!"
    
    # Procesar
    audio, sr = processor.process_message(test_message)
    
    # Guardar
    output_file = "test_advanced_message.wav"
    sf.write(output_file, audio, sr)
    print(f"\nAudio guardado: {output_file}")
