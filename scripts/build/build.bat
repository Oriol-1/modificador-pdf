@echo off
REM Script para compilar PDF Editor Pro a ejecutable
REM Ejecutar desde la carpeta pdf_editor

echo ========================================
echo   Compilando PDF Editor Pro
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado o no está en el PATH
    pause
    exit /b 1
)

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Instalar dependencias
echo.
echo Instalando dependencias...
pip install --upgrade pip
pip install -r requirements.txt

REM Verificar instalación
echo.
echo Verificando instalación...
python -c "import fitz; import PyQt5; print('Dependencias OK')"
if errorlevel 1 (
    echo [ERROR] Error en las dependencias
    pause
    exit /b 1
)

REM Compilar
echo.
echo Compilando ejecutable...
pyinstaller --clean build_exe.spec

if errorlevel 1 (
    echo.
    echo [ERROR] Error durante la compilación
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Compilación completada!
echo ========================================
echo.
echo El ejecutable se encuentra en:
echo   dist\PDF_Editor_Pro.exe
echo.

REM Desactivar entorno virtual
deactivate

pause
