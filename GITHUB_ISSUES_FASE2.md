# Tareas GitHub - Fase 2: Bold, Copy/Paste, Validación

**Milestone**: PDF Editor Pro v1.3.0  
**Período**: 4 semanas (2 sprints)  
**Estado**: Ready for Development

---

## 🔧 BACKEND - FontManager (Critical Path)

### [TASK] Implementar FontManager - core/font_manager.py

Blank line added for MD022 spacing

**ID**: PHASE2-101  
**Asignado a**: Backend Engineer  
**Prioridad**: CRÍTICA  
**Duración estimada**: 8 horas  
**Sprint**: 1  

**Descripción**:
Módulo centralizado para gestión de fuentes con fallbacks inteligentes y detección de negritas.

**Requerimientos**:

- [ ] Crear clase `FontManager` en `core/font_manager.py`
- [ ] Método `detect_font(span)` → extrae nombre, tamaño, color
- [ ] Tabla de mappeos `FONT_MAPPING` (Arial→helv, Times→times, etc.)
- [ ] Método `smart_fallback(font_name)` con heurísticas
- [ ] Método `get_bounding_rect(text, descriptor)` usando QFontMetrics
- [ ] Método `handle_bold(text, descriptor, should_bold)` con estrategias fallback
- [ ] Método `detect_possible_bold(span)` heurística (True/False/None)
- [ ] Crear `FontDescriptor` (NamedTuple o dataclass)
- [ ] Tests unitarios: `tests/test_font_manager.py` (80%+ cobertura)

**Aceptación**:

- ✅ Detecta fuentes estándar sin errores
- ✅ Fallback a Helvetica para custom fonts
- ✅ Heurística bold retorna True/False/None (nunca falla)
- ✅ QFontMetrics calcula bounding rect correctamente
- ✅ Tests pasan en Windows/Linux/macOS

**Referencia**: PROMPT_MEJORADO_v2.md líneas 200-240

**Bloquea**: PHASE2-102, PHASE2-201, PHASE2-202

---

### [TASK] Extender PDFDocument con 3 métodos

**ID**: PHASE2-102  
**Asignado a**: Backend Engineer  
**Prioridad**: CRÍTICA  
**Duración estimada**: 4 horas  
**Sprint**: 1  
**Dependencia**: PHASE2-101

**Descripción**:
Agregar métodos a `core/pdf_handler.py` para trabajar con fuentes y validar reemplazos.

**Requerimientos**:

- [ ] Método `get_text_run_descriptors(page_num, area_rect)` → List[FontDescriptor]
- [ ] Método `replace_text_preserving_metrics(page_num, old_text, new_text, descriptor)` → (bool, warnings)
- [ ] Método `detect_bold_in_span(span)` → Optional[bool]
- [ ] Integrar con `FontManager` (usar sus métodos)
- [ ] Loguear fallbacks y ajustes realizados
- [ ] Tests: `tests/test_pdf_handler.py` (agregar a existentes)

**Aceptacion**:

- ✅ `get_text_run_descriptors()` retorna descriptores de todos los spans en área
- ✅ `replace_text_preserving_metrics()` valida que cabe el texto
- ✅ `detect_bold_in_span()` retorna bool o None sin excepciones
- ✅ Loguea cada fallback de fuente

**Referencia**: PROMPT_MEJORADO_v2.md líneas 245-280

**Bloquea**: PHASE2-201

---

### [TASK] Sistema de reportes de cambios

**ID**: PHASE2-103  
**Asignado a**: Backend Engineer  
**Prioridad**: IMPORTANTE  
**Duración estimada**: 2 horas  
**Sprint**: 1  
**Dependencia**: PHASE2-102

**Descripción**:
Crear estructura `TextChangeReport` para documentar todos los cambios realizados en una edición.

**Requerimientos**:

- [ ] Crear `core/change_report.py`
- [ ] Dataclass `TextChangeReport` con campos:
  - `old_text`, `new_text`
  - `font_used`, `was_fallback`, `fallback_from`
  - `bold_strategy` (exact/approximate/none)
  - `tracking_adjusted` (% reducción)
  - `size_adjusted` (% reducción)
  - `warnings` (lista de strings)
- [ ] Método `as_dict()` para serializar a JSON/UI
- [ ] Tests: serialización, campos requeridos

**Aceptación**:

- ✅ Captura todos los cambios
- ✅ `as_dict()` serializa sin errores
- ✅ Fácil de mostrar en UI (tabla)

**Bloquea**: PHASE2-203

---

## 🎨 FRONTEND - Diálogos (Depende de Backend)

### [TASK] EnhancedTextEditDialog con preview en vivo

**ID**: PHASE2-201  
**Asignado a**: Frontend Engineer  
**Prioridad**: CRÍTICA  
**Duración estimada**: 12 horas  
**Sprint**: 2 (después de PHASE2-101)  
**Dependencia**: PHASE2-101

