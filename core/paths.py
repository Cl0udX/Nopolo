"""
Módulo central de rutas de Nopolo.

Detecta si la aplicación corre en modo BUILD (ejecutable compilado)
o en modo DEV (directorio de proyecto).

- En modo BUILD:
    - Windows : %APPDATA%\\Nopolo\\
    - macOS   : ~/Library/Application Support/Nopolo/
    - Linux   : ~/.local/share/Nopolo/

- En modo DEV:
    - Usa directamente las carpetas del proyecto (comportamiento anterior).

La variable de entorno NOPOLO_ENV puede forzar el modo:
    NOPOLO_ENV=build  → fuerza modo build (útil para testing)
    NOPOLO_ENV=dev    → fuerza modo dev   (valor por defecto en desarrollo)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SISTEMA DE MIGRACIÓN VERSIONADA CON HASHES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cada vez que se lanza una nueva versión de la app, el sistema compara
la versión del bundle contra la versión guardada en .schema_version.json.
Si difieren, aplica la estrategia correcta según el tipo de carpeta:

  backgrounds/   → ADD NEW FILES    : solo archivos nuevos, nunca sobreescribir.
  sounds/
  voices/

  config/*.json  → MERGE SMART      : añade claves/entradas nuevas sin tocar
                                       los valores del usuario.

  overlay/       → SMART REPLACE con hashes:
    Cada archivo del overlay se evalúa individualmente:

    Caso A — Primera ejecución (sin archivo de usuario):
      → Copiar directamente desde el bundle.

    Caso B — El bundle cambió Y el usuario NO tocó el archivo
      (hash_usuario == hash_bundle_anterior):
      → Reemplazar silenciosamente. El usuario tendrá la versión nueva.

    Caso C — El bundle cambió Y el usuario SÍ editó el archivo
      (hash_usuario != hash_bundle_anterior):
      → Renombrar el archivo del usuario a <nombre>.old
      → Copiar la versión nueva del bundle
      → Registrar en lista de notificaciones para mostrar popup al iniciar.

    Caso D — El bundle NO cambió (hash_bundle_actual == hash_bundle_anterior):
      → No tocar nada, independientemente de lo que tenga el usuario.

Los hashes (SHA-256) del bundle se guardan en .schema_version.json
después de cada migración, como referencia para la próxima actualización.

La función initialize_user_data() devuelve una lista de OverlayConflict
que main.py puede pasar a la GUI para mostrar el popup de notificación.
"""

import os
import sys
import json
import shutil
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Estructura de datos para notificaciones
# ──────────────────────────────────────────────

@dataclass
class OverlayConflict:
    """Representa un archivo del overlay que fue actualizado con conflicto."""
    filename: str          # ej: "overlay.html"
    old_path: Path         # ruta del .old que guardamos
    new_path: Path         # ruta de la versión nueva del bundle
    reason: str = ""       # descripción legible del cambio

# ──────────────────────────────────────────────
# Detección del modo de ejecución
# ──────────────────────────────────────────────

def _is_frozen() -> bool:
    """Devuelve True cuando se ejecuta como ejecutable PyInstaller."""
    return getattr(sys, "frozen", False)


def _configure_bundled_ffmpeg() -> None:
    """Apunta pydub al ffmpeg bundled cuando corremos como ejecutable.
    En sistemas frescos sin ffmpeg en PATH pydub falla al convertir MP3→WAV."""
    if not _is_frozen():
        return
    try:
        import pydub
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        ext = ".exe" if sys.platform == "win32" else ""
        ffmpeg_path  = base / f"ffmpeg{ext}"
        ffprobe_path = base / f"ffprobe{ext}"
        if ffmpeg_path.exists():
            pydub.AudioSegment.converter  = str(ffmpeg_path)
            pydub.AudioSegment.ffmpeg     = str(ffmpeg_path)
        if ffprobe_path.exists():
            pydub.AudioSegment.ffprobe    = str(ffprobe_path)
    except Exception:
        pass  # pydub no disponible aún, no es crítico aquí


_configure_bundled_ffmpeg()


