#!/bin/bash
# ========================================
#   CREADOR DE APPIMAGE
#   PDF Editor Pro - AppImage Universal
# ========================================

set -e

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     CREADOR DE APPIMAGE                                ║"
echo "║     PDF Editor Pro - Universal Linux                   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Variables
APP_NAME="PDF_Editor_Pro"
VERSION="1.0.0"

# Verificar que existe la compilación
if [ ! -d "dist/ModificadorPDF" ] && [ ! -d "dist/PDF_Editor_Pro" ]; then
    echo -e "${RED}[ERROR] No se encontró la compilación.${NC}"
    echo "        Ejecuta primero: ./build_linux.sh"
    exit 1
fi

# Determinar directorio de origen
if [ -d "dist/ModificadorPDF" ]; then
    SOURCE_DIR="dist/ModificadorPDF"
elif [ -d "dist/PDF_Editor_Pro" ]; then
    SOURCE_DIR="dist/PDF_Editor_Pro"
fi

# Directorio AppImage
APPDIR="dist/${APP_NAME}.AppDir"

echo -e "[1/5] Creando estructura AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share/doc/pdf-editor-pro"

# Copiar archivos de la aplicación
echo -e "[2/5] Copiando archivos de la aplicación..."
cp -r "$SOURCE_DIR"/* "$APPDIR/usr/bin/"

# Copiar licencias
cp LICENSE.txt "$APPDIR/usr/share/doc/pdf-editor-pro/" 2>/dev/null || true
cp LICENSE_EN.txt "$APPDIR/usr/share/doc/pdf-editor-pro/" 2>/dev/null || true

# Crear icono (placeholder - puedes reemplazar con tu propio icono)
echo -e "[3/5] Creando icono..."
if [ -f "installer/app_icon.png" ]; then
    cp installer/app_icon.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/pdf-editor-pro.png"
    cp installer/app_icon.png "$APPDIR/pdf-editor-pro.png"
else
    # Crear icono básico con ImageMagick si está disponible
    if command -v convert &> /dev/null; then
        convert -size 256x256 xc:#0078d4 \
            -fill white -font DejaVu-Sans-Bold -pointsize 100 \
            -gravity center -annotate 0 "PDF" \
            "$APPDIR/pdf-editor-pro.png" 2>/dev/null || true
    fi
fi

# Crear archivo .desktop
echo -e "[4/5] Creando archivo .desktop..."
cat > "$APPDIR/pdf-editor-pro.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PDF Editor Pro
GenericName=PDF Editor
Comment=Editor de PDF profesional
Exec=AppRun %F
Icon=pdf-editor-pro
Terminal=false
Categories=Office;Graphics;Viewer;
MimeType=application/pdf;
Keywords=pdf;editor;document;
X-AppImage-Version=$VERSION
EOF

# Crear enlace simbólico del .desktop
ln -sf pdf-editor-pro.desktop "$APPDIR/${APP_NAME}.desktop"

# Crear AppRun
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin/:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib/:${LD_LIBRARY_PATH}"
export QT_PLUGIN_PATH="${HERE}/usr/bin/PyQt5/Qt5/plugins"

cd "${HERE}/usr/bin"
if [ -f "./PDF_Editor_Pro" ]; then
    exec "./PDF_Editor_Pro" "$@"
elif [ -f "./Modificador de PDF" ]; then
    exec "./Modificador de PDF" "$@"
fi
EOF
chmod +x "$APPDIR/AppRun"

# Descargar appimagetool si no existe
echo -e "[5/5] Creando AppImage..."
APPIMAGETOOL="appimagetool-x86_64.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "      Descargando appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O "$APPIMAGETOOL" 2>/dev/null || {
        echo -e "${YELLOW}[AVISO] No se pudo descargar appimagetool${NC}"
        echo "        Descarga manualmente desde:"
        echo "        https://github.com/AppImage/AppImageKit/releases"
        echo ""
        echo "        Estructura AppDir creada en: $APPDIR"
        echo "        Para crear AppImage manualmente:"
        echo "        ./appimagetool-x86_64.AppImage $APPDIR"
        exit 0
    }
    chmod +x "$APPIMAGETOOL"
fi

# Crear AppImage
ARCH=x86_64 ./"$APPIMAGETOOL" "$APPDIR" "dist/${APP_NAME}-${VERSION}-x86_64.AppImage" 2>/dev/null || {
    echo -e "${YELLOW}[AVISO] Error al crear AppImage${NC}"
    echo "        Estructura AppDir creada en: $APPDIR"
    exit 0
}

if [ -f "dist/${APP_NAME}-${VERSION}-x86_64.AppImage" ]; then
    chmod +x "dist/${APP_NAME}-${VERSION}-x86_64.AppImage"
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     ✓ APPIMAGE CREADO                                 ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "AppImage creado:"
    echo "  dist/${APP_NAME}-${VERSION}-x86_64.AppImage"
    echo ""
    echo "Para ejecutar:"
    echo "  chmod +x dist/${APP_NAME}-${VERSION}-x86_64.AppImage"
    echo "  ./dist/${APP_NAME}-${VERSION}-x86_64.AppImage"
    echo ""
    echo "El AppImage es portable y funciona en cualquier distribución Linux."
    echo ""
fi
