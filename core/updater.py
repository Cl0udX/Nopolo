"""
core/updater.py — Sistema de auto-actualización de Nopolo.

Compara la versión instalada con la disponible en GitHub (version.json),
y si hay una nueva descarga el ZIP desde Cloudflare R2, extrae y reemplaza
la instalación actual.

Solo funciona en modo BUILD (ejecutable compilado). En modo DEV no hace nada.

Uso:
    from core.updater import check_for_updates, UpdateInfo
    info = check_for_updates()
    if info.available:
        print(f"Nueva versión: {info.remote_version}")
        download_and_install(info, progress_callback=...)
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError

logger = logging.getLogger(__name__)

# URL del version.json en GitHub (siempre actualizado)
VERSION_JSON_URL = "https://raw.githubusercontent.com/Cl0udX/Nopolo/main/version.json"

# Timeout para requests HTTP (segundos)
HTTP_TIMEOUT = 10


# ──────────────────────────────────────────────────────────────
# Detección de plataforma
# ──────────────────────────────────────────────────────────────

def detect_platform() -> str:
    """
    Detecta la plataforma actual y devuelve la clave usada en version.json.
    En Windows intenta leer NOPOLO_PLATFORM del .env para distinguir
    entre cpu / cuda124 / cuda128.
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        # Intentar leer del .env incluido en el bundle
        plat = _read_platform_from_env()
        if plat:
            return plat
        return "windows_cpu"  # fallback seguro
    return "windows_cpu"


def _read_platform_from_env() -> Optional[str]:
    """Lee NOPOLO_PLATFORM del .env junto al ejecutable."""
    try:
        from core.paths import get_app_base_dir
        env_path = get_app_base_dir() / ".env"
        if not env_path.exists():
            # Buscar al lado del ejecutable
            env_path = Path(sys.executable).parent / ".env"
        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("NOPOLO_PLATFORM="):
                        return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────
# Estructuras de datos
# ──────────────────────────────────────────────────────────────

@dataclass
class UpdateInfo:
    available: bool = False
    local_version: str = "0.0.0"
    remote_version: str = "0.0.0"
    platform: str = ""
    zip_name: str = ""
    download_url: str = ""
    error: str = ""
    changelog: list = field(default_factory=list)


# ──────────────────────────────────────────────────────────────
# Comparación de versiones
# ──────────────────────────────────────────────────────────────

def _parse_version(v: str) -> tuple:
    """Convierte "1.2.3" → (1, 2, 3) para comparar."""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0, 0, 0)


def is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


# ──────────────────────────────────────────────────────────────
# Check de actualización
# ──────────────────────────────────────────────────────────────

def get_local_version() -> str:
    """Devuelve la versión instalada actualmente."""
    # 1. Leer desde version.json en la raíz del bundle (tiene prioridad —
    #    se actualiza en cada release sin recompilar)
    try:
        from core.paths import get_bundle_data_dir
        vpath = get_bundle_data_dir() / "version.json"
        if vpath.exists():
            with open(vpath, encoding="utf-8") as f:
                v = json.load(f).get("version", "")
                if v:
                    return v
    except Exception:
        pass
    # 2. Fallback: version compilada en el binario
    try:
        from version import __version__
        return __version__
    except ImportError:
        pass
    return "0.0.0"


def check_for_updates(custom_url: str = None) -> UpdateInfo:
    """
    Consulta version.json en GitHub y compara con la versión local.
    Devuelve UpdateInfo con los detalles. No descarga nada.

    Args:
        custom_url: URL alternativa para version.json (tests/override)
    """
    info = UpdateInfo()
    info.local_version = get_local_version()
    info.platform      = detect_platform()

    url = custom_url or VERSION_JSON_URL
    logger.debug(f"[updater] Consultando: {url}")

    # Cloudflare bloquea el User-Agent por defecto de Python
    req = __import__("urllib.request", fromlist=["Request"]).Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; Nopolo-Updater/1.0)"}
    )

    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            remote = json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        info.error = f"Sin conexión o URL inaccesible: {e}"
        logger.warning(f"[updater] {info.error}")
        return info
    except Exception as e:
        info.error = f"Error al leer version.json remoto: {e}"
        logger.warning(f"[updater] {info.error}")
        return info

    info.remote_version = remote.get("version", "0.0.0")
    logger.info(f"[updater] local={info.local_version}  remoto={info.remote_version}  plataforma={info.platform}")

    if not is_newer(info.remote_version, info.local_version):
        logger.info("[updater] Sin actualizaciones disponibles.")
        return info

    # Hay actualización — construir URL de descarga
    downloads      = remote.get("downloads", {})
    base_url       = remote.get("downloads_base_url", "")
    zip_name       = downloads.get(info.platform, "")

    if not zip_name or not base_url:
        info.error = f"No hay descarga disponible para plataforma '{info.platform}'"
        logger.warning(f"[updater] {info.error}")
        return info

    info.available    = True
    info.zip_name     = zip_name
    info.download_url = f"{base_url.rstrip('/')}/{zip_name}"
    info.changelog    = remote.get("changelog", [])

    logger.info(f"[updater] Actualización disponible: {info.remote_version} → {info.download_url}")
    return info


