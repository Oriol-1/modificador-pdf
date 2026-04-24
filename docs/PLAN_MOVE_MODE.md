# Plan: Modo "Mover" para bloques de texto PDF

> **Estado**: 📋 Diseño aprobado, pendiente de implementación.
> **Rama base**: `remove-annotations` (tag `v2.1.1-no-annotations`).
> **Autor**: Sesión de diseño 2026-04-24.

---

## 1. Objetivo

Añadir un modo de herramienta `'move'` al editor que permita **desplazar libremente** una línea o un párrafo de texto existente en el PDF como si fuera un módulo independiente, **sin alterar contenido, tamaño, tipografía, estilo ni el fondo de la página**.

El movimiento debe sentirse "visual y posicional": el bloque se levanta, se arrastra y se deja en otra coordenada. Al guardar, el cambio se materializa en el PDF respetando todos los demás elementos.

## 2. Reglas de oro (no negociables)

1. **El fondo nunca se toca.** Prohibido `add_redact_annot`, prohibido pintar rectángulos blancos, prohibido `apply_redactions()` sobre la página.
2. **Los demás textos no se ven afectados.** La cirugía es por bloque identificado, no por área geométrica.
3. **El bloque movido conserva tipografía exacta.** Se reusan los operadores `Tf`, `Tc`, `Tw`, `Tz`, `Tr` y los glifos del original; sólo cambia la matriz de texto `Tm`.
4. **El movimiento sólo es visual durante la sesión.** El PDF en disco no se modifica hasta que el usuario pulsa Guardar.
5. **Cualquier limitación se comunica antes de guardar.** Aviso único, agregado, en el momento de `save()`. Nunca diálogos por interacción.

## 3. Decisiones de UX

| Acción | Resultado |
|---|---|
| Clic sobre texto en modo Mover | Selecciona la **línea** que está bajo el cursor |
| Shift + clic sobre texto en modo Mover | Selecciona el **párrafo** completo |
| Hover sobre texto en modo Mover | Resalta en verde la línea/párrafo candidato |
| Drag desde el bloque seleccionado | Mueve libremente (sin snap, sin restricciones) |
| Esc durante drag | Cancela el movimiento de ese bloque |
| Esc sin drag activo | Limpia la selección |
| Salir del modo Mover | No revierte movimientos hechos: quedan como `PendingMove` en sesión |
| Cerrar sin guardar | El PDF en disco queda intacto, los `PendingMove` se descartan |
| Guardar | Materializa todos los `PendingMove` en el PDF, con aviso único previo si hay riesgos |

## 4. Arquitectura — 3 capas independientes

```
┌────────────────────────────────────────────────────────────────┐
│  CAPA UI  •  ui/move_mode.py                                   │
│  ───────────────────────────────────────────────────           │
│  MoveModeController                                            │
│   - Activa/desactiva modo a partir de set_tool_mode('move')    │
│   - Captura clicks, shift+clicks y arrastres                   │
│   - Mantiene un overlay temporal (QGraphicsPixmapItem Z=120)   │
│     con el pixmap recortado del bloque                         │
│   - Acumula PendingMove en memoria de sesión                   │
│   - NO escribe nada en el PDF                                  │
└────────────────────────────────────────────────────────────────┘
                              ↓ (sólo al save())
┌────────────────────────────────────────────────────────────────┐
│  CAPA LÓGICA  •  core/text_engine/block_mover.py               │
│  ───────────────────────────────────────────────────           │
│  BlockMover                                                    │
│   - Resuelve qué spans/operadores Tj-TJ del content stream     │
│     pertenecen a un PendingMove                                │
│   - Detecta fonts subset por prefijo aleatorio (XXXXXX+Name)   │
│   - Acumula advertencias por bloque                            │
│   - Genera un MovePlan (lista de operaciones de cirugía)       │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│  CAPA PDF  •  core/text_engine/content_stream_surgeon.py       │
│  ───────────────────────────────────────────────────           │
│  ContentStreamSurgeon                                          │
│   - Lee page.read_contents() y tokeniza operadores             │
│   - Identifica bloques BT…ET candidatos                        │
│   - Elimina sólo los BT…ET del span objetivo                   │
│   - Inserta nuevos BT…ET con la misma fuente y Tm desplazada   │
│   - Escribe page.set_contents() con el stream resultante       │
│   - Nunca toca operadores de imagen (Do), vectores (f, S, re), │
│     ni otros bloques de texto                                  │
└────────────────────────────────────────────────────────────────┘
```

Cada capa es testeable de forma aislada (`tests/text_engine/test_block_mover.py`, `tests/text_engine/test_content_stream_surgeon.py`, `tests/ui/test_move_mode.py`).

## 5. Modelo de datos

### `PendingMove` (sesión, en memoria)

