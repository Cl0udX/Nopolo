#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Guía HTML para Nopolo TTS
"""

import json
from pathlib import Path

def load_json_config(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error al cargar {file_path}: {e}")
        return {}

def generate_voice_cards(voices_list):
    if not voices_list:
        return '<p style="color: #999; text-align: center; padding: 40px;">No hay voces configuradas</p>'
    cards = []
    for voice in sorted(voices_list, key=lambda x: x['id']):
        cards.append(f'<div class="item-card"><div class="item-id">{voice["id"]}</div><div class="item-name">{voice["name"]}</div></div>')
    return ''.join(cards)

def generate_sound_cards(sounds_list):
    if not sounds_list:
        return '<p style="color: #999; text-align: center; padding: 40px;">No hay sonidos configurados</p>'
    cards = []
    for sound in sorted(sounds_list, key=lambda x: int(x['id']) if x['id'].isdigit() else 9999):
        cards.append(f'<div class="item-card"><div class="item-id">{sound["id"]}</div><div class="item-name">{sound["name"]}</div></div>')
    return ''.join(cards)

def generate_background_cards(backgrounds_list):
    if not backgrounds_list:
        return '<p style="color: #999; text-align: center; padding: 40px;">No hay fondos configurados</p>'
    cards = []
    for bg in sorted(backgrounds_list, key=lambda x: x['id']):
        cards.append(f'<div class="item-card"><div class="item-id">{bg["id"]}</div><div class="item-name">{bg["name"]}</div></div>')
    return ''.join(cards)

def generate_html_guide():
    base_path = Path(__file__).parent
    voices_data = load_json_config(base_path / 'config' / 'voices.json')
    sounds_data = load_json_config(base_path / 'config' / 'sounds.json')
    backgrounds_data = load_json_config(base_path / 'config' / 'backgrounds.json')
    
    voices_list = []
    if 'profiles' in voices_data:
        for voice_id, voice_data in voices_data['profiles'].items():
            display_name = voice_data.get('display_name', voice_id)
            voices_list.append({'id': voice_id, 'name': display_name})
    
    sounds_list = []
    if 'sounds' in sounds_data:
        for sound in sounds_data['sounds']:
            sounds_list.append({'id': sound.get('id', '?'), 'name': sound.get('name', 'Sin nombre')})
    
    backgrounds_list = []
    if 'backgrounds' in backgrounds_data:
        for bg_id, bg_data in backgrounds_data['backgrounds'].items():
            bg_name = bg_data.get('name', bg_id)
            backgrounds_list.append({'id': bg_id, 'name': bg_name})
    
    output_path = base_path / 'guia_nopolo.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(generate_html_content(voices_list, sounds_list, backgrounds_list))
    
    print(f"Guía HTML generada: {output_path}")
    print(f"{len(voices_list)} voces | {len(sounds_list)} sonidos | {len(backgrounds_list)} fondos")

def generate_html_content(voices_list, sounds_list, backgrounds_list):
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nopolo TTS - Guía</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
.container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
.header h1 {{ font-size: 3em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
.header p {{ font-size: 1.2em; opacity: 0.9; }}
.main-tabs {{ display: flex; background: #f8f9fa; border-bottom: 3px solid #667eea; overflow-x: auto; }}
.main-tab {{ padding: 20px 40px; cursor: pointer; border: none; background: none; font-size: 1.2em; font-weight: 600; color: #666; transition: all 0.3s; white-space: nowrap; position: relative; }}
.main-tab:hover {{ background: #e9ecef; color: #667eea; }}
.main-tab.active {{ color: #667eea; background: white; }}
.main-tab.active::after {{ content: ''; position: absolute; bottom: -3px; left: 0; right: 0; height: 3px; background: #667eea; }}
.main-tab-content {{ display: none; padding: 40px; max-height: calc(100vh - 300px); overflow-y: auto; }}
.main-tab-content.active {{ display: block; }}
.info-box {{ background: #f8f9fa; border-left: 5px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 5px; }}
.info-box h3 {{ color: #764ba2; margin-bottom: 10px; font-size: 1.3em; }}
.info-box p {{ margin: 10px 0; line-height: 1.6; color: #333; }}
.syntax-item {{ background: white; border: 2px solid #e0e0e0; padding: 20px; margin: 15px 0; border-radius: 8px; transition: all 0.3s; }}
.syntax-item:hover {{ border-color: #667eea; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2); }}
.syntax-item h3 {{ color: #667eea; margin-bottom: 10px; font-size: 1.3em; }}
.syntax-item code {{ background: #f1f3f5; padding: 4px 10px; border-radius: 4px; color: #667eea; font-weight: bold; font-size: 1.1em; }}
.item-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 20px; }}
.item-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; transition: all 0.3s; }}
.item-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
.item-id {{ font-weight: bold; color: #667eea; font-size: 1.2em; margin-bottom: 5px; }}
.item-name {{ color: #666; }}
.example-box {{ background: #f8f9fa; border: 2px solid #667eea; border-radius: 10px; padding: 20px; margin: 20px 0; }}
.example-box h4 {{ color: #764ba2; margin-bottom: 15px; font-size: 1.3em; }}
.example-code {{ background: #2d2d2d; color: #f8f8f2; padding: 20px; border-radius: 8px; font-family: 'Courier New', monospace; line-height: 1.8; overflow-x: auto; margin: 10px 0; }}
.example-code .voice {{ color: #66d9ef; }}
.example-code .sound {{ color: #f92672; }}
.filter-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0; }}
.filter-item {{ background: white; padding: 12px; border-radius: 5px; border-left: 3px solid #667eea; font-family: monospace; }}
.filter-item strong {{ color: #667eea; font-size: 1.1em; }}
.section-title {{ color: #667eea; font-size: 1.8em; margin: 30px 0 20px 0; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
@media (max-width: 768px) {{
.header h1 {{ font-size: 2em; }}
.main-tab-content {{ padding: 20px; }}
.main-tab {{ padding: 15px 20px; font-size: 1em; }}
.item-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>🎙️ Nopolo TTS</h1>
<p>Sistema Multi-Voz con Efectos y Sonidos</p>
</div>

<div class="main-tabs">
<button class="main-tab active" onclick="openMainTab(event, 'guia')">📖 Guía de Uso</button>
<button class="main-tab" onclick="openMainTab(event, 'voces')">🎤 Voces</button>
<button class="main-tab" onclick="openMainTab(event, 'sonidos')">🔊 Sonidos</button>
<button class="main-tab" onclick="openMainTab(event, 'fondos')">🎵 Fondos</button>
<button class="main-tab" onclick="openMainTab(event, 'ejemplos')">💡 Ejemplos</button>
</div>

<div id="guia" class="main-tab-content active">
<h2 class="section-title">📢 CÓMO ENVIAR</h2>
<div class="info-box">
<h3>🔹 Agrega texto a tu suscripción</h3>
<p>Añade el texto que quieres que se reproduzca en tu mensaje de suscripción o donación.</p>
</div>
<div class="info-box">
<h3>🔺 Dona un mínimo de 10 bits</h3>
<p>Utiliza Cheers con al menos 10 bits para activar el TTS.</p>
</div>
<div class="info-box">
<h3>💎 Usa la recompensa de Puntos llamada '🔊 TTS'</h3>
<p>Canjea la recompensa de puntos del canal para enviar tu mensaje al TTS.</p>
</div>

<h2 class="section-title">📝 SINTAXIS</h2>
<div class="syntax-item">
<h3>🎤 Voces</h3>
<p>Usa las voces escribiendo un nombre de voz válido seguido de dos puntos:</p>
<p><code>enrique:</code> hola, cómo estás?</p>
</div>
<div class="syntax-item">
<h3>🔊 Sonidos</h3>
<p>Usa los sonidos escribiendo un nombre de sonido válido entre paréntesis:</p>
<p><code>(disparo2)</code></p>
</div>
<div class="syntax-item">
<h3>🎛️ Filtros de Audio</h3>
<p>Agrega un punto y el ID del filtro después de una voz o sonido:</p>
<p><code>enrique.r:</code> hola con eco</p>
<p><code>(disparo2.p)</code> disparo con efecto de teléfono</p>
</div>
<div class="syntax-item">
<h3>🎵 Fondos Musicales</h3>
<p>Agrega un punto y el ID del fondo después de una voz o sonido:</p>
<p><code>enrique.fa:</code> hola con música de fondo</p>
<p><code>(disparo2.fa)</code> disparo con fondo musical</p>
</div>

<h2 class="section-title">🎨 Filtros Disponibles</h2>
<div class="filter-grid">
<div class="filter-item"><strong>r</strong> - eco (reverb)</div>
<div class="filter-item"><strong>p</strong> - llamada (phone)</div>
<div class="filter-item"><strong>pu</strong> - aguda (pitch up)</div>
<div class="filter-item"><strong>pd</strong> - grave (pitch down)</div>
<div class="filter-item"><strong>m</strong> - afuera (muffled)</div>
<div class="filter-item"><strong>a</strong> - android</div>
<div class="filter-item"><strong>l</strong> - saturada (loud)</div>
<div class="filter-item"><strong>fc</strong> - fondo casa</div>
<div class="filter-item"><strong>fd</strong> - fondo desierto</div>
<div class="filter-item"><strong>fa</strong> - fondo ambiente</div>
</div>

<h2 class="section-title">🔢 MODO AVANZADO</h2>
<div class="info-box">
<h3>Usa IDs numéricos para ahorrar caracteres</h3>
<p><strong>Para sonidos:</strong> <code>(65)</code> en lugar de <code>(disparo2)</code></p>
<p><strong>Para voces:</strong> <code>9:</code> en lugar de <code>Rubius:</code></p>
</div>
</div>

<div id="voces" class="main-tab-content">
<h2 class="section-title">🎤 Voces Disponibles ({len(voices_list)} voces)</h2>
<div class="item-grid">{generate_voice_cards(voices_list)}</div>
</div>

<div id="sonidos" class="main-tab-content">
<h2 class="section-title">🔊 Sonidos Disponibles ({len(sounds_list)} sonidos)</h2>
<div class="item-grid">{generate_sound_cards(sounds_list)}</div>
</div>

<div id="fondos" class="main-tab-content">
<h2 class="section-title">🎵 Fondos Musicales Disponibles ({len(backgrounds_list)} fondos)</h2>
<div class="item-grid">{generate_background_cards(backgrounds_list)}</div>
</div>

<div id="ejemplos" class="main-tab-content">
<h2 class="section-title">💡 Ejemplos Prácticos</h2>
<div class="example-box">
<h4>Ejemplo 1: Conversación con efectos de naturaleza</h4>
<div class="example-code"><span class="voice">homero.fd:</span> hola postin estoy en la naturaleza <span class="sound">(71.fd)</span> <span class="voice">base_male.fd:</span> calma homero no te lo comas</div>
<p><strong>Explicación:</strong></p>
<ul style="margin-left: 20px; margin-top: 10px; line-height: 1.8;">
<li><code>homero.fd:</code> - Voz de Homero con fondo de desierto</li>
<li><code>(71.fd)</code> - Sonido #71 con fondo de desierto</li>
<li><code>base_male.fd:</code> - Voz masculina base con fondo de desierto</li>
</ul>
</div>
<div class="example-box">
<h4>Ejemplo 2: Conversación telefónica interrumpida</h4>
<div class="example-code"><span class="voice">vozBaseMasculina.fc:</span> hola como estan todos. <span class="sound">(330.fc)</span> Oh, una llamada. gente esperenme un momento que tengo una llamada <span class="sound">(327.fc)</span> halo, si diga? <span class="voice">homero.p:</span> cabron que haces, te estas demorando mucho tienes que iniciar stream</div>
<p><strong>Explicación:</strong></p>
<ul style="margin-left: 20px; margin-top: 10px; line-height: 1.8;">
<li><code>vozBaseMasculina.fc:</code> - Voz con fondo de casa</li>
<li><code>(330.fc)</code> - Sonido de notificación con fondo de casa</li>
<li><code>(327.fc)</code> - Sonido de teléfono con fondo de casa</li>
<li><code>homero.p:</code> - Voz de Homero con efecto de llamada telefónica</li>
</ul>
</div>
<div class="example-box">
<h4>Ejemplo 3: Acción con efectos de audio</h4>
<div class="example-code"><span class="voice">bugs:</span> Eh, qué hay de nuevo viejo? <span class="sound">(disparo.r)</span> <span class="voice">patolucas.r:</span> Auch! eso me dolió con eco!</div>
<p><strong>Explicación:</strong></p>
<ul style="margin-left: 20px; margin-top: 10px; line-height: 1.8;">
<li><code>bugs:</code> - Voz de Bugs Bunny</li>
<li><code>(disparo.r)</code> - Sonido de disparo con eco/reverb</li>
<li><code>patolucas.r:</code> - Voz de Pato Lucas con eco/reverb</li>
</ul>
</div>
<div class="example-box">
<h4>Ejemplo 4: Mezcla de voces y tonos</h4>
<div class="example-code"><span class="voice">dross:</span> Hola amigos <span class="sound">(aplausos)</span> <span class="voice">homero.pu:</span> Wuju! con voz aguda! <span class="voice">base_male.pd:</span> Y yo con voz grave...</div>
<p><strong>Explicación:</strong></p>
<ul style="margin-left: 20px; margin-top: 10px; line-height: 1.8;">
<li><code>dross:</code> - Voz de Dross normal</li>
<li><code>(aplausos)</code> - Sonido de aplausos</li>
<li><code>homero.pu:</code> - Voz de Homero con tono más agudo</li>
<li><code>base_male.pd:</code> - Voz base con tono más grave</li>
</ul>
</div>
</div>
</div>

<script>
function openMainTab(evt, tabName) {{
var tabContents = document.getElementsByClassName("main-tab-content");
for (var i = 0; i < tabContents.length; i++) {{ tabContents[i].classList.remove("active"); }}
var tabs = document.getElementsByClassName("main-tab");
for (var i = 0; i < tabs.length; i++) {{ tabs[i].classList.remove("active"); }}
document.getElementById(tabName).classList.add("active");
evt.currentTarget.classList.add("active");
}}
</script>
</body>
</html>'''

if __name__ == '__main__':
    print("Generando guía HTML para Nopolo TTS...")
    generate_html_guide()
