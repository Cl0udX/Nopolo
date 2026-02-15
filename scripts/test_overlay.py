#!/usr/bin/env python3
"""
Script de prueba para verificar el overlay en los 4 casos.
Ejecutar con: python scripts/test_overlay.py
"""
import requests
import time
import json

API_URL = "http://localhost:8000"

def print_test(name, description):
    print(f"\n{'='*60}")
    print(f" TEST: {name}")
    print(f"{'='*60}")
    print(f" {description}")
    print()

def test_normal_endpoint():
    """Test 1: Modo normal desde endpoint"""
    print_test(
        "Modo Normal - Endpoint",
        "Debe mostrar texto limpio SIN sintaxis resaltada"
    )
    
    payload = {
        "text": "Hola mundo, este es un mensaje de prueba normal"
    }
    
    print(f"Enviando a /api/tts:")
    print(f"   {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(f"{API_URL}/api/tts", json=payload)
        print(f"Respuesta: {response.status_code}")
        print(f"   {response.json()}")
        print()
        print("Verifica en el overlay:")
        print("   - Debe mostrar: 'Hola mundo, este es un mensaje de prueba normal'")
        print("   - Sin colores, sin resaltado")
        print("   - Nombre de voz visible (ej: 'VozBaseMasculina')")
    except Exception as e:
        print(f"Error: {e}")

def test_multivoice_endpoint():
    """Test 2: Modo Nopolo desde endpoint"""
    print_test(
        "Modo Nopolo - Endpoint",
        "Debe mostrar sintaxis CON resaltado (voces azul, sonidos rojo)"
    )
    
    payload = {
        "text": "9: un millon de años mas tarde (22) homero: doh!"
    }
    
    print(f"Enviando a /api/tts/multivoice:")
    print(f"   {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(f"{API_URL}/api/tts/multivoice", json=payload)
        print(f"Respuesta: {response.status_code}")
        print(f"   {response.json()}")
        print()
        print(" Verifica en el overlay:")
        print("   - Debe mostrar: '9: un millon de años mas tarde (22) homero: doh!'")
        print("   - '9:' y 'homero:' en AZUL (voces)")
        print("   - '(22)' en ROJO (sonido)")
        print("   - Nombre: 'Multi-Voz (API)'")
    except Exception as e:
        print(f" Error: {e}")

def test_with_author():
    """Test 3: Modo con autor personalizado"""
    print_test(
        "Modo con Autor - Endpoint",
        "Debe mostrar el nombre del autor en lugar del nombre de voz"
    )
    
    payload = {
        "text": "goku: te amo vegeta: no kakarato",
        "author": "postInCloud"
    }
    
    print(f" Enviando a /api/tts/multivoice con author:")
    print(f"   {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(f"{API_URL}/api/tts/multivoice", json=payload)
        print(f"Respuesta: {response.status_code}")
        print(f"{response.json()}")
        print()
        print("Verifica en el overlay:")
        print("  - Debe mostrar sintaxis resaltada")
        print("  - Nombre: 'postInCloud' (NO 'Multi-Voz (API)')")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🧪 TEST DE OVERLAY - NOPOLO TTS                     ║
║                                                              ║
║  Este script enviará mensajes a la API para verificar       ║
║  que el overlay muestre correctamente los 4 casos:          ║
║                                                              ║
║  1. ✅ Modo Normal desde endpoint                            ║
║  2. ✅ Modo Nopolo desde endpoint                            ║
║  3. ✅ Modo con autor personalizado                          ║
║                                                              ║
║  IMPORTANTE:                                                 ║
║  - El servidor API debe estar corriendo (puerto 8000)       ║
║  - El overlay debe estar visible en OBS                     ║
║  - Abre la consola del navegador (F12) para ver logs        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    input("Presiona ENTER para comenzar las pruebas...")
    
    # Test 1: Modo normal
    test_normal_endpoint()
    input("\n⏸️  Presiona ENTER para continuar con el siguiente test...")
    time.sleep(2)
    
    # Test 2: Modo Nopolo
    test_multivoice_endpoint()
    input("\nPresiona ENTER para continuar con el siguiente test...")
    time.sleep(2)
    
    # Test 3: Con autor
    test_with_author()
    
    print("\n" + "="*60)
    print("Tests completados!")
    print("="*60)
    print()
    print("Checklist de verificación:")
    print("   [ ] Test 1: Texto limpio, sin sintaxis")
    print("   [ ] Test 2: Sintaxis resaltada (azul/rojo)")
    print("   [ ] Test 3: Nombre 'postInCloud' visible")
    print()
    print("Para tests desde GUI:")
    print("   - Activa/desactiva checkbox 'Modo Nopolo'")
    print("   - Escribe texto con/sin sintaxis")
    print("   - Verifica logs en consola de Python")
    print()

if __name__ == "__main__":
    main()
