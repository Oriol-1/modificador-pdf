# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para Modificador de PDF
Compatible con Windows 10/11 y macOS
"""

import sys
import os

# Detectar sistema operativo
is_windows = sys.platform == 'win32'
is_mac = sys.platform == 'darwin'

# Rutas
spec_dir = os.path.dirname(os.path.abspath(SPEC))
icon_dir = os.path.join(spec_dir, 'installer')

# Icono según SO
if is_windows:
    icon_file = os.path.join(icon_dir, 'app_icon.ico')
elif is_mac:
    icon_file = os.path.join(icon_dir, 'app_icon.icns')
else:
    icon_file = None

# Verificar que existe el icono
if icon_file and not os.path.exists(icon_file):
    icon_file = None
    print(f"⚠ Icono no encontrado, se usará el predeterminado")

# Hidden imports necesarios para PyQt5 y PyMuPDF
hidden_imports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',
    'fitz',
    'fitz.fitz',
]

# Análisis del código
a = Analysis(
    ['main.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=[
        # Incluir iconos si existen
        (os.path.join(icon_dir, 'app_icon.ico'), 'installer') if os.path.exists(os.path.join(icon_dir, 'app_icon.ico')) else (None, None),
        (os.path.join(icon_dir, 'app_icon.png'), 'installer') if os.path.exists(os.path.join(icon_dir, 'app_icon.png')) else (None, None),
        # Incluir archivos de licencia
        ('LICENSE.txt', '.'),
        ('LICENSE_EN.txt', '.'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tkinter',
        'unittest',
        'pytest',
        'setuptools',
        'pip',
    ],
    noarchive=False,
    optimize=1,
)

# Filtrar datas None
a.datas = [d for d in a.datas if d[0] is not None]

# Crear PYZ (archivo comprimido de Python)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Configuración del ejecutable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Modificador de PDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Sin consola (aplicación GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
    version='version_info.txt' if is_windows and os.path.exists('version_info.txt') else None,
)

# Recopilar archivos
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ModificadorPDF',
)

# Para macOS: crear bundle .app
if is_mac:
    app = BUNDLE(
        coll,
        name='Modificador de PDF.app',
        icon=icon_file,
        bundle_identifier='com.modificadorpdf.app',
        info_plist={
            'CFBundleName': 'Modificador de PDF',
            'CFBundleDisplayName': 'Modificador de PDF',
            'CFBundleGetInfoString': 'Herramienta para organizar y clasificar PDFs',
            'CFBundleIdentifier': 'com.modificadorpdf.app',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,  # Soporte modo oscuro
            'LSMinimumSystemVersion': '10.13.0',
        },
    )
