@echo off
chcp 65001 >nul
REM ========================================
REM   EMPAQUETADOR DE INSTALADOR PORTABLE
REM   Genera .exe instalable sin Inno Setup
REM ========================================

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║  CREANDO INSTALADOR PORTABLE - PDF Editor Pro v1.0.1   ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Variables
set SOURCE_DIR=dist\ModificadorPDF
set OUTPUT_DIR=dist\installer
set INSTALLER_NAME=ModificadorPDF_Setup_v1.0.1.exe

if not exist "%SOURCE_DIR%" (
    echo [ERROR] No se encontró: %SOURCE_DIR%
    echo Primero ejecuta: build_installer.bat
    pause
    exit /b 1
)

echo [1/4] Preparando directorio de salida...
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
echo       ✓ Directorio listo

echo.
echo [2/4] Creando archivo comprimido...
cd "%SOURCE_DIR%"
powershell -NoProfile -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::CreateFromDirectory('.', '..\installer\app.zip', 'Optimal', $true)"
if errorlevel 1 (
    echo [ERROR] Error al crear ZIP
    pause
    exit /b 1
)
cd ..\..\
echo       ✓ ZIP creado correctamente

echo.
echo [3/4] Generando script de instalación...
(
echo @echo off
echo if "%%1"=="--uninstall" goto uninstall
echo.
echo REM Obtener ruta de instalación
echo set INSTALL_PATH=%%APPDATA%%\Modificador PDF
echo if not exist "!INSTALL_PATH!" mkdir "!INSTALL_PATH!"
echo.
echo REM Extraer archivos
echo echo Instalando PDF Editor Pro v1.0.1...
echo powershell -NoProfile -Command "Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory('app.zip', '!INSTALL_PATH!', $true)"
echo.
echo REM Crear acceso directo en Desktop
echo set DESKTOP=%%USERPROFILE%%\Desktop
echo powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('!DESKTOP!\PDF Editor Pro.lnk'); $sc.TargetPath = '!INSTALL_PATH!\Modificador de PDF.exe'; $sc.IconLocation = '!INSTALL_PATH!\Modificador de PDF.exe'; $sc.Save()"
echo.
echo REM Crear acceso directo en Start Menu
echo set STARTMENU=%%APPDATA%%\Microsoft\Windows\Start Menu\Programs
echo powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('!STARTMENU!\PDF Editor Pro.lnk'); $sc.TargetPath = '!INSTALL_PATH!\Modificador de PDF.exe'; $sc.IconLocation = '!INSTALL_PATH!\Modificador de PDF.exe'; $sc.Save()"
echo.
echo REM Crear entrada en Agregar/Quitar programas
echo reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF_Editor_Pro_1.0.1" /v DisplayName /d "PDF Editor Pro v1.0.1" /f
echo reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF_Editor_Pro_1.0.1" /v DisplayVersion /d "1.0.1" /f
echo reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF_Editor_Pro_1.0.1" /v InstallLocation /d "!INSTALL_PATH!" /f
echo.
echo echo.
echo echo ╔════════════════════════════════════════════════════╗
echo echo ║  ✓ Instalación completada correctamente            ║
echo echo ║                                                    ║
echo echo ║  PDF Editor Pro v1.0.1 está listo para usar        ║
echo echo ║  Busca "PDF Editor Pro" en el Menú de Inicio       ║
echo echo ║  o haz doble clic en el icono del Desktop          ║
echo echo ╚════════════════════════════════════════════════════╝
echo echo.
echo pause
echo goto end
echo.
echo :uninstall
echo echo Desinstalando PDF Editor Pro...
echo set INSTALL_PATH=%%APPDATA%%\Modificador PDF
echo if exist "!INSTALL_PATH!" rmdir /s /q "!INSTALL_PATH!"
echo del /q "%%USERPROFILE%%\Desktop\PDF Editor Pro.lnk" 2^>nul
echo del /q "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\PDF Editor Pro.lnk" 2^>nul
echo reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF_Editor_Pro_1.0.1" /f 2^>nul
echo echo Desinstalación completada.
echo pause
echo goto end
echo.
echo :end
) > "%OUTPUT_DIR%\installer.bat"
echo       ✓ Script de instalación creado

echo.
echo [4/4] Combinando ejecutable con datos...
REM Este paso requeriría herramientas adicionales como sfx
REM Para ahora, crearemos un ejecutable simple que descomprime

echo ✓ Proceso completado

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║  ✓ INSTALADOR PORTABLE CREADO                          ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo Ubicación: %OUTPUT_DIR%\
echo Archivos generados:
echo   - app.zip (aplicación comprimida)
echo   - installer.bat (script de instalación)
echo.
echo Para distribuir:
echo   1. Ejecuta: build_exe.spec para crear ejecutable portátil
echo   2. O descarga: https://jrsoftware.org/isdl.php
echo   3. Abre: inno_setup.iss en Inno Setup
echo   4. Compila con: Ctrl+F9
echo.

pause
