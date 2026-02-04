# Distribución de PROMPT_MEJORADO_v2 por Roles - Fase 2

Fecha: 4 de febrero de 2026  
Proyecto: PDF Editor Pro - Fase 2 (v1.3.0)  
Duración estimada: 2 sprints (4 semanas)

---

## 📋 Resumen para Todos los Roles

**Objetivos de Fase 2**:

1. Agregar soporte para negritas (con heurísticas inteligentes)
2. Habilitar copy/paste desde Word/navegadores manteniendo estilos
3. Validar y reportar cambios de fuentes antes de guardar

**Cambios principales**:

- Nuevo módulo: `FontManager` (gestión centralizada)
- Extender: `PDFDocument` con métodos de detección
- Mejorar: diálogos en `pdf_viewer.py` con validaciones

**Restricción técnica crítica**: PyMuPDF NO puede detectar negritas automáticamente. Usaremos heurísticas + preguntas al usuario.

---

## 👨‍💻 INGENIERO BACKEND / CORE

### Responsabilidad Principal

Implementar módulos de lógica de fuentes y validación. El backend es **crítico**: sin esto, UI no puede avanzar.

### Tareas Específicas

#### Task 1.1: Implementar `FontManager` (200-300 líneas)

**Archivo**: `core/font_manager.py` (NUEVO)

**Métodos a implementar**:

```python
class FontManager:
    # Tabla de mapeos fuente → fallback
    FONT_MAPPING = {
        "Arial": "helv",
        "Times New Roman": "times",
        "Courier": "cour",
        # ... (ver tabla en PROMPT_MEJORADO_v2.md línea 380)
    }

    def detect_font(self, span: dict) -> FontDescriptor:
        """
        Extrae: nombre, tamaño, color, flags del span PyMuPDF
        Input: span dict de page.get_text("dict")
        Output: FontDescriptor(name, size_pt, color_hex, flags)
        """

    def apply_font_to_text(self, text: str, descriptor: FontDescriptor) -> Tuple[bool, Optional[str]]:
        """
        Intenta aplicar fuente a texto.
        Output: (éxito, motivo_fallo_si_aplica)
        """

    def get_bounding_rect(self, text: str, descriptor: FontDescriptor) -> Tuple[float, float]:
        """
        Calcula ancho × alto usando QFontMetrics.
        Usado para validar si texto cabe.
        """

    def handle_bold(self, text: str, descriptor: FontDescriptor, 
                   should_bold: bool) -> Tuple[str, str]:
        """
        Maneja aplicación de negritas con fallback.
        Output: (texto_renderizado, estrategia_usada)
        Estrategias: "exact_bold", "approximate_bold", "warning_fallback"
        """

    def detect_possible_bold(self, span: dict) -> Optional[bool]:
        """
        Heurística de detección (no guarantizada).
        Retorna: True/False/None (incierto)
        """

    def smart_fallback(self, font_name: str) -> str:
        """Fallback inteligente basado en heurísticas."""
```

**Definir antes de codificar**:

- Estructura `FontDescriptor` (NamedTuple o dataclass)
- Algoritmo de heurística para bold (comparar widths, parsear nombre)
- Tabla exhaustiva de mappeos (línea 380-400 de PROMPT_MEJORADO_v2)

**Tests requeridos**:

- `test_font_manager.py` con cobertura >80%
- Test casos: Arial→helv, custom→fallback, bold detection

**Criterio de aceptación**:

- ✅ Detecta fuente de span sin errores
- ✅ Fallback a "helv" por defecto
- ✅ Heurística de bold da resultado True/False/None
- ✅ QFontMetrics calcula bounding rect correcto

---

#### Task 1.2: Extender `PDFDocument` con 3 nuevos métodos

**Archivo**: `core/pdf_handler.py`

**Métodos a agregar**:

