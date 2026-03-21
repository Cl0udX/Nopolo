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
from .rvc_isolated import RVCIsolatedEngine  # fallback aislado
from .rvc_persistent_worker import get_persistent_rvc_engine  # worker persistente
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
        # Per-voice cached TTS engines (one per voice_id).
        # Allows parallel synthesis without shared-state collisions.
        self._tts_engines: dict = {}
    
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
    
    def process_message(self, message: str, target_sr: int = 16000,
                        return_timeline: bool = False):
        """
        Procesa un mensaje complejo y genera audio.

        Pipeline:
          1. Parsear segmentos
          2. Procesar cada segmento SIN fondo (audio limpio)
          3. Concatenar con crossfade corto de 60ms (solo elimina clicks)
          4. Superponer capa de fondo continua (respetando volumen del JSON)
          5. Fade global de 120ms solo en los extremos del audio completo
          6. Normalizar

        Args:
            return_timeline: Si True, devuelve (audio, sr, timeline) donde
                timeline es lista de dicts {start_sec, end_sec, profile, peaks}.
                peaks = [(offset_sec, is_talking), ...] pre-calculados.
        """
        import gc
        import traceback

        print(f"Procesando mensaje: '{message}'")

        # ── 1. Parsear ────────────────────────────────────────────────────────
        segments = self.parser.parse(message)
        print(f"{len(segments)} segmentos detectados")

        # ── 2a. Pre-sintetizar todo el TTS en paralelo ───────────────────────
        pre_tts = self._pre_synthesize_all(segments)

        # ── 2. Procesar segmentos (SIN fondos – se mezclan al final) ─────────
        clean_chunks: List[np.ndarray] = []
        # bg_timeline: qué fondo va en qué muestra del audio final
        # {bg_id, start_sample, end_sample}
        bg_timeline: List[dict] = []
        # avatar_timeline: [(start_sec, end_sec, VoiceProfile_or_None, peaks)]
        # peaks = [(offset_sec, is_talking), ...]   — pre-calculados si return_timeline
        avatar_timeline: List[dict] = []
        current_sample = 0

        for i, segment in enumerate(segments):
            print(f"\n{'='*50}")
            print(f"Segmento {i+1}/{len(segments)}: {segment.type.value}")
            print(f"{'='*50}")

            chunk = None
            try:
                if segment.type == SegmentType.VOICE:
                    chunk = self._process_voice_segment(segment, target_sr,
                                                        apply_background=False,
                                                        pre_tts_path=pre_tts.get(i))
                elif segment.type == SegmentType.SOUND:
                    chunk = self._process_sound_segment(segment, target_sr,
                                                        apply_background=False)
                else:
                    print(f"Tipo de segmento desconocido: {segment.type}")
                    continue

                if chunk is not None and len(chunk) > 0:
                    clean_chunks.append(chunk)
                    end_sample = current_sample + len(chunk)
                    for bg_id in self._get_background_filters(segment):
                        bg_timeline.append({
                            'bg_id':  bg_id,
                            'start':  current_sample,
                            'end':    end_sample,
                        })

                    # Capturar bloque para el timeline de avatares
                    if return_timeline and segment.type == SegmentType.VOICE:
                        profile = None
                        if segment.voice:       # ← atributo correcto del MessageSegment
                            try:
                                profile = self.voice_manager.get_profile_by_name_or_id(segment.voice)
                            except Exception:
                                pass
                        # Pre-calcular peaks para este chunk
                        peaks = self._compute_avatar_peaks(chunk, target_sr)
                        avatar_entry = {
                            'start_sec': current_sample / target_sr,
                            'end_sec':   end_sample / target_sr,
                            'profile':   profile,
                            'peaks':     peaks,
                            'is_sound':  False,
                        }
                        # Agregar campos desglosados para compatibilidad con rest_server.py
                        if profile:
                            avatar_entry['display_name'] = profile.display_name
                            avatar_entry['image_idle'] = profile.rvc_config.image_idle if profile.rvc_config else None
                            avatar_entry['image_talking'] = profile.rvc_config.image_talking if profile.rvc_config else None
                        avatar_timeline.append(avatar_entry)
                    elif return_timeline and segment.type == SegmentType.SOUND:
                        avatar_timeline.append({
                            'start_sec': current_sample / target_sr,
                            'end_sec':   end_sample / target_sr,
                            'profile':   None,
                            'peaks':     [],
                            'is_sound':  True,
                        })

                    current_sample = end_sample
                    del chunk

            except Exception as e:
                print(f"Error procesando segmento {i+1}: {e}")
                traceback.print_exc()
            finally:
                gc.collect()

        if not clean_chunks:
            print("No se generó audio")
            empty = (np.zeros(target_sr, dtype=np.float32), target_sr)
            return (*empty, []) if return_timeline else empty

        # ── 3. Concatenar con crossfade corto ────────────────────────────────
        print(f"\nCombinando {len(clean_chunks)} chunks...")
        final_voice = self._concat_smooth(clean_chunks, target_sr, xfade_ms=60)

        # ── 4. Capa de fondo continua ────────────────────────────────────────
        if bg_timeline:
            final_audio = self._overlay_backgrounds(final_voice, target_sr, bg_timeline)
        else:
            final_audio = final_voice

        # ── 5. Fade global SOLO en extremos ──────────────────────────────────
        final_audio = self._apply_global_fade(final_audio, target_sr, fade_ms=120)

        # ── 6. Normalizar ────────────────────────────────────────────────────
        max_val = np.max(np.abs(final_audio))
        if max_val > 0:
            final_audio = final_audio / max_val * 0.92

        if not np.isfinite(final_audio).all():
            print("Advertencia: valores inválidos en audio final, limpiando...")
            final_audio = np.nan_to_num(final_audio, nan=0.0, posinf=0.9, neginf=-0.9)

        print(f"Audio final generado: {len(final_audio)/target_sr:.2f}s")
        result = (final_audio.astype(np.float32), target_sr)
        return (*result, avatar_timeline) if return_timeline else result

    # ── Helpers de combinación ─────────────────────────────────────────────────

    def _compute_avatar_peaks(self, audio: np.ndarray, sr: int,
                               interval_ms: int = 40,
                               threshold: float = 0.05) -> list:
        """
        Pre-calcula eventos boca-abierta/cerrada para un chunk de audio.

        Returns:
            [(offset_sec, is_talking), ...] en intervalos de interval_ms
        """
        chunk_size = max(1, int(sr * interval_ms / 1000))
        flat = audio.flatten()
        peaks = []
        for i in range(0, len(flat), chunk_size):
            chunk = flat[i:i + chunk_size]
            rms = float(np.sqrt(np.mean(chunk ** 2))) if len(chunk) > 0 else 0.0
            peaks.append((i / sr, rms > threshold))
        return peaks

    def _concat_smooth(self, chunks: List[np.ndarray], sr: int,
                       xfade_ms: int = 60) -> np.ndarray:
        """
        Concatena chunks con un crossfade MUY corto entre ellos.
        Solo elimina clicks en las uniones — NO desvanece las voces.
        """
        if not chunks:
            return np.array([], dtype=np.float32)
        if len(chunks) == 1:
            return chunks[0].copy()

        xfade = int(sr * xfade_ms / 1000)
        result = chunks[0].copy()

        for chunk in chunks[1:]:
            overlap = min(xfade, len(result), len(chunk))
            if overlap > 0:
                t = np.linspace(0, np.pi, overlap)
                fade_out = 0.5 * (1 + np.cos(t))
                fade_in  = 0.5 * (1 - np.cos(t))
                blended  = result[-overlap:] * fade_out + chunk[:overlap] * fade_in
                result   = np.concatenate([result[:-overlap], blended, chunk[overlap:]])
            else:
                result = np.concatenate([result, chunk])

        return result.astype(np.float32)

    def _apply_global_fade(self, audio: np.ndarray, sr: int,
                           fade_ms: int = 120) -> np.ndarray:
        """
        Aplica fade-in y fade-out de fade_ms ms SOLO en los extremos del audio
        completo. Las voces intermedias no se tocan.
        """
        if len(audio) == 0:
            return audio

        fade_s = min(int(sr * fade_ms / 1000), len(audio) // 4)
        if fade_s <= 0:
            return audio

        result = audio.copy()
        t = np.linspace(0, np.pi, fade_s)
        result[:fade_s]  *= 0.5 * (1 - np.cos(t))
        result[-fade_s:] *= 0.5 * (1 + np.cos(t))
        return result

    def _overlay_backgrounds(self, voice: np.ndarray, sr: int,
                              bg_timeline: List[dict]) -> np.ndarray:
        """
        Construye una capa de fondo continua y la mezcla sobre la voz.

        Reglas:
        - El volumen del fondo es el configurado en backgrounds.json
        - Segmentos consecutivos con el MISMO fondo se reproducen como un loop
          continuo (sin restart en cada segmento)
        - El fondo hace fade-in al entrar y fade-out al salir (300ms)
        - Se pueden apilar varios fondos en el mismo segmento (p.ej. fa + fb)
        - La voz nunca se modifica: solo se suma la capa de fondo
        """
        total_len = len(voice)
        bg_layer  = np.zeros(total_len, dtype=np.float32)

        # Cache SOLO del array de audio (resampled, normalizado a peak 1.0).
        # El volumen NO se cachea: se lee siempre fresco del JSON para que
        # cambios en backgrounds.json tomen efecto sin reiniciar la app.
        audio_cache: dict = {}

        def get_bg(bg_id: str):
            """Retorna (audio_normalizado, volume_actual). Audio cacheado, volumen fresco."""
            # Cargar y cachear el array de audio la primera vez
            if bg_id not in audio_cache:
                data = self.background_manager.load_background_audio(bg_id)
                if data is None:
                    audio_cache[bg_id] = None
                    return None
                bg_audio, bg_sr, _vol = data
                if bg_sr != sr:
                    from scipy.signal import resample as sp_resample
                    new_len  = int(len(bg_audio) * sr / bg_sr)
                    bg_audio = sp_resample(bg_audio, new_len).astype(np.float32)
                peak = np.max(np.abs(bg_audio))
                if peak > 0:
                    bg_audio = bg_audio / peak   # Normalizar a peak 1.0
                audio_cache[bg_id] = bg_audio

            cached_audio = audio_cache[bg_id]
            if cached_audio is None:
                return None

            # Leer el volumen SIEMPRE fresco (costo mínimo: solo stat() si el JSON no cambió)
            bg_vol = self.background_manager.get_background_volume(bg_id)
            return cached_audio, bg_vol

        # ------------------------------------------------------------------
        # Fusionar entradas consecutivas del MISMO fondo en un único span
        # Esto garantiza que el loop del fondo sea continuo entre segmentos
        # ------------------------------------------------------------------
        merged: dict = {}  # bg_id → [(start, end), ...]
        for entry in bg_timeline:
            bg_id = entry['bg_id']
            start = max(0, entry['start'])
            end   = min(total_len, entry['end'])
            if start >= end:
                continue
            if bg_id not in merged:
                merged[bg_id] = [(start, end)]
            else:
                last_s, last_e = merged[bg_id][-1]
                # Considerar consecutivos si están a menos de 5ms de distancia
                gap_tolerance = int(sr * 0.005)
                if start <= last_e + gap_tolerance:
                    merged[bg_id][-1] = (last_s, max(last_e, end))
                else:
                    merged[bg_id].append((start, end))

        # ------------------------------------------------------------------
        # Rellenar bg_layer con cada fondo en sus spans
        # ------------------------------------------------------------------
        for bg_id, spans in merged.items():
            bg_data = get_bg(bg_id)
            if bg_data is None:
                print(f"  Fondo '{bg_id}' no encontrado, ignorando")
                continue
            bg_audio, bg_vol = bg_data

            for span_start, span_end in spans:
                span_len = span_end - span_start
                if span_len <= 0:
                    continue

                # Loop continuo del fondo para cubrir toda la duración del span
                if len(bg_audio) < span_len:
                    reps      = int(np.ceil(span_len / len(bg_audio)))
                    bg_tiled  = np.tile(bg_audio, reps)[:span_len]
                else:
                    bg_tiled  = bg_audio[:span_len].copy()

                # Acumular (permite múltiples fondos en el mismo rango)
                bg_layer[span_start:span_end] += bg_tiled * bg_vol
                print(f"  Fondo '{bg_id}' (vol={bg_vol:.2f}): "
                      f"{span_start/sr:.2f}s – {span_end/sr:.2f}s")

        if np.max(np.abs(bg_layer)) == 0:
            return voice   # Sin fondo activo → devolver voz sin cambios

        # ------------------------------------------------------------------
        # Fade-in/out del fondo (300ms) al inicio y final de la región activa
        # Esto evita que el fondo entre/salga abruptamente
        # ------------------------------------------------------------------
        fade_s     = int(sr * 0.30)   # 300ms
        active_idx = np.where(np.abs(bg_layer) > 1e-8)[0]
        if len(active_idx) > 0:
            a_start = int(active_idx[0])
            a_end   = int(active_idx[-1]) + 1

            fi = min(fade_s, a_end - a_start)
            if fi > 0:
                t_in  = np.linspace(0, np.pi, fi)
                bg_layer[a_start:a_start + fi] *= 0.5 * (1 - np.cos(t_in))

            fo = min(fade_s, a_end - a_start)
            if fo > 0:
                t_out = np.linspace(0, np.pi, fo)
                bg_layer[a_end - fo:a_end] *= 0.5 * (1 + np.cos(t_out))

        # ------------------------------------------------------------------
        # Mezcla: voz al 100% + fondo con su volumen original
        # No re-normalizar — el volumen del JSON es el que manda
        # Solo hacemos clip suave para evitar distorsión
        # ------------------------------------------------------------------
        mixed = voice + bg_layer
        mixed = np.clip(mixed, -0.99, 0.99)
        return mixed.astype(np.float32)
    
    def _get_tts_engine_for_voice(self, voice_id: str) -> Optional["TTSEngine"]:
        """
        Retorna (o crea) un TTSEngine dedicado para este voice_id.
        Cada voz tiene su propio engine para que la syntheses paralelas
        no compartan estado.
        """
        if voice_id in self._tts_engines:
            return self._tts_engines[voice_id]

        voice_config = self.voice_manager.get_profile_by_name_or_id(voice_id)
        if not voice_config or not voice_config.enabled:
            return None

        cfg = voice_config.tts_config
        provider = getattr(cfg, 'provider_name', 'edge_tts')

        # TTSEngine creation must be sequential (gRPC init not thread-safe)
        engine = TTSEngine(config=cfg, provider_name=provider)
        self._tts_engines[voice_id] = engine
        return engine

    def _pre_synthesize_all(self, segments: List[MessageSegment]) -> dict:
        """
        Pre-sintetiza TTS de todos los segmentos de voz EN PARALELO usando
        un thread pool (funciona con Edge TTS y Google TTS).

        Engines se crean secuencialmente (gRPC init no es thread-safe) y luego
        se llama a .synthesize() en paralelo (I/O puro, sin estado compartido).

        Retorna {segment_index: wav_file_path}.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 1. Collect segments to synthesize
        tasks = []  # (segment_idx, voice_id, text)
        for i, segment in enumerate(segments):
            if segment.type != SegmentType.VOICE:
                continue
            voice_config = self.voice_manager.get_profile_by_name_or_id(segment.voice)
            if not voice_config or not voice_config.enabled:
                continue
            tasks.append((i, segment.voice, segment.content.strip()))

        if not tasks:
            return {}

        # 2. Ensure one TTSEngine per voice exists (sequential, with gRPC lock)
        seen_voices = set()
        for _, voice_id, _ in tasks:
            if voice_id not in seen_voices:
                seen_voices.add(voice_id)
                self._get_tts_engine_for_voice(voice_id)  # creates + caches if new

        # 3. Dispatch synthesis in parallel (I/O bound — threads are fine)
        def _synth_one(segment_idx, voice_id, text):
            engine = self._tts_engines.get(voice_id)
            if engine is None:
                return segment_idx, None
            try:
                # Each engine has its own state — safe to call concurrently
                wav_path = engine.synthesize(text)
                return segment_idx, wav_path
            except Exception as e:
                print(f"  [TTS-parallel] Error voz '{voice_id}': {e}")
                return segment_idx, None

        print(f"[TTS-parallel] Sintetizando {len(tasks)} segmento(s) en paralelo...")
        t0 = time.time()
        results = {}
        with ThreadPoolExecutor(max_workers=min(len(tasks), 6)) as pool:
            futures = {pool.submit(_synth_one, *t): t[0] for t in tasks}
            for fut in as_completed(futures):
                idx, path = fut.result()
                if path:
                    results[idx] = path
        print(f"[TTS-parallel] Listo en {time.time() - t0:.2f}s ({len(results)}/{len(tasks)} OK)")
        return results

    def _process_voice_segment(self, segment: MessageSegment, target_sr: int, apply_background: bool = True, pre_tts_path: Optional[str] = None) -> Optional[np.ndarray]:
        """
        Procesa un segmento de voz (TTS + RVC + Filtros).

        Args:
            segment: Segmento de voz
            target_sr: Sample rate objetivo
            apply_background: Si debe aplicar filtros de fondo (False para aplicación global)
            pre_tts_path: Ruta a un WAV de TTS pre-sintetizado en paralelo (opcional)

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
            print("  Creando RVC Engine PERSISTENTE (primera vez)...")
            # Worker persistente: carga Hubert UNA vez y lo mantiene en memoria.
            # Segunda conversion en adelante solo paga el costo de inferencia (~1-2s).
            rvc_engine = get_persistent_rvc_engine()
            self.rvc_engine = rvc_engine  # Guardar referencia para reutilizar

        try:
            # 1. TTS → Audio neutral
            print("Generando TTS...")

            if pre_tts_path:
                # Ya fue sintetizado en paralelo: usar directamente
                tts_file_path = pre_tts_path
            else:
                # Fallback secuencial: usar engine dedicado para esta voz
                voice_engine = self._get_tts_engine_for_voice(voice_id) or tts_engine
                voice_engine.update_config(voice_config.tts_config)
                tts_file_path = voice_engine.synthesize(text)

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

        # ── Normalización de loudness (RMS) ──────────────────────────────────
        # Los sonidos cargados desde disco pueden tener niveles muy distintos
        # a las voces TTS+RVC. Normalizamos al mismo RMS objetivo (~0.12)
        # para que sonidos y voces tengan percepción de volumen equivalente.
        TARGET_RMS = 0.12
        rms = np.sqrt(np.mean(audio ** 2))
        if rms > 1e-6:
            audio = audio * (TARGET_RMS / rms)
        np.clip(audio, -0.99, 0.99, out=audio)
        
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
