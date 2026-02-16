#!/usr/bin/env python3
"""
Script de prueba para validar la estabilidad del motor RVC
con las mejoras de manejo de memoria y recuperación de errores.
"""

import sys
import os
import time
import traceback
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

from core.rvc_engine import RVCEngine
from core.models.rvc_config import RVCConfig

def test_rvc_stability():
    """Prueba de estabilidad del motor RVC con múltiples conversiones"""
    
    print("=" * 60)
    print("PRUEBA DE ESTABILIDAD DEL MOTOR RVC")
    print("=" * 60)
    
    try:
        # Crear una configuración de prueba (ajusta según tus modelos)
        config = RVCConfig(
            model_id="homero_test",
            name="Homero Test",
            model_path="voices/homero/homero.pth",
            index_path="voices/homero/added_IVF113_Flat_nprobe_1_homero_v2.index",
            pitch_shift=0,
            index_rate=0.75,
            filter_radius=3,
            rms_mix_rate=0.25,
            protect=0.33
        )
        
        # Crear motor RVC
        print("1. Inicializando motor RVC...")
        rvc_engine = RVCEngine()
        
        # Cargar modelo
        print("2. Cargando modelo RVC...")
        rvc_engine.load_model(config)
        
        # Crear audio de prueba (silencio o tono simple)
        print("3. Creando audio de prueba...")
        test_audio_path = create_test_audio()
        
        # Probar múltiples conversiones
        print("4. Iniciando prueba de conversiones múltiples...")
        print(f"   - Límite de conversiones antes de reinicio: {rvc_engine.max_conversions_before_restart}")
        print(f"   - Total de conversiones a probar: 15")
        print("-" * 60)
        
        successful_conversions = 0
        failed_conversions = 0
        
        for i in range(15):
            try:
                print(f"\nConversión {i+1}/15:")
                
                # Crear un nuevo archivo de audio para cada conversión
                # ya que RVC lo elimina después de procesar
                current_test_audio = create_test_audio()
                
                # Usar el método con recuperación automática
                start_time = time.time()
                audio_data, sample_rate = rvc_engine.convert_with_recovery(
                    current_test_audio, 
                    max_retries=2
                )
                end_time = time.time()
                
                print(f"   ✅ Éxito ({end_time - start_time:.2f}s)")
                print(f"   📊 Contador de conversiones: {rvc_engine.conversion_count}")
                print(f"   🎵 Audio generado: {len(audio_data)} muestras @ {sample_rate}Hz")
                
                successful_conversions += 1
                
                # Pequeña pausa entre conversiones
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ Fallo: {e}")
                failed_conversions += 1
                
                # Verificar si el motor se recuperó
                if rvc_engine.conversion_count > 0:
                    print(f"   🔄 Motor aún operativo (contador: {rvc_engine.conversion_count})")
                else:
                    print(f"   ⚠️  Motor reseteado debido al error")
        
        print("\n" + "=" * 60)
        print("RESULTADOS DE LA PRUEBA")
        print("=" * 60)
        print(f"✅ Conversiones exitosas: {successful_conversions}")
        print(f"❌ Conversiones fallidas: {failed_conversions}")
        print(f"📈 Tasa de éxito: {(successful_conversions/15)*100:.1f}%")
        print(f"🔄 Reinicios automáticos: {successful_conversions // rvc_engine.max_conversions_before_restart}")
        
        # Prueba de limpieza de emergencia
        print("\n5. Probando limpieza de emergencia...")
        rvc_engine.emergency_cleanup()
        print("   ✅ Limpieza de emergencia completada")
        
        # Limpiar archivo de prueba
        if os.path.exists(test_audio_path):
            os.unlink(test_audio_path)
        
        print("\n🎉 PRUEBA COMPLETADA")
        
        return successful_conversions >= 10  # Considerar éxito si >= 10/15 conversiones
        
    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO EN PRUEBA: {e}")
        traceback.print_exc()
        return False

def create_test_audio():
    """Crea un archivo WAV de prueba simple"""
    import numpy as np
    import scipy.io.wavfile as wavfile
    
    # Generar un tono simple de 1 segundo
    sample_rate = 16000
    duration = 1.0
    frequency = 440  # A4
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.5  # 50% volume
    
    # Convertir a int16
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Guardar archivo temporal
    temp_path = "test_audio.wav"
    wavfile.write(temp_path, sample_rate, audio_data)
    
    return temp_path

def test_memory_usage():
    """Monitorea el uso de memoria durante las conversiones"""
    try:
        import psutil
        import gc
        
        print("\n" + "=" * 60)
        print("MONITOREO DE MEMORIA")
        print("=" * 60)
        
        process = psutil.Process()
        
        # Memoria inicial
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Memoria inicial: {initial_memory:.1f} MB")
        
        # Ejecutar prueba
        success = test_rvc_stability()
        
        # Forzar garbage collection
        gc.collect()
        
        # Memoria final
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"Memoria final: {final_memory:.1f} MB")
        print(f"Cambio de memoria: {final_memory - initial_memory:+.1f} MB")
        
        return success
        
    except ImportError:
        print("psutil no disponible - omitiendo monitoreo de memoria")
        return test_rvc_stability()

if __name__ == "__main__":
    print("Iniciando prueba de estabilidad RVC...")
    print("Este script probará el manejo de memoria y recuperación de errores.")
    print("Presiona Ctrl+C para detener la prueba en cualquier momento.\n")
    
    try:
        success = test_memory_usage()
        
        if success:
            print("\n🎉 PRUEBA SUPERADA - El motor RVC es estable")
            sys.exit(0)
        else:
            print("\n⚠️  PRUEBA FALLIDA - Se detectaron problemas de estabilidad")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  PRUEBA INTERRUMPIDA POR EL USUARIO")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 ERROR INESPERADO: {e}")
        traceback.print_exc()
        sys.exit(1)