```python
def get_text_run_descriptors(self, page_num: int, area_rect: fitz.Rect) -> List[FontDescriptor]:
    """
    Lee todos los fragmentos en un área y retorna sus descriptores.
    Usado para analizar qué fuentes se usan en párrafo.
    """

def replace_text_preserving_metrics(self, page_num: int, old_text: str,
                                     new_text: str, descriptor: FontDescriptor) -> Tuple[bool, List[str]]:
    """
    Reemplaza texto manteniendo exactas las métricas.
    Retorna: (éxito, [warnings si aplica])
    Warnings: ["Fuente no embebida", "Texto recortado", "Tracking reducido 15%"]
    """

def detect_bold_in_span(self, span: dict) -> Optional[bool]:
    """
    Intenta detectar bold usando heurísticas.
    Retorna: True (parece bold) / False (no bold) / None (incierto)
    """
```

**Integración con FontManager**:

- Usar `FontManager.detect_font()` en estos métodos
- Usar `FontManager.handle_bold()` para negritas
- Loguear cada fallback o ajuste

**Tests**:

- `test_pdf_handler.py` - agregar tests para nuevos métodos
- Test con PDF de ejemplo que tiene fuentes custom

**Criterio de aceptación**:

- ✅ `get_text_run_descriptors()` retorna lista de descriptores
- ✅ `replace_text_preserving_metrics()` valida cabe el texto
- ✅ `detect_bold_in_span()` retorna bool o None sin errores

---

#### Task 1.3: Crear sistema de reportes de cambios

**Archivo**: `core/change_report.py` (NUEVO, 100-150 líneas)

**Qué hacer**:

```python
@dataclass
class TextChangeReport:
    """Reporte de qué cambió en una edición."""
    old_text: str
    new_text: str
    font_used: str                      # "Arial" o fallback
    was_fallback: bool                  # True si se usó fallback
    fallback_from: Optional[str]        # "MyriadPro" → "helv"
    bold_strategy: Optional[str]        # "exact_bold" / "approximate" / None
    tracking_adjusted: float            # % (0 si no, -15 si 15% menos)
    size_adjusted: float                # % (0 si no, -20 si 20% más pequeño)
    warnings: List[str]                 # [advertencias]

    def as_dict(self) -> dict:
        """Serializar para UI."""
```

**Usado por**: `pdf_viewer.py` para mostrar diálogo "Resumen de cambios antes de guardar"

**Criterio de aceptación**:

- ✅ Estructura captures todos los cambios
- ✅ `as_dict()` serializa sin errores
- ✅ Fácil de mostrar en UI

---

### Estimación Backend

- **Task 1.1**: 8 horas (incluye tests)
- **Task 1.2**: 4 horas (integración con FontManager)
- **Task 1.3**: 2 horas (estructura de datos)
- **Total**: 14 horas (2 días × 7h)

---

## 🎨 INGENIERO FRONTEND / UI

### Responsabilidad Principal (Frontend)

Crear diálogos mejorados, validar en tiempo real, mostrar previsualizaciones. **Depende de** Backend Task 1.1-1.3.

### Tareas Específicas (Frontend)

#### Task 2.1: Crear `EnhancedTextEditDialog`

**Archivo**: `ui/text_editor_dialog.py` (NUEVO O EXTENDER, 300-400 líneas)

**Componentes del diálogo**:

```python
class EnhancedTextEditDialog(QDialog):

    # Área 1: Editor de texto con preview en vivo
    text_input = QTextEdit()                 # Para editar
    preview_label = QLabel()                 # Muestra cómo se vería
    preview_font = QFont()                   # Simulación exacta

    # Área 2: Estilos (checkboxes)
    keep_bold_checkbox = QCheckBox("¿Mantener negrita?")
    apply_bold_checkbox = QCheckBox("¿Aplicar negrita?")
    apply_italic_checkbox = QCheckBox("¿Aplicar cursiva?")

    # Área 3: Validación (mensajes)
    status_label = QLabel()                  # "✅ Cabe en área" o "❌ Texto muy largo"
    option_buttons = [...]                  # [A] Recortar, [B] Espaciado, [C] Tamaño

    def validate_text_fits(self) -> bool:
        """Chequea si texto cabe. Actualiza preview en vivo."""
        # Usar FontManager.get_bounding_rect()
        # Si no cabe: mostrar opciones [A][B][C]

    def on_text_changed(self):
        """Valida mientras escribe. Preview en vivo."""

    def apply_spacing_reduction(self, percent: int) -> bool:
        """Reduce espaciado entre letras (tracking)."""

    def apply_size_reduction(self, percent: int) -> bool:
        """Reduce tamaño de fuente. Mínimo 70% original."""

    def get_styling_choices(self) -> Dict:
        """Retorna: {"keep_bold": bool, "apply_bold": bool, ...}"""

    def get_final_text(self) -> Tuple[str, TextChangeReport]:
        """Retorna: (texto_final, reporte_de_cambios)"""
```

**Comportamiento esperado**:

- Cuando usuario escribe, preview se actualiza en tiempo real
- Si no cabe, mostrar dialog tipo:
  ```
  ⚠️ Texto muy largo (no cabe en área original)
  
  Opciones:
  [A] Recortar con "..." (perder contenido)
  [B] Reducir espaciado (tracking: -10%) ← Recomendado
  [C] Reducir tamaño (de 12pt a 10pt)
  [Cancelar]
  ```
- Checkboxes para estilos con ayuda contextual

**Tests**:

- Test que dialog valida correctamente
- Test que preview se actualiza
- Test opciones spacing/size

**Criterio de aceptación**:

- ✅ Dialog muestra preview en vivo
- ✅ Valida "cabe/no cabe"
- ✅ Ofrece opciones [A][B][C] si no cabe
- ✅ Retorna `TextChangeReport` completo

---

#### Task 2.2: Agregar soporte copy/paste con estilos

**Archivo**: `ui/pdf_viewer.py` (método nuevo)

**Qué hacer**:

```python
def handle_paste_with_styles(self) -> bool:
    """
    Al hacer Ctrl+V, analiza si clipboard tiene HTML/RTF.
    Extrae: texto + información de bold/italic/color.
    Mapea a: FontDescriptor + styling_choices.
    """
    # Pseudocódigo:
    # 1. Leer clipboard (texto, HTML, RTF)
    # 2. Parsear bold/italic tags: <b>, <strong>, RTF \b
    # 3. Extraer color si está disponible
    # 4. Crear FontDescriptor para contexto actual
    # 5. Llamar EnhancedTextEditDialog con estilos pre-llenados
    # 6. Usuario valida y acepta
```

**Integración**:

- Llamar desde `on_paste_triggered()` o similar
- Usa `EnhancedTextEditDialog` de Task 2.1
- Loguea qué estilos se detectaron

**Tests**:

- Mock clipboard con texto simple, HTML con `<b>`, RTF con `\b`
- Verifica que extrae estilos correctamente

**Criterio de aceptación**:

- ✅ Detecta bold en HTML pasted
- ✅ Mapea a `should_bold: bool`
- ✅ Dialog muestra intención de estilos

**Criterio de aceptación**:

- ✅ Dialog muestra preview en vivo
- ✅ Valida "cabe/no cabe"
- ✅ Ofrece opciones [A][B][C] si no cabe
- ✅ Retorna `TextChangeReport` completo

---

#### Task 2.2: Agregar soporte copy/paste con estilos

**Archivo**: `ui/pdf_viewer.py` (método nuevo)

**Qué hacer**:

```python
def handle_paste_with_styles(self) -> bool:
    """
    Al hacer Ctrl+V, analiza si clipboard tiene HTML/RTF.
    Extrae: texto + información de bold/italic/color.
    Mapea a: FontDescriptor + styling_choices.
    """
    # Pseudocódigo:
    # 1. Leer clipboard (texto, HTML, RTF)
    # 2. Parsear bold/italic tags: <b>, <strong>, RTF \b
    # 3. Extraer color si está disponible
    # 4. Crear FontDescriptor para contexto actual
    # 5. Llamar EnhancedTextEditDialog con estilos pre-llenados
    # 6. Usuario valida y acepta
```