def get_run_mode() -> str:
    """
    Devuelve 'build' o 'dev' según el entorno de ejecución.

    Orden de prioridad:
      1. Variable de entorno NOPOLO_ENV
      2. Detección automática (frozen → build, script → dev)
    """
    env_override = os.getenv("NOPOLO_ENV", "").strip().lower()
    if env_override in ("build", "dev"):
        return env_override
    return "build" if _is_frozen() else "dev"


# ──────────────────────────────────────────────
# Directorio base de la aplicación (binarios / código fuente)
# ──────────────────────────────────────────────

def get_app_base_dir() -> Path:
    """
    Directorio donde están los archivos de la aplicación (lectura).
    - build : _MEIPASS (internal de PyInstaller)
    - dev   : raíz del repositorio
    """
    if _is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_bundle_data_dir() -> Path:
    """
    Directorio donde están las carpetas editables empaquetadas con el build
    (backgrounds/, voices/, sounds/, overlay/, config/).

    - build : padre de _MEIPASS  ← build_executable.py las movió ahí afuera
    - dev   : raíz del repositorio (mismo que get_app_base_dir)
    """
    if _is_frozen():
        return Path(sys._MEIPASS).parent
    return get_app_base_dir()


# ──────────────────────────────────────────────
# Directorio de datos de usuario (lectura/escritura)
# ──────────────────────────────────────────────

def get_user_data_dir() -> Path:
    """
    Directorio donde se guardan los datos editables del usuario.

    - build/Windows : %APPDATA%\\Nopolo
    - build/macOS   : ~/Library/Application Support/Nopolo
    - build/Linux   : ~/.local/share/Nopolo
    - dev           : raíz del proyecto (igual que antes)
    """
    if get_run_mode() == "dev":
        return get_app_base_dir()

    platform = sys.platform
    if platform == "win32":
        appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "Nopolo"
    elif platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Nopolo"
    else:  # Linux y otros
        xdg = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(xdg) / "Nopolo"


# ──────────────────────────────────────────────
# Rutas de carpetas específicas
# ──────────────────────────────────────────────

def get_voices_dir() -> Path:
    return get_user_data_dir() / "voices"

def get_backgrounds_dir() -> Path:
    return get_user_data_dir() / "backgrounds"

def get_sounds_dir() -> Path:
    return get_user_data_dir() / "sounds"

def get_overlay_dir() -> Path:
    return get_user_data_dir() / "overlay"

def get_config_dir() -> Path:
    return get_user_data_dir() / "config"

# Rutas de archivos de configuración específicos
def get_voices_config() -> Path:
    return get_config_dir() / "voices.json"

def get_backgrounds_config() -> Path:
    return get_config_dir() / "backgrounds.json"

def get_sounds_config() -> Path:
    return get_config_dir() / "sounds.json"

def get_providers_config() -> Path:
    return get_config_dir() / "providers.json"

def get_app_settings_config() -> Path:
    return get_config_dir() / "app_settings.json"

def get_edge_voices_config() -> Path:
    return get_config_dir() / "edge_voices.json"

def get_overlay_html() -> Path:
    return get_overlay_dir() / "overlay.html"


# ──────────────────────────────────────────────
# Versión de esquema y hashes del bundle
# ──────────────────────────────────────────────

_SCHEMA_VERSION_FILE = ".schema_version.json"


