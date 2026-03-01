"""
Sistema de filtros de audio para Nopolo.

Implementa los filtros de Mopolo:
- r: Eco/reverberación
- p: Llamada telefónica
- pu: Voz aguda (pitch up)
- pd: Voz grave (pitch down)
- m: Voz apagada/afuera (muffled)
- a: Android/robot
- l: Saturada/distorsión
"""

import numpy as np
from scipy import signal
from typing import Tuple
import soundfile as sf


class AudioFilters:
    """
    Procesador de filtros de audio.
    """
    
    @staticmethod
    def apply_reverb(audio: np.ndarray, sr: int, room_scale: float = 0.5) -> np.ndarray:
        """
        Aplica efecto de eco/reverberación.
        
        Args:
            audio: Audio de entrada
            sr: Sample rate
            room_scale: Tamaño de habitación (0-1)
            
        Returns:
            Audio con reverberación
        """
        # Crear impulse response simple para reverb
        decay_time = 0.3 + room_scale * 0.7  # 0.3 a 1.0 segundos
        ir_length = int(sr * decay_time)
        
        # Impulse response exponencial decayente
        t = np.linspace(0, decay_time, ir_length)
        ir = np.exp(-t / (decay_time * 0.3))
        
        # Agregar reflexiones aleatorias
        ir += np.random.randn(ir_length) * 0.1 * ir
        
        # Normalizar
        ir = ir / np.max(np.abs(ir))
        
        # Aplicar convolución
        audio_reverb = signal.convolve(audio, ir, mode='same')
        
        # Mix húmedo/seco (70% original, 30% reverb)
        output = 0.7 * audio + 0.3 * audio_reverb
        
        # Normalizar para evitar clipping
        output = output / np.max(np.abs(output)) * 0.9
        
        return output.astype(np.float32)
    
    @staticmethod
    def apply_phone_filter(audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Aplica filtro de llamada telefónica (bandpass 300-3400 Hz).
        
        Args:
            audio: Audio de entrada
            sr: Sample rate
            
        Returns:
            Audio con filtro telefónico
        """
        # Frecuencias de corte típicas de teléfono
        lowcut = 300.0   # Hz
        highcut = 3400.0 # Hz
        
        # Diseñar filtro bandpass
        nyquist = sr / 2.0
        low = lowcut / nyquist
        high = highcut / nyquist
        
        # Butterworth bandpass filter
        b, a = signal.butter(4, [low, high], btype='band')
        
        # Aplicar filtro
        filtered = signal.filtfilt(b, a, audio)
        
        # Agregar leve distorsión digital
        filtered = np.tanh(filtered * 1.5)
        
        # Normalizar
        filtered = filtered / np.max(np.abs(filtered)) * 0.9
        
        return filtered.astype(np.float32)
    
    @staticmethod
    def apply_pitch_shift(audio: np.ndarray, sr: int, semitones: float) -> np.ndarray:
        """
        Cambia el pitch del audio (simple time-stretching).
        
        Args:
            audio: Audio de entrada
            sr: Sample rate
            semitones: Cantidad de semitonos a cambiar (+/- 12)
            
        Returns:
            Audio con pitch modificado
        """
        # Factor de pitch (2^(semitones/12))
        pitch_factor = 2.0 ** (semitones / 12.0)
        
        # Resample para cambiar pitch
        new_length = int(len(audio) / pitch_factor)
        
        # Usar scipy resample
        resampled = signal.resample(audio, new_length)
        
        # Si es más corto, hacer pad; si es más largo, truncar
        if len(resampled) < len(audio):
            output = np.pad(resampled, (0, len(audio) - len(resampled)), mode='constant')
        else:
            output = resampled[:len(audio)]
        
        # Normalizar
        output = output / np.max(np.abs(output)) * 0.9
        
        return output.astype(np.float32)
    
    @staticmethod
    def apply_muffled_filter(audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Aplica filtro de voz apagada/afuera (lowpass + reverb leve).
        
        Args:
            audio: Audio de entrada
            sr: Sample rate
            
        Returns:
            Audio apagado
        """
        # Lowpass filter a 800 Hz
        cutoff = 800.0
        nyquist = sr / 2.0
        normal_cutoff = cutoff / nyquist
        
        # Butterworth lowpass
        b, a = signal.butter(3, normal_cutoff, btype='low')
        
        # Aplicar filtro
        muffled = signal.filtfilt(b, a, audio)
        
        # Agregar reverb leve
        muffled = AudioFilters.apply_reverb(muffled, sr, room_scale=0.3)
        
        # Reducir volumen
        muffled = muffled * 0.7
        
        return muffled.astype(np.float32)
    
    @staticmethod
    def apply_robot_filter(audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Aplica filtro de voz robótica/android (vocoder simple).
        
        Args:
            audio: Audio de entrada
            sr: Sample rate
            
        Returns:
            Audio robótico
        """
        # Generar carrier tone (onda cuadrada a 200 Hz)
        duration = len(audio) / sr
        t = np.linspace(0, duration, len(audio))
        carrier = signal.square(2 * np.pi * 200 * t)
        
        # Ring modulation
        modulated = audio * carrier
        
        # Agregar vibrato leve
        vibrato_freq = 5.0  # Hz
        vibrato_depth = 0.02
        vibrato = np.sin(2 * np.pi * vibrato_freq * t) * vibrato_depth + 1.0
        modulated = modulated * vibrato
        
        # Lowpass para suavizar
        b, a = signal.butter(2, 0.3, btype='low')
        robot = signal.filtfilt(b, a, modulated)
        
        # Mix con original (20% original, 80% robot)
        output = 0.2 * audio + 0.8 * robot
        
        # Normalizar
        output = output / np.max(np.abs(output)) * 0.9
        
        return output.astype(np.float32)
    
    @staticmethod
    def apply_distortion(audio: np.ndarray, sr: int, gain: float = 3.0) -> np.ndarray:
        """
        Aplica distorsión/saturación.
        
        Args:
            audio: Audio de entrada
            sr: Sample rate
            gain: Cantidad de ganancia pre-distorsión
            
        Returns:
            Audio distorsionado
        """
        # Amplificar
        boosted = audio * gain
        
        # Soft clipping (tanh)
        distorted = np.tanh(boosted)
        
        # Agregar highpass para enfatizar agudos
        b, a = signal.butter(2, 0.1, btype='high')
        distorted = signal.filtfilt(b, a, distorted)
        
        # Normalizar
        distorted = distorted / np.max(np.abs(distorted)) * 0.9
        
        return distorted.astype(np.float32)
    
    @staticmethod
    def apply_background(audio: np.ndarray, sr: int, background_audio: np.ndarray, 
                        background_sr: int, background_volume: float = 0.3) -> np.ndarray:
        """
        Mezcla el audio con un fondo continuo.
        
        El fondo se reproduce en loop si es más corto que el audio principal,
        o se recorta si es más largo.
        
        Args:
            audio: Audio principal (voz)
            sr: Sample rate del audio principal
            background_audio: Audio de fondo
            background_sr: Sample rate del fondo
            background_volume: Volumen del fondo (0.0 - 1.0, recomendado 0.2-0.4)
            
        Returns:
            Audio mezclado
        """
        # Resamplear fondo si tiene diferente sample rate
        if background_sr != sr:
            # Calcular nuevo tamaño
            new_length = int(len(background_audio) * sr / background_sr)
            
            # Protección: Si el resampling requiere mucha memoria, usar método más simple
            estimated_memory_mb = (new_length * 4) / (1024 * 1024)  # float32 = 4 bytes
            if estimated_memory_mb > 500:  # Más de 500MB
                print(f"Resampling grande ({estimated_memory_mb:.1f}MB), usando método simple...")
                # Usar interpolación lineal simple en lugar de scipy
                indices = np.linspace(0, len(background_audio) - 1, new_length)
                background_resampled = np.interp(indices, np.arange(len(background_audio)), background_audio)
            else:
                # Resamplear usando interpolación scipy
                from scipy.signal import resample
                try:
                    background_resampled = resample(background_audio, new_length)
                except MemoryError as e:
                    print(f"Error de memoria al resamplear fondo: {e}, usando método simple")
                    indices = np.linspace(0, len(background_audio) - 1, new_length)
                    background_resampled = np.interp(indices, np.arange(len(background_audio)), background_audio)
                except Exception as e:
                    print(f"Error al resamplear fondo: {e}, usando fondo sin resamplear")
                    background_resampled = background_audio.copy()
        else:
            background_resampled = background_audio.copy()
        
        # Asegurar que el fondo sea del mismo largo que el audio
        audio_length = len(audio)
        bg_length = len(background_resampled)
        
        if bg_length < audio_length:
            # Loop del fondo si es más corto
            num_repeats = int(np.ceil(audio_length / bg_length))
            # Limitar a máximo 100 repeticiones para evitar arrays gigantes
            if num_repeats > 100:
                print(f"Advertencia: Fondo muy corto ({bg_length} samples) para audio largo ({audio_length} samples)")
                num_repeats = 100
            background_looped = np.tile(background_resampled, num_repeats)
            background_final = background_looped[:audio_length]
        else:
            # Recortar si es más largo
            background_final = background_resampled[:audio_length]
        
        # Normalizar el fondo a peak 1.0, luego escalar con background_volume
        # relativo al nivel del audio principal.
        # NO re-normalizar el mix final: eso destruiría el volumen configurado.
        audio_peak = np.max(np.abs(audio)) if np.max(np.abs(audio)) > 0 else 1.0
        bg_peak    = np.max(np.abs(background_final)) if np.max(np.abs(background_final)) > 0 else 1.0

        # El fondo suena a `background_volume` del nivel de la voz
        bg_scaled = background_final / bg_peak * audio_peak * background_volume

        mixed = audio + bg_scaled

        # Clip suave para evitar distorsión (sin re-normalizar)
        mixed = np.clip(mixed, -0.99, 0.99)

        # Validar
        if not np.isfinite(mixed).all():
            print("Audio mezclado contiene valores inválidos, limpiando...")
            mixed = np.nan_to_num(mixed, nan=0.0, posinf=0.99, neginf=-0.99)

        return mixed.astype(np.float32)
    
    @classmethod
    def apply_filter(cls, audio: np.ndarray, sr: int, filter_id: str) -> np.ndarray:
        """
        Aplica un filtro según su ID.
        
        Args:
            audio: Audio de entrada
            sr: Sample rate
            filter_id: ID del filtro ('r', 'p', 'pu', 'pd', 'm', 'a', 'l')
            
        Returns:
            Audio procesado
        """
        filter_map = {
            'r': lambda a, s: cls.apply_reverb(a, s),
            'p': lambda a, s: cls.apply_phone_filter(a, s),
            'pu': lambda a, s: cls.apply_pitch_shift(a, s, semitones=5),   # +5 semitonos
            'pd': lambda a, s: cls.apply_pitch_shift(a, s, semitones=-5),  # -5 semitonos
            'm': lambda a, s: cls.apply_muffled_filter(a, s),
            'a': lambda a, s: cls.apply_robot_filter(a, s),
            'l': lambda a, s: cls.apply_distortion(a, s)
        }
        
        if filter_id not in filter_map:
            print(f"Filtro desconocido: {filter_id}")
            return audio
        
        try:
            return filter_map[filter_id](audio, sr)
        except Exception as e:
            print(f"Error aplicando filtro {filter_id}: {e}")
            return audio


# Ejemplo de uso
if __name__ == "__main__":
    # Generar audio de prueba (440 Hz durante 1 segundo)
    sr = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration))
    test_audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # Probar filtros
    filters_to_test = ['r', 'p', 'pu', 'pd', 'm', 'a', 'l']
    
    for fid in filters_to_test:
        print(f"Aplicando filtro '{fid}'...")
        filtered = AudioFilters.apply_filter(test_audio, sr, fid)
        
        # Guardar para escuchar
        output_file = f"test_filter_{fid}.wav"
        sf.write(output_file, filtered, sr)
        print(f"  Guardado: {output_file}")
