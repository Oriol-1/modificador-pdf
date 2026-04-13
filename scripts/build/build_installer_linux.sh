#!/bin/bash
# ========================================
#   CREADOR DE INSTALADOR .DEB
#   PDF Editor Pro para Debian/Ubuntu
# ========================================

set -e

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     CREADOR DE INSTALADOR .DEB                         ║"
echo "║     PDF Editor Pro - Debian/Ubuntu                     ║"
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
APP_NAME="pdf-editor-pro"
VERSION="1.0.0"
MAINTAINER="Oriol Alonso Esplugas <alonsoesplugas@gmail.com>"
DESCRIPTION="Editor de PDF profesional con capacidades de edición de texto"
ARCH="amd64"

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

# Directorio del paquete DEB
DEB_DIR="dist/${APP_NAME}_${VERSION}_${ARCH}"

echo -e "[1/6] Creando estructura del paquete..."
rm -rf "$DEB_DIR"
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/opt/pdf-editor-pro"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/doc/pdf-editor-pro"
mkdir -p "$DEB_DIR/usr/bin"

# Copiar archivos de la aplicación
echo -e "[2/6] Copiando archivos de la aplicación..."
cp -r "$SOURCE_DIR"/* "$DEB_DIR/opt/pdf-editor-pro/"

# Copiar licencias
echo -e "[3/6] Copiando documentación..."
cp LICENSE.txt "$DEB_DIR/usr/share/doc/pdf-editor-pro/" 2>/dev/null || true
cp LICENSE_EN.txt "$DEB_DIR/usr/share/doc/pdf-editor-pro/" 2>/dev/null || true

# Crear archivo de copyright
cat > "$DEB_DIR/usr/share/doc/pdf-editor-pro/copyright" << EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: PDF Editor Pro
Source: https://github.com/Oriol-1/modificador-pdf

Files: *
Copyright: 2026 Oriol Alonso Esplugas
License: Proprietary
 Este software es gratuito para uso personal.
 Uso comercial requiere autorización del autor.
 Ver LICENSE.txt para los términos completos.
EOF

# Crear script ejecutable
echo -e "[4/6] Creando ejecutable..."
cat > "$DEB_DIR/usr/bin/pdf-editor-pro" << 'EOF'
#!/bin/bash
cd /opt/pdf-editor-pro
if [ -f "./PDF_Editor_Pro" ]; then
    ./PDF_Editor_Pro "$@"
elif [ -f "./Modificador de PDF" ]; then
    "./Modificador de PDF" "$@"
fi
EOF
chmod 755 "$DEB_DIR/usr/bin/pdf-editor-pro"

# Crear archivo .desktop
cat > "$DEB_DIR/usr/share/applications/pdf-editor-pro.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PDF Editor Pro
GenericName=PDF Editor
Comment=Editor de PDF profesional
Comment[es]=Editor de PDF profesional
Exec=pdf-editor-pro %F
Icon=pdf-editor-pro
Terminal=false
Categories=Office;Graphics;Viewer;
MimeType=application/pdf;
Keywords=pdf;editor;document;
EOF

# Crear archivo de control
echo -e "[5/6] Creando metadatos del paquete..."
cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $VERSION
Section: editors
Priority: optional
Architecture: $ARCH
Depends: libxcb-xinerama0, libxkbcommon-x11-0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0
Maintainer: $MAINTAINER
Description: $DESCRIPTION
 PDF Editor Pro es un editor de PDF profesional con capacidades de:
  - Selección de texto precisa
  - Resaltado de texto
  - Eliminación de texto
  - Edición de texto manteniendo formato
  - Sistema de workspace para flujo de trabajo
Homepage: https://github.com/Oriol-1/modificador-pdf
EOF

# Scripts de instalación
cat > "$DEB_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
chmod +x /opt/pdf-editor-pro/*
update-desktop-database /usr/share/applications 2>/dev/null || true
EOF
chmod 755 "$DEB_DIR/DEBIAN/postinst"

cat > "$DEB_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
update-desktop-database /usr/share/applications 2>/dev/null || true
EOF
chmod 755 "$DEB_DIR/DEBIAN/postrm"

# Construir paquete DEB
echo -e "[6/6] Construyendo paquete .deb..."
dpkg-deb --build "$DEB_DIR" 2>/dev/null || {
    echo -e "${YELLOW}[AVISO] dpkg-deb no disponible, creando estructura sin empaquetar${NC}"
    echo "        Para crear el .deb, ejecuta en un sistema Debian/Ubuntu:"
    echo "        dpkg-deb --build $DEB_DIR"
}

if [ -f "dist/${APP_NAME}_${VERSION}_${ARCH}.deb" ]; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     ✓ PAQUETE .DEB CREADO                             ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Instalador creado:"
    echo "  dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
    echo ""
    echo "Para instalar:"
    echo "  sudo dpkg -i dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
    echo "  sudo apt-get install -f  # Si hay dependencias faltantes"
    echo ""
    echo "Para desinstalar:"
    echo "  sudo apt remove pdf-editor-pro"
    echo ""
else
    echo ""
    echo -e "${GREEN}Estructura del paquete creada en:${NC}"
    echo "  $DEB_DIR/"
    echo ""
fi
