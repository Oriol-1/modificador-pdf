# Plan: Sistema de Unión de PDFs y Reordenamiento de Páginas

## Índice

1. [Análisis del Estado Actual](#1-análisis-del-estado-actual)
2. [Problemas Identificados y Riesgos](#2-problemas-identificados-y-riesgos)
3. [Decisión Arquitectónica Central: UUID de Página](#3-decisión-arquitectónica-central-uuid-de-página)
4. [Fases de Implementación](#4-fases-de-implementación)
5. [Fase 1: Sistema de Identidad de Página](#fase-1-sistema-de-identidad-de-página-pageidentity)
6. [Fase 2: Operaciones de Página en el Core](#fase-2-operaciones-de-página-en-el-core)
7. [Fase 3: Remapeo Automático de Datos](#fase-3-remapeo-automático-de-datos)
8. [Fase 4: UI de Reordenamiento](#fase-4-ui-de-reordenamiento-drag--drop-en-thumbnails)
9. [Fase 5: UI de Unión/Inserción de PDF](#fase-5-ui-de-unióninserción-de-pdf)
10. [Fase 6: Undo/Redo para Operaciones de Página](#fase-6-undoredo-para-operaciones-de-página)
11. [Fase 7: Tests](#fase-7-tests)
12. [Matriz de Casos Edge](#8-matriz-de-casos-edge)
13. [Orden de Ejecución y Dependencias](#9-orden-de-ejecución-y-dependencias)

---

## 1. Análisis del Estado Actual

### Estructuras de datos que referencian páginas por índice numérico

El sistema actual almacena **toda** la información de edición usando el índice numérico de página (0-based) como clave. Esto significa que si una página que era la nº 3 pasa a ser la nº 5, todos los datos asociados quedan **huérfanos o apuntando a la página equivocada**.

Las estructuras afectadas son:

| Estructura | Ubicación | Tipo de clave | Qué almacena |
| --- | --- | --- | --- |
| `editable_texts_data` | `ui/pdf_viewer.py` | `dict[int, list[dict]]` | Textos editados/añadidos por página |
| `EditableTextItem.page_num` | `ui/graphics_items.py` | `int` | A qué página pertenece cada item gráfico |
| `EditableTextItem.data_index` | `ui/graphics_items.py` | `int` | Índice dentro de la lista de su página |
| `_highlights` | `core/pdf_handler.py` | `dict[int, list[dict]]` | Highlights por página |
| `_undo_snapshots` | `core/pdf_handler.py` | `list[tuple(bytes, dict)]` | Snapshots con overlay_state que contiene `editable_texts_data` |
| `_redo_snapshots` | `core/pdf_handler.py` | `list[tuple(bytes, dict)]` | Idem |
| `EditOperation.page_num` | `core/models.py` | `int` | Página donde se hizo la operación |
| `EditableSpan.page_num` | `core/text_engine/page_document_model.py` | `int` | Span asociado a página |
| `TextBlock.page_num` | `core/models.py` | `int` | Bloque de texto extraído de una página |
| `ChangePosition.page` | `core/change_report.py` | `int` | Posición del cambio en el reporte |

### Lo que NO existe todavía

- Ningún método para insertar, eliminar, mover o reordenar páginas en `PDFDocument`
- Ningún mecanismo de remapeo de datos al cambiar el orden de páginas
- Ningún concepto de "identidad de página" independiente de su posición

---

## 2. Problemas Identificados y Riesgos

### Riesgo Principal: Corrupción de datos al reindexar

**Escenario concreto:**

1. El usuario edita texto en la página 3 → `editable_texts_data[3] = [{text: "Hola", ...}]`
2. El usuario inserta un PDF de 2 páginas al inicio
3. La página que era la 3 ahora es la 5 en el documento
4. Pero `editable_texts_data[3]` sigue apuntando al índice 3
5. **Resultado**: el texto "Hola" aparece en una página equivocada o se pierde

### Riesgo Secundario: Highlights incrustados en el PDF

Los highlights se escriben directamente como anotaciones en el PDF (no en memoria). Cuando PyMuPDF reordena páginas internamente, las anotaciones **sí se mueven con su página** porque son parte del objeto página. Sin embargo, el dict `_highlights` en memoria queda desincronizado.

### Riesgo Terciario: Snapshots de Undo contaminados

Cada snapshot contiene `(pdf_bytes, overlay_state)`. Si se reordenan páginas y luego se hace undo, el `overlay_state` restaurado tendría las claves de página antiguas pero el `pdf_bytes` del estado anterior (con el orden anterior). Esto **sí es consistente** dentro del snapshot, pero hay que garantizar que al restaurar un snapshot anterior al reordenamiento, se restaure todo el estado coherentemente.

### Riesgo Cuarto: Textos pendientes de escribir (`pending_write`)

Si hay textos overlay que aún no se han persistido al PDF (`pending_write=True`) y se reordenan páginas, estos textos existen SOLO en `editable_texts_data`. Al reordenar las páginas en el PDF con PyMuPDF, las páginas se mueven pero los overlays no, porque no están en el PDF aún.

---

## 3. Decisión Arquitectónica Central: UUID de Página

### El problema fundamental

El índice numérico es **posicional**, no **identitario**. Cambiar el orden rompe todas las referencias.

### La solución: `PageIdentityMap`

Introducir una capa de abstracción que asigne un **UUID inmutable** a cada página del documento. Todas las estructuras de datos usarán este UUID como clave interna, y solo se traduce a índice numérico para operaciones de renderizado y acceso a PyMuPDF.

```text
┌─────────────────────────────────────────────────────┐
│                  PageIdentityMap                     │
│                                                      │
│   UUID_A  ←→  página índice 0                        │
│   UUID_B  ←→  página índice 1                        │
│   UUID_C  ←→  página índice 2                        │
│                                                      │
│   Reordenar (mover página 0 al final):               │
│                                                      │
│   UUID_B  ←→  página índice 0                        │
│   UUID_C  ←→  página índice 1                        │
│   UUID_A  ←→  página índice 2                        │
│                                                      │
│   editable_texts_data[UUID_A] → sigue intacto        │
│   Solo cambia la traducción UUID → índice            │
└─────────────────────────────────────────────────────┘
```

### ¿Por qué NO migrar todo a UUID de golpe?

Migrar `editable_texts_data`, `EditableTextItem`, highlights, etc. a usar UUID directamente sería la solución ideal a largo plazo, pero implica un refactor masivo con alto riesgo de regresiones.

#### Estrategia elegida: Migración progresiva con capa de traducción

1. `PageIdentityMap` se crea y mantiene como fuente de verdad del mapeo
2. `editable_texts_data` se migra a UUID como clave (cambio contenido, no de API completa)
3. Cada acceso a `editable_texts_data` usa un helper que traduce `page_index → UUID` cuando es necesario
4. Los componentes existentes siguen usando índices numéricos para renderizado, pero la capa de datos usa UUID internamente

---

## 4. Fases de Implementación

```text
Fase 1 ─── PageIdentityMap + Migración de editable_texts_data a UUID
  │
  ▼
Fase 2 ─── Operaciones de página en PDFDocument (insert, delete, move, merge)
  │
  ▼
Fase 3 ─── Sistema de remapeo automático (actualizar mapas al operar)
  │
  ▼
Fase 4 ─── UI: Reordenamiento por drag & drop en thumbnails
  │
  ▼
Fase 5 ─── UI: Diálogo de inserción/unión de PDF
  │
  ▼
Fase 6 ─── Undo/Redo extendido para operaciones de página
  │
  ▼
Fase 7 ─── Tests completos (unitarios + integración)
```

---

## Fase 1: Sistema de Identidad de Página (`PageIdentity`)

### Archivos a crear/modificar

| Acción | Archivo | Descripción |
| --- | --- | --- |
| **Crear** | `core/page_identity.py` | Clase `PageIdentityMap` |
| Modificar | `core/pdf_handler.py` | Integrar `PageIdentityMap` en `PDFDocument` |
| Modificar | `ui/pdf_viewer.py` | Migrar `editable_texts_data` de `int` → `str (UUID)` |
| Modificar | `ui/graphics_items.py` | Añadir `page_uuid` a `EditableTextItem` |

### Diseño de `PageIdentityMap`

```python
# core/page_identity.py
import uuid
from typing import Dict, List, Optional

class PageIdentityMap:
    """
    Mantiene una correspondencia bidireccional entre UUIDs inmutables
    y los índices posicionales de página del PDF.
    
    Invariante: len(self._order) == doc.page_count en todo momento.
    """
    
    def __init__(self):
        self._order: List[str] = []  # [uuid_pag0, uuid_pag1, ...]
    
    # --- Inicialización ---
    
    def initialize(self, page_count: int):
        """Crea UUIDs para un documento recién abierto."""
        self._order = [str(uuid.uuid4()) for _ in range(page_count)]
    
    # --- Consultas ---
    
    def uuid_for_index(self, page_index: int) -> Optional[str]:
        """Devuelve el UUID de la página en la posición dada."""
        if 0 <= page_index < len(self._order):
            return self._order[page_index]
        return None
    
    def index_for_uuid(self, page_uuid: str) -> Optional[int]:
        """Devuelve el índice actual de la página con ese UUID."""
        try:
            return self._order.index(page_uuid)
        except ValueError:
            return None
    
    @property
    def page_count(self) -> int:
        return len(self._order)
    
    @property
    def order(self) -> List[str]:
        """Lista ordenada de UUIDs (posición = índice de página)."""
        return list(self._order)
    
    # --- Mutaciones (retornan el mapeo viejo→nuevo para remapeo) ---
    
    def insert_pages(self, at_index: int, count: int) -> Dict[str, int]:
        """
        Inserta 'count' páginas nuevas en la posición 'at_index'.
        Retorna dict {uuid: nuevo_indice} para TODAS las páginas afectadas.
        """
        new_uuids = [str(uuid.uuid4()) for _ in range(count)]
        for i, uid in enumerate(new_uuids):
            self._order.insert(at_index + i, uid)
        return self._build_full_index_map()
    
    def remove_page(self, page_index: int) -> str:
        """Elimina una página. Retorna el UUID eliminado."""
        return self._order.pop(page_index)
    
    def reorder(self, new_order: List[int]) -> Dict[str, int]:
        """
        Reordena páginas. new_order es lista de índices antiguos en nuevo orden.
        Ejemplo: [2, 0, 1] → la página que era 2 pasa a ser 0, etc.
        Retorna dict {uuid: nuevo_indice}.
        """
        self._order = [self._order[i] for i in new_order]
        return self._build_full_index_map()
    
    def move_page(self, from_index: int, to_index: int) -> Dict[str, int]:
        """
        Mueve una página de from_index a to_index.
        Retorna dict {uuid: nuevo_indice}.
        """
        uid = self._order.pop(from_index)
        self._order.insert(to_index, uid)
        return self._build_full_index_map()
    
    # --- Serialización (para snapshots) ---
    
    def to_list(self) -> List[str]:
        """Serializa para snapshot."""
        return list(self._order)
    
    def from_list(self, order: List[str]):
        """Restaura desde snapshot."""
        self._order = list(order)
    
    # --- Interno ---
    
    def _build_full_index_map(self) -> Dict[str, int]:
        """Construye mapeo completo {uuid: indice_actual}."""
        return {uid: idx for idx, uid in enumerate(self._order)}
```

### Migración de `editable_texts_data`

**Antes** (actual):

```python
editable_texts_data = {
    0: [text_data_1, text_data_2],  # página índice 0
    3: [text_data_3],                # página índice 3
}
```

**Después** (propuesto):

```python
editable_texts_data = {
    "a1b2c3d4-...": [text_data_1, text_data_2],  # UUID de la página
    "e5f6g7h8-...": [text_data_3],                 # UUID de la página
}
```

### Helpers de transición (en `PDFPageView`)

```python
def _page_uuid(self, page_index: int = None) -> str:
    """Obtiene el UUID de la página actual o la indicada."""
    idx = page_index if page_index is not None else self.current_page
    return self.pdf_doc.page_map.uuid_for_index(idx)

def _get_page_texts(self, page_index: int = None) -> list:
    """Obtiene los textos de una página por su índice."""
    uid = self._page_uuid(page_index)
    return self.editable_texts_data.get(uid, [])

def _set_page_texts(self, texts: list, page_index: int = None):
    """Establece los textos de una página por su índice."""
    uid = self._page_uuid(page_index)
    self.editable_texts_data[uid] = texts
```

### Puntos de acceso a migrar en `pdf_viewer.py`

Todos los patrones `self.editable_texts_data[self.current_page]` y `self.editable_texts_data[page_num]` deben usar los helpers. He identificado los siguientes puntos de acceso:

1. `_add_editable_text()` – añadir texto → usar `_page_uuid()`
2. `_remove_text_data_for_item()` – eliminar texto → usar `_page_uuid()`
3. `commit_overlay_texts()` – iterar por páginas → iterar por UUID, traducir a índice para PyMuPDF
4. `sync_all_text_items_to_data()` – sincronizar → sin cambios (no accede por clave)
5. `get_overlay_state()` – snapshot → ya devuelve dict (ahora con UUIDs como clave)
6. `restore_overlay_state()` – restaurar → ya acepta dict
7. `clear_editable_texts_data()` – limpiar → sin cambios
8. `display_page()` – al renderizar → usar `_get_page_texts()`

---

## Fase 2: Operaciones de Página en el Core

### Archivos a modificar

| Acción | Archivo | Descripción |
| --- | --- | --- |
| Modificar | `core/pdf_handler.py` | Añadir métodos de operación de página |

### Métodos a implementar en `PDFDocument`

```python
# --- En PDFDocument ---

def __init__(self):
    # ... existente ...
    self.page_map = PageIdentityMap()

def open(self, file_path: str) -> bool:
    # ... existente ...
    if success:
        self.page_map.initialize(self.doc.page_count)
    return success

# === NUEVAS OPERACIONES ===

def insert_pdf(self, source_path: str, at_page: int = -1) -> bool:
    """
    Inserta todas las páginas de un PDF externo en la posición indicada.
    
    Args:
        source_path: Ruta al PDF a insertar.
        at_page: Índice donde insertar (0-based). 
                 -1 = al final del documento.
    
    Returns:
        True si la inserción fue exitosa.
    
    Flujo:
        1. Guardar snapshot (para undo)
        2. Abrir PDF fuente con fitz
        3. Insertar páginas con doc.insert_pdf()
        4. Actualizar PageIdentityMap
        5. Emitir señal de cambio de estructura
    """

def insert_pages_from_pdf(self, source_path: str, 
                           source_pages: List[int],
                           at_page: int = -1) -> bool:
    """
    Inserta páginas específicas de un PDF externo.
    
    Args:
        source_path: Ruta al PDF fuente.
        source_pages: Lista de índices de páginas a insertar del fuente.
        at_page: Posición de inserción en el documento actual.
    """

def move_page(self, from_index: int, to_index: int) -> bool:
    """
    Mueve una página de una posición a otra.
    
    Flujo:
        1. Guardar snapshot
        2. doc.move_page(from_index, to_index)  # PyMuPDF nativo
        3. page_map.move_page(from_index, to_index)
        4. Emitir señal
    """

def reorder_pages(self, new_order: List[int]) -> bool:
    """
    Reordena todas las páginas según la lista dada.
    
    Args:
        new_order: Lista donde new_order[nueva_pos] = vieja_pos.
                   Ejemplo: [2, 0, 1] → la pág 2 pasa a ser la 0.
    
    Flujo:
        1. Guardar snapshot
        2. Crear nuevo documento con páginas en nuevo orden
        3. Reemplazar self.doc
        4. page_map.reorder(new_order)
        5. Emitir señal
    """

def delete_page(self, page_index: int) -> bool:
    """
    Elimina una página del documento.
    
    Flujo:
        1. Guardar snapshot
        2. doc.delete_page(page_index)
        3. page_map.remove_page(page_index)
        4. Limpiar datos huérfanos de editable_texts_data
        5. Emitir señal
    """
```

### Detalle de implementación: `reorder_pages`

PyMuPDF no tiene un método directo para reordenar múltiple páginas a la vez. La estrategia es:

```python
def reorder_pages(self, new_order: List[int]) -> bool:
    """Implementación usando select() de PyMuPDF."""
    self._save_snapshot()
    try:
        # fitz.Document.select() acepta una lista de índices de página
        # y reorganiza el documento para contener solo esas páginas en ese orden
        self.doc.select(new_order)
        self.page_map.reorder(new_order)
        self.modified = True
        return True
    except Exception as e:
        self._last_error = str(e)
        return False
```

### Detalle de implementación: `insert_pdf`

```python
def insert_pdf(self, source_path: str, at_page: int = -1) -> bool:
    self._save_snapshot()
    try:
        source_doc = fitz.open(source_path)
        insert_count = source_doc.page_count
        
        # Posición de inserción
        if at_page < 0:
            at_page = self.doc.page_count
        
        # PyMuPDF: insert_pdf inserta DESPUÉS de start_at
        # start_at=-1 inserta al inicio, start_at=0 después de página 0, etc.
        self.doc.insert_pdf(source_doc, start_at=at_page - 1)
        
        source_doc.close()
        
        # Actualizar mapa de identidad
        self.page_map.insert_pages(at_page, insert_count)
        
        self.modified = True
        return True
    except Exception as e:
        self._last_error = str(e)
        return False
```

---

## Fase 3: Remapeo Automático de Datos

### Archivos a crear/modificar (Fase 3)

| Acción | Archivo | Descripción |
| --- | --- | --- |
| **Crear** | `core/page_remap.py` | Funciones de remapeo centralizadas |
| Modificar | `core/pdf_handler.py` | Llamar al remapeo después de cada operación |
| Modificar | `ui/pdf_viewer.py` | Callback para remapear datos del viewer |

### ¿Por qué es necesario si ya usamos UUID?

Con UUIDs, `editable_texts_data` **no necesita remapeo** porque sus claves son UUIDs que no cambian. Sin embargo, sí necesitamos:

1. **Remapear `_highlights`** en `pdf_handler.py` (si se mantiene con claves numéricas)  
   → **Decisión**: migrar `_highlights` a UUID también. Las anotaciones en el PDF se mueven con la página automáticamente (PyMuPDF las mantiene ligadas al objeto página), pero el dict en memoria necesita UUID.

2. **Remapear snapshots de undo/redo**  
   → **No es necesario**. Los snapshots guardan el estado COMPLETO (bytes PDF + overlay_state). Al restaurar un snapshot, se restauran AMBOS coherentemente. El PDF vuelve a su estado anterior y el overlay_state tiene los UUIDs correctos para ese estado.

3. **Actualizar `EditableTextItem.page_num`** en items gráficos activos  
   → Cuando se reordena, los items gráficos de la página visible necesitan saber su nuevo índice para renderización. Pero su `page_uuid` no cambia.

4. **Limpiar datos de páginas eliminadas**

### Diseño del remapeo

```python
# core/page_remap.py

class PageRemapper:
    """Centraliza la lógica de actualización de datos tras operaciones de página."""
    
    @staticmethod
    def after_insert(page_map: PageIdentityMap,
                     highlights: dict,
                     at_index: int, 
                     count: int):
        """
        Actualiza estructuras tras insertar páginas.
        
        - highlights: se migra a UUID si aún no lo está
        - editable_texts_data: no necesita cambios (ya usa UUID)
        """
        pass  # _highlights ya migrado a UUID
    
    @staticmethod
    def after_reorder(page_map: PageIdentityMap,
                      highlights: dict,
                      new_order: List[int]):
        """
        Actualiza estructuras tras reordenar páginas.
        Con UUID, solo _highlights necesita actualizarse si no usa UUID.
        """
        pass
    
    @staticmethod
    def after_delete(page_map: PageIdentityMap,
                     editable_texts: dict,
                     highlights: dict,
                     deleted_uuid: str):
        """
        Limpia datos huérfanos de la página eliminada.
        """
        editable_texts.pop(deleted_uuid, None)
        highlights.pop(deleted_uuid, None)
```

### Señal de cambio de estructura

Para mantener la UI sincronizada:

```python
# En PDFDocument (o mediante callback)
# Señal: page_structure_changed(operation: str, details: dict)
#
# Operaciones:
#   "insert"  → details = {"at_index": int, "count": int, "new_uuids": List[str]}
#   "delete"  → details = {"deleted_uuid": str, "was_index": int}
#   "reorder" → details = {"new_order": List[int]}
#   "move"    → details = {"from": int, "to": int}
```

---

## Fase 4: UI de Reordenamiento (Drag & Drop en Thumbnails)

### Archivos a modificar (Fase 4)

| Acción | Archivo | Descripción |
| --- | --- | --- |
| Modificar | `ui/thumbnail_panel.py` | Habilitar drag & drop |
| Modificar | `ui/main_window.py` | Conectar señales del panel al core |

### Comportamiento esperado

1. El usuario ve las miniaturas de todas las páginas en el panel lateral
2. Puede **arrastrar y soltar** una miniatura para cambiar su posición
3. Al soltar, se ejecuta la operación de reordenamiento
4. Las miniaturas se regeneran en el nuevo orden
5. Si estaba viendo una página, la vista se mantiene en **esa misma página** (que ahora puede tener otro índice)

### Implementación del drag & drop

```python
# En ThumbnailPanel

def __init__(self):
    # ...
    self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
    self.list_widget.setDefaultDropAction(Qt.MoveAction)
    self.list_widget.model().rowsMoved.connect(self._on_pages_reordered)

def _on_pages_reordered(self):
    """Detecta el nuevo orden tras drag & drop y emite señal."""
    new_order = []
    for i in range(self.list_widget.count()):
        item = self.list_widget.item(i)
        old_index = item.data(Qt.UserRole)  # Índice original
        new_order.append(old_index)
    
    self.pagesReordered.emit(new_order)  # Nueva señal

# Nueva señal
pagesReordered = pyqtSignal(list)  # Emite [old_idx_en_nueva_pos_0, old_idx_en_nueva_pos_1, ...]
```

### Menú contextual adicional

```python
def _show_context_menu(self, pos):
    """Menú contextual sobre miniatura."""
    menu = QMenu(self)
    
    move_up = menu.addAction("Mover arriba")
    move_down = menu.addAction("Mover abajo")
    move_first = menu.addAction("Mover al inicio")
    move_last = menu.addAction("Mover al final")
    menu.addSeparator()
    delete_page = menu.addAction("Eliminar página")
    
    # Conectar acciones...
```

---

## Fase 5: UI de Unión/Inserción de PDF

### Archivos a crear/modificar (Fase 5)

| Acción | Archivo | Descripción |
| --- | --- | --- |
| **Crear** | `ui/insert_pdf_dialog.py` | Diálogo de inserción |
| Modificar | `ui/main_window.py` | Menú y acción para insertar PDF |
| Modificar | `ui/toolbar.py` | Botón opcional en toolbar |

### Diálogo de inserción: `InsertPDFDialog`

```text
┌─────────────────────────────────────────────────┐
│  Insertar PDF                              [X]  │
│─────────────────────────────────────────────────│
│                                                  │
│  Archivo a insertar:                             │
│  [________________________] [Examinar...]        │
│                                                  │
│  ┌──────────────────┐  Páginas a insertar:       │
│  │ Vista previa del │  ○ Todas                   │
│  │ PDF a insertar   │  ○ Rango: [__] a [__]     │
│  │ (miniatura)      │  ○ Selección: [1,3,5-7]   │
│  └──────────────────┘                            │
│                                                  │
│  Posición de inserción:                          │
│  ○ Al inicio del documento                       │
│  ○ Al final del documento                        │
│  ● Después de la página: [ 3 ▼]                 │
│                                                  │
│  ─── Vista previa del resultado ──────────────  │
│  │ P1 │ P2 │ P3 │ [N1] │ [N2] │ P4 │ P5 │     │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  [Cancelar]                        [Insertar]   │
└─────────────────────────────────────────────────┘
```

### Campos del diálogo

| Campo | Tipo | Descripción |
| --- | --- | --- |
| Archivo fuente | `QFileDialog` | Seleccionar PDF a insertar |
| Páginas a insertar | `QRadioButton` + `QLineEdit` | Todas, rango, o selección personalizada |
| Posición de inserción | `QRadioButton` + `QSpinBox` | Inicio, final, o después de página N |
| Vista previa | `QListWidget` horizontal | Miniaturas del resultado esperado |

### Flujo completo de inserción

```text
1. Usuario abre menú "Documento → Insertar PDF..." (o Ctrl+Shift+I)
2. Se abre InsertPDFDialog
3. Usuario selecciona archivo PDF
4. Se muestran miniaturas del PDF fuente
5. Usuario elige páginas y posición
6. Vista previa muestra resultado esperado
7. Usuario confirma
8. Se ejecuta:
   a. PDFDocument._save_snapshot()
   b. PDFDocument.insert_pdf() o insert_pages_from_pdf()
   c. PageIdentityMap se actualiza
   d. ThumbnailPanel.generate_thumbnails() se refresca
   e. Vista se posiciona en la primera página insertada
```

### Protección de textos editados durante la inserción

**Caso crítico**: el usuario tiene textos editados no guardados (`pending_write=True`) **antes** de insertar.

**Solución**:

1. Antes de insertar, se hace `commit_overlay_texts()` para escribir al PDF todos los textos pendientes
2. Se guarda snapshot (que ya incluye los textos comprometidos)
3. Se realiza la inserción
4. Los textos ya comprometidos están en el PDF y se mueven con su página
5. Los textos que estén en `editable_texts_data` con `pending_write=False` son referencia visual y usan UUID → no se afectan

```python
# En MainWindow, al confirmar inserción:
def _on_insert_pdf_confirmed(self, source_path, pages, at_page):
    """Ejecuta la inserción segura de PDF."""
    
    # PASO 1: Comprometer textos pendientes al PDF
    if hasattr(self.pdf_viewer, 'commit_overlay_texts'):
        self.pdf_viewer.commit_overlay_texts()
    
    # PASO 2: Insertar
    if pages is None:  # Todas las páginas
        success = self.pdf_doc.insert_pdf(source_path, at_page)
    else:
        success = self.pdf_doc.insert_pages_from_pdf(source_path, pages, at_page)
    
    if success:
        # PASO 3: Refrescar UI
        self.thumbnail_panel.generate_thumbnails()
        self.pdf_viewer.display_page(at_page)  # Ir a primera página insertada
        self.update_title()
```

---

## Fase 6: Undo/Redo para Operaciones de Página

### Estrategia

El sistema de undo/redo actual ya guarda `(pdf_bytes, overlay_state)`. Las operaciones de página se integran naturalmente:

1. **Antes** de cada operación de página → `_save_snapshot()`
2. El snapshot incluye:
   - `pdf_bytes`: estado completo del PDF (con su orden de páginas)
   - `overlay_state`: copia de `editable_texts_data` (con UUIDs)
3. **Además**, guardar el estado de `PageIdentityMap` en el snapshot

### Modificación del snapshot

```python
# Cambiar el formato de snapshot de:
#   (pdf_bytes, overlay_state)
# A:
#   (pdf_bytes, overlay_state, page_map_state)

def _save_snapshot(self):
    current_bytes = self.doc.tobytes(garbage=0)
    overlay_state = self._get_overlay_state_callback() if self._get_overlay_state_callback else None
    page_map_state = self.page_map.to_list()
    
    self._undo_snapshots.append((current_bytes, overlay_state, page_map_state))

def undo(self) -> bool:
    # ...
    previous_state = self._undo_snapshots.pop()
    previous_bytes, previous_overlay, previous_page_map = previous_state
    
    # Restaurar PDF
    self.doc.close()
    self.doc = fitz.open(stream=previous_bytes, filetype="pdf")
    
    # Restaurar overlay
    if self._restore_overlay_state_callback and previous_overlay:
        self._restore_overlay_state_callback(previous_overlay)
    
    # Restaurar mapa de páginas
    if previous_page_map:
        self.page_map.from_list(previous_page_map)
```

### Compatibilidad con snapshots antiguos

```python
# Al restaurar, manejar el formato antiguo (tupla de 2) y nuevo (tupla de 3)
if len(previous_state) == 3:
    previous_bytes, previous_overlay, previous_page_map = previous_state
elif len(previous_state) == 2:
    previous_bytes, previous_overlay = previous_state
    previous_page_map = None
```

---

## Fase 7: Tests

### Archivos a crear

| Archivo | Cobertura |
| --- | --- |
| `tests/test_page_identity.py` | PageIdentityMap: init, insert, remove, reorder, move, serialize |
| `tests/test_page_operations.py` | PDFDocument: insert_pdf, move_page, reorder_pages, delete_page |
| `tests/test_page_remap.py` | Remapeo de editable_texts_data, highlights, snapshots |
| `tests/test_insert_pdf_integration.py` | Flujo completo: abrir → editar → insertar → verificar textos intactos |
| `tests/test_reorder_integration.py` | Flujo completo: abrir → editar → reordenar → verificar textos intactos |

### Casos de test críticos

```python
# test_page_identity.py

def test_uuid_stable_after_reorder():
    """Los UUIDs no cambian al reordenar, solo su posición."""
    pm = PageIdentityMap()
    pm.initialize(3)
    original_uuids = pm.order.copy()
    
    pm.reorder([2, 0, 1])
    
    assert set(pm.order) == set(original_uuids)  # Mismos UUIDs
    assert pm.order[0] == original_uuids[2]       # La pág 2 está ahora en pos 0

def test_uuid_stable_after_insert():
    """Los UUIDs existentes no cambian tras insertar páginas nuevas."""
    pm = PageIdentityMap()
    pm.initialize(3)
    original_uuids = pm.order.copy()
    
    pm.insert_pages(1, 2)  # Insertar 2 páginas en posición 1
    
    assert pm.page_count == 5
    assert pm.order[0] == original_uuids[0]   # Pág 0 intacta
    assert pm.order[3] == original_uuids[1]   # Pág 1 original ahora en pos 3
    assert pm.order[4] == original_uuids[2]   # Pág 2 original ahora en pos 4

def test_texts_survive_reorder():
    """Textos editados permanecen en su página tras reordenamiento."""
    # 1. Crear documento con 5 páginas
    # 2. Añadir texto "EDITADO" en página 2
    # 3. Reordenar: [4, 3, 2, 1, 0]  (invertir orden)
    # 4. Verificar que "EDITADO" está en la nueva posición de la página original 2
    # 5. Verificar que el texto tiene las mismas coordenadas y formato

def test_texts_survive_insert():
    """Textos editados sobreviven a la inserción de otro PDF."""
    # 1. Crear documento con 3 páginas
    # 2. Editar texto en página 1
    # 3. Insertar PDF de 2 páginas después de página 0
    # 4. La página con el texto editado ahora es la 3 (era la 1)
    # 5. Verificar que el texto está intacto en la posición correcta

def test_undo_after_insert():
    """Undo revierte la inserción completamente."""
    # 1. Abrir PDF de 3 páginas, editar texto
    # 2. Insertar PDF de 2 páginas
    # 3. Verificar 5 páginas
    # 4. Undo
    # 5. Verificar 3 páginas con textos originales intactos

def test_undo_after_reorder():
    """Undo revierte el reordenamiento completamente."""

def test_multiple_operations_sequence():
    """Secuencia: editar → insertar → reordenar → editar → undo × 3."""

def test_insert_at_beginning():
    """Insertar al inicio no corrompe textos existentes."""

def test_insert_at_end():
    """Insertar al final no corrompe textos existentes."""

def test_insert_between_edited_pages():
    """Insertar entre dos páginas con ediciones conserva ambas."""

def test_delete_page_with_edits():
    """Eliminar página limpia sus datos de editable_texts_data."""

def test_delete_page_preserves_others():
    """Eliminar una página no afecta los textos de otras páginas."""

def test_pending_write_before_insert():
    """Textos pending_write se commitean antes de insertar."""

def test_reorder_with_highlights():
    """Highlights se mantienen en su página tras reordenar."""
```

---

## 8. Matriz de Casos Edge

| # | Escenario | Riesgo | Mitigación |
| --- | --- | --- | --- |
| 1 | Insertar PDF vacío (0 páginas) | Error o estado incoherente | Validar `source_doc.page_count > 0` antes de insertar |
| 2 | Insertar PDF protegido con contraseña | Fallo al abrir | Detectar con `source_doc.is_encrypted`, pedir contraseña o rechazar |
| 3 | Insertar PDF corrupto | Crash de PyMuPDF | Envolver en try/except, validar con `fitz.open()` |
| 4 | Reordenar con lista inválida (ej: [0, 0, 1]) | Duplicar página | Validar que `new_order` sea permutación de `range(page_count)` |
| 5 | Mover página a la misma posición | Operación innecesaria | Detectar y no hacer nada (no gastar snapshot) |
| 6 | Insertar en posición fuera de rango | IndexError | Clampar `at_page` entre 0 y `page_count` |
| 7 | Documentos con páginas de tamaños diferentes | Textos con coordenadas de tamaño incorrecto | Las coordenadas son relativas a cada página; no se afectan |
| 8 | Insertar PDF con formularios interactivos | Pueden perder interactividad | Documentar limitación; `insert_pdf()` preserva formularios |
| 9 | Texto `pending_write=True` durante reordenamiento | Texto no escrito se asocia a página equivocada | **Forzar commit** antes de reordenar o insertar |
| 10 | Undo después de guardar | Undo a estado pre-guardado con archivos modificados | Igualar comportamiento actual (undo funciona sobre bytes en memoria) |
| 11 | Múltiples inserciones consecutivas | Acumulación de UUIDs, posible mem leak | Limitar snapshots (ya existe `_max_undo_levels = 20`) |
| 12 | Reordenar y luego editar texto en nueva posición | El UUID debe apuntar correctamente | UUID no cambia; el texto se asocia al UUID de la página |
| 13 | Insertar el mismo PDF sobre sí mismo | Posible bloqueo de archivo | Abrir source como bytes primero: `fitz.open(stream=bytes, filetype="pdf")` |
| 14 | Documento con más de 1000 páginas | Rendimiento del drag & drop | Lazy loading de thumbnails, reorder con `doc.select()` es O(n) |
| 15 | Highlights como anotaciones PDF durante reorder | Anotaciones se mueven con la página | Sin riesgo; PyMuPDF mantiene anotaciones con su página |
| 16 | Overlay state en snapshot tiene el formato antiguo (sin page_map) | Crash al desempaquetar tupla de 2 vs 3 | Compatibilidad: `len(state)` check |

---

## 9. Orden de Ejecución y Dependencias

```text
Semana 1: Fase 1 (PageIdentityMap + migración editable_texts_data)
    ├── Crear core/page_identity.py
    ├── Integrar en PDFDocument.__init__() y open()
    ├── Migrar editable_texts_data a UUID-keys
    ├── Crear helpers en PDFPageView
    ├── Actualizar EditableTextItem (añadir page_uuid)
    └── Tests unitarios de PageIdentityMap

Semana 2: Fase 2 + 3 (Operaciones core + remapeo)
    ├── Implementar insert_pdf(), move_page(), reorder_pages(), delete_page()
    ├── Crear core/page_remap.py
    ├── Migrar _highlights a UUID
    ├── Señales de cambio de estructura
    └── Tests unitarios de operaciones

Semana 3: Fase 4 + 5 (UI)
    ├── Drag & drop en ThumbnailPanel
    ├── Menú contextual en thumbnails
    ├── Crear InsertPDFDialog
    ├── Menú "Documento → Insertar PDF..."
    ├── Flujo de commit antes de operaciones de página
    └── Tests de integración UI

Semana 4: Fase 6 + 7 (Undo/Redo + Tests finales)
    ├── Extender snapshots para page_map
    ├── Compatibilidad con snapshots antiguos
    ├── Tests de integración completos
    ├── Tests de casos edge
    └── Revisión y estabilización
```

### Diagrama de dependencias entre módulos

```text
core/page_identity.py  ──────────────────────────────────┐
         │                                                │
         ▼                                                │
core/pdf_handler.py (insert_pdf, reorder, move, delete)   │
         │                                                │
         ▼                                                │
core/page_remap.py (limpieza de datos huérfanos)          │
         │                                                │
         ├──────────────────┐                             │
         ▼                  ▼                             │
ui/pdf_viewer.py      ui/thumbnail_panel.py               │
 (editable_texts_data   (drag & drop,                     │
  con UUID-keys,         señales de reorden)               │
  helpers de acceso)                                       │
         │                  │                             │
         ▼                  ▼                             │
ui/main_window.py (conecta señales, menús, diálogos)      │
         │                                                │
         ▼                                                │
ui/insert_pdf_dialog.py ──────────────────────────────────┘
```

---

## Resumen de Archivos Afectados

| Archivo | Tipo de cambio | Complejidad |
| --- | --- | --- |
| `core/page_identity.py` | **Nuevo** | Media |
| `core/page_remap.py` | **Nuevo** | Baja |
| `ui/insert_pdf_dialog.py` | **Nuevo** | Media-Alta |
| `core/pdf_handler.py` | Modificación significativa | Alta |
| `ui/pdf_viewer.py` | Modificación significativa | Alta |
| `ui/thumbnail_panel.py` | Modificación media | Media |
| `ui/main_window.py` | Modificación media | Media |
| `ui/graphics_items.py` | Modificación menor | Baja |
| `core/models.py` | Sin cambios | — |
| `core/change_report.py` | Modificación menor (nuevos ChangeType) | Baja |
| `tests/test_page_identity.py` | **Nuevo** | Media |
| `tests/test_page_operations.py` | **Nuevo** | Media |
| `tests/test_page_remap.py` | **Nuevo** | Media |
| `tests/test_insert_pdf_integration.py` | **Nuevo** | Alta |
| `tests/test_reorder_integration.py` | **Nuevo** | Alta |

---

## Principios de Diseño Aplicados

1. **Identidad sobre posición**: UUID inmutable vs índice cambiante
2. **Commit antes de mutar**: siempre persistir textos pendientes antes de cambiar estructura
3. **Snapshot atómico**: cada operación de página guarda estado completo (PDF + overlays + mapa)
4. **Compatibilidad hacia atrás**: snapshots antiguos (tupla de 2) siguen funcionando
5. **Separación de responsabilidades**: PageIdentityMap no sabe del PDF, PDFDocument no sabe de la UI
6. **Fail-safe**: validaciones exhaustivas antes de cada operación (permutación válida, archivo accesible, etc.)
7. **Migración progresiva**: no reescribir todo de golpe; capa de traducción para convivencia
