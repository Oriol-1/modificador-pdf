# PROMPT MEJORADO - Editor de Texto en PDFs v2.0

> **Tono**: Senior Engineer. **Enfoque**: Realismo técnico + aspiración controlada.
> **Stack**: PyMuPDF (fitz) + PyQt5 + Python 3.8+

---

## 📋 VISIÓN GENERAL

Construir un **editor de texto profesional para PDFs** que permita ediciones **controladas y reversibles** manteniendo la fidelidad visual original del documento. A diferencia de recomposición completa (type-reset), este sistema opera con **edición localizada** sobre el contenido existente.

### Restricción de Alcance (Crítica)

El editor **respetará tipografía y tamaño existentes**, pero dentro de los límites técnicos de PyMuPDF:

- ✅ Fuentes embebidas **se detectan** pero se mapean a equivalentes estándar PDF

- ✅ Tamaño exacto **se preserva**

- 🟡 Negritas **se aproximan** (no detección automática disponible)

- 🟡 Kerning/spacing **se respeta** en PDFs nativos, pero sin garantía en escaneados

---

## 🎯 OBJETIVO PRIMARIO

Permitir que usuarios **editen contenido textual** en un PDF sin:

1. Romper la estructura o layout del documento
2. Perder estilos (tamaño, fuente base, posición)
3. Necesidad de recomposición global de páginas
4. Cambio visual notable del documento (excepto el texto editado)

---

## 📌 REQUISITOS FUNCIONALES (Priorizados)

### Nivel 1 - CRÍTICO (MVP)

#### 1.1 - Edición Localizada sin Reflujo

- [ ] El usuario selecciona un fragmento de texto en la página

- [ ] Puede reemplazarlo con nuevo contenido

- [ ] El nuevo texto **mantiene exactamente la misma**:
  - Fuente base (o equivalente estándar si no disponible)
  - Tamaño en puntos (pt)
  - Posición (x, y) del párrafo
  - Color (si es posible detectable)

- [ ] NO se modifican:
  - Márgenes de página
  - Espaciado de párrafos circundantes
  - Elementos gráficos (imágenes, líneas)
  - Estructura de bloques de texto

#### 1.2 - Preservación de Métricas Tipográficas

- [ ] **Detectar** automáticamente (antes de editar):
  - Nombre de fuente: `fitz page.get_text("dict")` → `span["font"]`
  - Tamaño: `span["size"]` (típicamente 10-14 pt para body)
  - Color de texto: `span["color"]` o `span["flags"]`
  - Relleno actual (width × height del rect del fragmento)

- [ ] **Aplicar** lo detectado:
  - Usar `QFont(font_name, size_pt)` en PyQt5 para rendering local
  - Validar con `QFontMetrics` que el nuevo texto cabe en el área
  - Si no cabe, aplicar estrategia del Requisito 1.5

- [ ] **Mapeo de Fuentes** (fallback):
  - Mantener tabla:

    ```text
    "Arial"        → "helv" (Helvetica)
    "Times New Roman" → "times" (Times)
    "Courier"      → "cour" (Courier)
    "Symbol", "Wingdings" → "symbols" (Symbol)
    [otros]        → "helv" (fallback seguro)
    ```text

  - **Cuando se use fallback, loguear advertencia**:
    `"Fuente 'Custom' no disponible en PDF, usando Helvetica"`

#### 1.3 - Sistema de Formato Mínimo (Negritas)

**IMPORTANTE**: Negritas tienen limitación técnica. PyMuPDF NO expone el "weight" de fuentes:

- [ ] **Detección de negritas existentes**:
  - ❌ NO es posible detectar automáticamente si original es bold
  - Workaround: Ofrecer **opción manual** en UI: "¿Mantener negrita?"
  - El editor **asume texto normal** por defecto

- [ ] **Aplicación de negritas (por usuario)**:
  - Si el usuario marca "negrita" en la edición:
    - Intentar usar variante bold: `fitz text_dict` con `weight=700`
    - Si falla, usar aproximación: **subrayado + color oscuro** (fallback visual)
    - **Loguear**: qué estrategia se usó

- [ ] **Copy/Paste de negritas**:
  - Al pegar texto externo con RTF/HTML:
    - Extraer información de estilo (HTML `<b>` o RTF `\b`)
    - Mapear a: texto normal + flag de "aplicar bold"
    - Aplicar strategy de arriba
  - Resultado: texto pegado adopta fuente/tamaño del destino, pero mantiene intención de bold