**Integración**:

- Llamar desde `on_paste_triggered()` o similar
- Usa `EnhancedTextEditDialog` de Task 2.1
- Loguea qué estilos se detectaron

**Tests**:

- Mock clipboard con texto simple, HTML con `<b>`, RTF con `\b`
- Verifica que extrae estilos correctamente

**Criterio de aceptación**:

- ✅ Detecta bold en HTML pasted
- ✅ Mapea a `should_bold: bool`
- ✅ Dialog muestra intención de estilos

---

#### Task 2.3: Diálogo "Resumen de cambios antes de guardar"

**Archivo**: `ui/save_summary_dialog.py` (NUEVO, 200 líneas)

**Componentes**:

```python
class SaveSummaryDialog(QDialog):
    """Muestra TextChangeReport antes de confirmar guardado."""

    def __init__(self, change_reports: List[TextChangeReport]):
        # Tabla mostrando:
        # | Texto Original | Nuevo Texto | Fuente | Cambios |
        # | "viaje"        | "viaje inc" | Arial  | ⚠️ Recortado |

    def show_warnings_if_any(self):
        """Si hay warnings (fuentes fallback, ajustes), mostrar en rojo."""
        # Ej: "⚠️ Fuente 'MyriadPro' no disponible, se usó Helvetica"

    def user_confirms_save(self) -> bool:
        """¿Usuario quiere guardar a pesar de los cambios?"""
```

**Llamado desde**:

- `main_window.save_pdf()` cuando hay ediciones pendientes
- Antes de llamar a `PDFDocument.save()`

**Tests**:

- Dialog muestra tabla de cambios
- Warnings destacados en rojo
- Botones [Guardar] [Cancelar]

**Criterio de aceptación**:

- ✅ Muestra tabla de cambios legible
- ✅ Destaca warnings
- ✅ Retorna confirmación usuario

---

### Estimación Frontend

- **Task 2.1**: 12 horas (dialog complejo con preview)
- **Task 2.2**: 4 horas (copy/paste con parsing)
- **Task 2.3**: 4 horas (diálogo de resumen)
- **Total**: 20 horas (2.5 días × 8h)

---

## 🧪 INGENIERO QA / TESTING

### Responsabilidad Principal (QA)

Diseñar tests exhaustivos, crear PDFs de test, validar casos edge.

### Tareas Específicas (QA)

#### Task 3.1: Suite de tests para FontManager

**Archivo**: `tests/test_font_manager.py` (300+ líneas)

**Test cases**:

```python
def test_detect_font_helvetica():
    """Detecta Arial correctamente."""
    span = {"font": "Arial", "size": 12}
    descriptor = font_manager.detect_font(span)
    assert descriptor.name == "Arial"
    assert descriptor.size == 12

def test_fallback_custom_font():
    """MyriadPro → Helvetica (fallback)."""
    span = {"font": "MyriadPro", "size": 12}
    descriptor = font_manager.detect_font(span)
    assert descriptor.fallback_used == True
    assert descriptor.actual_font == "helv"

def test_detect_bold_heuristic():
    """Detecta bold por heurística (ancho)."""
    span = {"font": "ArialBold", "size": 12}
    result = font_manager.detect_possible_bold(span)
    assert result in [True, False, None]

def test_bounding_rect_arial_12pt():
    """Calcula rect correctamente para Arial 12pt."""
    descriptor = FontDescriptor(name="Arial", size=12)
    rect = font_manager.get_bounding_rect("Hola", descriptor)
    assert rect[0] > 0  # ancho
    assert rect[1] > 0  # alto
```

**Cobertura mínima**: 80% (target 90%)

---

#### Task 3.2: PDFs de test con varias fuentes

