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
from .rvc_isolated import RVCIsolatedEngine  # Motor aislado en proceso separado
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
    
    def _apply_fade(self, audio: np.ndarray, sr: int, fade_duration: float = 0.15) -> np.ndarray:
        """
        Aplica fade in y fade out a un audio para suavizar transiciones.
        Usa curva de coseno para transiciones mas suaves y naturales.
        
        Args:
            audio: Audio a procesar
            sr: Sample rate
            fade_duration: Duracion del fade en segundos (default 150ms)
            
        Returns:
            Audio con fades aplicados
        """
        if len(audio) == 0:
            return audio
        
        fade_samples = int(sr * fade_duration)
        
        # No aplicar fade si el audio es muy corto
        if len(audio) < fade_samples * 2:
            fade_samples = len(audio) // 4  # Usar 25% del audio para fade
        
        if fade_samples <= 0:
            return audio
        
        # Crear copia para no modificar el original
        faded = audio.copy()
        
        # Fade in (inicio) - Curva de coseno para transicion mas suave
        fade_in_curve = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade_samples)))
        faded[:fade_samples] *= fade_in_curve
        
        # Fade out (final) - Curva de coseno para transicion mas suave
        fade_out_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_samples)))
        faded[-fade_samples:] *= fade_out_curve
        
        return faded
    
    def _apply_smart_fade(self, audio: np.ndarray, sr: int, apply_fade_in: bool, apply_fade_out: bool, fade_duration: float = 0.4) -> np.ndarray:
        """
        Aplica fade in y/o fade out selectivamente.
        
        Args:
            audio: Audio a procesar
            sr: Sample rate
            apply_fade_in: Si aplicar fade in
            apply_fade_out: Si aplicar fade out
            fade_duration: Duracion del fade en segundos (default 400ms)
            
        Returns:
            Audio con fades aplicados
        """
        if len(audio) == 0:
            return audio
        
        if not apply_fade_in and not apply_fade_out:
            return audio  # No aplicar ningun fade
        
        fade_samples = int(sr * fade_duration)
        
        # No aplicar fade si el audio es muy corto
        if len(audio) < fade_samples * 2:
            fade_samples = len(audio) // 4
        
        if fade_samples <= 0:
            return audio
        
        # Crear copia para no modificar el original
        faded = audio.copy()
        
        # Fade in (inicio) - Solo si apply_fade_in=True
        if apply_fade_in:
            fade_in_curve = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade_samples)))
            faded[:fade_samples] *= fade_in_curve
        
        # Fade out (final) - Solo si apply_fade_out=True
        if apply_fade_out:
            fade_out_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_samples)))
            faded[-fade_samples:] *= fade_out_curve
        
        return faded
    
    def _crossfade_chunks(self, chunks: List[np.ndarray], metadata: List[dict], sr: int, crossfade_duration: float = 0.3) -> np.ndarray:
        """
        Combina chunks de audio con crossfade inteligente.
        
        Si dos chunks consecutivos tienen el mismo fondo, aplica crossfade overlap.
        Si tienen fondos diferentes, los concatena normalmente.
        
        Args:
            chunks: Lista de chunks de audio
            metadata: Metadata de cada chunk (fondos)
            sr: Sample rate
            crossfade_duration: Duracion del crossfade en segundos (default 300ms)
            
        Returns:
            Audio combinado
        """
        if not chunks:
            return np.array([], dtype=np.float32)
        
        if len(chunks) == 1:
            return chunks[0]
        
        crossfade_samples = int(sr * crossfade_duration)
        result = chunks[0]
        
        for i in range(1, len(chunks)):
            prev_backgrounds = metadata[i-1]['backgrounds']
            curr_backgrounds = metadata[i]['backgrounds']
            
            # Si ambos tienen fondos Y son iguales → CROSSFADE
            if prev_backgrounds and curr_backgrounds and prev_backgrounds == curr_backgrounds:
                print(f"  Crossfade entre chunk {i} y {i+1} (fondos iguales: {prev_backgrounds})")
                
                # Asegurar que hay suficiente audio para crossfade
                overlap = min(crossfade_samples, len(result), len(chunks[i]))
                
                if overlap > 0:
                    # Extraer región de overlap del resultado actual
                    overlap_start = len(result) - overlap
                    overlap_region_prev = result[overlap_start:].copy()
                    overlap_region_curr = chunks[i][:overlap].copy()
                    
                    # Crear curvas de crossfade (coseno)
                    fade_out_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, overlap)))
                    fade_in_curve = 0.5 * (1 - np.cos(np.linspace(0, np.pi, overlap)))
                    
                    # Aplicar crossfade
                    crossfaded = overlap_region_prev * fade_out_curve + overlap_region_curr * fade_in_curve
                    
                    # Reemplazar región de overlap y agregar el resto
                    result = np.concatenate([
                        result[:overlap_start],
                        crossfaded,
                        chunks[i][overlap:]
                    ])
                else:
                    # Si no hay suficiente para overlap, concatenar normalmente
                    result = np.concatenate([result, chunks[i]])
            else:
                # Fondos diferentes o sin fondos → concatenar normalmente
                print(f"  Concatenacion normal entre chunk {i} y {i+1}")
                result = np.concatenate([result, chunks[i]])
        
        return result
    
    def _get_background_filters(self, segment: MessageSegment) -> List[str]:
        """
        Extrae los filtros de fondo de un segmento.
        
        Args:
            segment: Segmento a analizar
            
        Returns:
            Lista de IDs de fondos (ej: ['fc', 'fd'])
        """
        if not segment.filters:
            return []
        
        backgrounds = []
        for f in segment.filters:
            if f.value.startswith('f') and len(f.value) == 2:  # fa, fb, fc, fd, fe
                backgrounds.append(f.value)
        
        return backgrounds
    
    def _should_apply_fade(self, segments: List[MessageSegment], current_idx: int, fade_type: str) -> bool:
        """
        Determina si se debe aplicar fade in o fade out a un segmento.
        
        Logica:
        - Si segmentos consecutivos tienen el MISMO fondo NO VACIO, NO aplicar fade entre ellos
        - Si ambos NO tienen fondo, SI aplicar fade (para separar voces normales)
        - Si tienen fondos DIFERENTES, SI aplicar fade
        
        Args:
            segments: Lista completa de segmentos
            current_idx: Indice del segmento actual
            fade_type: 'in' o 'out'
            
        Returns:
            True si debe aplicar fade, False si no
        """
        if current_idx < 0 or current_idx >= len(segments):
            return True
        
        current_backgrounds = set(self._get_background_filters(segments[current_idx]))
        
        if fade_type == 'in':
            # Fade in: comparar con segmento ANTERIOR
            if current_idx == 0:
                return True  # Siempre fade in al inicio
            
            prev_backgrounds = set(self._get_background_filters(segments[current_idx - 1]))
            
            # Si AMBOS tienen fondos Y son iguales → NO aplicar fade (continuidad)
            if current_backgrounds and prev_backgrounds and current_backgrounds == prev_backgrounds:
                return False
            
            # En cualquier otro caso → SI aplicar fade
            return True
            
        else:  # fade_type == 'out'
            # Fade out: comparar con segmento SIGUIENTE
            if current_idx == len(segments) - 1:
                return True  # Siempre fade out al final
            
            next_backgrounds = set(self._get_background_filters(segments[current_idx + 1]))
            
            # Si AMBOS tienen fondos Y son iguales → NO aplicar fade (continuidad)
            if current_backgrounds and next_backgrounds and current_backgrounds == next_backgrounds:
                return False
            
            # En cualquier otro caso → SI aplicar fade
            return True
    
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
        
        # 2. Procesar cada segmento (fondos son LOCALES a cada segmento)
        audio_chunks = []
        segment_metadata = []  # Guardar metadata de cada segmento para crossfade
        
        for i, segment in enumerate(segments):
            print(f"\n{'='*50}")
            print(f"Segmento {i+1}/{len(segments)}: {segment.type.value}")
            print(f"{'='*50}")
            
            try:
                if segment.type == SegmentType.VOICE:
                    chunk = self._process_voice_segment(segment, target_sr, apply_background=True)
                elif segment.type == SegmentType.SOUND:
                    chunk = self._process_sound_segment(segment, target_sr, apply_background=True)
                else:
                    print(f"Tipo de segmento desconocido: {segment.type}")
                    continue
                
                if chunk is not None:
                    # Aplicar fades INTELIGENTES: solo si fondos cambian
                    apply_fade_in = self._should_apply_fade(segments, i, 'in')
                    apply_fade_out = self._should_apply_fade(segments, i, 'out')
                    
                    # Log de fades aplicados
                    fade_info = []
                    if apply_fade_in:
                        fade_info.append("fade-in")
                    if apply_fade_out:
                        fade_info.append("fade-out")
                    
                    if fade_info:
                        print(f"  Aplicando: {', '.join(fade_info)}")
                    else:
                        print(f"  Sin fades (continuidad de fondo)")
                    
                    chunk = self._apply_smart_fade(
                        chunk, 
                        target_sr, 
                        apply_fade_in=apply_fade_in,
                        apply_fade_out=apply_fade_out,
                        fade_duration=0.4  # 400ms para fades MUY suaves
                    )
                    
                    audio_chunks.append(chunk)
                    # Guardar metadata del segmento para crossfade posterior
                    segment_metadata.append({
                        'backgrounds': set(self._get_background_filters(segment)),
                        'segment_idx': i
                    })
                    
                    # Liberar referencia del chunk original para ayudar al GC
                    del chunk
                    
                # Limpieza de memoria AGRESIVA después de cada segmento
                # Esto previene acumulación que causa segfaults
                import gc
                gc.collect()
                    
            except MemoryError as e:
                print(f"Error de memoria en segmento {i+1}: {e}")
                print(f"Audio demasiado largo o complejo - saltando segmento")
                # Liberar memoria y continuar
                import gc
                gc.collect()
                continue
            except RuntimeError as e:
                # RuntimeError puede indicar problemas de CUDA/GPU
                print(f"Error de runtime en segmento {i+1}: {e}")
                print(f"Posible problema de GPU - saltando segmento")
                import gc
                gc.collect()
                continue
            except Exception as e:
                print(f"Error procesando segmento {i+1}: {e}")
                import traceback
                traceback.print_exc()
                # Continuar con siguiente segmento
                import gc
                gc.collect()
        
        # 3. Concatenar chunks con crossfade inteligente
        if not audio_chunks:
            print("No se generó audio")
            # Retornar silencio de 1 segundo
            return (np.zeros(target_sr, dtype=np.float32), target_sr)
        
        print(f"\nCombinando {len(audio_chunks)} chunks de audio con crossfade inteligente...")
        
        # Aplicar crossfade entre chunks con fondos iguales
        final_audio = self._crossfade_chunks(audio_chunks, segment_metadata, target_sr)
        
        # 4. Normalizar audio final
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
        
        # USAR TTS y RVC compartidos (no crear nuevos por solicitud)
        # Crear nuevos engines causa heap corruption en Windows (0xc0000374)
        # porque los modelos Hubert/RMVPE no se liberan correctamente
        tts_engine = self.tts_engine
        rvc_engine = self.rvc_engine
        
        # Solo crear si realmente no existe (primera vez)
        if tts_engine is None:
            print("  Creando TTS Engine (primera vez)...")
            # IMPORTANTE: Forzar Edge TTS porque Google Cloud TTS usa gRPC
            # que NO es thread-safe y causa heap corruption en Windows
            from .models import EdgeTTSConfig
            edge_config = EdgeTTSConfig()
            tts_engine = TTSEngine(config=edge_config, provider_name='edge_tts')
            self.tts_engine = tts_engine  # Guardar referencia para reutilizar
        
        if rvc_engine is None:
            print("  Creando RVC Engine ISOLATED (primera vez)...")
            # IMPORTANTE: Usar RVCIsolatedEngine que ejecuta cada conversión
            # en un proceso separado para evitar heap corruption en Windows
            rvc_engine = RVCIsolatedEngine()
            self.rvc_engine = rvc_engine  # Guardar referencia para reutilizar
        
        try:
            # 1. TTS → Audio neutral
            print("Generando TTS...")
            
            # Actualizar config y sintetizar
            tts_engine.update_config(voice_config.tts_config)
            
            # synthesize() retorna la ruta del archivo WAV
            tts_file_path = tts_engine.synthesize(text)
            
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
                    rvc_engine.load_model(voice_config.rvc_config)
                    
                    # Convertir con protección contra segfaults
                    rvc_audio, rvc_sr = rvc_engine.convert(rvc_input_file.name)
                    
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
                    print(f"Error en RVC (usando TTS sin conversión): {rvc_error}")
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
            
            # 4. Resample si es necesario
            if final_sr != target_sr:
                print(f"  4. Resampling {final_sr} -> {target_sr} Hz")
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