#### 1.4 - Undo/Redo Garantizado

- [ ] Cada edición crea un **snapshot** (PDF bytes + overlay state)

- [ ] Máximo 20 niveles de undo (configurable)

- [ ] Botones Undo/Redo funcionales

- [ ] Atajo: `Ctrl+Z` / `Ctrl+Y`

- [ ] Al deshacer, restaurar **estado visual completo** (texto, posición, selección)

#### 1.5 - Política Estricta: "Texto que No Cabe"

Definir de forma clara y consistente:

**Prioridad 1 (Predeterminado)**: Recorte con advertencia

- Calcular relleno disponible: `QFontMetrics.boundingRect(new_text).width()`

- Si excede: **mostrar diálogo**:  ```text
  "El texto no cabe en el área original.
  Opciones:
  [A] Recortar con '...' (perder contenido)
  [B] Reducir espaciado (tracking: -5%, -10%, -15%, -20%)
  [C] Reducir tamaño (usuario autoriza % reducción)
  [Cancelar]"
  ```text

- **Valor por defecto recomendado**: [B] espaciado (-10%)

**Prioridad 2**: Ajuste de tracking (espaciado entre letras)

- Permitir reducción máxima: -20% del espaciado estándar

- No permitir aumento (evitar desborde)

- Validar visualmente antes de aplicar

**Prioridad 3**: Reducción de tamaño

- Solo si usuario lo aprueba explícitamente

- Mínimo permitido: 70% del tamaño original (ej: 12pt → 8.4pt)

- Loguear decisión

**Nunca**:

- Cambiar fuente

- Mover párrafos circundantes

- Crear reflujo de texto

---

### Nivel 2 - IMPORTANTE (Post-MVP)

#### 2.1 - Múltiples Selecciones en un Párrafo

- [ ] Permitir seleccionar + editar múltiples fragmentos sin perder contexto

- [ ] Aplicar negritas parciales (ej: "Esta **parte** es bold")

- [ ] Requiere: parsing de "runs" de estilo (compatible con struct interno)

#### 2.2 - Estilos Adicionales (Futuro)

- Cursiva (igual limitación que bold)

- Subrayado (más viable con PyMuPDF)

- Tachado

#### 2.3 - Validación de Viabilidad

- [ ] Antes de guardar, verificar:
  - "¿PDF original embebía fuentes custom? Sí/No"
  - "¿Se usó fallback de fuentes? [list]"
  - "¿Se ajustó tracking o tamaño? [detalles]"

- [ ] Ofrecer **reporte de cambios** antes de guardar

---

## 🛠️ ARQUITECTURA MEJORADA

### Módulos Propuestos (refactorización leve)

#### `core/font_manager.py` (NUEVO - 200-300 líneas)

```python
class FontManager:
    """Gestión centralizada de fuentes con fallbacks."""

    # Tabla de mapeos conocidos
    FONT_MAPPING = {...}

    def detect_font(self, span: dict) -> FontDescriptor:
        """
        Extrae: nombre, tamaño, color, flags
        Retorna: (font_name, size_pt, color_hex, flags)
        """
        pass

    def apply_font_to_text(self, text: str, descriptor: FontDescriptor) -> bool:
        """
        Intenta escribir en PDF con exactas métricas.
        Retorna: éxito, o (éxito, fallback_reason)
        """
        pass

    def get_bounding_rect(self, text: str, descriptor: FontDescriptor) -> QRectF:
        """
        Calcula tamaño exacto en QFont para validar cabe.
        """
        pass

    def handle_bold(self, text: str, descriptor: FontDescriptor,
                   should_bold: bool) -> Tuple[str, str]:
        """
        Retorna: (rendered_text, bold_strategy)
        bold_strategy in ["exact_bold", "approximate_bold", "warning_fallback"]
        """
        pass

```text

#### `core/pdf_handler.py` (EXTENDER)

```python
class PDFDocument:
    # Agregar métodos:

    def get_text_run_descriptors(self, page_num: int, area_rect: fitz.Rect
                                  ) -> List[FontDescriptor]:
        """
        Lee todos los fragmentos en una área y sus estilos.
        """
        pass

    def replace_text_preserving_metrics(self, page_num: int, old_text: str,
                                         new_text: str, descriptor: FontDescriptor
                                         ) -> bool:
        """
        Reemplaza + valida que métricas se mantienen.
        Retorna: éxito o (éxito, warnings)
        """
        pass

    def detect_bold_in_span(self, span: dict) -> Optional[bool]:
        """
        Intenta heurística de detección de bold:
        - Comparar font_name con variantes (_Bold, -B, Bold)
        - Comparar bbox width esperado vs. actual
        Retorna: bool o None (incierto)
        """
        pass

```text