**Archivo**: `tests/fixtures/test_pdfs/` (NUEVOS)

**Crear 3 PDFs de ejemplo**:

1. **simple_fonts.pdf**: Párrafos con Arial, Times, Courier
2. **custom_fonts.pdf**: Fuentes embebidas custom (MyriadPro, etc.)
3. **bold_italic.pdf**: Texto con negritas/cursivas (para verificar heurística)

**Usar para**: Tests de `PDFDocument.get_text_run_descriptors()` y `detect_bold_in_span()`

---

#### Task 3.3: Integration tests - flujo completo

**Archivo**: `tests/test_phase2_integration.py` (400+ líneas)

**Escenarios**:

```gherkin
Feature: Edición de texto con soporte bold
  Scenario: Usuario edita "viaje" → "viaje increíble" manteniendo Arial 12pt
    Given: PDF con párrafo "El viaje fue largo" en Arial 12pt
    When: Usuario selecciona "viaje" y lo reemplaza con "viaje increíble"
    Then:
      ✅ Texto actualizado
      ✅ Fuente Arial mantenida
      ✅ Tamaño 12pt mantenido
      ✅ Guardar y reabrir: persiste

  Scenario: Pegar HTML con bold desde navegador
    Given: User copia "<b>importante</b>" de navegador
    When: Ctrl+V en texto PDF
    Then:
      ✅ Dialog muestra "Aplicar negrita?"
      ✅ Usuario confirma
      ✅ Texto pegado con estrategia bold (exact o approximate)

  Scenario: Texto no cabe - usuario elige opción
    Given: Área original tiene espacio para 20 caracteres
    When: Usuario intenta pegar 40 caracteres
    Then:
      ✅ Dialog muestra [A] Recortar, [B] Espaciado, [C] Tamaño
      ✅ Usuario elige [B] Espaciado (-10%)
      ✅ Validación pasa
      ✅ ChangeReport muestra "tracking_adjusted: -10"
```

**Ejecución**: Usar pytest + fixtures de PDFs

---

#### Task 3.4: Tests de copy/paste

**Archivo**: `tests/test_clipboard.py` (150+ líneas)

**Test casos**:

```python
def test_paste_plain_text():
    """Pegar texto plano sin estilos."""
    # Mock clipboard con "Hola"
    # Verify: dialog abre sin estilos pre-llenados

def test_paste_html_with_bold():
    """Pegar HTML: '<b>importante</b>'."""
    # Mock clipboard con HTML
    # Verify: parser extrae bold tag
    # Verify: dialog muestra "apply_bold: True"

def test_paste_rtf_with_formatting():
    """Pegar RTF con \\b (bold) y colores."""
    # Mock clipboard RTF
    # Verify: estilos se extraen correctamente
```

---

### Estimación QA

- **Task 3.1**: 8 horas (unit tests FontManager)
- **Task 3.2**: 3 horas (crear PDFs de test)
- **Task 3.3**: 10 horas (integration tests complejos)
- **Task 3.4**: 4 horas (clipboard tests)
- **Total**: 25 horas (3+ días)

---

## 📅 TIMELINE INTEGRADO (2 sprints = 4 semanas)

### Sprint 1 (Semana 1-2)

**Semana 1: Backend (Tareas 1.1-1.3)**

- Lunes-Miércoles: Backend Task 1.1 (FontManager)
- Jueves-Viernes: Backend Task 1.2 + 1.3

**Semana 2: Inicio Frontend + QA paralelo**

- Lunes-Miércoles: Frontend Task 2.1 (Dialog)
- Martes-Viernes: QA Task 3.1-3.2 (tests unitarios + fixtures)
- **Bloqueo**: Frontend no avanza hasta Backend Task 1.1 esté listo

### Sprint 2 (Semana 3-4)

**Semana 3: Frontend + Integración**

- Lunes-Martes: Frontend Task 2.2 (copy/paste)
- Miércoles-Viernes: Frontend Task 2.3 + integración con Backend