**Descripción**:
Diálogo mejorado para edición de texto con validación en tiempo real y opciones para texto que no cabe.

**Requerimientos**:

- [ ] Crear `ui/text_editor_dialog.py`
- [ ] Componentes:
  - QTextEdit para input
  - QLabel para preview en vivo (fuente exacta)
  - QCheckBox "¿Mantener negrita?"
  - QCheckBox "¿Aplicar negrita?"
  - Status label validaciones
  - Botones [A] Recortar, [B] Espaciado, [C] Tamaño (si no cabe)
- [ ] Método `validate_text_fits()` → bool
- [ ] Método `on_text_changed()` → actualiza preview en vivo
- [ ] Método `apply_spacing_reduction(percent)` → reduce tracking
- [ ] Método `apply_size_reduction(percent)` → reduce tamaño (mín 70%)
- [ ] Método `get_styling_choices()` → dict de estilos
- [ ] Método `get_final_text()` → (str, TextChangeReport)
- [ ] Tests: `tests/test_text_editor_dialog.py`

**Aceptación**:

- ✅ Preview muestra cómo se vería el texto
- ✅ Valida "cabe/no cabe" sin lag
- ✅ Ofrece opciones [A][B][C] si no cabe
- ✅ Checkboxes bold funcionan
- ✅ Retorna TextChangeReport con todos los cambios

**Referencia**: DISTRIBUCIÓN_ROLES_FASE2.md sección "Task 2.1"

---

### [TASK] Soporte copy/paste con estilos

**ID**: PHASE2-202  
**Asignado a**: Frontend Engineer  
**Prioridad**: IMPORTANTE  
**Duración estimada**: 4 horas  
**Sprint**: 2  
**Dependencia**: PHASE2-201

**Descripción**:
Al hacer Ctrl+V, detectar si clipboard contiene HTML/RTF con bold/italic y mapear a estilos.


**Requerimientos**:
- [ ] Método `handle_paste_with_styles()` en `ui/pdf_viewer.py`
- [ ] Parsear HTML (`<b>`, `<strong>`, `<em>`, `<i>` tags)
- [ ] Parsear RTF (`\b` para bold)
- [ ] Extraer color si disponible
- [ ] Crear FontDescriptor para contexto actual
- [ ] Llamar a `EnhancedTextEditDialog` con estilos pre-llenados
- [ ] Loguea estilos detectados
- [ ] Tests: `tests/test_clipboard.py`

**Aceptación**:

- ✅ Detecta bold en HTML pasted
- ✅ Detecta bold en RTF pasted
- ✅ Dialog abre con "apply_bold: True" si se detectó bold
- ✅ Usuario puede confirmar/descartar estilos

**Referencia**: DISTRIBUCIÓN_ROLES_FASE2.md sección "Task 2.2"

---

### [TASK] Diálogo "Resumen de cambios antes de guardar"

**ID**: PHASE2-203  
**Asignado a**: Frontend Engineer  
**Prioridad**: IMPORTANTE  
**Duración estimada**: 4 horas  
**Sprint**: 2  
**Dependencia**: PHASE2-103

**Descripción**:
Muestra tabla de cambios (TextChangeReport) antes de guardar PDF.

**Requerimientos**:

- [ ] Crear `ui/save_summary_dialog.py`
- [ ] Tabla con columnas: Original | Nuevo | Fuente | Cambios
- [ ] Mostrar warnings en rojo (fuentes fallback, ajustes)
- [ ] Botones [Guardar] [Cancelar]
- [ ] Método `show_warnings_if_any()`
- [ ] Método `user_confirms_save()` → bool
- [ ] Tests: mostrar tabla, warnings destacados

**Aceptación**:
- ✅ Tabla legible
- ✅ Warnings en rojo (ej: "Fuente no disponible")
- ✅ Usuario puede confirmar/cancelar

**Referencia**: DISTRIBUCIÓN_ROLES_FASE2.md sección "Task 2.3"

---

## 🧪 QA - Tests y Fixtures

### [TASK] Suite de tests FontManager

**ID**: PHASE2-301  
**Asignado a**: QA Engineer  
**Prioridad**: IMPORTANTE  
**Duración estimada**: 8 horas  
**Sprint**: 1-2 (paralelo)  
**Dependencia**: PHASE2-101

**Descripción**:
Tests unitarios exhaustivos para FontManager (80%+ cobertura).

**Requerimientos**:

- [ ] Crear `tests/test_font_manager.py`
- [ ] Test `detect_font_*` para Arial, Times, Courier, custom fonts
- [ ] Test `smart_fallback()` para fuentes conocidas y desconocidas
- [ ] Test `detect_possible_bold()` retorna True/False/None
- [ ] Test `get_bounding_rect()` para varios tamaños y textos
- [ ] Test `handle_bold()` estrategias exact/approximate/fallback
- [ ] Cobertura: 80%+ (target 90%)

**Aceptación**:
- ✅ 80%+ cobertura de `font_manager.py`
- ✅ Todos los tests pasan
- ✅ Casos edge: fuentes vacías, tamaños 0, None values

