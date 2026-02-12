# run_api.py
"""
Ejecuta solo el servidor REST API sin interfaz gráfica.
Útil para correr como servicio en segundo plano.
"""
import argparse
from core.tts_engine import TTSEngine
from core.rvc_engine import RVCEngine
from core.audio_queue import AudioQueue
from core.voice_manager import VoiceManager
from api.rest_server import TTSAPIServer


def main():
    parser = argparse.ArgumentParser(description="Nopolo TTS REST API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host para el servidor (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor (default: 8000)")
    parser.add_argument("--config", default="config/voices.json", help="Archivo de configuración de voces")
    
    args = parser.parse_args()
    
    print("="*60)
    print("Nopolo TTS - REST API Server")
    print("="*60)
    
    # Inicializar componentes
    print("Inicializando motores TTS y RVC...")
    tts_engine = TTSEngine()
    rvc_engine = RVCEngine()
    
    print("Cargando perfiles de voz...")
    voice_manager = VoiceManager(config_path=args.config)
    print(f"{len(voice_manager.profiles)} voces cargadas")
    
    print("Iniciando cola de audio...")
    audio_queue = AudioQueue(tts_engine, rvc_engine)
    
    # Crear y arrancar servidor
    print(f"Iniciando servidor REST API en {args.host}:{args.port}...")
    server = TTSAPIServer(
        voice_manager=voice_manager,
        audio_queue=audio_queue,
        host=args.host,
        port=args.port
    )
    
    server.start()
    
    print("\n" + "="*60)
    print("Servidor iniciado correctamente")
    print("="*60)
    print(f"API REST: http://{args.host}:{args.port}")
    print(f"Documentación: http://localhost:{args.port}/docs")
    print(f"Prueba rápida:")
    print(f"   curl -X POST http://localhost:{args.port}/api/tts \\")
    print(f'        -H "Content-Type: application/json" \\')
    print(f'        -d \'{{"text": "Hola desde Streamer bot"}}\'')
    print("\nPresiona Ctrl+C para detener el servidor")
    print("="*60)
    
    try:
        # Mantener el programa corriendo
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nDeteniendo servidor...")
        server.stop()
        print("Servidor detenido. ¡Hasta luego!")


if __name__ == "__main__":
    main()