#### `ui/text_editor_dialog.py` (EXTENDER O NUEVO)

```python
class EnhancedTextEditDialog:
    """
    Diálogo de edición con validaciones en tiempo real.
    """

    def __init__(self, original_text: str, font_descriptor: FontDescriptor, ...):
        # Preview en vivo: mostrar texto como aparecería
        # Aviso si no cabe: "Texto muy largo, opciones: [A][B][C]"
        # Checkboxes: "Mantener negrita?" / "Aplicar negrita?"
        pass

    def validate_text_fits(self) -> Tuple[bool, Optional[str]]:
        """
        Retorna: (cabe, mensaje_si_no)
        """
        pass

    def get_styling_choices(self) -> Dict:
        """
        Retorna: {"keep_bold": bool, "apply_bold": bool, "apply_italic": bool, ...}
        """
        pass

```text

#### `ui/pdf_viewer.py` (MODIFICAR)

```python
class PDFPageView:
    # Métodos nuevos/mejorados:

    def sync_all_text_items_to_data(self):
        """Ya existe. Extiende para incluir análisis de bold."""
        pass

    def _apply_style_to_item(self, item: EditableTextItem,
                            style_choices: Dict) -> None:
        """Aplica estilos finales (bold, italic, etc.)"""
        pass

    def on_text_edited(self, item_id: str, new_text: str,
                      font_descriptor: FontDescriptor) -> bool:
        """
        Triggers cuando usuario termina de editar.
        Valida, aplica estrategia de espaciado si es necesario.
        """
        pass

```text

---

## 📊 ESTRATEGIA DE FUENTES (MEJORADA)

### 1. Fuentes Embebidas en PDF

**Caso A: Fuente estándar PDF detectada**

```text
Original: "Arial, 12pt"
Detectado en: span["font"] = "Arial"
Mapeo: Arial → "helv" (Helvetica)
Acción: Usar "helv" al escribir
Resultado: ✅ Visual casi idéntico
Aviso: Bajo (fuente estándar)

```text

**Caso B: Fuente custom/proprietaria**

```text
Original: "MyriadPro, 12pt"
Detectado: span["font"] = "MyriadPro" o nombre embebido
Mapeo: MyriadPro → ??? (no hay mapping)
Fallback: MyriadPro → "helv" (Helvetica)
Resultado: 🟡 Similar pero no idéntica
Aviso: ALTO - mostrar al usuario antes de guardar

```text

**Tabla de Mappeos (Exhaustiva)**

```python
FONT_FALLBACK_TABLE = {
    # [PDF Std] → [fitz name]
    "ArialMT": "helv",
    "Arial": "helv",
    "Helvetica": "helv",
    "HelveticaNeue": "helv",

    "TimesNewRomanPSMT": "times",
    "Times-Roman": "times",
    "TimesRoman": "times",

    "Courier": "cour",
    "CourierNew": "cour",
    "Courier-Oblique": "cour",

    "Symbol": "symbols",
    "ZapfDingbats": "symbols",

    # Fallbacks comunes (mapping inteligente)
    "Georgia": "times",      # Serif similar
    "Verdana": "helv",       # Sans-serif similar
    "Comic Sans MS": "helv", # Unsafe fallback
    "Impact": "helv",        # Bold-heavy → seguro

}

# Estrategia: si no está en tabla, usar categorización

def smart_fallback(font_name: str) -> str:
    # 1. Búsqueda exacta
    if font_name in FONT_FALLBACK_TABLE:
        return FONT_FALLBACK_TABLE[font_name]

    # 2. Búsqueda parcial (prefijos)
    for key, value in FONT_FALLBACK_TABLE.items():
        if font_name.lower().startswith(key.lower()):
            return value

    # 3. Heurística: ¿contiene "serif"?
    if "serif" in font_name.lower():
        return "times"

    # 4. Default seguro
    return "helv"

```text

### 2. Detección de Negritas (Limitada)

**Problema**: PyMuPDF **NO expone `weight`** de forma confiable.

**Estrategia Mixta**:

```python
def detect_possible_bold(span: dict, page: fitz.Page) -> Optional[bool]:
    """
    Intenta heurística multi-fuente.
    Retorna: True (probably bold), False (probably normal), None (uncertain)
    """

    # Heurística 1: Nombre de fuente
    font_name = span.get("font", "").lower()
    if "bold" in font_name or "-b" in font_name:
        return True  # Probable

    # Heurística 2: Comparación de anchura (EXPERIMENTAL)
    # Este método es frágil pero útil como "pista"
    expected_width = calculate_expected_width(span["text"], span["size"], font_name)
    actual_width = span["bbox"][2] - span["bbox"][0]
    ratio = actual_width / expected_width if expected_width > 0 else 1.0

    if ratio > 1.15:  # 15% más ancho = probablemente bold
        return True

    # Heurística 3: Lookup en fuentes embebidas de PyMuPDF
    try:
        page_fonts = page.get_fonts()  # [(name, type, flags), ...]
        for fname, ftype, fflags in page_fonts:
            if fflags & 0x20:  # Flag bold en PDF spec
                return True
    except:
        pass

    # Incierto
    return None

# En UI: si None o False, preguntar al usuario

def ask_user_about_bold(original_text: str) -> bool:
    """Muestra diálogo: '¿Mantener negrita en este texto?'"""
    dialog = QMessageBox(...)
    return dialog.exec_() == QMessageBox.Yes

```text

### 3. Preservación de Negritas en Copy/Paste

**Flujo**:

```text
1. Usuario copia texto desde Word/Pages/otro app
   - Clipboard contiene: texto + metadata (RTF/HTML)

2. Editor detecta: "¿Hay negritas en metadata?"
   - Parsea HTML: <b>...</b> o RTF: \b...\b

3. Al pegar en el PDF:
   - Texto se adapta a: fuente/tamaño del PDF
   - Pero se marcan segmentos como "bold_intent"

4. Al guardar:
   - Aplicar estrategia de bold (exact o approximate)

# Pseudo-código

clipboard_html = extract_html_from_clipboard()
matches = re.findall(r'<b>(.*?)</b>', clipboard_html)
bold_segments = set(matches)

pasted_text = "Hello World"

# Si "World" está en bold_segments:

#   apply_bold_to_segment("World")

```text

---

## 🎬 FLUJO DE EDICIÓN (PASO A PASO)

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario selecciona texto en PDF                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. DETECTAR MÉTRICAS                                        │
│    - font_descriptor = detect_font(span)                    │

│    - maybe_bold = detect_possible_bold(span)                │

│    - Crear snapshot de undo                                 │

└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ABRIR DIÁLOGO DE EDICIÓN                                │
│    - Mostrar texto original                                │

│    - Preview: cómo se vería el nuevo texto                 │

│    - Opciones de bold (si maybe_bold != None)             │

└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. USUARIO ESCRIBE NUEVO TEXTO                             │
│    - En vivo: validar que cabe (VALIDATE_TEXT_FITS)        │

│    - Si no cabe: mostrar opciones [A][B][C]               │

└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. APLICAR ESTILOS (opcional)                              │
│    - ¿Bold? → exact_bold() o approximate_bold()           │

│    - ¿Italic? → future                                     │

└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. SYNC + COMMIT                                           │
│    - sync_all_text_items_to_data()                         │

│    - commit_overlay_texts(font_descriptor, style_choices)  │

│    - Loguear: qué se cambió, warnings, fallbacks          │

└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. GUARDAR                                                 │
│    - Guardar PDF + generar reporte de cambios             │

│    - "Se editaron 3 textos. Warnings: fuente 'custom'     │

│     usó fallback Helvetica. ¿Continuar?"                  │
└─────────────────────────────────────────────────────────────┘

```text

---

## ✅ CRITERIOS DE ACEPTACIÓN (REALISTAS)

### 1. Edición Básica

```gherkin
Given: PDF con párrafo "El viaje fue largo"
When: Usuario edita "viaje" → "viaje increíble"
Then:
  ✅ Texto actualizado a "El viaje increíble fue largo"
  ✅ Fuente y tamaño idénticos
  ✅ Posición del párrafo sin cambios
  ✅ Color igual
  ✅ Guardar y reabrir: cambio persiste

```text

### 2. Preservación de Métricas

```gherkin
Given: PDF original con Times 12pt
When: Editar con nuevo texto (5 palabras → 3 palabras)
Then:
  ✅ Nuevo texto en Times 12pt (no Helvetica)
  ✅ Bounding box del párrafo sin cambios notables
  ✅ Si fallback a "times" ≈ "TimesNewRoman": aceptable

