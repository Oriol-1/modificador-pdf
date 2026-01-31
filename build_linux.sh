#!/bin/bash
# ========================================
#   COMPILADOR DE PDF EDITOR PRO
#   Genera ejecutable para Linux
# ========================================

set -e  # Salir si hay error

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     COMPILADOR - PDF EDITOR PRO                        ║"
echo "║     Linux Application Builder                          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color

# Ir al directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Verificar Python
echo -e "[1/7] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python3 no está instalado${NC}"
    echo "        Instala Python3 con: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "      ${GREEN}✓ $PYTHON_VERSION encontrado${NC}"

# Verificar dependencias del sistema para PyQt5
echo ""
echo -e "[2/7] Verificando dependencias del sistema..."
MISSING_DEPS=""

# Verificar librerías necesarias para PyQt5
if ! ldconfig -p | grep -q libxcb; then
    MISSING_DEPS="$MISSING_DEPS libxcb-xinerama0"
fi

if [ -n "$MISSING_DEPS" ]; then
    echo -e "${YELLOW}[AVISO] Algunas dependencias pueden faltar:${NC}"
    echo "        sudo apt install $MISSING_DEPS libxcb-xinerama0 libxkbcommon-x11-0"
fi
echo -e "      ${GREEN}✓ Dependencias verificadas${NC}"

# Crear/activar entorno virtual
echo ""
echo -e "[3/7] Configurando entorno virtual..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi
echo -e "      ${GREEN}✓ Entorno virtual activado${NC}"

# Instalar dependencias
echo ""
echo -e "[4/7] Instalando dependencias Python..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
pip install pyinstaller > /dev/null 2>&1
echo -e "      ${GREEN}✓ Dependencias instaladas${NC}"

# Verificar que las dependencias funcionan
echo ""
echo -e "[5/7] Verificando módulos..."
python3 -c "import fitz; import PyQt5; print('      ✓ PyMuPDF y PyQt5 OK')" || {
    echo -e "${RED}[ERROR] Error al importar módulos${NC}"
    exit 1
}

# Generar icono si no existe
echo ""
echo -e "[6/7] Preparando recursos..."
mkdir -p installer
if [ -f "installer/create_icon.py" ]; then
    python3 installer/create_icon.py 2>/dev/null || true
fi
echo -e "      ${GREEN}✓ Recursos preparados${NC}"

# Compilar con PyInstaller
echo ""
echo -e "[7/7] Compilando ejecutable..."
echo ""

# Usar spec file si existe, sino crear uno básico
if [ -f "ModificadorPDF.spec" ]; then
    pyinstaller --clean ModificadorPDF.spec
else
    pyinstaller --clean \
        --name="PDF_Editor_Pro" \
        --windowed \
        --onedir \
        --add-data="LICENSE.txt:." \
        --add-data="LICENSE_EN.txt:." \
        --hidden-import=PyQt5 \
        --hidden-import=PyQt5.QtCore \
        --hidden-import=PyQt5.QtGui \
        --hidden-import=PyQt5.QtWidgets \
        --hidden-import=fitz \
        main.py
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     ✓ COMPILACIÓN COMPLETADA                          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "El ejecutable se encuentra en:"
    echo "  ./dist/PDF_Editor_Pro/ o ./dist/ModificadorPDF/"
    echo ""
    echo "Para ejecutar:"
    echo "  cd dist/PDF_Editor_Pro && ./PDF_Editor_Pro"
    echo ""
else
    echo -e "${RED}[ERROR] La compilación falló${NC}"
    exit 1
fi

# Desactivar entorno virtual
deactivate 2>/dev/null || true

echo "¿Deseas crear también la versión portable? (s/n)"
read -r response
if [[ "$response" =~ ^[Ss]$ ]]; then
    bash build_portable_linux.sh
fi
