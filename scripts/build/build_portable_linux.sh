#!/bin/bash
# ========================================
#   CREADOR DE VERSIÓN PORTABLE
#   PDF Editor Pro para Linux
# ========================================

set -e

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     CREADOR DE VERSIÓN PORTABLE                        ║"
echo "║     PDF Editor Pro - Linux                             ║"
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

# Verificar que existe la compilación
if [ ! -d "dist/ModificadorPDF" ] && [ ! -d "dist/PDF_Editor_Pro" ]; then
    echo -e "${RED}[ERROR] No se encontró la compilación.${NC}"
    echo "        Ejecuta primero: ./build_linux.sh"
    exit 1
fi

# Determinar directorio de origen
if [ -d "dist/ModificadorPDF" ]; then
    SOURCE_DIR="dist/ModificadorPDF"
    EXE_NAME="Modificador de PDF"
elif [ -d "dist/PDF_Editor_Pro" ]; then
    SOURCE_DIR="dist/PDF_Editor_Pro"
    EXE_NAME="PDF_Editor_Pro"
fi

# Nombre del portable
VERSION="1.0.0"
PORTABLE_NAME="PDF_Editor_Pro_${VERSION}_Linux_Portable"
PORTABLE_DIR="dist/${PORTABLE_NAME}"

echo -e "[1/5] Creando estructura de carpetas..."
rm -rf "$PORTABLE_DIR"
mkdir -p "$PORTABLE_DIR"
mkdir -p "$PORTABLE_DIR/bin"
mkdir -p "$PORTABLE_DIR/docs"

# Copiar ejecutable y dependencias
echo -e "[2/5] Copiando ejecutable y dependencias..."
cp -r "$SOURCE_DIR"/* "$PORTABLE_DIR/bin/"

# Copiar licencias y documentación
echo -e "[3/5] Copiando documentación..."
cp LICENSE.txt "$PORTABLE_DIR/docs/" 2>/dev/null || true
cp LICENSE_EN.txt "$PORTABLE_DIR/docs/" 2>/dev/null || true
cp README.md "$PORTABLE_DIR/docs/" 2>/dev/null || true

# Crear archivo .desktop
echo -e "[4/5] Creando acceso directo..."
cat > "$PORTABLE_DIR/PDF_Editor_Pro.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=PDF Editor Pro
Comment=Editor de PDF profesional
Exec=./bin/PDF_Editor_Pro
Icon=pdf-editor
Terminal=false
Categories=Office;Graphics;
MimeType=application/pdf;
EOF

# Crear script de ejecución
cat > "$PORTABLE_DIR/run.sh" << 'EOF'
#!/bin/bash
# Script de ejecución para PDF Editor Pro Portable
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/bin"

# Configurar variables de entorno si es necesario
export QT_QPA_PLATFORM_PLUGIN_PATH="$SCRIPT_DIR/bin/PyQt5/Qt5/plugins/platforms"

# Ejecutar la aplicación
if [ -f "./PDF_Editor_Pro" ]; then
    ./PDF_Editor_Pro "$@"
elif [ -f "./Modificador de PDF" ]; then
    "./Modificador de PDF" "$@"
else
    echo "Error: No se encontró el ejecutable"
    exit 1
fi
EOF
chmod +x "$PORTABLE_DIR/run.sh"

# Crear README para el portable
cat > "$PORTABLE_DIR/LEEME.txt" << EOF
================================================================================
                    PDF EDITOR PRO - VERSIÓN PORTABLE
                           Linux - Versión $VERSION
================================================================================

INSTRUCCIONES DE USO
--------------------

1. EJECUTAR LA APLICACIÓN:
   - Doble clic en 'run.sh'
   - O desde terminal: ./run.sh

2. CREAR ACCESO DIRECTO:
   - Copia 'PDF_Editor_Pro.desktop' a tu escritorio
   - O a ~/.local/share/applications/ para menú de aplicaciones

3. REQUISITOS:
   - Sistema Linux con escritorio gráfico (X11 o Wayland)
   - Librerías: libxcb, libxkbcommon (normalmente ya instaladas)

LICENCIA
--------
Este software es GRATUITO para uso personal.
Uso comercial requiere autorización del autor.
Ver docs/LICENSE.txt para términos completos.

CONTACTO
--------
Email: alonsoesplugas@gmail.com
GitHub: https://github.com/Oriol-1

================================================================================
          © 2026 Oriol Alonso Esplugas - Todos los derechos reservados
================================================================================
EOF

# Crear archivo comprimido
echo -e "[5/5] Creando archivo comprimido..."
cd dist
tar -czvf "${PORTABLE_NAME}.tar.gz" "$PORTABLE_NAME" > /dev/null 2>&1

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✓ VERSIÓN PORTABLE CREADA                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Archivos creados:"
echo "  - dist/${PORTABLE_NAME}/ (carpeta)"
echo "  - dist/${PORTABLE_NAME}.tar.gz (comprimido)"
echo ""
echo "Para distribuir, comparte el archivo .tar.gz"
echo ""
