"""
Lock global para serializar la creación/actualización de providers TTS.

Vive en su propio módulo -- separado de core/tts_engine.py -- a propósito:
la recarga en caliente del motor TTS (gui/mainWindowComponents/tts_reload_mixin.py)
hace importlib.reload(core.tts_engine), lo que re-ejecuta el top-level del
módulo y, si el lock estuviera definido ahí, lo reemplazaría por un objeto
threading.Lock() nuevo bajo el mismo nombre global.

Cualquier código que ya hubiera entrado a una sección crítica con el lock
viejo (por ejemplo, el worker de audio_queue o el worker multi-voz
construyendo un TTSEngine) dejaría de estar sincronizado con código que,
tras la recarga, adquiere el lock nuevo -- reabriendo la condición de
carrera de inicialización de gRPC/OpenSSL (heap corruption 0xc0000374 en
Windows) que este lock existe para evitar.

Este módulo NUNCA se recarga en caliente, así que la identidad del lock
persiste sin importar cuántas veces se recargue core.tts_engine.
"""
import threading

PROVIDER_CREATION_LOCK = threading.Lock()