**Referencia**: DISTRIBUCIÓN_ROLES_FASE2.md sección "Task 3.1"

---

### [TASK] Crear PDFs de test con varias fuentes

**ID**: PHASE2-302  
**Asignado a**: QA Engineer  
**Prioridad**: IMPORTANTE  
**Duración estimada**: 3 horas  
**Sprint**: 1  

**Descripción**:
PDFs de ejemplo para testing de detección de fuentes y bold.

**Requerimientos**:

- [ ] Crear `tests/fixtures/test_pdfs/simple_fonts.pdf`
  - Párrafos con Arial 12pt, Times 12pt, Courier 12pt
- [ ] Crear `tests/fixtures/test_pdfs/custom_fonts.pdf`
  - Con fuentes embebidas custom (MyriadPro, etc.)
- [ ] Crear `tests/fixtures/test_pdfs/bold_italic.pdf`
  - Texto con negritas y cursivas (para heurística)

**Aceptación**:

- ✅ 3 PDFs creados y válidos
- ✅ Legibles en Adobe Reader
- ✅ Contienen texto extraíble (no imágenes)

---

### [TASK] Integration tests - flujo completo

**ID**: PHASE2-303  
**Asignado a**: QA Engineer  
**Prioridad**: CRÍTICA  
**Duración estimada**: 10 horas  
**Sprint**: 2  
**Dependencia**: PHASE2-201, PHASE2-202, PHASE2-203

**Descripción**:
Tests de flujo completo (Gherkin) que cubren escenarios reales de usuario.

**Requerimientos**:
- [ ] Crear `tests/test_phase2_integration.py`
- [ ] Escenarios Gherkin:
  - Editar "viaje" → "viaje increíble" (Arial 12pt)
  - Pegar bold desde navegador (detecta, dialog, confirma)
  - Texto no cabe (elige opción spacing)
  - Guardar y reabrir PDF (persiste cambios)
  - Deshacer cambios (Ctrl+Z)
- [ ] Tests para copy/paste HTML y RTF
- [ ] Validación de ChangeReport en cada caso
- [ ] Mínimo 10 escenarios

**Aceptación**:

- ✅ 10+ escenarios cubiertos
- ✅ Todos pasan
- ✅ Cobertura integration: >70%

**Referencia**: DISTRIBUCIÓN_ROLES_FASE2.md sección "Task 3.3"

---

### [TASK] Tests de clipboard

**ID**: PHASE2-304  
**Asignado a**: QA Engineer  
**Prioridad**: IMPORTANTE  
**Duración estimada**: 4 horas  
**Sprint**: 2  
**Dependencia**: PHASE2-202

**Descripción**:
Tests específicos para copy/paste con HTML y RTF.

**Requerimientos**:

- [ ] Crear `tests/test_clipboard.py`
- [ ] Mock clipboard con texto plano
- [ ] Mock clipboard con HTML: `<b>importante</b>`
- [ ] Mock clipboard con HTML: `<i>cursiva</i>`
- [ ] Mock clipboard con RTF: `\b` (bold)
- [ ] Verificar que extrae estilos correctamente
- [ ] Verificar que dialog abre con estilos pre-llenados


**Aceptación**:

- ✅ Detecta bold en HTML
- ✅ Detecta italic en HTML
- ✅ Detecta bold en RTF
- ✅ Dialog muestra estilos correctamente

---

## 📋 RESUMEN DE TAREAS

| ID | Descripción | Rol | Horas | Sprint | Estado |
| --- | --------- | --- | ----- | ------ | ------ |
| PHASE2-101 | FontManager (core) | Backend | 8 | 1 | Ready |
| PHASE2-102 | Extender PDFDocument | Backend | 4 | 1 | Ready |
| PHASE2-103 | ChangeReport | Backend | 2 | 1 | Ready |
| PHASE2-201 | Enhanced Dialog | Frontend | 12 | 2 | Blocked |
| PHASE2-202 | Copy/Paste | Frontend | 4 | 2 | Blocked |
| PHASE2-203 | Summary Dialog | Frontend | 4 | 2 | Blocked |
| PHASE2-301 | FontManager Tests | QA | 8 | 1-2 | Ready |
| PHASE2-302 | Test PDFs | QA | 3 | 1 | Ready |
| PHASE2-303 | Integration Tests | QA | 10 | 2 | Blocked |
| PHASE2-304 | Clipboard Tests | QA | 4 | 2 | Blocked |
| **TOTAL** | | | **59 horas** | | |

**Total Esfuerzo**: 59 horas = ~7.5 días de ingeniero

---

## 🔗 Links Útiles

- **Especificación**: PROMPT_MEJORADO_v2.md
- **Análisis**: ANALISIS_PROMPT_MEJORADO.md
- **Distribución de Roles**: DISTRIBUCION_ROLES_FASE2.md
- **Rama**: `develop` → PR a `main` (después de tests)
