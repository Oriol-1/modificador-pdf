# 🏗️ PROMPT ARQUITECTO SENIOR - PDF Editor Pro

> **Usa este prompt ANTES de cualquier análisis o refactor del proyecto**

---

## 📋 CONTEXTO DEL PROYECTO

### Descripción
**PDF Editor Pro** - Editor de PDF de escritorio con:
- Selección y edición de texto preservando tipografía original
- Resaltado y eliminación de texto
- Sistema de workspace para gestión de múltiples PDFs
- Soporte para PDFs de imagen (texto overlay)
- Sistema undo/redo basado en snapshots
- Interfaz PyQt5 con tema oscuro

### Stack Tecnológico
```
├── Python 3.11+
├── PyQt5 (UI desktop)
├── PyMuPDF/fitz (manipulación PDF)
├── pikepdf (reparación de PDFs)
└── PyInstaller (distribución)
```

### Estructura Actual
```
modificar-pdf/
├── main.py                    # Punto de entrada (35 líneas)
├── core/
│   └── pdf_handler.py         # Motor PDF (~1500 líneas) ⚠️ CRÍTICO
├── ui/
│   ├── main_window.py         # Ventana principal (~1860 líneas) ⚠️ CRÍTICO
│   ├── pdf_viewer.py          # Visor/editor (~2600 líneas) ⚠️ MÁS CRÍTICO
│   ├── workspace_manager.py   # Gestión workspaces (~1300 líneas)
│   ├── thumbnail_panel.py     # Panel miniaturas (131 líneas)
│   ├── toolbar.py             # Barra herramientas (286 líneas)
│   └── help_system.py         # Sistema ayuda (503 líneas)
├── tests/
│   ├── test_pdf_editor.py     # Tests del editor
│   └── test_workspace.py      # Tests de workspace
├── pdf_editor/                # ⚠️ DUPLICACIÓN: Carpeta duplicada
│   └── [mismos archivos...]   # TODO: Consolidar con raíz
└── installer/
    └── inno_setup.iss         # Script instalador Windows
```

---

## 🎯 PRINCIPIO FUNDAMENTAL

> **"Mover texto = reescribir el mismo texto cambiando posicionamiento (matrix/offset), sin parchear el stream y sin recrear elementos externos"**

El usuario quiere un comportamiento estilo Adobe Acrobat:
1. Seleccionar texto con click
2. Moverlo arrastrando
3. Modificar sin afectar objetos adyacentes (imágenes, gráficos)
4. Preservar estilos originales (fuente, tamaño, color)

---

## 🚨 PROBLEMAS IDENTIFICADOS

### 1. Código Monolítico (Crítico)
```python
# pdf_viewer.py tiene ~2600 líneas en UNA clase
# Mezcla responsabilidades:
# - Renderizado de página
# - Gestión de selección
# - Edición de texto
# - Eventos de mouse/teclado
# - Items visuales (highlights, overlays)
# - Menús contextuales
```

### 2. Duplicación de Código
```
raíz/           vs    pdf_editor/
├── core/             ├── core/
├── ui/               ├── ui/
└── tests/            └── tests/
```
- Mismos archivos duplicados
- Difícil saber cuál es el "correcto"
- Cambios en uno no se reflejan en otro

### 3. Acoplamiento Fuerte
```python
# En pdf_viewer.py:
self.pdf_doc.delete_text_in_rect(...)  # Acceso directo al documento
self.pdf_doc.highlight_text(...)       # Sin capa de abstracción
self.pdf_doc.edit_text(...)            # Difícil de testear
```

### 4. Sistema de Coordenadas Complejo
- PyMuPDF usa coordenadas PDF (origen abajo-izquierda, Y crece hacia arriba)
- Qt usa coordenadas pantalla (origen arriba-izquierda, Y crece hacia abajo)
- Páginas pueden tener rotación (0, 90, 180, 270)
- Transformaciones dispersas por el código

---

## 📐 ARQUITECTURA RECOMENDADA

### Capa 1: Core (Sin dependencias UI)
```python
core/
├── models.py           # Dataclasses: TextBlock, TextSpan, BoundingBox
├── document.py         # PDFDocument: abrir, cerrar, guardar, undo/redo
├── parser.py           # PDFTextParser: extraer texto con formato
├── editor.py           # PDFTextEditor: modificar, mover, eliminar
├── coordinates.py      # Sistema de coordenadas unificado
└── spatial_index.py    # Índice espacial para hit-testing O(1)
```

### Capa 2: Services (Lógica de negocio)
```python
services/
├── text_grouper.py     # Agrupar spans en palabras/líneas/bloques
├── font_mapper.py      # Mapear fuentes PDF a sistema
└── undo_manager.py     # Gestión de snapshots para undo/redo
```

