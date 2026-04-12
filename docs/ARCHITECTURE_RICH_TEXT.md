# 📝 Arquitectura del Sistema de Edición de Texto Enriquecido

## Estado: ✅ Implementado

**Fecha**: 4 de febrero de 2026  
**Versión**: Phase 2.5

---

## 🎯 Problema Resuelto

El editor anterior trataba cada bloque de texto como una unidad completa, sin permitir:

- Selección parcial de texto
- Aplicar negrita solo a algunas palabras
- Preservar diferentes estilos dentro del mismo bloque

---

## 🏗️ A) Arquitectura del Sistema

### Módulos Implementados

```text
core/
├── pdf_handler.py        # +100 líneas nuevas
│   ├── get_text_spans_in_rect()     # Extrae spans con estilos
│   ├── add_text_runs_to_page()      # Escribe múltiples runs
│   └── (métodos existentes mejorados)
│
ui/
├── rich_text_editor.py   # ✨ NUEVO (600+ líneas)
│   ├── TextRun           # Dataclass: fragmento con estilo
│   ├── TextBlock         # Colección de runs
│   ├── RichTextEditor    # Widget QTextEdit con soporte runs
│   ├── RichTextPreview   # Preview con fuente exacta
│   └── RichTextEditDialog # Diálogo principal
│
├── pdf_viewer.py         # Modificado
│   ├── _get_text_spans_for_item()   # Detecta múltiples estilos
│   ├── _edit_text_content()         # Usa editor apropiado
│   ├── _apply_rich_text_edit()      # Aplica runs al item
│   └── commit_overlay_texts()       # Soporta runs mixtos
```

### Flujo de Datos

```text
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   PDF Original  │      │  RichTextEditor  │      │   PDF Final     │
│   (spans)       │ ──── │  (edición)       │ ──── │  (runs)         │
└─────────────────┘      └──────────────────┘      └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
  get_text_spans_          TextBlock con              add_text_runs_
  in_rect()                TextRuns                   to_page()
```

---

## 🔤 B) Estrategia de Fuentes

### Detección de Fuente Embebida

```python
# En pdf_handler.py - get_text_spans_in_rect()
font_name = span.get("font", "")
flags = span.get("flags", 0)

# Detectar bold desde flags (bit 16) o nombre
is_bold = bool(flags & 16) or "bold" in font_name.lower()
is_italic = bool(flags & 2) or "italic" in font_name.lower()
```

### Uso de la Misma Fuente

```python
# En add_text_runs_to_page()
if is_bold and is_italic:
    font_name = "hebi"  # Helvetica-BoldOblique
elif is_bold:
    font_name = "hebo"  # Helvetica-Bold
elif is_italic:
    font_name = "heit"  # Helvetica-Oblique
else:
    font_name = "helv"  # Helvetica
```

### Fallback cuando no está disponible

1. **Prioridad métricas equivalentes**: Usar Helvetica como base universal
2. **Reglas para evitar cambios visibles**:
   - Preservar tamaño exacto
   - Preservar posición exacta
   - Factor de ajuste 0.75 para diferencia Qt vs PDF
3. **Advertencia al usuario**: El sistema detecta y alerta si no cabe

---

## 🔵 C) Política de Negritas

### Mapeo Normal → Bold

```python
# TextRun define el estilo
@dataclass
class TextRun:
    text: str
    font_name: str = "Helvetica"
    font_size: float = 12.0
    is_bold: bool = False
    is_italic: bool = False
    color: str = "#000000"
```

### Si no existe variante Bold

**Estrategia implementada:**

1. Usar `hebo` (Helvetica-Bold) como fuente bold universal
2. PyMuPDF embebe las fuentes base automáticamente
3. No se usa "fake bold" (stroke expansion) - siempre fuente real

---

## 📋 D) Plan de Copy/Paste

### Formato Intermedio

El `RichTextEditor` usa `QTextDocument` internamente:

- Soporta HTML rico nativamente
- Preserva formato al pegar desde clipboard
- Normaliza a TextRuns al extraer

### Regla de Adaptación

```python
def get_text_block(self) -> TextBlock:
    """Extrae contenido como TextBlock con runs."""
    # Itera por el documento extrayendo runs
    # Agrupa caracteres con mismo estilo
    # Retorna TextBlock normalizado
```

Al pegar:

- **Mantiene negrita**: Sí
- **Adapta fuente/tamaño**: Usa la fuente base configurada

---

## ✅ E) Criterios de Aceptación

### Test 1: Editar palabra manteniendo fuente

```text
✅ Doble clic en texto → Abre RichTextEditDialog
✅ Editar contenido → Mantiene misma fuente
✅ Guardar → PDF se ve igual salvo texto editado
```

### Test 2: Aplicar negrita parcial

```text
✅ Seleccionar parte del texto
✅ Ctrl+B o botón Bold → Aplica solo a selección
✅ Preview muestra resultado exacto
✅ Guardar → PDF tiene múltiples runs con estilos
```

### Test 3: Pegar texto con negritas

```text
✅ Copiar texto con formato (ej: de Word)
✅ Pegar en editor → Mantiene negritas
✅ Fuente/tamaño se adaptan al destino
```

---

## 🎛️ Uso del Editor

1. **Abrir PDF** (arrastrar o Ctrl+O)
2. **Activar modo edición** (icono ✏️)
3. **Doble clic en texto** → Se abre el editor apropiado
4. **Seleccionar texto** y usar:

   - **Ctrl+B**: Negrita
   - **Ctrl+I**: Cursiva
   - **Botones de toolbar**
5. **Preview en tiempo real** muestra resultado exacto
6. **Validación automática** indica si el texto cabe
7. **Aceptar** → Cambios se aplican como overlay
8. **Guardar (Ctrl+S)** → Commits al PDF con SummaryDialog

---

## 📊 Componentes UI

| Componente | Descripción |
| ------------ | ------------- |
| `TextRun` | Fragmento de texto con estilo único |
| `TextBlock` | Colección ordenada de TextRuns |
| `RichTextEditor` | QTextEdit con soporte para runs |
| `RichTextPreview` | Vista previa con fuente exacta |
| `RichTextEditDialog` | Diálogo completo de edición |

---

## 🔧 Integración con PDFViewer

```python
# _edit_text_content() detecta automáticamente:
spans = self._get_text_spans_for_item(text_item)
has_mixed_styles = len(spans) > 1

if HAS_RICH_TEXT_EDITOR and has_mixed_styles:
    # Usa RichTextEditDialog
    result = show_rich_text_editor(...)
elif HAS_ENHANCED_DIALOG:
    # Usa EnhancedTextEditDialog (texto simple)
    result = show_text_edit_dialog(...)
else:
    # Fallback: TextEditDialog básico
    dialog = TextEditDialog(...)
```

---

## 📝 Archivos Modificados/Creados

| Archivo | Cambio |
| --------- | -------- |
| `ui/rich_text_editor.py` | ✨ **NUEVO** - 600+ líneas |
| `core/pdf_handler.py` | +100 líneas (spans, runs) |
| `ui/pdf_viewer.py` | +150 líneas (integración) |
| `ui/__init__.py` | Exports actualizados |

---

## 🚀 Resultado

El editor ahora permite:

- ✅ Selección parcial de texto
- ✅ Aplicar negrita a selección
- ✅ Preservar estilos originales
- ✅ Preview en tiempo real
- ✅ Validación de que el texto cabe
- ✅ Copy/paste con formato
- ✅ Múltiples runs con diferentes estilos
