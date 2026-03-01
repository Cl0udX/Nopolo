#!/usr/bin/env python
"""
Script de prueba aislado para diagnosticar el crash en multi-voz.

Ejecutar con:
    python test_multi_voice.py
    
Esto probará el procesamiento multi-voz de forma aislada sin GUI.
"""
import sys
import os
import faulthandler
import logging
import traceback
import gc

# Activar faulthandler
faulthandler.enable()

# Logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_multi_voice_debug.log', encoding='utf-8', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info("=" * 60)
logging.info("TEST MULTI-VOZ - DIAGNÓSTICO AISLADO")
logging.info("=" * 60)


def test_basic_imports():
    """Test 1: Verificar que los imports básicos funcionan"""
    logging.info("\n[TEST 1] Verificando imports básicos...")
    try:
        from core.voice_manager import VoiceManager
        logging.info("  ✅ VoiceManager importado")
        
        from core.tts_engine import TTSEngine
        logging.info("  ✅ TTSEngine importado")
        
        from core.rvc_engine import RVCEngine
        logging.info("  ✅ RVCEngine importado")
        
        from core.advanced_processor import AdvancedAudioProcessor
        logging.info("  ✅ AdvancedAudioProcessor importado")
        
        return True
    except Exception as e:
        logging.error(f"  ❌ Error en imports: {e}")
        traceback.print_exc()
        return False


def test_voice_manager():
    """Test 2: Verificar que VoiceManager carga las voces"""
    logging.info("\n[TEST 2] Verificando VoiceManager...")
    try:
        from core.voice_manager import VoiceManager
        
        vm = VoiceManager()
        profiles = vm.profiles
        
        logging.info(f"  ✅ VoiceManager cargado con {len(profiles)} perfiles")
        
        # Listar voces con RVC
        rvc_voices = [p for p in profiles.values() if p.rvc_config and p.rvc_config.enabled]
        logging.info(f"  📊 Voces con RVC: {len(rvc_voices)}")
        for v in rvc_voices:
            logging.info(f"     - {v.display_name}: {v.rvc_config.model_path}")
        
        return vm
    except Exception as e:
        logging.error(f"  ❌ Error en VoiceManager: {e}")
        traceback.print_exc()
        return None


def test_single_voice(voice_manager):
    """Test 3: Procesar UNA sola voz con RVC"""
    logging.info("\n[TEST 3] Probando UNA sola voz con RVC...")
    
    try:
        from core.tts_engine import TTSEngine
        from core.rvc_engine import RVCEngine
        import soundfile as sf
        import tempfile
        
        # Buscar una voz con RVC
        voice = None
        for p in voice_manager.profiles.values():
            if p.rvc_config and p.rvc_config.enabled:
                voice = p
                break
        
        if not voice:
            logging.warning("  ⚠️ No hay voces con RVC configuradas")
            return True
        
        logging.info(f"  Usando voz: {voice.display_name}")
        
        # Crear TTS
        tts = TTSEngine()
        tts.update_config(voice.tts_config)
        
        # Generar TTS
        logging.info("  Generando TTS...")
        tts_file = tts.synthesize("Hola mundo, esta es una prueba")
        tts_audio, tts_sr = sf.read(tts_file, dtype='float32')
        os.unlink(tts_file)
        logging.info(f"  ✅ TTS generado: {len(tts_audio)} samples")
        
        # Crear RVC
        logging.info("  Creando RVC Engine...")
        rvc = RVCEngine()
        
        # Cargar modelo
        logging.info(f"  Cargando modelo RVC: {voice.rvc_config.model_path}")
        rvc.load_model(voice.rvc_config)
        logging.info("  ✅ Modelo RVC cargado")
        
        # Convertir
        logging.info("  Convirtiendo voz...")
        rvc_input = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        rvc_input.close()
        sf.write(rvc_input.name, tts_audio, tts_sr)
        
        rvc_audio, rvc_sr = rvc.convert(rvc_input.name)
        os.unlink(rvc_input.name)
        
        logging.info(f"  ✅ Voz convertida: {len(rvc_audio)} samples")
        
        # Limpiar
        rvc.emergency_cleanup()
        del rvc
        del tts
        gc.collect()
        
        logging.info("  ✅ Test 3 completado - Una voz funciona correctamente")
        return True
        
    except Exception as e:
        logging.error(f"  ❌ Error en test de voz única: {e}")
        traceback.print_exc()
        return False