# ──────────────────────────────────────────────────────────────
# Descarga e instalación
# ──────────────────────────────────────────────────────────────

ProgressCallback = Callable[[int, int, str], None]
"""Callback(bytes_descargados, bytes_totales, mensaje)"""


def download_and_install(
    update: UpdateInfo,
    progress_cb: ProgressCallback = None,
) -> bool:
    """
    Descarga el ZIP de la nueva versión y reemplaza la instalación actual.

    El reemplazo es seguro:
    - Se descarga en un tmp dir
    - Se extrae en tmp dir
    - Se mueve _internal/ nuevo → backup → swap → borra backup
    - Si algo falla, restaura el backup

    Args:
        update: UpdateInfo obtenido de check_for_updates()
        progress_cb: función opcional para reportar progreso

    Returns:
        True si la instalación fue exitosa, False si falló.
    """
    from core.paths import get_run_mode
    if get_run_mode() != "build":
        logger.warning("[updater] Auto-update solo disponible en modo BUILD.")
        return False

    def _progress(msg: str, downloaded: int = 0, total: int = 0):
        logger.info(f"[updater] {msg}")
        if progress_cb:
            progress_cb(downloaded, total, msg)

    _progress(f"Iniciando descarga de {update.zip_name}...")

    with tempfile.TemporaryDirectory(prefix="nopolo_update_") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / update.zip_name

        # ── 1. Descargar ──────────────────────────────────────
        try:
            _download_with_progress(update.download_url, zip_path, _progress)
        except Exception as e:
            _progress(f"Error en descarga: {e}")
            logger.error(f"[updater] Descarga fallida: {e}")
            return False

        # ── 2. Verificar ZIP ──────────────────────────────────
        if not zipfile.is_zipfile(zip_path):
            _progress("El archivo descargado no es un ZIP válido.")
            return False

        _progress("Extrayendo...")

        # ── 3. Extraer ────────────────────────────────────────
        extract_dir = tmp_path / "extracted"
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
        except Exception as e:
            _progress(f"Error al extraer: {e}")
            return False

        # ── 4. Localizar _internal/ en el ZIP extraído ────────
        new_internal = _find_internal(extract_dir)
        if not new_internal:
            _progress("No se encontró _internal/ en el ZIP.")
            logger.error("[updater] Estructura del ZIP inesperada.")
            return False

        # ── 5. Reemplazar _internal/ actual ───────────────────
        current_internal = _get_current_internal()
        if not current_internal or not current_internal.exists():
            _progress("No se encontró _internal/ del bundle actual.")
            return False

        _progress("Instalando actualización...")
        success = _swap_internal(current_internal, new_internal, _progress)

        if not success:
            return False

        # ── 6. Actualizar archivos extras en raíz del bundle ──
        bundle_root = current_internal.parent
        _update_root_files(extract_dir, bundle_root, _progress)

        # ── 7. Renombrar carpeta del bundle a nueva versión ───
        # NOTA: NO reemplazamos el ejecutable en caliente — macOS invalida la
        # firma de código al modificar un binario en ejecución (SIGKILL codesign).
        # El ejecutable del nuevo bundle (zip) se usa tal cual tras el rename.
        new_bundle_root = _rename_bundle_folder(bundle_root, update.remote_version, _progress)

        # ── 8. Renombrar el binario dentro del nuevo bundle ───
        if new_bundle_root:
            _rename_executable_in_bundle(new_bundle_root, update.remote_version, _progress)

        _progress(f"✅ Actualización a v{update.remote_version} completada.")

        # Guardar la ruta del nuevo ejecutable para el reinicio
        update._new_bundle_root = new_bundle_root or bundle_root
        update._new_version     = update.remote_version
        return True


