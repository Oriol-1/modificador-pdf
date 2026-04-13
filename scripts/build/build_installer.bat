@echo off
chcp 65001 >nul
REM ========================================
REM   COMPILADOR DE MODIFICADOR DE PDF
REM   Genera ejecutable e instalador Windows
REM ========================================

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     COMPILADOR - MODIFICADOR DE PDF                    ║
echo ║     Windows 10/11 Installer Builder                    ║
echo ╚════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM Verificar Python
echo [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado o no está en el PATH
    pause
    exit /b 1
)
echo       ✓ Python encontrado

REM Activar entorno virtual
echo.
echo [2/6] Configurando entorno virtual...
if exist "..\..\.venv\Scripts\activate.bat" (
    call "..\..\.venv\Scripts\activate.bat"
    echo       ✓ Entorno virtual activado
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
    echo       ✓ Entorno virtual local activado
) else (
    echo       ! Usando Python global
)

REM Instalar dependencias
echo.
echo [3/6] Instalando dependencias...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1
pip install Pillow >nul 2>&1
echo       ✓ Dependencias instaladas

REM Generar icono
echo.
echo [4/6] Generando icono de la aplicación...
if not exist "installer" mkdir installer
python installer\create_icon.py
if errorlevel 1 (
    echo       ! No se pudo generar el icono, continuando...
) else (
    echo       ✓ Icono generado
)

REM Limpiar builds anteriores
echo.
echo [5/6] Limpiando builds anteriores...
if exist "dist\ModificadorPDF" rmdir /s /q "dist\ModificadorPDF"
if exist "build\ModificadorPDF" rmdir /s /q "build\ModificadorPDF"
echo       ✓ Limpieza completada

REM Compilar con PyInstaller
echo.
echo [6/6] Compilando ejecutable...
echo       Esto puede tardar varios minutos...
echo.
pyinstaller --clean --noconfirm ModificadorPDF.spec

if errorlevel 1 (
    echo.
    echo ╔════════════════════════════════════════════════════════╗
    echo ║  [ERROR] La compilación falló                          ║
    echo ╚════════════════════════════════════════════════════════╝
    pause
    exit /b 1
)

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║  ✓ COMPILACIÓN EXITOSA                                 ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo El ejecutable está en: dist\ModificadorPDF\
echo.
echo ─────────────────────────────────────────────────────────
echo SIGUIENTE PASO - Crear instalador:
echo.
echo 1. Descarga Inno Setup: https://jrsoftware.org/isinfo.php
echo 2. Abre: installer\inno_setup.iss
echo 3. Compila con Ctrl+F9
echo.
echo El instalador se guardará en: dist\installer\
echo ─────────────────────────────────────────────────────────

REM Verificar si Inno Setup está instalado
where iscc >nul 2>&1
if not errorlevel 1 (
    echo.
    echo Inno Setup detectado! ¿Crear instalador ahora? (S/N)
    set /p crear_installer=
    if /i "%crear_installer%"=="S" (
        echo.
        echo Creando instalador...
        if not exist "dist\installer" mkdir "dist\installer"
        iscc "installer\inno_setup.iss"
        if not errorlevel 1 (
            echo.
            echo ✓ Instalador creado en: dist\installer\
            explorer "dist\installer"
        )
    )
)

echo.
pause
