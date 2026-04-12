# Análisis del Proyecto y Mejora del Prompt

## 📊 ANÁLISIS DE ESTRUCTURA ACTUAL

### Tecnologías Confirmadas

- **Motor PDF**: PyMuPDF (fitz) v1.23.0+

- **UI Framework**: PyQt5 v5.15.0+

- **Lenguaje**: Python 3.8+

- **Build**: PyInstaller 6.0+

- **VCS**: Git con GitHub

### Arquitectura Actual (5 módulos principales)

#### 1. **core/pdf_handler.py** (1506 líneas)

**Responsabilidad**: Manipulación de PDF a bajo nivel

**Capacidades confirmadas**:

- ✅ Lectura de fuentes embebidas: `span.get("font", "")`

- ✅ Extracción de tamaño: `span.get("size", 12)`

- ✅ Obtención de texto editables: `page.get_text("dict")`

- ✅ Borrado transparente: `erase_text_transparent()` usando rendering de fitz

- ✅ Sistema de snapshots para undo/redo (20 niveles máximo)

- ✅ Mapeo de fuentes standard: Helvetica, Times, Courier, etc.

**Limitaciones técnicas confirmadas**:

- 🔴 PyMuPDF **NO puede detectar la variante bold** exacta de fuentes embebidas

- 🔴 PyMuPDF **NO expone el weight/thickness** de fuentes en el documento

- 🔴 Usa fallback a fuentes estándar PDF (helv=Helvetica, times, etc.)

- 🔴 **Desconocimiento automático de negritas**: No hay API oficial de fitz para leer "es esta fuente bold?"

#### 2. **ui/pdf_viewer.py** (2339 líneas)

**Responsabilidad**: Edición visual y overlays

**Capacidades confirmadas**:

- ✅ Sistema de `EditableTextItem`: QGraphicsItem para texto editable

- ✅ `sync_all_text_items_to_data()`: Sincronización antes de guardar

- ✅ `commit_overlay_texts()`: Integración de cambios al PDF

- ✅ `_calculate_text_rect_for_view()`: Cálculo exacto de bounding boxes con QFontMetrics

- ✅ Manejo de PDFs nativos vs. escaneados (overlay system)

- ✅ Deshacer/rehacer integrado con snapshots

**Limitaciones confirmadas**:

- 🔴 **No detecta negritas existentes**: Solo lee "texto", no "peso"

- 🔴 Overlays asumen texto sin estilos complejos

- 🟡 Fuentes: USA QFont estándar, puede no coincidir exactamente con originales

#### 3. **ui/main_window.py** (1883 líneas)

**Responsabilidad**: Orquestación y lógica de negocio

**Funciones relevantes para el prompt**:

- `save_file()` → llama `sync_all_text_items_to_data()` ANTES de guardar

- `save_file_as()` → mismo patrón

- `undo()` / `redo()` → restauran snapshots

#### 4. **ui/coordinate_utils.py** (110 líneas)

**Responsabilidad**: Transformación de coordenadas

**Utilidad**:

- Convierte view coordinates ↔ PDF coordinates

- Maneja zoom y rotación

- Crítico para posicionamiento exacto de texto editado

#### 5. **core/models.py**

**Responsabilidad**: Estructuras de datos

**Tipos clave**:

- `TextBlock(text, rect, font_name, font_size, color)`

- `EditOperation(type, block_before, block_after)`

---

## 🚨 LIMITACIONES CRÍTICAS ENCONTRADAS

### 1. **Negritas (Bold) - PROBLEMA PRINCIPAL**

```text
Estado actual: ❌ NO SE DETECTAN
Razón: PyMuPDF NO expone el "weight" de fuentes en la API pública
Workaround en uso: Asumir todo es normal, sin bold
Impacto: Perder negritas originales al editar

```text

### 2. **Fuentes Embebidas**

```text
Detección: ✅ Se LEE el nombre (via span["font"])
Uso: 🔴 NO se pueden reutilizar directamente
Razón: PyMuPDF solo puede escribir con 14 fuentes estándar PDF
Solución actual: Mapeo a fuentes estándar (Helvetica → helv)
Impacto: Posible cambio de apariencia en PDFs con fuentes custom

```text

### 3. **Kerning y Spacing**

```text
Detección: ❌ NO se detecta tracking/kerning
Razón: PyMuPDF NO expone métricas avanzadas
Impacto: Texto pegado/pegoteado sin espaviador correcto

```text

### 4. **Copy/Paste Multiplataforma**

```text
Estado: 🟡 Funciona básico (texto plano)
Negritas: ❌ NO se preservan en copy/paste
Razón: No hay mapeo de estilos RTF→PDF

```text

---

## ✅ CAPACIDADES REALES CONFIRMADAS

| Feature | Estado | Confiabilidad | Notas |
| --------- | -------- | --------------- | ------- |
| Leer fuente (nombre) | ✅ | 95% | Via `span["font"]` |
| Leer tamaño | ✅ | 95% | Via `span["size"]` |
| Leer posición (x,y) | ✅ | 95% | Via `span["origin"]` |
| Escribir texto mismo tamaño | ✅ | 90% | Puede variar con QFont rendering |
| Borrar texto (no visual) | ✅ | 95% | Usando `erase_text_transparent()` |
| Undo/Redo | ✅ | 98% | Sistema de snapshots robusto |
| PDFs nativos (con texto) | ✅ | 95% | Soporte completo |
| PDFs escaneados (overlay) | ✅ | 90% | Funciona bien |
| Guardar cambios persistentes | ✅ | 98% | Verificado en pruebas reales |
| Detectar negritas | ❌ | 0% | Limitación de PyMuPDF |
| Aplicar negritas | 🟡 | 40% | Workaround con aproximaciones |
| Kerning exacto | ❌ | 0% | No disponible en API |

---

## 🎯 RECOMENDACIONES PARA MEJORAR EL PROMPT

El prompt original es **bueno pero aspiracional**. Necesita:

1. **Ser honesto sobre límites técnicos**
   - No prometer detección automática de negritas (NO ES POSIBLE)
   - Aclarar que el mapeo de fuentes tendrá fallbacks

2. **Especificar trade-offs**
   - Si debe respetar 100% la tipografía → será sobre PDFs nativos solamente
   - Si debe soportar cualquier PDF → aceptar que habr pérdida de estilos complejos

3. **Dividir en MVP vs. Futuro**
   - MVP (v1.2.0 actual): Editar texto, mantener tamaño y posición
   - Futuro: Negritas, kerning avanzado (requeriría bibliotecas adicionales)

4. **Agregar sección de "Decisiones de Diseño"**
   - Por qué bold es aproximado vs. exacto
   - Por qué copy/paste no preserva todo

5. **Incluir Criterios de Aceptación más realistas**

---

## 📝 PROMPT MEJORADO (VER ABAJO)

