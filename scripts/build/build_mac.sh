#!/bin/bash
# ========================================
#   COMPILADOR DE MODIFICADOR DE PDF
#   Genera aplicación .app para macOS
# ========================================

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     COMPILADOR - MODIFICADOR DE PDF                    ║"
echo "║     macOS Application Builder                          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Ir al directorio del script
cd "$(dirname "$0")"

# Verificar Python
echo "[1/6] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 no está instalado"
    exit 1
fi
echo "      ✓ Python3 encontrado"

# Crear/activar entorno virtual
echo ""
echo "[2/6] Configurando entorno virtual..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi
echo "      ✓ Entorno virtual activado"

# Instalar dependencias
echo ""
echo "[3/6] Instalando dependencias..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
pip install Pillow > /dev/null 2>&1
echo "      ✓ Dependencias instaladas"

# Generar icono
echo ""
echo "[4/6] Generando icono de la aplicación..."
mkdir -p installer
python3 installer/create_icon.py

# Convertir PNG a ICNS si es posible
if [ -f "installer/app_icon_mac.png" ]; then
    echo "      Convirtiendo a formato ICNS..."
    mkdir -p installer/icon.iconset
    
    # Generar diferentes tamaños
    sips -z 16 16     installer/app_icon_mac.png --out installer/icon.iconset/icon_16x16.png > /dev/null 2>&1
    sips -z 32 32     installer/app_icon_mac.png --out installer/icon.iconset/icon_16x16@2x.png > /dev/null 2>&1
    sips -z 32 32     installer/app_icon_mac.png --out installer/icon.iconset/icon_32x32.png > /dev/null 2>&1
    sips -z 64 64     installer/app_icon_mac.png --out installer/icon.iconset/icon_32x32@2x.png > /dev/null 2>&1
    sips -z 128 128   installer/app_icon_mac.png --out installer/icon.iconset/icon_128x128.png > /dev/null 2>&1
    sips -z 256 256   installer/app_icon_mac.png --out installer/icon.iconset/icon_128x128@2x.png > /dev/null 2>&1
    sips -z 256 256   installer/app_icon_mac.png --out installer/icon.iconset/icon_256x256.png > /dev/null 2>&1
    sips -z 512 512   installer/app_icon_mac.png --out installer/icon.iconset/icon_256x256@2x.png > /dev/null 2>&1
    sips -z 512 512   installer/app_icon_mac.png --out installer/icon.iconset/icon_512x512.png > /dev/null 2>&1
    sips -z 1024 1024 installer/app_icon_mac.png --out installer/icon.iconset/icon_512x512@2x.png > /dev/null 2>&1
    
    # Crear ICNS
    iconutil -c icns installer/icon.iconset -o installer/app_icon.icns 2>/dev/null
    
    if [ -f "installer/app_icon.icns" ]; then
        echo "      ✓ ICNS generado"
    else
        echo "      ! No se pudo crear ICNS (continuando sin icono personalizado)"
    fi
fi

# Limpiar builds anteriores
echo ""
echo "[5/6] Limpiando builds anteriores..."
rm -rf dist/ModificadorPDF
rm -rf "dist/Modificador de PDF.app"
rm -rf build/ModificadorPDF
echo "      ✓ Limpieza completada"

# Compilar con PyInstaller
echo ""
echo "[6/6] Compilando aplicación..."
echo "      Esto puede tardar varios minutos..."
echo ""
pyinstaller --clean --noconfirm ModificadorPDF.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  [ERROR] La compilación falló                          ║"
    echo "╚════════════════════════════════════════════════════════╝"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✓ COMPILACIÓN EXITOSA                                 ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Verificar resultado
if [ -d "dist/Modificador de PDF.app" ]; then
    echo "La aplicación está en: dist/Modificador de PDF.app"
    echo ""
    echo "Para instalar:"
    echo "  1. Arrastra 'Modificador de PDF.app' a la carpeta Aplicaciones"
    echo "  2. La primera vez, clic derecho > Abrir (para evitar Gatekeeper)"
    echo ""
    
    # Preguntar si crear DMG
    echo "¿Deseas crear un archivo DMG para distribución? (s/n)"
    read -r crear_dmg
    
    if [ "$crear_dmg" = "s" ] || [ "$crear_dmg" = "S" ]; then
        echo "Creando DMG..."
        
        # Crear DMG simple
        mkdir -p dist/dmg_temp
        cp -R "dist/Modificador de PDF.app" dist/dmg_temp/
        ln -s /Applications dist/dmg_temp/Applications
        
        hdiutil create -volname "Modificador de PDF" \
                       -srcfolder dist/dmg_temp \
                       -ov -format UDZO \
                       "dist/ModificadorPDF_v1.0.0.dmg"
        
        rm -rf dist/dmg_temp
        
        if [ -f "dist/ModificadorPDF_v1.0.0.dmg" ]; then
            echo ""
            echo "✓ DMG creado: dist/ModificadorPDF_v1.0.0.dmg"
        fi
    fi
else
    echo "La aplicación está en: dist/ModificadorPDF/"
    echo "Puedes ejecutarla con: ./dist/ModificadorPDF/Modificador\\ de\\ PDF"
fi

echo ""
