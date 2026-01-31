# PDF Editor Pro

Editor de PDF profesional para Windows con capacidades completas de edición de texto.

## Características

- ✅ **Arrastrar y soltar PDFs** directamente en la ventana
- ✅ **Selección de texto** precisa con el ratón
- ✅ **Resaltado** de texto seleccionado
- ✅ **Eliminación real** de texto (no solo visual)
- ✅ **Edición de texto** manteniendo la tipografía original
- ✅ **Preservación de formularios** y estructura del PDF
- ✅ **Deshacer/Rehacer** operaciones
- ✅ **Navegación** con miniaturas de páginas
- ✅ **Zoom** flexible (25% - 400%)
- ✅ **Guardar** y **Exportar** PDF con cambios

## Requisitos del Sistema

- Windows 10/11 (64-bit)
- Python 3.8 o superior (solo para desarrollo)

## Instalación para Desarrollo

1. **Clonar o descargar** el proyecto

2. **Crear entorno virtual:**

   ```bash
   cd pdf_editor
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Instalar dependencias:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar:**

   ```bash
   python main.py
   ```

## Crear Ejecutable (.exe)

### Método Automático

Ejecutar el script `build.bat`:

```bash
build.bat
```

### Método Manual

```bash
pip install pyinstaller
pyinstaller build_exe.spec
```

El ejecutable se generará en `dist/PDF_Editor_Pro.exe`

## Uso

### Abrir PDF

- **Arrastra un PDF** directamente a la ventana
- Menú: Archivo → Abrir
- Atajo: `Ctrl+O`

### Herramientas de Edición

| Herramienta | Descripción |
| ----------- | ----------- |
| 🔤 Seleccionar | Selecciona texto para copiar o ver información |
| 🖍️ Resaltar | Resalta texto seleccionado en amarillo |
| 🗑️ Eliminar | Elimina permanentemente el texto seleccionado |
| ✏️ Editar | Click en texto para modificarlo |

### Selección y Eliminación de Texto

1. Selecciona la herramienta **Eliminar** (🗑️)
2. Arrastra con el ratón sobre el texto a eliminar
3. Confirma la eliminación en el diálogo
4. El texto se elimina **permanentemente** del PDF

### Edición de Texto

1. Selecciona la herramienta **Editar** (✏️)
2. Haz click sobre el texto a modificar
3. Escribe el nuevo texto en el diálogo
4. El nuevo texto mantiene el formato original

### Guardar Cambios

- **Guardar**: `Ctrl+S` - Guarda en el archivo actual
- **Guardar como**: `Ctrl+Shift+S` - Guarda como nuevo archivo

### Navegación

- **Zoom**: `Ctrl + Rueda del ratón` o botones de zoom
- **Páginas**: Click en miniaturas o usar controles de página
- **Ajustar**: Ajustar al ancho o ver página completa

## Notas Técnicas

### Preservación de Estructura

El editor preserva:

- Campos de formulario (AcroForm)
- Metadatos del documento
- Enlaces y marcadores
- Capas y adjuntos

### Limitaciones

- Solo funciona con PDFs textuales (no escaneados)
- PDFs protegidos con contraseña requieren desbloqueo previo
- La edición de texto compleja puede afectar el layout

## Tecnologías Utilizadas

- **Python 3.x** - Lenguaje principal
- **PyMuPDF (fitz)** - Manipulación de PDF
- **PyQt5** - Interfaz gráfica
- **PyInstaller** - Creación de ejecutable

## Estructura del Proyecto

```text
pdf_editor/
├── main.py              # Punto de entrada
├── requirements.txt     # Dependencias
├── build.bat           # Script de compilación
├── build_exe.spec      # Configuración PyInstaller
├── core/
│   ├── __init__.py
│   └── pdf_handler.py  # Lógica de manipulación PDF
└── ui/
    ├── __init__.py
    ├── main_window.py  # Ventana principal
    ├── pdf_viewer.py   # Visor de PDF
    ├── thumbnail_panel.py  # Panel de miniaturas
    └── toolbar.py      # Barra de herramientas
```

## Licencia

PDF Editor Pro © 2026 Oriol Alonso Esplugas - Todos los derechos reservados

Este software es **GRATUITO para uso personal**. Consulta el archivo [LICENSE.txt](LICENSE.txt) para los términos completos.

### Resumen de la licencia

| ✅ Permitido            | ❌ Prohibido sin autorización |
| ----------------------- | ----------------------------- |
| Uso personal gratuito   | Vender el software            |
| Redistribución gratuita | Uso comercial                 |
| Uso educativo           | Monetización                  |

⚠️ **IMPORTANTE**: Cualquier uso comercial, venta o monetización requiere autorización previa y retribución al autor.

📧 **Contacto**: [GitHub - Oriol-1](https://github.com/Oriol-1)

---

**Versión**: 1.0.0
