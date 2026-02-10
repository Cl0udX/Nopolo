from TTS.utils.manage import ModelManager

# Obtener el manager
manager = ModelManager()

# Listar modelos TTS
models = manager.list_tts_models()

# Filtrar español
spanish_models = [m for m in models if '/es/' in m]

print("=== Modelos en Español ===")
for model in spanish_models:
    print(model)

print("\n=== Modelos Multilingües ===")
multilingual = [m for m in models if 'multilingual' in m]
for model in multilingual:
    print(model)