```text

### 3. Manejo de No-Cabe

```gherkin
Given: Párrafo en 12pt con espacio limitado
When: Editar con texto 40% más largo
Then:
  ✅ Diálogo muestra opciones
  ✅ Usuario elige [A] recorte, [B] spacing, [C] size
  ✅ Resultado es visual y legible

```text

### 4. Undo/Redo

```gherkin
Given: 3 ediciones sucesivas
When: Ctrl+Z × 2
Then:
  ✅ Estado restaurado a edición #1
  ✅ Ctrl+Y restaura edición #2 y #3
  ✅ Ningún error de snapshot

```text

### 5. Copy/Paste

```gherkin
Given: Texto de Word con "parte **negrita** normal"

When: Pegar en PDF
Then:
  ✅ Texto pegado en fuente/tamaño del PDF
  ✅ Intención de bold detectada y aplicada (si es posible)
  ✅ No fallos de parsing

```text

### 6. Warnings y Reporting

```gherkin
Given: PDF con fuentes custom ("MyriadPro")
When: Editar + Guardar
Then:
  ✅ Antes de guardar: advertencia "Fuente no estándar"
  ✅ Reporte: "Se usó fallback: MyriadPro → Helvetica"
  ✅ Usuario puede rechazar o aceptar

```text

### 7. Casos Edge

```gherkin
Scenario A: Texto con caracteres especiales (€, ñ, 中文)
  ✅ Preservar encoding
  ✅ Fuente soporta símbolos

Scenario B: PDF encriptado
  ✅ Detectar y denegar edición (o solicitar password)

Scenario C: Múltiples idiomas en una página
  ✅ Cada texto preserva su fuente original
  ✅ Ej: árabe + inglés + chino = 3 fuentes diferentes OK

```text

---

## 📦 DELIVERABLES

### Fase 1 (MVP - Current v1.2.0)

- [x] Edición básica de texto

- [x] Preservación de tamaño

- [x] Sistema de undo/redo

- [x] Guardado persistente

- [ ] Mejor detección de fuentes (FontManager)

- [ ] Diálogos mejorados con preview

### Fase 2 (v1.3.0+)

- [ ] Detección + aplicación de negritas (con warnings)

- [ ] Copy/paste con estilos

- [ ] Validación de cabe + opciones automáticas

- [ ] Reporte pre-guardado de cambios

### Fase 3 (v2.0.0+)

- [ ] Cursiva

- [ ] Subrayado

- [ ] Colores de texto

- [ ] Multi-párrafo + estilos parciales

---

## 🎓 DOCUMENTACIÓN NECESARIA

Por cada módulo nuevo/modificado:
1. **Docstrings** detallados (parámetros, retorno, excepciones)

2. **Logs** con niveles: INFO (operación OK), WARNING (fallback), ERROR

3. **Tests**: casos happy-path + edge cases (charset especial, fuentes custom, etc.)
4. **Ejemplos**: cómo usar FontManager, cómo interpretar warnings

---

## 🚀 IMPLEMENTACIÓN SUGERIDA

1. **Refactor FontManager** (core/font_manager.py): 1-2 días

2. **Extender PDFDocument** con métodos de detección: 1 día

3. **Mejorar diálogos de edición**: 1-2 días
4. **Testing exhaustivo**: 2-3 días
5. **Documentación**: 1 día

**Timeline total**: ~1-2 sprints (2 semanas)

---

## ⚠️ LIMITACIONES DOCUMENTADAS

| Limitación | Razón | Workaround |
| ----------- | ------- | ----------- |
| No detectar bold automático | PyMuPDF API limitation | Heurística + preguntar usuario |
| No reutilizar fuentes custom | PyMuPDF solo 14 fonts | Mapeo + fallback inteligente |
| No kerning perfecto | No API en PyMuPDF | Ajuste de tracking (espaciado) |
| No soporte de ligaduras | No API | Aceptar aproximación visual |
| No detección de tamaño dinámico | PDF ambiguo | Usar QFontMetrics como referencia |

---

## 📖 REFERENCIAS TÉCNICAS

- **PyMuPDF Docs**: https://pymupdf.readthedocs.io/

- **PDF Spec** (Font handling): ISO 32000

- **PyQt5 QFontMetrics**: https://doc.qt.io/qt-5/qfontmetrics.html

- **Bold Detection Heuristics**: Post de análisis interno (ver `detect_possible_bold()`)

---

**Versión**: 2.0
**Último update**: Feb 2026
**Status**: Ready for Implementation Phase 1

