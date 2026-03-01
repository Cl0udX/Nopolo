#!/usr/bin/env python
"""
Test mejorado para encontrar el Segmentation Fault en multi-voz
"""
import sys
import os
import faulthandler
import logging
import traceback
import gc

# Activar faulthandler VERBOSE
faulthandler.enable(all_threads=True)

# Logging
logging.basicConfig(
    level=logging.INFO,  # Menos verbose para ver mejor
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('segfault_debug.log', encoding='utf-8', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

print("\n" + "="*70)
print("BUSCANDO SEGMENTATION FAULT EN MULTI-VOZ")
print("="*70 + "\n")

def safe_test(func, *args, **kwargs):
    """Ejecuta un test y continúa incluso si falla"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.error(f"ERROR {func.__name__} fallo: {e}")
        traceback.print_exc()
        return None  # Continuar de todos modos

def test_single_voice_fixed():
    """Test con el fix del archivo temporal"""
    logging.info("\n[TEST] UNA VOZ con fix de archivos temporales...")
    
    from core.voice_manager import VoiceManager
    from core.tts_engine import TTSEngine
    from core.rvc_engine import RVCEngine
    import soundfile as sf
    import tempfile
    
    vm = VoiceManager()
    
    # Buscar voz con RVC
    voice = None
    for p in vm.profiles.values():
        if p.rvc_config and p.rvc_config.enabled:
            voice = p
            break
    
    if not voice:
        logging.warning("No hay voces con RVC")
        return
    
    logging.info(f"Usando: {voice.display_name}")
    
    # TTS
    tts = TTSEngine()
    tts.update_config(voice.tts_config)
    tts_file = tts.synthesize("Test simple")
    tts_audio, tts_sr = sf.read(tts_file, dtype='float32')
    
    # Limpiar TTS
    try:
        os.unlink(tts_file)
    except:
        pass
    
    # RVC
    rvc = RVCEngine()
    rvc.load_model(voice.rvc_config)
    
    # Usar with para manejar el archivo temporal
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        sf.write(tmp_path, tts_audio, tts_sr)
        rvc_audio, rvc_sr = rvc.convert(tmp_path)
        logging.info(f"OK Conversion: {len(rvc_audio)} samples")
    finally:
        # Intentar limpiar
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    # Cleanup
    rvc.emergency_cleanup()
    del rvc, tts
    gc.collect()
    
    logging.info("OK Test single voice completado")

def test_two_voices_sequential():
    """Test con DOS voces SECUENCIALMENTE (donde probablemente crashea)"""
    logging.info("\n[TEST] DOS VOCES SECUENCIALES...")
    logging.info("WARNING: AQUI ES DONDE PROBABLEMENTE CRASHEA\n")
    
    from core.voice_manager import VoiceManager
    from core.tts_engine import TTSEngine
    from core.rvc_engine import RVCEngine
    import soundfile as sf
    import tempfile
    import torch
    
    vm = VoiceManager()
    
    # Buscar 2 voces
    rvc_voices = [p for p in vm.profiles.values() if p.rvc_config and p.rvc_config.enabled][:2]
    
    if len(rvc_voices) < 2:
        logging.warning("Se necesitan 2 voces con RVC")
        return
    
    logging.info(f"Voces: {[v.display_name for v in rvc_voices]}\n")
    
    for i, voice in enumerate(rvc_voices):
        logging.info(f"--- VOZ {i+1}: {voice.display_name} ---")
        
        # TTS
        logging.info("  1. Creando TTS...")
        tts = TTSEngine()
        tts.update_config(voice.tts_config)
        
        logging.info("  2. Generando audio...")
        tts_file = tts.synthesize(f"Hola soy {voice.display_name}")
        tts_audio, tts_sr = sf.read(tts_file, dtype='float32')
        
        try:
            os.unlink(tts_file)
        except:
            pass
        
        # RVC
        logging.info("  3. Creando RVC Engine...")
        rvc = RVCEngine()
        
        logging.info(f"  4. Cargando modelo: {voice.rvc_config.model_path}")
        rvc.load_model(voice.rvc_config)
        
        # Archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            logging.info("  5. Escribiendo audio temporal...")
            sf.write(tmp_path, tts_audio, tts_sr)
            
            logging.info("  6. Convirtiendo con RVC... WARNING: CRITICO")
            rvc_audio, rvc_sr = rvc.convert(tmp_path)
            
            logging.info(f"  OK Conversion: {len(rvc_audio)} samples")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        # LIMPIEZA AGRESIVA
        logging.info("  7. Limpiando recursos...")
        rvc.emergency_cleanup()
        del rvc
        del tts
        
        # Limpiar CUDA
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        gc.collect()
        
        logging.info(f"  OK Voz {i+1} completada\n")
    
    logging.info("OK Test dos voces completado SIN CRASH")

def test_advanced_processor():
    """Test con AdvancedAudioProcessor (el que usa la API)"""
    logging.info("\n[TEST] ADVANCED AUDIO PROCESSOR (API)...")
    logging.info("WARNING: ESTE ES EL QUE USA LA API REAL\n")
    
    from core.voice_manager import VoiceManager
    from core.advanced_processor import AdvancedAudioProcessor
    
    vm = VoiceManager()
    processor = AdvancedAudioProcessor(
        voice_manager=vm,
        tts_engine=None,
        rvc_engine=None
    )
    
    # Test simple
    logging.info("Test 1: Una sola voz")
    audio1, sr1 = processor.process_message("homero: hola mundo")
    logging.info(f"OK Audio generado: {len(audio1)} samples\n")
    
    # Test multi-voz
    logging.info("Test 2: Multi-voz SIN sonidos")
    audio2, sr2 = processor.process_message("homero: hola goku: que tal")
    logging.info(f"OK Audio generado: {len(audio2)} samples\n")
    
    # Test con sonido (donde puede crashear)
    logging.info("Test 3: Multi-voz CON sonido WARNING: CRITICO")
    audio3, sr3 = processor.process_message("homero: hola (1) goku: que tal")
    logging.info(f"OK Audio generado: {len(audio3)} samples\n")
    
    del processor
    gc.collect()
    
    logging.info("OK AdvancedAudioProcessor completado SIN CRASH")

def main():
    print("Iniciando tests...\n")
    
    # Test 1: Una sola voz (con fix)
    safe_test(test_single_voice_fixed)
    
    input("\n[PAUSA] Presiona ENTER para continuar con DOS voces (donde puede crashear)...")
    
    # Test 2: Dos voces secuenciales (AQUI DEBERIA CRASHEAR)
    safe_test(test_two_voices_sequential)
    
    input("\n[PAUSA] Presiona ENTER para probar AdvancedAudioProcessor...")
    
    # Test 3: Advanced Processor (el que usa la API)
    safe_test(test_advanced_processor)
    
    print("\n" + "="*70)
    print("OK TODOS LOS TESTS PASARON SIN SEGFAULT")
    print("="*70)
    print("\nSi llegaste aqui SIN CRASH, el problema esta en:")
    print("  1. El worker thread de la API")
    print("  2. La reproduccion de audio")
    print("  3. Alguna interaccion con la GUI")
    print("\nRevisa segfault_debug.log para mas detalles")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrumpido")
    except Exception as e:
        print(f"\nERROR CRASH: {e}")
        traceback.print_exc()