# Guía de Release — Nopolo

Cómo compilar y publicar una nueva versión para cada plataforma.

---

## Arquitectura general

```
version.json (en GitHub)
    ↑ lee               ↓ descarga ZIP
  App del usuario    Cloudflare R2
                    (almacena los ZIPs)
```

- `version.json` vive en GitHub. La app lo consulta al arrancar para saber si hay update.
- Los ZIPs (binarios compilados) viven en Cloudflare R2. Son pesados (1-3 GB), GitHub no los acepta.
- **Solo se guarda la última versión por plataforma** en R2 para ahorrar espacio.

---

## Plataformas y sus repos

| Plataforma         | Argumento            | Repo de compilación          | Sufijo ZIP        |
|--------------------|----------------------|------------------------------|-------------------|
| macOS              | `--platform macos`          | `workspace/Nopolo_mac/`      | `mac`             |
| Windows CPU        | `--platform windows_cpu`    | `workspace/Nopolo_cpu/`      | `win-cpu`         |
| Windows GPU 12.4   | `--platform windows_cuda124`| `workspace/Nopolo_cuda124/`  | `win-cuda124`     |
| Windows GPU 12.8   | `--platform windows_cuda128`| `workspace/Nopolo_cuda128/`  | `win-cuda128`     |

Cada plataforma se compila **en su propio repo** con su propio venv.  
macOS se compila en Mac. Windows se compila en una máquina Windows.

---

## Requisito: `.env.upload`

El archivo `.env.upload` contiene las credenciales de Cloudflare R2.  
Está en `.gitignore` — **nunca se sube al repo**.  
Usa `.env.upload.example` como plantilla si necesitas recrearlo.

```
R2_ENDPOINT=https://xxxx.r2.cloudflarestorage.com
R2_BUCKET=nopolo-updates
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
```

---

## Flujo completo de un release

### 1 · Editar la versión

En `version.json` (repo dev `Compu/Nopolo/`), cambia el número:

```json
{
  "version": "1.1.1",
  ...
}
```

### 2 · Copiar `version.json` al repo de compilación

```bash
cp /Users/santo/Documents/Compu/Nopolo/version.json \
   /Users/santo/Documents/workspace/Nopolo_mac/version.json
```

### 3 · Compilar (en el repo de compilación)

```bash
cd /Users/santo/Documents/workspace/Nopolo_mac
python build_executable.py --yes
```

Genera `dist/Nopolo-1.1.1/` con el binario completo. Tarda ~5-10 min.

### 4 · Publicar a R2 (en el repo de compilación)

```bash
python release.py --platform macos
```

Esto hace automáticamente:
1. Lee la versión de `version.json`
2. Comprime `dist/Nopolo-1.1.1/` → `Nopolo-1.1.1-mac.zip`
3. Borra `Nopolo-1.1.0-mac.zip` de R2 (versión anterior)
4. Sube `Nopolo-1.1.1-mac.zip` a R2
5. Actualiza `version.json` → `"macos": "Nopolo-1.1.1-mac.zip"`
6. Hace `git commit + push` de `version.json`

### 5 · Verificar

Al publicar, la app verá que `1.1.1 > 1.1.0` y mostrará el diálogo de actualización.

---

## `--dry-run`: probar sin subir nada

```bash
python release.py --platform macos --dry-run
```

Hace todo **excepto** subir a R2 y hacer git push.  
Útil para verificar que el ZIP se crea correctamente antes de publicar.

---

## Flags disponibles

| Flag                  | Descripción                                              |
|-----------------------|----------------------------------------------------------|
| `--platform <nombre>` | **Obligatorio.** Plataforma a publicar (ver tabla arriba)|
| `--dry-run`           | Simula el proceso sin subir ni hacer push                |
| `--no-git`            | Sube a R2 pero no hace git commit/push                   |
| `--keep-zip`          | No borra el ZIP local después de subir                   |

---

## Ejemplo: release completo de todas las plataformas

```bash
# 1. Editar version.json → "version": "1.2.0"
# 2. Compilar en cada máquina/repo, luego en cada uno:

python release.py --platform macos           # en Mac
python release.py --platform windows_cpu     # en PC sin GPU
python release.py --platform windows_cuda124 # en PC con GPU CUDA 12.4
python release.py --platform windows_cuda128 # en PC con GPU CUDA 12.8
```

Solo el **primer** `release.py` que se ejecute hará el `git push` de `version.json`.  
Los siguientes también harán push (con sus respectivas entradas actualizadas).

---

## Simular una actualización (prueba sin recompilar)

Para testear el sistema de auto-update sin tener que recompilar:

```bash
# Tienes el binario 1.1.1 ya compilado y publicado.
# Solo cambia la versión en version.json y vuelve a publicar:

# 1. Editar version.json → "version": "1.1.2"
# 2. (opcional) dry-run para verificar:
python release.py --platform macos --dry-run

# 3. Publicar:
python release.py --platform macos

# 4. Abrir el binario 1.1.1 → aparece el diálogo "1.1.2 disponible"
```

---

## Estructura de `version.json` después de un release

```json
{
  "version": "1.1.1",
  "app_name": "Nopolo",
  "update_url": "https://raw.githubusercontent.com/Cl0udX/Nopolo/main/version.json",
  "downloads_base_url": "https://pub-b2d8e9c3fb894b55bfca2ac1281ce346.r2.dev",
  "downloads": {
    "macos":           "Nopolo-1.1.1-mac.zip",
    "windows_cpu":     "Nopolo-1.1.1-win-cpu.zip",
    "windows_cuda124": "Nopolo-1.1.1-win-cuda124.zip",
    "windows_cuda128": "Nopolo-1.1.1-win-cuda128.zip"
  }
}
```
