#!/usr/bin/env python3
"""
release.py — Empaqueta y publica una versión de Nopolo en Cloudflare R2.

Uso:
    python release.py --platform macos
    python release.py --platform windows_cpu
    python release.py --platform windows_cuda124
    python release.py --platform windows_cuda128
    python release.py --platform macos --dry-run   # simula sin subir

La versión se lee automáticamente de version.json.
Las credenciales R2 se leen de .env.upload (nunca del repo).

Flujo:
    1. Lee version.json → obtiene versión y nombre de archivo destino
    2. Busca dist/Nopolo-X.X.X/ y lo comprime en un ZIP
    3. Conecta a R2, borra el ZIP anterior de esa plataforma (si existe)
    4. Sube el nuevo ZIP
    5. Actualiza version.json con el nuevo nombre de archivo
    6. Hace git commit + push automático
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────────────────────
# Plataformas válidas
# ──────────────────────────────────────────────────────────────
PLATFORMS = {
    "macos":           "mac",
    "windows_cpu":     "win-cpu",
    "windows_cuda124": "win-cuda124",
    "windows_cuda128": "win-cuda128",
}

# ──────────────────────────────────────────────────────────────
# Colores para terminal
# ──────────────────────────────────────────────────────────────
class C:
    OK    = "\033[92m"
    WARN  = "\033[93m"
    ERR   = "\033[91m"
    BOLD  = "\033[1m"
    CYAN  = "\033[96m"
    RESET = "\033[0m"

def ok(msg):   print(f"{C.OK}✅ {msg}{C.RESET}")
def warn(msg): print(f"{C.WARN}⚠️  {msg}{C.RESET}")
def err(msg):  print(f"{C.ERR}❌ {msg}{C.RESET}")
def info(msg): print(f"{C.CYAN}   {msg}{C.RESET}")
def bold(msg): print(f"{C.BOLD}{msg}{C.RESET}")

# ──────────────────────────────────────────────────────────────
# Carga de configuración
# ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent

def load_version_json() -> dict:
    path = ROOT / "version.json"
    if not path.exists():
        err("No se encontró version.json")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_version_json(data: dict):
    path = ROOT / "version.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def load_r2_credentials() -> dict:
    """Lee .env.upload para obtener credenciales R2."""
    upload_env = ROOT / ".env.upload"
    if not upload_env.exists():
        err(".env.upload no encontrado.")
        info("Crea el archivo .env.upload con tus credenciales R2.")
        info("Puedes usar .env.upload.example como plantilla.")
        sys.exit(1)

    creds = {}
    with open(upload_env, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                creds[key.strip()] = val.strip()

    required = ["R2_ENDPOINT", "R2_BUCKET", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"]
    for key in required:
        if not creds.get(key):
            err(f"Falta {key} en .env.upload")
            sys.exit(1)

    return creds

# ──────────────────────────────────────────────────────────────
# Buscar carpeta dist
# ──────────────────────────────────────────────────────────────

def find_dist(version: str, app_name: str) -> Path:
    """Busca la carpeta dist/Nopolo-X.X.X/ generada por PyInstaller."""
    candidates = [
        ROOT / "dist" / f"{app_name}-{version}",
        ROOT / "dist" / app_name,
    ]
    for c in candidates:
        if c.is_dir():
            return c
    err(f"No se encontró carpeta dist. Buscado en:")
    for c in candidates:
        info(str(c))
    info("Asegúrate de haber ejecutado build_executable.py primero.")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────
# Comprimir
# ──────────────────────────────────────────────────────────────

def create_zip(dist_dir: Path, zip_path: Path) -> Path:
    """Crea un ZIP de dist_dir en zip_path. Devuelve el path del ZIP."""
    # Copiar version.json a la raíz del bundle antes de zipear
    # Así el updater puede leer la versión sin depender del binario compilado
    version_src = ROOT / "version.json"
    version_dst = dist_dir / "version.json"
    if version_src.exists():
        shutil.copy2(str(version_src), str(version_dst))
        info(f"version.json copiado a bundle: {version_dst}")

    if zip_path.exists():
        zip_path.unlink()
        info(f"ZIP anterior eliminado: {zip_path.name}")

    bold(f"\n📦 Comprimiendo {dist_dir.name}...")
    info(f"Destino: {zip_path}")

    total_files = sum(1 for _ in dist_dir.rglob("*") if _.is_file())
    compressed  = 0
    interval    = max(total_files // 20, 1)   # progreso cada ~5%

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in dist_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(dist_dir.parent)
                zf.write(file, arcname)
                compressed += 1
                if compressed % interval == 0:
                    pct = int(compressed / total_files * 100)
                    print(f"\r   Comprimiendo... {pct}% ({compressed}/{total_files})", end="", flush=True)

    print()  # nueva línea tras el progreso
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    ok(f"ZIP creado: {zip_path.name} ({size_mb:.1f} MB)")
    return zip_path

# ──────────────────────────────────────────────────────────────
# R2 — subir / borrar
# ──────────────────────────────────────────────────────────────

def get_r2_client(creds: dict):
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        err("boto3 no está instalado. Ejecuta: pip install boto3")
        sys.exit(1)

    return boto3.client(
        "s3",
        endpoint_url          = creds["R2_ENDPOINT"],
        aws_access_key_id     = creds["R2_ACCESS_KEY_ID"],
        aws_secret_access_key = creds["R2_SECRET_ACCESS_KEY"],
        config                = Config(signature_version="s3v4"),
        region_name           = "auto",
    )

def delete_old_platform_zip(client, bucket: str, platform_suffix: str, current_zip_name: str):
    """Borra en R2 cualquier ZIP de la misma plataforma que no sea el actual."""
    bold(f"\n🗑  Buscando versiones anteriores de '{platform_suffix}' en R2...")
    try:
        resp = client.list_objects_v2(Bucket=bucket)
        objects = resp.get("Contents", [])
    except Exception as e:
        warn(f"No se pudo listar el bucket: {e}")
        return

    pattern = re.compile(rf"Nopolo-[\d.]+-{re.escape(platform_suffix)}\.zip")
    deleted = 0
    for obj in objects:
        key = obj["Key"]
        if pattern.match(key) and key != current_zip_name:
            try:
                client.delete_object(Bucket=bucket, Key=key)
                info(f"Eliminado: {key}")
                deleted += 1
            except Exception as e:
                warn(f"No se pudo eliminar {key}: {e}")

    if deleted == 0:
        info("No había versiones anteriores.")
    else:
        ok(f"{deleted} archivo(s) anterior(es) eliminado(s)")

def upload_zip(client, bucket: str, zip_path: Path, zip_name: str):
    """Sube el ZIP a R2 con barra de progreso."""
    bold(f"\n☁️  Subiendo {zip_name} a R2...")
    size = zip_path.stat().st_size
    uploaded = [0]

    def progress(bytes_amount):
        uploaded[0] += bytes_amount
        pct = int(uploaded[0] / size * 100)
        mb  = uploaded[0] / (1024 * 1024)
        total_mb = size / (1024 * 1024)
        print(f"\r   Subiendo... {pct}% ({mb:.1f}/{total_mb:.1f} MB)", end="", flush=True)

    try:
        with open(zip_path, "rb") as f:
            client.upload_fileobj(
                f, bucket, zip_name,
                ExtraArgs={"ContentType": "application/zip"},
                Callback=progress,
            )
        print()
        ok(f"Subida completa: {zip_name}")
    except Exception as e:
        print()
        err(f"Error al subir: {e}")
        sys.exit(1)

# ──────────────────────────────────────────────────────────────
# Git — commit + push de version.json
# ──────────────────────────────────────────────────────────────

def git_push_version(version: str, platform: str):
    bold("\n📤 Actualizando version.json en GitHub...")
    try:
        subprocess.run(["git", "add", "version.json"], cwd=ROOT, check=True)
        msg = f"release: v{version} [{platform}]"
        subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)
        ok("version.json actualizado en GitHub")
    except subprocess.CalledProcessError as e:
        warn(f"Git push falló: {e}")
        warn("Actualiza version.json en GitHub manualmente.")

# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Publica una versión de Nopolo en Cloudflare R2"
    )
    parser.add_argument(
        "--platform", "-p",
        required=True,
        choices=list(PLATFORMS.keys()),
        help="Plataforma a publicar",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula el proceso sin subir ni modificar nada",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="No hace git push al final",
    )
    parser.add_argument(
        "--keep-zip",
        action="store_true",
        help="No elimina el ZIP local al terminar",
    )
    args = parser.parse_args()

    bold("=" * 60)
    bold("  NOPOLO RELEASE")
    bold("=" * 60)

    # ── Cargar configuración ─────────────────────────────────
    vdata    = load_version_json()
    version  = vdata["version"]
    app_name = vdata.get("app_name", "Nopolo")
    suffix   = PLATFORMS[args.platform]
    zip_name = f"Nopolo-{version}-{suffix}.zip"
    zip_path = ROOT / zip_name

    info(f"Versión   : {version}")
    info(f"Plataforma: {args.platform}  →  {suffix}")
    info(f"ZIP       : {zip_name}")
    if args.dry_run:
        warn("MODO DRY-RUN — no se subirá nada ni se modificará nada")

    # ── Buscar dist ──────────────────────────────────────────
    dist_dir = find_dist(version, app_name)
    info(f"Dist dir  : {dist_dir}")

    # ── Comprimir ────────────────────────────────────────────
    create_zip(dist_dir, zip_path)

    if args.dry_run:
        bold("\n[DRY-RUN] Fin. ZIP creado pero no se subió.")
        if not args.keep_zip:
            zip_path.unlink(missing_ok=True)
        return

    # ── Credenciales R2 ──────────────────────────────────────
    creds  = load_r2_credentials()
    bucket = creds["R2_BUCKET"]
    client = get_r2_client(creds)

    # ── Borrar versión anterior en R2 ────────────────────────
    delete_old_platform_zip(client, bucket, suffix, zip_name)

    # ── Subir nuevo ZIP ──────────────────────────────────────
    upload_zip(client, bucket, zip_path, zip_name)

    # ── Actualizar version.json con nombre de archivo ────────
    bold("\n📝 Actualizando version.json...")
    if "downloads" not in vdata:
        vdata["downloads"] = {}
    vdata["downloads"][args.platform] = zip_name
    save_version_json(vdata)
    ok(f"downloads.{args.platform} = {zip_name}")

    # ── Git push ─────────────────────────────────────────────
    if not args.no_git:
        git_push_version(version, args.platform)

    # ── Limpiar ZIP local ────────────────────────────────────
    if not args.keep_zip:
        zip_path.unlink(missing_ok=True)
        info(f"ZIP local eliminado: {zip_name}")

    # ── Resumen ──────────────────────────────────────────────
    public_url = vdata.get("downloads_base_url", "")
    bold("\n" + "=" * 60)
    ok(f"Release v{version} [{args.platform}] publicado exitosamente")
    if public_url:
        info(f"URL: {public_url}/{zip_name}")
    bold("=" * 60)


if __name__ == "__main__":
    main()