```python
@dataclass(frozen=True)
class PendingMove:
    page_index: int
    block_id: str             # hash estable: page+bbox_origin+text
    unit: BlockUnit           # LINE | PARAGRAPH
    original_bbox: fitz.Rect  # bbox original en coords PDF
    delta_pdf: tuple[float, float]  # (dx, dy) en coords PDF
    spans_snapshot: list[EditableSpan]  # copia inmutable para restaurar/persistir
    has_subset_font: bool
    warnings: list[str] = field(default_factory=list)
```

### `MovePlan` (generado en save)

```python
@dataclass
class MovePlan:
    moves: list[PendingMove]
    blocked: list[PendingMove]      # imposibles de mover (e.g. fonts no embebidos)
    needs_user_confirmation: list[PendingMove]  # subset, requieren consentimiento
```

## 6. Detección de fonts subset

Convención PDF estándar: los fonts subset llevan un prefijo aleatorio de **6 letras mayúsculas + `+`** antes del PostScript name. Ejemplo: `SDIUIR+Helvetica`, `HUHQIP+TimesNewRoman`.

```python
import re
SUBSET_PREFIX_RE = re.compile(r'^[A-Z]{6}\+')

def is_subset_font(font_name: str) -> bool:
    return bool(SUBSET_PREFIX_RE.match(font_name))
```

Al hacer hit-test de un bloque, se computa `has_subset_font = any(is_subset_font(s.font_name) for s in spans)`. Se almacena en `PendingMove`. **No se muestra ningún aviso** en ese momento.

## 7. Estrategias de persistencia (en orden de preferencia)

Cuando el usuario guarda, `BlockMover` evalúa cada `PendingMove` y elige una estrategia:

| Prioridad | Estrategia | Cuándo se aplica | Garantías |
|---|---|---|---|
| A | **Cirugía exacta de content stream** | Bloque sin subset, font embebido o estándar | Texto editable y seleccionable, fidelidad 1:1 |
| B | **Reinserción con TextWriter** usando el font del subset embebido | Subset cuyos glifos usados ya están todos cubiertos | Texto editable, fidelidad alta |
| C | **Capa overlay como XObject de imagen** (rasterización opt-in) | Subset con glifos no cubiertos, *y* el usuario aceptó en el diálogo final | El bloque queda como imagen separada encima del fondo intacto. **No** se mezcla con el contenido base. Se pierde la editabilidad como texto |
| BLOCK | **No mover, dejar en posición original** | Usuario rechaza C en el diálogo final | El PDF se guarda con el bloque en su sitio original |

**Importante**: la estrategia C **nunca** modifica el fondo. La rasterización se inserta como un objeto independiente encima, en la nueva posición. Si más tarde se mueve otro bloque, ese sigue intacto.

## 8. Diálogo único previo al guardado

Al pulsar Guardar:

1. `BlockMover.build_plan(pending_moves)` clasifica cada move en A/B/C/BLOCK.
2. Si hay alguno en C o BLOCK, se abre `MoveWarningDialog` con:
   - Tabla de bloques problemáticos (página, primeras palabras del texto, motivo).
   - Acción global: "Aceptar rasterización para los bloques marcados" (checkbox).
   - Acción individual por fila: descartar movimiento (vuelve a posición original).
   - Botones: **Guardar** | **Cancelar guardado**.
3. Sin bloques problemáticos → guardado directo sin diálogo.

## 9. Algoritmo de cirugía del content stream (estrategia A)

Pseudocódigo:

```
1. raw = page.read_contents()
2. tokens = tokenize_pdf_operators(raw)        # secuencia de (operator, args)
3. text_blocks = extract_BT_ET_blocks(tokens)  # cada bloque con su bbox calculada
4. target = match_block(text_blocks, pending_move.spans_snapshot)
5. if target is None: raise BlockNotFoundError  → estrategia B o C
6. new_block = deepcopy(target)
7. translate_Tm(new_block, pending_move.delta_pdf)
8. tokens_out = remove(tokens, target) + insert_at_end_text_layer(new_block)
9. page.set_contents(serialize(tokens_out))
```

**Puntos delicados a validar en F5**:
- Múltiples `Tm`/`Td`/`TD` dentro del mismo BT…ET → trasladar sólo el primer `Tm` (origen) y dejar los relativos intactos.
- Bloques BT que mezclan varios spans en líneas distintas → la unidad mínima de cirugía es el BT entero; si el move es por línea pero el BT contiene 3 líneas, hay que **partir el BT** en tres antes de mover.
- Estados gráficos (`q … Q`) que envuelven el BT → preservarlos en el bloque insertado.

## 10. Plan de fases

