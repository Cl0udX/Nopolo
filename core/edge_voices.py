"""
Lista todas las voces disponibles de Edge TTS.
"""
import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import edge_tts
from core.paths import get_edge_voices_config

load_dotenv()

# Ruta al JSON de voces — usa paths.py o variable de entorno como override
_env_override = os.getenv("EDGE_VOICES_JSON", "")
VOICES_JSON_PATH = Path(_env_override) if _env_override else get_edge_voices_config()


async def get_all_voices():
    """Obtiene todas las voces disponibles de Edge TTS"""
    voices = await edge_tts.list_voices()
    return voices


def get_voices_by_language(language_code: str = None):
    """
    Obtiene voces filtradas por idioma.
    
    Args:
        language_code: Código de idioma (ej: "es", "en"). Si es None, retorna todas.
    
    Returns:
        Lista de diccionarios con info de voces
    """
    voices = asyncio.run(get_all_voices())
    
    if language_code:
        voices = [v for v in voices if v['Locale'].startswith(language_code)]
    
    # Formatear para uso más fácil
    formatted = []
    for v in voices:
        formatted.append({
            'id': v['ShortName'],
            'name': v['FriendlyName'],
            'gender': v['Gender'],
            'locale': v['Locale'],
            'language': v['Locale'].split('-')[0]
        })
    
    return formatted


def get_spanish_voices():
    """Obtiene todas las voces en español"""
    return get_voices_by_language('es')


def get_english_voices():
    """Obtiene todas las voces en inglés"""
    return get_voices_by_language('en')


def get_popular_voices():
    """Carga voces desde JSON"""
    if not VOICES_JSON_PATH.exists():
        print(f"No se encontró {VOICES_JSON_PATH}, usando voces por defecto")
        return _get_default_voices()
    
    try:
        with open(VOICES_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertir formato JSON a formato antiguo (solo IDs)
        result = {}
        for category, voices in data['voices'].items():
            result[category] = [v['id'] for v in voices]
        
        return result
    except Exception as e:
        print(f"Error cargando {VOICES_JSON_PATH}: {e}")
        return _get_default_voices()


def _get_default_voices():
    """Voces por defecto si no existe el JSON"""
    return {
        'Español México': ['es-MX-DaliaNeural', 'es-MX-JorgeNeural'],
        'Inglés US': ['en-US-AvaNeural', 'en-US-AndrewNeural']
    }