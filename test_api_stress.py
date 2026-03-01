#!/usr/bin/env python
"""
Test de stress para la API - Martilla el endpoint multi-voz 50 veces.
Esto ayuda a identificar si el problema está en el worker thread o concurrencia.

Ejecutar:
1. Primero inicia la app: python main.py
2. Luego en otra terminal: python test_api_stress.py

python test_api_stress.py --requests 100 --delay 0.3
"""
import requests
import time
import sys

API_URL = "http://localhost:8000/api/tts/multivoice"

def test_stress(num_requests=50, delay=0.5):
    """
    Envía múltiples requests al endpoint multi-voz.
    
    Args:
        num_requests: Número de requests a enviar
        delay: Pausa entre requests en segundos
    """
    print("=" * 60)
    print("STRESS TEST - API MULTI-VOZ")
    print("=" * 60)
    print(f"URL: {API_URL}")
    print(f"Requests: {num_requests}")
    print(f"Delay: {delay}s")
    print("=" * 60 + "\n")
    
    successes = 0
    failures = 0
    
    for i in range(num_requests):
        print(f"[{i+1}/{num_requests}] Enviando request...", end=" ")
        
        try:
            response = requests.post(
                API_URL,
                json={
                    "text": "homero: hola mundo (1) goku: que tal",
                    "author": f"test_user_{i+1}"
                },
                timeout=60  # Timeout generoso
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"OK - Queue pos: {data.get('queue_position', '?')}")
                successes += 1
            else:
                print(f"ERROR HTTP {response.status_code}: {response.text[:100]}")
                failures += 1
        
        except requests.exceptions.Timeout:
            print("TIMEOUT - El servidor no respondió en 60s")
            failures += 1
        
        except requests.exceptions.ConnectionError as e:
            print(f"CONNECTION ERROR - ¿Se crasheó el servidor?")
            print(f"  Detalle: {e}")
            failures += 1
            print("\nDETENIENDO TEST - El servidor parece haber crasheado")
            break
        
        except Exception as e:
            print(f"EXCEPTION: {type(e).__name__}: {e}")
            failures += 1
        
        # Pausa entre requests
        if i < num_requests - 1:
            time.sleep(delay)
    
    print("\n" + "=" * 60)
    print("RESULTADOS")
    print("=" * 60)
    print(f"Exitosos: {successes}")
    print(f"Fallidos: {failures}")
    print(f"Total: {num_requests}")
    
    if failures == 0:
        print("\nTODOS LOS TESTS PASARON - El problema NO está en la API")
    else:
        print(f"\nHUBO {failures} FALLOS - Revisar logs del servidor")


def test_single_voice_stress(num_requests=30):
    """Test alternativo: solo voces simples sin sonidos"""
    print("\n" + "=" * 60)
    print("TEST ALTERNATIVO - VOZ SIMPLE")
    print("=" * 60 + "\n")
    
    API_URL_SINGLE = "http://localhost:8000/api/tts"
    
    for i in range(num_requests):
        print(f"[{i+1}/{num_requests}] Voz simple...", end=" ")
        
        try:
            response = requests.post(
                API_URL_SINGLE,
                json={
                    "text": "Hola mundo esta es una prueba",
                    "voice_id": "homero"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                print("OK")
            else:
                print(f"ERROR {response.status_code}")
        
        except Exception as e:
            print(f"CRASH: {e}")
            break
        
        time.sleep(0.3)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Stress test para API Nopolo")
    parser.add_argument("--requests", "-n", type=int, default=50, help="Número de requests")
    parser.add_argument("--delay", "-d", type=float, default=0.5, help="Delay entre requests")
    parser.add_argument("--single", action="store_true", help="Test solo voz simple")
    
    args = parser.parse_args()
    
    if args.single:
        test_single_voice_stress(args.requests)
    else:
        test_stress(args.requests, args.delay)