def _file_sha256(path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo. Devuelve '' si no existe."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _get_bundle_version() -> str:
    """Lee la versión actual de la app desde version.json del bundle."""
    try:
        version_file = get_app_base_dir() / "version.json"
        with open(version_file, "r", encoding="utf-8") as f:
            return json.load(f).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def _load_schema_data() -> dict:
    """
    Carga el contenido completo de .schema_version.json del usuario.
    Estructura:
    {
      "version": "1.1.0",
      "overlay_hashes": {
        "overlay.html": "<sha256>",
        "overlay.css":  "<sha256>"
      }
    }
    """
    try:
        schema_file = get_user_data_dir() / _SCHEMA_VERSION_FILE
        with open(schema_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "0.0.0", "overlay_hashes": {}}


def _get_user_schema_version() -> str:
    return _load_schema_data().get("version", "0.0.0")


def _save_schema_data(version: str, overlay_hashes: dict) -> None:
    """Guarda la versión y los hashes del bundle en .schema_version.json."""
    try:
        schema_file = get_user_data_dir() / _SCHEMA_VERSION_FILE
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(
                {"version": version, "overlay_hashes": overlay_hashes},
                f, indent=2
            )
    except Exception as e:
        logger.warning(f"[paths] No se pudo guardar schema data: {e}")


def _compute_bundle_overlay_hashes(src: Path) -> dict:
    """Calcula los hashes SHA-256 de todos los archivos en el overlay del bundle."""
    hashes = {}
    if not src.exists():
        return hashes
    for item in src.rglob("*"):
        if item.is_file():
            rel = str(item.relative_to(src))
            hashes[rel] = _file_sha256(item)
    return hashes


# ──────────────────────────────────────────────
# Estrategias de migración
# ──────────────────────────────────────────────

def _parse_overlay_changelog(src: Path) -> dict:
    """
    Parsea overlay/CHANGELOG.md y devuelve un dict {filename: descripcion}.

    Formato esperado:
        ## overlay.html
        Línea 1 de descripción.
        Línea 2 de descripción.

        ## overlay.css
        Otra descripción.
    """
    changelog_path = src / "CHANGELOG.md"
    result: dict = {}
    if not changelog_path.exists():
        return result

    try:
        text = changelog_path.read_text(encoding="utf-8")
        current_file = None
        current_lines: list = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.startswith("## ") and not line.startswith("### "):
                # Guardar sección anterior
                if current_file and current_lines:
                    result[current_file] = "\n".join(current_lines).strip()
                current_file = line[3:].strip()
                current_lines = []
            elif current_file is not None:
                # Ignorar separadores y líneas de comentario genérico
                if line and not line.startswith("---") and not line.startswith("#"):
                    current_lines.append(line)

        # Guardar última sección
        if current_file and current_lines:
            result[current_file] = "\n".join(current_lines).strip()

    except Exception as e:
        logger.warning(f"[paths] overlay changelog: no se pudo parsear: {e}")

    return result


def _strategy_overlay_smart(
    src: Path,
    dst: Path,
    prev_bundle_hashes: dict
) -> List[OverlayConflict]:
    """
    SMART REPLACE para overlay/ — evalúa cada archivo individualmente.

    Casos:
      A. Archivo no existe en usuario        → copiar directamente.
      B. Bundle cambió, usuario NO lo tocó   → reemplazar silencioso.
      C. Bundle cambió, usuario SÍ lo tocó   → renombrar a .old + copiar nuevo + notificar.
      D. Bundle NO cambió                    → no tocar nada.

    Devuelve lista de OverlayConflict (vacía si no hubo conflictos).
    """
    if not src.exists():
        logger.warning(f"[paths] overlay: fuente no encontrada: {src}")
        return []

    changelog = _parse_overlay_changelog(src)

    dst.mkdir(parents=True, exist_ok=True)
    conflicts: List[OverlayConflict] = []

    for src_item in src.rglob("*"):
        if not src_item.is_file():
            continue

        rel        = src_item.relative_to(src)
        rel_str    = str(rel)
        dst_item   = dst / rel
        dst_item.parent.mkdir(parents=True, exist_ok=True)

        hash_new_bundle  = _file_sha256(src_item)
        hash_prev_bundle = prev_bundle_hashes.get(rel_str, "")
        hash_user        = _file_sha256(dst_item) if dst_item.exists() else ""

        bundle_changed = (hash_new_bundle != hash_prev_bundle)
        user_edited    = (hash_user != hash_prev_bundle) and (hash_user != "")
        first_run      = (hash_user == "")

        if first_run:
            # Caso A: primera vez
            shutil.copy2(src_item, dst_item)
            logger.info(f"[paths] overlay: instalado {rel_str}")

        elif not bundle_changed:
            # Caso D: nada cambió en el bundle → respetar al usuario
            logger.debug(f"[paths] overlay: sin cambios en bundle para {rel_str}")

        elif not user_edited:
            # Caso B: bundle cambió, usuario no tocó → reemplazar silencioso
            shutil.copy2(src_item, dst_item)
            logger.info(f"[paths] overlay: actualizado {rel_str} (sin ediciones del usuario)")

        else:
            # Caso C: bundle cambió Y usuario editó → .old + notificar
            old_path = dst_item.with_suffix(dst_item.suffix + ".old")
            # Si ya existe un .old anterior, lo sobreescribimos
            shutil.copy2(dst_item, old_path)
            shutil.copy2(src_item, dst_item)
            logger.info(
                f"[paths] overlay: CONFLICTO en {rel_str} — "
                f"versión del usuario guardada en {old_path.name}"
            )
            conflicts.append(OverlayConflict(
                filename=rel_str,
                old_path=old_path,
                new_path=dst_item,
                reason=changelog.get(rel_str, ""),
            ))

    return conflicts


def _merge_json(src_file: Path, dst_file: Path) -> None:
    """
    MERGE SMART para un archivo JSON individual.
    - Si el destino no existe → copiar directamente.
    - Si existe → combinar recursivamente:
        * Las claves nuevas del bundle se añaden con su valor por defecto.
        * Las claves que el usuario ya tiene se preservan intactas.
        * Para listas: se añaden entradas cuyo 'id'/'name' no exista.
    """
    if not src_file.exists():
        return

    dst_file.parent.mkdir(parents=True, exist_ok=True)

    if not dst_file.exists():
        shutil.copy2(src_file, dst_file)
        logger.info(f"[paths] merge: creado {dst_file.name}")
        return

    try:
        with open(src_file, "r", encoding="utf-8") as f:
            bundle_data = json.load(f)
        with open(dst_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        changed = _deep_merge(bundle_data, user_data)

        with open(dst_file, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)

        if changed:
            logger.info(f"[paths] merge: actualizado {dst_file.name} con nuevas claves del bundle")
        else:
            logger.debug(f"[paths] merge: {dst_file.name} sin cambios necesarios")

    except Exception as e:
        logger.warning(f"[paths] merge: error en {dst_file.name}: {e}")


def _deep_merge(bundle: dict, user: dict) -> bool:
    """Fusiona bundle → user recursivamente. Solo añade, nunca sobreescribe."""
    changed = False
    for key, bundle_val in bundle.items():
        if key not in user:
            user[key] = bundle_val
            logger.debug(f"[paths] merge: nueva clave '{key}' añadida")
            changed = True
        elif isinstance(bundle_val, dict) and isinstance(user[key], dict):
            if _deep_merge(bundle_val, user[key]):
                changed = True
        elif isinstance(bundle_val, list) and isinstance(user[key], list):
            if _merge_list(bundle_val, user[key]):
                changed = True
    return changed


def _merge_list(bundle_list: list, user_list: list) -> bool:
    """Añade a user_list entradas de bundle_list que no existan (por id/name)."""
    changed = False
    for bundle_item in bundle_list:
        if isinstance(bundle_item, dict):
            match_key = "id" if "id" in bundle_item else ("name" if "name" in bundle_item else None)
            if match_key:
                match_val = bundle_item[match_key]
                exists = any(
                    isinstance(u, dict) and u.get(match_key) == match_val
                    for u in user_list
                )
            else:
                exists = bundle_item in user_list
        else:
            exists = bundle_item in user_list

        if not exists:
            user_list.append(bundle_item)
            logger.debug(f"[paths] merge-list: nueva entrada añadida")
            changed = True
    return changed


def _strategy_add_new_files(src: Path, dst: Path) -> None:
    """ADD NEW FILES — backgrounds/, sounds/, voices/. Nunca sobreescribir."""
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        relative = item.relative_to(src)
        dest_item = dst / relative
        if item.is_dir():
            dest_item.mkdir(parents=True, exist_ok=True)
        elif item.is_file() and not dest_item.exists():
            dest_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest_item)
            logger.info(f"[paths] add-new: {relative}")


def _strategy_merge_config(src: Path, dst: Path) -> None:
    """MERGE SMART — para config/. Merge inteligente sobre cada JSON."""
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*.json"):
        relative = item.relative_to(src)
        _merge_json(item, dst / relative)
    for item in src.rglob("*"):
        if item.is_file() and item.suffix != ".json":
            relative = item.relative_to(src)
            dest_item = dst / relative
            if not dest_item.exists():
                dest_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_item)