def test_multi_voice_sequential(voice_manager):
    """Test 4: Procesar MÚLTIPLES voces SECUENCIALMENTE"""
    logging.info("\n[TEST 4] Probando MÚLTIPLES voces SECUENCIALMENTE...")
    
    try:
        from core.tts_engine import TTSEngine
        from core.rvc_engine import RVCEngine
        import soundfile as sf
        import tempfile
        
        # Buscar dos voces con RVC
        rvc_voices = [p for p in voice_manager.profiles.values() 
                      if p.rvc_config and p.rvc_config.enabled]
        
        if len(rvc_voices) < 2:
            logging.warning("  ⚠️ Se necesitan al menos 2 voces con RVC")
            return True
        
        voices_to_test = rvc_voices[:2]
        logging.info(f"  Probando con: {[v.display_name for v in voices_to_test]}")
        
        for i, voice in enumerate(voices_to_test):
            logging.info(f"\n  --- Voz {i+1}/{len(voices_to_test)}: {voice.display_name} ---")
            
            # Crear TTS NUEVO para cada voz
            tts = TTSEngine()
            tts.update_config(voice.tts_config)
            
            # Generar TTS
            tts_file = tts.synthesize(f"Hola, soy {voice.display_name}")
            tts_audio, tts_sr = sf.read(tts_file, dtype='float32')
            os.unlink(tts_file)
            logging.info(f"    TTS generado: {len(tts_audio)} samples")
            
            # Crear RVC NUEVO para cada voz
            rvc = RVCEngine()
            rvc.load_model(voice.rvc_config)
            logging.info(f"    Modelo RVC cargado")
            
            # Convertir
            rvc_input = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            rvc_input.close()
            sf.write(rvc_input.name, tts_audio, tts_sr)
            
            rvc_audio, rvc_sr = rvc.convert(rvc_input.name)
            os.unlink(rvc_input.name)
            logging.info(f"    Voz convertida: {len(rvc_audio)} samples")
            
            # LIMPIAR TODO antes de la siguiente voz
            logging.info(f"    Limpiando recursos...")
            rvc.emergency_cleanup()
            del rvc
            del tts
            gc.collect()
            logging.info(f"    ✅ Recursos limpiados")
        
        logging.info("\n  ✅ Test 4 completado - Múltiples voces secuenciales funcionan")
        return True
        
    except Exception as e:
        logging.error(f"  ❌ Error en test de múltiples voces: {e}")
        traceback.print_exc()
        return False


def test_advanced_processor(voice_manager):
    """Test 5: Probar AdvancedAudioProcessor directamente"""
    logging.info("\n[TEST 5] Probando AdvancedAudioProcessor...")
    
    try:
        from core.advanced_processor import AdvancedAudioProcessor
        
        # Crear procesador
        processor = AdvancedAudioProcessor(
            voice_manager=voice_manager,
            tts_engine=None,
            rvc_engine=None
        )
        logging.info("  ✅ AdvancedAudioProcessor creado")
        
        # Mensaje de prueba simple
        test_message = "homero: hola mundo"
        
        logging.info(f"  Procesando: '{test_message}'")
        audio, sr = processor.process_message(test_message)
        
        logging.info(f"  ✅ Audio generado: {len(audio)} samples a {sr} Hz")
        
        # Limpiar
        del processor
        gc.collect()
        
        return True
        
    except Exception as e:
        logging.error(f"  ❌ Error en AdvancedAudioProcessor: {e}")
        traceback.print_exc()
        return False


def test_multi_voice_full(voice_manager):
    """Test 6: Probar mensaje multi-voz completo"""
    logging.info("\n[TEST 6] Probando mensaje multi-voz COMPLETO...")
    
    try:
        from core.advanced_processor import AdvancedAudioProcessor
        
        # Crear procesador
        processor = AdvancedAudioProcessor(
            voice_manager=voice_manager,
            tts_engine=None,
            rvc_engine=None
        )
        
        # Mensaje multi-voz
        test_message = "homero: como estas (1) goku: todo bien"
        
        logging.info(f"  Procesando: '{test_message}'")
        audio, sr = processor.process_message(test_message)
        
        logging.info(f"  ✅ Audio multi-voz generado: {len(audio)} samples")
        
        # Limpiar
        del processor
        gc.collect()
        
        return True
        
    except Exception as e:
        logging.error(f"  ❌ Error en multi-voz completo: {e}")
        traceback.print_exc()
        return False


def main():
    logging.info("Iniciando tests de diagnóstico...\n")
    
    # Test 1: Imports
    if not test_basic_imports():
        logging.error("\n❌ FALLO en Test 1 - No se pueden continuar los tests")
        return
    
    # Test 2: VoiceManager
    voice_manager = test_voice_manager()
    if not voice_manager:
        logging.error("\n❌ FALLO en Test 2 - No se pueden continuar los tests")
        return
    
    # Test 3: Una sola voz
    if not test_single_voice(voice_manager):
        logging.error("\n❌ FALLO en Test 3 - El problema está en el procesamiento de una sola voz")
        return
    
    # Test 4: Múltiples voces secuenciales
    if not test_multi_voice_sequential(voice_manager):
        logging.error("\n❌ FALLO en Test 4 - El problema está en procesar múltiples voces")
        return
    
    # Test 5: AdvancedAudioProcessor simple
    if not test_advanced_processor(voice_manager):
        logging.error("\n❌ FALLO en Test 5 - El problema está en AdvancedAudioProcessor")
        return
    
    # Test 6: Multi-voz completo
    if not test_multi_voice_full(voice_manager):
        logging.error("\n❌ FALLO en Test 6 - El problema está en el procesamiento multi-voz completo")
        return
    
    logging.info("\n" + "=" * 60)
    logging.info("✅ TODOS LOS TESTS PASARON")
    logging.info("=" * 60)
    logging.info("\nEl problema puede estar en:")
    logging.info("  1. La interacción con la GUI")
    logging.info("  2. El worker thread del API")
    logging.info("  3. El reproductor de audio")
    logging.info("\nRevisa nopolo_debug.log para más detalles")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"\n❌ EXCEPCIÓN NO MANEJADA: {e}")
        traceback.print_exc()
    except KeyboardInterrupt:
        logging.info("\n\nTest interrumpido por usuario")