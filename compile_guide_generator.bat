@echo off
REM Script para compilar el generador de guía en ejecutable
REM Ejecutar desde la raíz del proyecto

echo ======================================================================
echo   COMPILANDO GENERADOR DE GUIA NOPOLO
echo ======================================================================
echo.

REM Verificar si PyInstaller está instalado
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [ERROR] PyInstaller no esta instalado
    echo Instalando PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] No se pudo instalar PyInstaller
        pause
        exit /b 1
    )
)

echo [OK] PyInstaller encontrado
echo.

REM Compilar con PyInstaller
echo Compilando ejecutable...
echo Esto puede tardar unos segundos...
echo.

pyinstaller --clean --noconfirm generate_guide.spec

if errorlevel 1 (
    echo.
    echo [ERROR] La compilacion fallo
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo   COMPILACION COMPLETADA
echo ======================================================================
echo.
echo Ejecutable generado en: dist\Generar_Guia_Nopolo.exe
echo.
echo Puedes mover este archivo a la carpeta raiz de Nopolo
echo y ejecutarlo con doble clic para generar la guia HTML
echo.
pause