**Semana 4: Testing final + Bug fixes**

- Lunes-Miércoles: QA Task 3.3-3.4 (integration tests)
- Jueves-Viernes: Bug fixes, documentación, release prep

---

## 🔄 Dependencias

```
Backend Task 1.1 (FontManager)
    ↓
Frontend Task 2.1 (Dialog)
    ↓
Frontend Task 2.2 (Copy/Paste)
    ↓
Frontend Task 2.3 (Summary Dialog)
    ↓
QA Task 3.3-3.4 (Integration Tests)
```

**Critical Path**: Backend 1.1 → Frontend 2.1-2.3 → QA 3.3 → Release

---

## 📊 Métricas de Éxito

| Métrica | Target |
| --------- | ---------- |
| Cobertura tests | 85%+ |
| PDFs test cases | 3+ |
| Integration tests | 10+ escenarios |
| Diálogos usables | Heurística bold working |
| Copy/paste | Detecta bold en HTML/RTF |
| ChangeReport | Captura todos los cambios |

---

## 🔗 Referencias

- **PROMPT_MEJORADO_v2.md** - Especificación técnica completa
- **ANALISIS_PROMPT_MEJORADO.md** - Contexto de limitaciones PyMuPDF
- **COMPARATIVA_PROMPTS.md** - Antes/después + estimaciones

---

### Estimación QA

- **Task 3.1**: 8 horas (unit tests FontManager)
- **Task 3.2**: 3 horas (crear PDFs de test)
- **Task 3.3**: 10 horas (integration tests complejos)
- **Task 3.4**: 4 horas (clipboard tests)
- **Total**: 25 horas (3+ días)

---

## 📅 TIMELINE INTEGRADO (2 sprints = 4 semanas)

### Sprint 1 (Semana 1-2)

**Semana 1: Backend (Tareas 1.1-1.3)**

- Lunes-Miércoles: Backend Task 1.1 (FontManager)
- Jueves-Viernes: Backend Task 1.2 + 1.3

**Semana 2: Inicio Frontend + QA paralelo**

- Lunes-Miércoles: Frontend Task 2.1 (Dialog)
- Martes-Viernes: QA Task 3.1-3.2 (tests unitarios + fixtures)
- **Bloqueo**: Frontend no avanza hasta Backend Task 1.1 esté listo

### Sprint 2 (Semana 3-4)

**Semana 3: Frontend + Integración**

- Lunes-Martes: Frontend Task 2.2 (copy/paste)
- Miércoles-Viernes: Frontend Task 2.3 + integración con Backend

**Semana 4: Testing final + Bug fixes**

- Lunes-Miércoles: QA Task 3.3-3.4 (integration tests)
- Jueves-Viernes: Bug fixes, documentación, release prep

---

## 🔄 Dependencias

```
Backend Task 1.1 (FontManager)
    ↓
Frontend Task 2.1 (Dialog)
    ↓
Frontend Task 2.2 (Copy/Paste)
    ↓
Frontend Task 2.3 (Summary Dialog)
    ↓
QA Task 3.3-3.4 (Integration Tests)
```

**Critical Path**: Backend 1.1 → Frontend 2.1-2.3 → QA 3.3 → Release

---

## 📊 Métricas de Éxito

| Métrica | Target |
| --------- | ---------- |
| Cobertura tests | 85%+ |
| PDFs test cases | 3+ |
| Integration tests | 10+ escenarios |
| Diálogos usables | Heurística bold working |
| Copy/paste | Detecta bold en HTML/RTF |
| ChangeReport | Captura todos los cambios |

---

## 🔗 Referencias
## 🔗 Referencias

- **PROMPT_MEJORADO_v2.md** - Especificación técnica completa
- **ANALISIS_PROMPT_MEJORADO.md** - Contexto de limitaciones PyMuPDF
- **COMPARATIVA_PROMPTS.md** - Antes/después + estimaciones