def _download_with_progress(url: str, dest: Path, progress_fn):
    """Descarga con reporte de progreso."""
    import urllib.request

    # Cloudflare bloquea el User-Agent por defecto de Python
    USER_AGENT = "Mozilla/5.0 (compatible; Nopolo-Updater/1.0)"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(req) as resp:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size  = 1024 * 256  # 256 KB

        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = min(int(downloaded / total_size * 100), 100)
                    mb  = downloaded / (1024 * 1024)
                    total_mb = total_size / (1024 * 1024)
                    progress_fn(
                        f"Descargando... {pct}% ({mb:.1f}/{total_mb:.1f} MB)",
                        downloaded,
                        total_size,
                    )
                else:
                    mb = downloaded / (1024 * 1024)
                    progress_fn(f"Descargando... {mb:.1f} MB", downloaded, 0)


def _find_internal(extract_dir: Path) -> Optional[Path]:
    """Busca la carpeta _internal/ dentro del ZIP extraído."""
    # El ZIP tiene: Nopolo-X.X.X/_internal/  o directamente _internal/
    for candidate in extract_dir.rglob("_internal"):
        if candidate.is_dir():
            return candidate
    return None


def _get_current_internal() -> Optional[Path]:
    """Devuelve el Path de _internal/ de la instalación actual."""
    try:
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    except AttributeError:
        return None


def _swap_internal(current: Path, new: Path, progress_fn) -> bool:
    """
    Reemplaza current/_internal/ con new/_internal/ de forma segura.
    Mantiene backup en caso de error.
    """
    backup = current.parent / "_internal_backup"

    try:
        # Borrar backup previo si existe
        if backup.exists():
            shutil.rmtree(backup)

        # Renombrar actual → backup
        progress_fn("Guardando backup...")
        shutil.move(str(current), str(backup))

        # Mover nuevo → actual
        progress_fn("Copiando nueva versión...")
        shutil.move(str(new), str(current))

        # Borrar backup
        shutil.rmtree(backup)
        progress_fn("Backup eliminado.")
        return True

    except Exception as e:
        progress_fn(f"Error durante el swap: {e}. Restaurando backup...")
        logger.error(f"[updater] Swap fallido: {e}")
        # Intentar restaurar
        try:
            if backup.exists() and not current.exists():
                shutil.move(str(backup), str(current))
                progress_fn("Backup restaurado.")
        except Exception as re_err:
            logger.error(f"[updater] No se pudo restaurar backup: {re_err}")
        return False


def _rename_executable_in_bundle(bundle_root: Path, new_version: str, progress_fn):
    """
    Renombra el ejecutable principal (Nopolo-X.X.X) dentro del bundle
    recién instalado a Nopolo-Y.Y.Y para que coincida con la nueva versión.

    Busca específicamente archivos que empiecen con 'Nopolo-' seguido de
    un número de versión, para no confundirse con Generar_Guia_Nopolo u otros.
    """
    import re, stat

    for candidate in bundle_root.iterdir():
        # Solo archivos que sean exactamente "Nopolo-X.X.X" (con versión)
        if candidate.is_file() and re.match(r'^Nopolo-\d+\.\d+', candidate.name):
            match = re.match(r'^(Nopolo)-\d+\.\d+[\.\d]*$', candidate.name)
            if match:
                new_name = f"Nopolo-{new_version}"
                new_path = bundle_root / new_name
                if new_path != candidate:
                    try:
                        candidate.rename(new_path)
                        progress_fn(f"Ejecutable renombrado: {candidate.name} → {new_name}")
                        logger.info(f"[updater] Ejecutable renombrado: {candidate.name} → {new_name}")
                    except Exception as e:
                        logger.warning(f"[updater] No se pudo renombrar ejecutable: {e}")
                break