### Capa 3: UI (PyQt5)
```python
ui/
├── main_window.py      # Orquestación principal
├── toolbar.py          # Acciones de toolbar
├── thumbnail_panel.py  # Navegación de páginas
├── viewer/
│   ├── page_view.py    # QGraphicsView para una página
│   ├── selection.py    # Gestión de selección
│   └── overlays.py     # Items visuales (highlights, etc)
├── dialogs/
│   └── text_edit.py    # Diálogos de edición
└── workspace/
    └── manager.py      # Gestión de grupos de trabajo
```

---

## 🔧 INSTRUCCIONES PARA REFACTOR

### DO (Hacer)
1. **Mantener funcionalidad existente** - El programa actual FUNCIONA
2. **Refactor incremental** - Un archivo a la vez
3. **Tests antes de cambiar** - Asegurar que no se rompe nada
4. **Separar responsabilidades** - Una clase = una responsabilidad
5. **Documentar cambios** - Comentarios claros del "por qué"

### DON'T (No hacer)
1. ❌ Reescribir todo desde cero (ya lo intentamos, falló)
2. ❌ Crear nuevas carpetas paralelas sin migrar
3. ❌ Cambiar la API pública sin actualizar usos
4. ❌ Ignorar la duplicación existente
5. ❌ Añadir dependencias sin necesidad

---

## 📊 MÉTRICAS ACTUALES

| Archivo | Líneas | Complejidad | Prioridad |
|---------|--------|-------------|-----------|
| pdf_viewer.py | 2,596 | ALTA | 🔴 URGENTE |
| main_window.py | 1,864 | ALTA | 🟠 ALTA |
| pdf_handler.py | 1,501 | MEDIA | 🟠 ALTA |
| workspace_manager.py | 1,307 | MEDIA | 🟡 MEDIA |
| help_system.py | 503 | BAJA | 🟢 BAJA |
| toolbar.py | 286 | BAJA | 🟢 BAJA |
| thumbnail_panel.py | 131 | BAJA | 🟢 BAJA |

**Total código de aplicación: ~8,200 líneas**

---

## 🎯 PLAN DE ACCIÓN SUGERIDO

### Fase 1: Consolidación (Inmediato)
1. Eliminar carpeta `pdf_editor/` duplicada
2. Asegurar que solo hay UNA versión del código
3. Verificar que todo funciona desde raíz

### Fase 2: Extracción de Modelos
1. Crear `core/models.py` con dataclasses
2. Extraer `TextBlock`, `BoundingBox`, etc. de `pdf_handler.py`
3. Actualizar imports

### Fase 3: Sistema de Coordenadas
1. Crear `core/coordinates.py`
2. Centralizar todas las transformaciones
3. Documentar claramente PDF ↔ Screen

### Fase 4: Dividir PDFPageView
1. Extraer `SelectionManager` de `pdf_viewer.py`
2. Extraer `OverlayManager` para items visuales
3. Extraer lógica de edición a clase separada

### Fase 5: Tests
1. Tests unitarios para `core/`
2. Tests de integración para flujos principales
3. Tests de UI con pytest-qt

---

## 💬 CÓMO USAR ESTE PROMPT

Cuando me pidas analizar o modificar el código, **primero dame el contexto**:

```
"Quiero [OBJETIVO].
Actualmente el problema es [DESCRIPCIÓN].
El archivo principal es [ARCHIVO].
Usa el prompt PDF_EDITOR_ARCHITECT.md como guía."
```

### Ejemplo:
```
"Quiero separar la lógica de selección de pdf_viewer.py.
Actualmente mouseReleaseEvent tiene 200 líneas.
El archivo principal es ui/pdf_viewer.py.
Usa el prompt PDF_EDITOR_ARCHITECT.md como guía."
```

---

## 📚 REFERENCIAS RÁPIDAS

### Abrir PDF
```python
# En main_window.py
self.pdf_doc = PDFDocument()
self.pdf_doc.open(file_path)
self.pdf_viewer.set_document(self.pdf_doc)
```

### Renderizar Página
```python
# En pdf_viewer.py
pixmap = self.pdf_doc.render_page(page_num, zoom=self.zoom_factor)
qimage = QImage(pixmap.samples, pixmap.width, pixmap.height, ...)
```

### Encontrar Texto en Punto
```python
# En pdf_handler.py
block = self.find_text_at_point(page_num, (x, y), use_visual_coords=True)
```

### Editar Texto
```python
# En pdf_handler.py
success = self.edit_text(page_num, old_rect, new_text, new_size, is_bold)
```

---

## ⚠️ NOTAS IMPORTANTES

1. **El programa FUNCIONA** - No romper funcionalidad existente
2. **Usuarios reales** - Hay gente usando esto en producción
3. **Windows primero** - El target principal es Windows 10/11
4. **Instalador Inno Setup** - Cambios deben ser compatibles

---

*Última actualización: 4 de febrero de 2026*
*Versión del proyecto: 1.0.1*
*Branch activo: pruebas-experimentales*