# ──────────────────────────────────────────────
# Inicialización y migración principal
# ──────────────────────────────────────────────

def initialize_user_data() -> List[OverlayConflict]:
    """
    Punto de entrada principal. Llama a esto desde main.py al arrancar.

    Devuelve una lista de OverlayConflict que main.py puede pasar a la GUI
    para mostrar el popup de notificación (lista vacía = sin conflictos).

    - En modo dev : no hace nada.
    - En modo build:
        1. Primera ejecución → instala archivos por defecto.
        2. Actualización detectada → aplica migración por carpeta.
        3. Sin cambios → no toca nada.
    """
    if get_run_mode() == "dev":
        logger.info("[paths] Modo DEV — usando archivos del proyecto directamente.")
        return []

    user_dir    = get_user_data_dir()
    bundle_dir  = get_bundle_data_dir()   # carpetas editables del paquete
    bundle_ver  = _get_bundle_version()
    schema      = _load_schema_data()
    user_ver    = schema.get("version", "0.0.0")
    prev_hashes = schema.get("overlay_hashes", {})

    logger.info(f"[paths] Modo: BUILD | bundle={bundle_ver} | usuario={user_ver}")
    logger.info(f"[paths] Bundle data dir: {bundle_dir}")
    user_dir.mkdir(parents=True, exist_ok=True)

    if bundle_ver == user_ver:
        logger.info("[paths] Sin actualizaciones pendientes.")
        return []

    is_first = (user_ver == "0.0.0")
    logger.info(
        "[paths] Primera ejecución — instalando archivos..." if is_first
        else f"[paths] Actualización {user_ver} → {bundle_ver}"
    )

    # ── overlay/ : SMART REPLACE con hashes ─────────────────────────────────
    conflicts = _strategy_overlay_smart(
        src=bundle_dir / "overlay",
        dst=user_dir / "overlay",
        prev_bundle_hashes=prev_hashes
    )

    # ── config/ : MERGE SMART ────────────────────────────────────────────────
    _strategy_merge_config(
        src=bundle_dir / "config",
        dst=user_dir / "config"
    )

    # ── backgrounds/, sounds/, voices/ : ADD NEW FILES ───────────────────────
    for folder in ("backgrounds", "sounds", "voices"):
        _strategy_add_new_files(
            src=bundle_dir / folder,
            dst=user_dir / folder
        )

    # ── Guardar nueva versión + hashes actuales del bundle ───────────────────
    new_hashes = _compute_bundle_overlay_hashes(bundle_dir / "overlay")
    _save_schema_data(bundle_ver, new_hashes)
    logger.info(f"[paths] Migración completada → schema v{bundle_ver}")

    return conflicts


# ──────────────────────────────────────────────
# Utilidad de diagnóstico
# ──────────────────────────────────────────────

def print_paths_info() -> None:
    """Imprime en consola las rutas activas para diagnóstico."""
    bundle_ver = _get_bundle_version()
    user_ver   = _get_user_schema_version() if get_run_mode() == "build" else bundle_ver
    print("=" * 57)
    print(f"  NOPOLO PATHS  |  Modo: {get_run_mode().upper()}")
    print(f"  Bundle v{bundle_ver}  |  Usuario v{user_ver}")
    print("=" * 57)
    print(f"  App base dir  : {get_app_base_dir()}")
    print(f"  Bundle data   : {get_bundle_data_dir()}")
    print(f"  User data dir : {get_user_data_dir()}")
    print(f"  voices/       : {get_voices_dir()}")
    print(f"  backgrounds/  : {get_backgrounds_dir()}")
    print(f"  sounds/       : {get_sounds_dir()}")
    print(f"  overlay/      : {get_overlay_dir()}")
    print(f"  config/       : {get_config_dir()}")
    print("=" * 57)
