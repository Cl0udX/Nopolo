import os

# Ruta al archivo a parchear
filepath = r"C:\Users\Santiago\Documents\Canal\Nopolo\.venv\Lib\site-packages\TTS\utils\io.py"

# Leer el archivo
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Aplicar el parche
content = content.replace(
    'return torch.load(f, map_location=map_location, **kwargs)',
    'return torch.load(f, map_location=map_location, weights_only=False, **kwargs)'
)

# Guardar el archivo parcheado
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Parche aplicado exitosamente!")
print("Ahora puedes usar XTTS v2 con PyTorch 2.6 y tu RTX 5070 Ti")