| Fase | Entregable | Riesgo | Aceptación |
|---|---|---|---|
| **F0** | Spike: pixmap recortado del bloque arrastrable en QGraphicsScene, **sin tapar el fondo** | 🟢 Bajo | Click levanta visualmente el bloque, fondo intacto debajo |
| **F1** | Botón "🚚 Mover" en toolbar + `set_tool_mode('move')` + cursor `OpenHandCursor` | 🟢 Bajo | No rompe modos existentes |
| **F2** | Hit-test → clic = línea, Shift+clic = párrafo. Hover en verde | 🟢 Bajo | Selección visual estable |
| **F3** | Drag visual + acumulación `PendingMove`. Esc cancela | 🟢 Bajo | Bloque queda en nueva pos visual, repetible |
| **F4** | Detección interna de subset, marcado de bloques. Sin diálogos aún | 🟢 Bajo | `has_subset_font` correctamente poblado |
| **F5** | `ContentStreamSurgeon` POC en script independiente. Validación con Acrobat | 🔴 Alto | PDF de prueba conserva imágenes/vectores/otros textos; sólo el bloque movido se desplaza |
| **F6** | Integrar Surgeon en `PDFDocument.save()`. Estrategia A funcional | 🟡 Medio | Save genera PDF con bloques movidos, fondo idéntico |
| **F7** | Estrategia B (TextWriter con font del subset) | 🟡 Medio | Documentos con subset moderado guardan bien |
| **F8** | Estrategia C (overlay rasterizado opt-in) sin tocar fondo | 🟡 Medio | Caso extremo funciona sin contaminar capa base |
| **F9** | `MoveWarningDialog` y flujo de confirmación previo a guardar | 🟢 Bajo | Aviso único agregado, opciones por fila |
| **F10** | Tests unit + integración (≥10 por módulo) | 🟢 Bajo | `pytest tests/` verde |

**Hito de seguridad**: hasta F4 todo es sesión visual, cero escritura. Si F5 no sale bien, descartamos sin haber dañado el PDF.

## 11. Tests previstos

```
tests/text_engine/
  test_block_mover.py              # ≥10: detección, snapshot, plan
  test_content_stream_surgeon.py   # ≥10: tokenizar, eliminar BT, trasladar Tm
  test_subset_font_detection.py    # ≥5: regex, prefijos válidos/inválidos

tests/ui/
  test_move_mode.py                # ≥10: activación, hit-test, drag, esc
  test_move_warning_dialog.py      # ≥5: render, opciones, cancelación

tests/integration/
  test_move_save_roundtrip.py      # ≥5: mover + guardar + reabrir + verificar
```

## 12. Lo que NO entra en este plan

- Mover **imágenes** existentes del PDF (sólo texto).
- Mover bloques **entre páginas distintas**.
- Edición del **contenido** del bloque movido (sigue siendo responsabilidad de `PageWriter`).
- **Rotar** o **redimensionar** el bloque movido.
- Mover en PDFs **escaneados sin OCR** (no hay texto vectorial que mover).

## 13. Riesgos identificados y mitigación

| Riesgo | Mitigación |
|---|---|
| Cirugía rompe el content stream y el PDF queda corrupto | Antes de `set_contents`, validar con `fitz.Document.is_valid_pdf()`. Si falla, descartar el cambio y mostrar error. Ningún cambio se materializa hasta `doc.save()` final |
| Múltiples spans de un BT con diferentes orígenes obligan a partir el BT | F5 tiene un caso de test específico para esto |
| Fonts subset no embebidos completos → glifos desconocidos al reinsertar | Estrategia B detecta esto antes de escribir; si falla, va a C o BLOCK |
| Usuario espera deshacer movimientos como en Word | F3 incluye Esc; deshacer global por shortcut Ctrl+Z queda fuera del scope inicial |
| Rotación de página no aplicada al delta | El delta se guarda en coords PDF; `CoordinateConverter` ya maneja rotación |

## 14. Referencias del código actual

- Selección y hit-test: [ui/text_selection_overlay.py](../ui/text_selection_overlay.py), [core/text_engine/text_hit_tester.py](../core/text_engine/text_hit_tester.py)
- Modelo de spans: [core/text_engine/page_document_model.py](../core/text_engine/page_document_model.py)
- Coordenadas: [ui/coordinate_utils.py](../ui/coordinate_utils.py)
- Toolbar/menús: [ui/toolbar.py](../ui/toolbar.py), [ui/main_window.py](../ui/main_window.py)
- Guardado: [core/pdf_handler.py](../core/pdf_handler.py)

## 15. Antecedentes (intentos previos descartados)

Tres intentos previos manipulando spans individuales fracasaron porque trataban el problema **por span**, no **por bloque**:

| Intento | Enfoque | Síntoma |
|---|---|---|
| 1 | `isolate-batch` con `Tc/Tw/Tz` | El tamaño seguía creciendo |
| 2 | Recálculo de bbox desde original | Primer move desaparece, segundo pierde palabras |
| 3 | Redact + rewrite por span en cada drag | Texto se junta y cambia tamaño |

**Causa raíz**: cada operación de "mover" forzaba a recalcular dimensiones de spans individuales con kerning subset, divergiendo de las métricas del content stream.

**Conclusión adoptada**: la unidad atómica de cirugía es el **bloque BT…ET**, no el span. Y la operación "mover" no comparte ruta con "editar contenido" — son problemas distintos.

---

**Próximo paso aprobado**: comenzar **F0** — spike de pixmap arrastrable sin tocar el PDF.
