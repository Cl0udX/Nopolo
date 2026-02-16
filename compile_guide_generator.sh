#!/bin/bash
# Script para compilar el generador de guía en ejecutable (Mac/Linux)
# Ejecutar desde la raíz del proyecto

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "  COMPILANDO GENERADOR DE GUIA NOPOLO"
echo "======================================================================"
echo

# Verificar si PyInstaller está instalado
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo -e "${RED}[ERROR] PyInstaller no está instalado${NC}"
    echo "Instalando PyInstaller..."
    pip3 install pyinstaller || { echo -e "${RED}[ERROR] No se pudo instalar PyInstaller${NC}"; exit 1; }
fi

echo -e "${GREEN}[OK] PyInstaller encontrado${NC}"
echo

echo "Compilando ejecutable..."
echo "Esto puede tardar unos segundos..."
echo

pyinstaller --clean --noconfirm generate_guide.spec

if [ $? -ne 0 ]; then
    echo
    echo -e "${RED}[ERROR] La compilación falló${NC}"
    exit 1
fi

echo
echo "======================================================================"
echo "  COMPILACION COMPLETADA"
echo "======================================================================"
echo
if [ -f dist/Generar_Guia_Nopolo ]; then
    echo "Ejecutable generado en: dist/Generar_Guia_Nopolo"
else
    echo "Ejecutable generado en: dist/ (verifica el nombre exacto)"
fi
echo
