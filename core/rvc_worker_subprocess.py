"""
Worker subprocess for isolated RVC conversion.

This script runs as a separate process to completely isolate
the RVC conversion from the main process.

Usage:
    python -m core.rvc_worker_subprocess <input_wav> <output_wav> <voice_config_json>
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import traceback
import gc
import tempfile
import time

# Add root directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def log(message: str):
    """Log with timestamp for debugging - ASCII only to avoid encoding issues"""
    timestamp = time.strftime("%H:%M:%S")
    # Replace non-ASCII characters
    safe_message = message.encode('ascii', 'replace').decode('ascii')
    print(f"[RVC-Worker {timestamp}] {safe_message}", flush=True)


def cleanup_gpu():
    """Limpieza agresiva de GPU"""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            gc.collect()
            log("GPU limpiada")
    except Exception as e:
        log(f"Error limpiando GPU: {e}")


def convert_rvc(input_wav: str, output_wav: str, voice_config: dict) -> bool:
    """
    Ejecuta la conversiรณn RVC de forma aislada.
    
    Args:
        input_wav: Archivo WAV de entrada
        output_wav: Archivo WAV de salida
        voice_config: Configuraciรณn de la voz
        
    Returns:
        True si exitoso, False si falla
    """
    rvc_engine = None
    
    try:
        log(f"Iniciando conversiรณn RVC")
        log(f"  Input: {input_wav}")
        log(f"  Output: {output_wav}")
        log(f"  Modelo: {voice_config.get('model_path', 'N/A')}")
        
        # Importar RVCEngine solo cuando se necesita
        from core.rvc_engine import RVCEngine
        
        # Crear motor RVC
        log("Creando motor RVC...")
        rvc_engine = RVCEngine()
        
        # Construir RVC config
        # NOTA: RVCConfig usa pitch_shift, no pitch
        from core.models.rvc_config import RVCConfig
        rvc_config = RVCConfig(
            model_id=voice_config.get('model_id', 'unknown'),
            name=voice_config.get('name', 'Unknown'),
            model_path=voice_config.get('model_path', ''),
            index_path=voice_config.get('index_path', ''),
            pitch_shift=voice_config.get('pitch_shift', 0),  # pitch_shift, no pitch
            filter_radius=voice_config.get('filter_radius', 3),
            rms_mix_rate=voice_config.get('rms_mix_rate', 0.25),
            protect=voice_config.get('protect', 0.33),
            enabled=True
        )
        
        # Cargar modelo
        log("Cargando modelo RVC...")
        rvc_engine.load_model(rvc_config)
        
        # Convertir
        log("Ejecutando conversiรณn...")
        audio_data, sample_rate = rvc_engine.convert(input_wav)
        
        # Guardar resultado
        log(f"Guardando audio ({len(audio_data)} samples a {sample_rate} Hz)...")
        import soundfile as sf
        sf.write(output_wav, audio_data, sample_rate)
        
        log("Conversiรณn completada exitosamente")
        return True
        
    except Exception as e:
        log(f"ERROR en conversiรณn RVC: {e}")
        traceback.print_exc()
        return False
        
    finally:
        # Limpieza agresiva
        log("Ejecutando limpieza...")
        if rvc_engine:
            try:
                rvc_engine.emergency_cleanup()
            except:
                pass
            rvc_engine = None
        
        cleanup_gpu()
        gc.collect()
        log("Limpieza completada")


def main():
    """Punto de entrada del subprocess"""
    if len(sys.argv) < 4:
        print("Uso: python -m core.rvc_worker_subprocess <input_wav> <output_wav> <voice_config_json>")
        sys.exit(1)
    
    input_wav = sys.argv[1]
    output_wav = sys.argv[2]
    voice_config_json = sys.argv[3]
    
    # Parsear configuraciรณn
    try:
        voice_config = json.loads(voice_config_json)
    except json.JSONDecodeError as e:
        log(f"Error parseando JSON: {e}")
        sys.exit(1)
    
    # Verificar que existe el archivo de entrada
    if not os.path.exists(input_wav):
        log(f"Archivo de entrada no existe: {input_wav}")
        sys.exit(1)
    
    # Ejecutar conversiรณn
    success = convert_rvc(input_wav, output_wav, voice_config)
    
    # Salir con cรณdigo apropiado
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()