def _rename_bundle_folder(bundle_root: Path, new_version: str, progress_fn) -> Optional[Path]:
    """
    Renombra la carpeta del bundle de Nopolo-X.X.X → Nopolo-Y.Y.Y.

    Si ya existe Nopolo-Y.Y.Y/, en lugar de borrarla usa un sufijo
    con timestamp para no perder nada: Nopolo-Y.Y.Y_20260309_191500
    """
    parent   = bundle_root.parent
    old_name = bundle_root.name   # ej: "Nopolo-1.1.1"

    # Extraer prefijo (todo antes del bloque de versión)
    import re
    match = re.match(r'^(.*?)[-_ ]?\d+\.\d+[\.\d]*$', old_name)
    prefix = match.group(1).rstrip('-_ ') if match else old_name

    new_name = f"{prefix}-{new_version}"
    new_path = parent / new_name

    # Si ya existe, añadir timestamp en lugar de borrar
    if new_path.exists():
        from datetime import datetime
        stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{prefix}-{new_version}_{stamp}"
        new_path = parent / new_name
        logger.warning(
            f"[updater] '{prefix}-{new_version}' ya existe — "
            f"usando nombre alternativo: {new_name}"
        )

    try:
        bundle_root.rename(new_path)
        progress_fn(f"Carpeta renombrada: {new_name}")
        logger.info(f"[updater] Bundle renombrado: {old_name} → {new_name}")
        return new_path
    except Exception as e:
        logger.warning(f"[updater] No se pudo renombrar carpeta del bundle: {e}")
        return None


def _update_root_files(extract_dir: Path, bundle_root: Path, progress_fn):
    """
    Copia archivos de la raíz del bundle (overlay/, config/, etc.)
    que puedan haber cambiado. La migración real la hace paths.py
    en el próximo arranque — aquí solo actualizamos el bundle source.
    """
    # Carpetas del bundle que pueden actualizarse
    bundle_folders = ["overlay", "config", "sounds"]
    for folder in bundle_folders:
        # Buscar en el ZIP extraído
        for candidate in extract_dir.rglob(folder):
            if candidate.is_dir() and candidate.parent.name != "_internal":
                dest = bundle_root / folder
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(str(candidate), str(dest))
                progress_fn(f"Actualizado: {folder}/")
                break

    # Actualizar version.json en el bundle
    for candidate in extract_dir.rglob("version.json"):
        if candidate.parent.name != "_internal":
            dest = bundle_root / "version.json"
            shutil.copy2(str(candidate), str(dest))
            progress_fn("Actualizado: version.json")
            break


# ──────────────────────────────────────────────────────────────
# Reinicio post-actualización
# ──────────────────────────────────────────────────────────────

def restart_app(update: "UpdateInfo" = None):
    """
    Reinicia la aplicación después de una actualización.

    Lanza el ejecutable desde el nuevo bundle renombrado.
    El nombre del ejecutable puede haber cambiado (ej. Nopolo-1.1.1 → Nopolo-1.1.2).
    """
    logger.info("[updater] Reiniciando aplicación...")
    try:
        current_exe = Path(sys.executable)

        # Determinar la carpeta del nuevo bundle
        if update is not None and hasattr(update, "_new_bundle_root"):
            new_bundle_root = update._new_bundle_root
        else:
            new_bundle_root = current_exe.parent

        # Determinar el nombre del ejecutable en el nuevo bundle
        # Puede haberse renombrado de Nopolo-1.1.1 → Nopolo-1.1.2
        import re, stat as _stat
        new_exe = None
        new_version = getattr(update, "_new_version", None) if update else None

        if new_version:
            # Buscar exactamente "Nopolo-1.1.2" (con versión en el nombre)
            candidate = new_bundle_root / f"Nopolo-{new_version}"
            if candidate.exists():
                new_exe = candidate

        if not new_exe:
            # Fallback: buscar cualquier archivo Nopolo-X.X.X en la raíz
            for candidate in new_bundle_root.iterdir():
                if candidate.is_file() and re.match(r'^Nopolo-\d+\.\d+', candidate.name):
                    new_exe = candidate
                    break

        if not new_exe or not new_exe.exists():
            logger.warning(f"[updater] Ejecutable no encontrado en {new_bundle_root}, usando actual.")
            new_exe = current_exe

        logger.info(f"[updater] Lanzando: {new_exe}")

        if sys.platform == "win32":
            subprocess.Popen([str(new_exe)] + sys.argv[1:])
            sys.exit(0)
        else:
            # os.execv reemplaza el proceso actual — limpio, sin fork
            os.execv(str(new_exe), [str(new_exe)] + sys.argv[1:])

    except Exception as e:
        logger.error(f"[updater] No se pudo reiniciar: {e}")
