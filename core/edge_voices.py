"""
Lista todas las voces disponibles de Edge TTS.
"""
import asyncio
import edge_tts

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
    """Obtiene las voces verificadas y funcionales de Edge TTS (Feb 2026)"""
    return {
        'Español México': [
            'es-MX-DaliaNeural',    # Mujer - Muy estable
            'es-MX-JorgeNeural',    # Hombre - La mejor para Goku
        ],
        'Español España': [
            'es-ES-AlvaroNeural',   # Hombre
            'es-ES-ElviraNeural',   # Mujer
            'es-ES-XimenaNeural',   # Mujer
        ],
        'Español Argentina': [
            'es-AR-ElenaNeural',    # Mujer
            'es-AR-TomasNeural',    # Hombre
        ],
        'Español Colombia': [
            'es-CO-GonzaloNeural',  # Hombre
            'es-CO-SalomeNeural',   # Mujer
        ],
        'Español Chile': [
            'es-CL-CatalinaNeural', # Mujer
            'es-CL-LorenzoNeural',  # Hombre
        ],
        'Español Perú': [
            'es-PE-AlexNeural',     # Hombre
            'es-PE-CamilaNeural',   # Mujer
        ],
        'Español Bolivia': [
            'es-BO-MarceloNeural',  # Hombre
            'es-BO-SofiaNeural',    # Mujer
        ],
        'Español Costa Rica': [
            'es-CR-JuanNeural',     # Hombre
            'es-CR-MariaNeural',    # Mujer
        ],
        'Español Cuba': [
            'es-CU-BelkysNeural',   # Mujer
            'es-CU-ManuelNeural',   # Hombre
        ],
        'Español Ecuador': [
            'es-EC-AndreaNeural',   # Mujer
            'es-EC-LuisNeural',     # Hombre
        ],
        'Español Guatemala': [
            'es-GT-AndresNeural',   # Hombre
            'es-GT-MartaNeural',    # Mujer
        ],
        'Español Honduras': [
            'es-HN-CarlosNeural',   # Hombre
            'es-HN-KarlaNeural',    # Mujer
        ],
        'Español Nicaragua': [
            'es-NI-FedericoNeural', # Hombre
            'es-NI-YolandaNeural',  # Mujer
        ],
        'Español Panamá': [
            'es-PA-MargaritaNeural', # Mujer
            'es-PA-RobertoNeural',   # Hombre
        ],
        'Español Paraguay': [
            'es-PY-MarioNeural',    # Hombre
            'es-PY-TaniaNeural',    # Mujer
        ],
        'Español Puerto Rico': [
            'es-PR-KarinaNeural',   # Mujer
            'es-PR-VictorNeural',   # Hombre
        ],
        'Español El Salvador': [
            'es-SV-LorenaNeural',   # Mujer
            'es-SV-RodrigoNeural',  # Hombre
        ],
        'Español USA': [
            'es-US-AlonsoNeural',   # Hombre
            'es-US-PalomaNeural',   # Mujer
        ],
        'Español Uruguay': [
            'es-UY-MateoNeural',    # Hombre
            'es-UY-ValentinaNeural', # Mujer
        ],
        'Español Venezuela': [
            'es-VE-PaolaNeural',    # Mujer
            'es-VE-SebastianNeural', # Hombre
        ],
        'Español República Dominicana': [
            'es-DO-EmilioNeural',   # Hombre
            'es-DO-RamonaNeural',   # Mujer
        ],
        'Español Guinea Ecuatorial': [
            'es-GQ-JavierNeural',   # Hombre
            'es-GQ-TeresaNeural',   # Mujer
        ],
        'Inglés US': [
            'en-US-AvaNeural',
            'en-US-AndrewNeural',
            'en-US-EmmaNeural',
            'en-US-BrianNeural',
            'en-US-AnaNeural',
            'en-US-AndrewMultilingualNeural',
            'en-US-AriaNeural',
            'en-US-AvaMultilingualNeural',
            'en-US-BrianMultilingualNeural',
            'en-US-ChristopherNeural',
            'en-US-EmmaMultilingualNeural',
            'en-US-EricNeural',
            'en-US-GuyNeural',
            'en-US-JennyNeural',
            'en-US-MichelleNeural',
            'en-US-RogerNeural',
            'en-US-SteffanNeural'
        ],
        'Inglés UK': [
            'en-GB-LibbyNeural',
            'en-GB-MaisieNeural',
            'en-GB-RyanNeural',
            'en-GB-SoniaNeural',
            'en-GB-ThomasNeural'
        ],
        'Inglés Australia': [
            'en-AU-NatashaNeural',
            'en-AU-WilliamMultilingualNeural'
        ],
        'Inglés Canadá': [
            'en-CA-ClaraNeural',
            'en-CA-LiamNeural'
        ],
        'Inglés India': [
            'en-IN-NeerjaExpressiveNeural',
            'en-IN-NeerjaNeural',
            'en-IN-PrabhatNeural'
        ],
        'Inglés Irlanda': [
            'en-IE-ConnorNeural',
            'en-IE-EmilyNeural'
        ]
    }