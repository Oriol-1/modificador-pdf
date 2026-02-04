# Guía de Estilo Markdown para el Proyecto

Esta guía establece estándares para evitar los errores más comunes de markdownlint.

## Reglas Críticas

### 1. MD022: Espacios alrededor de encabezados

❌ **Incorrecto:**

```markdown
## Encabezado
contenido sin línea en blanco
```

✅ **Correcto:**
```markdown
Contenido anterior.

## Encabezado

Contenido posterior.
```

**Regla:** Siempre deja UNA línea en blanco ANTES y DESPUÉS de cada encabezado.

---

### 2. MD032: Espacios alrededor de listas

❌ **Incorrecto:**

```markdown
## Encabezado
- Item 1
- Item 2
contenido
```

✅ **Correcto:**

```markdown
## Encabezado

- Item 1
- Item 2

Contenido posterior.
```

**Regla:** Siempre rodea las listas con líneas en blanco.

---

### 3. MD031: Espacios alrededor de bloques de código

❌ **Incorrecto:**

```markdown
Texto anterior

```python
code
```

Texto posterior
```

✅ **Correcto:**

```markdown
Texto anterior

```python
code
```

Texto posterior.
```

**Regla:** Siempre deja una línea en blanco antes y después de bloques de código.

---

### 4. MD040: Especificar lenguaje en bloques de código

❌ **Incorrecto:**

```markdown
```
código sin especificar
```
```

✅ **Correcto:**

```markdown
```python
código especificado
```
```

**Lenguajes comunes:**

- `python` - código Python
- `javascript` - código JavaScript
- `bash` - comandos de shell
- `markdown` - markdown
- `json` - archivos JSON
- `yaml` - archivos YAML
- `html` - HTML
- `css` - CSS
- `sql` - SQL
- `text` o `plaintext` - texto sin resalte

---

### 5. MD009: Sin espacios al final de líneas

❌ **Incorrecto:**

```markdown
Esta línea tiene espacios al final
```

✅ **Correcto:**

```markdown
Esta línea no tiene espacios
```

**Solución:** Usa un editor que resalte espacios finales (VS Code tiene esta opción).

---

### 6. MD060: Consistencia en tablas

❌ **Incorrecto:**

```markdown
|Columna 1|Columna 2|
|-|-|
|Dato|Dato|
```

✅ **Correcto:**

```markdown
| Columna 1 | Columna 2 |
| --------- | --------- |
| Dato      | Dato      |
```

**Regla:** Usa espacios consistentes alrededor de pipes (`|`). Recomendado: espacio antes y después de cada pipe.

---

### 7. MD012: Una línea en blanco entre párrafos

❌ **Incorrecto:**

```markdown
Párrafo 1


Párrafo 2
```

✅ **Correcto:**

```markdown
Párrafo 1

Párrafo 2
```

**Regla:** Máximo UNA línea en blanco entre elementos.

---

### 8. MD034: URLs deben estar entre paréntesis

❌ **Incorrecto:**

```markdown
Visita https://ejemplo.com para más info
```

✅ **Correcto:**

```markdown
Visita [este sitio](https://ejemplo.com) para más info
```

O si es una referencia:

```markdown
Visita <https://ejemplo.com> para más info
```

---

### 9. MD036: No usar énfasis como encabezados

❌ **Incorrecto:**

```markdown
**Esto es un encabezado falso**
Contenido...
```

✅ **Correcto:**

```markdown
## Esto es un encabezado real

Contenido...
```

---

## Plantilla para Nuevos Documentos

```markdown
# Título Principal

Párrafo introductorio.

## Sección 1

Contenido de la sección.

- Item 1
- Item 2
- Item 3

Más contenido.

```python
código_ejemplo = "con lenguaje especificado"
```

Explicación del código.

## Sección 2

Contenido de la segunda sección.

### Subsección

Contenido anidado.

## Referencias

- [Enlace descriptivo](https://ejemplo.com)
```

---

## Checklist antes de Commit

- [ ] ¿Todos los encabezados tienen líneas en blanco antes y después?
- [ ] ¿Todas las listas están rodeadas de líneas en blanco?
- [ ] ¿Todos los bloques de código tienen lenguaje especificado?
- [ ] ¿Todos los bloques de código están rodeados de líneas en blanco?
- [ ] ¿No hay espacios finales en las líneas?
- [ ] ¿Las tablas tienen espacios consistentes?
- [ ] ¿Los URLs están entre `[]()` o `<>`?
- [ ] ¿No hay énfasis usado como encabezados?

---

## Configuración Automática en VS Code

Añade esto a tu `.vscode/settings.json`:

```json
{
  "editor.trimAutoWhitespace": true,
  "[markdown]": {
    "editor.trimAutoWhitespace": true,
    "editor.formatOnSave": false,
    "editor.renderWhitespace": "boundary",
    "editor.insertSpaces": true,
    "editor.tabSize": 2
  },
  "markdownlint.config": {
    "MD022": {"lines": 1},
    "MD031": true,
    "MD032": true,
    "MD040": true
  }
}
```

---

## Extensiones Recomendadas

1. **markdownlint** (David Anson) - Validación en tiempo real
2. **Markdown Preview Enhanced** - Vista previa mejorada
3. **Prettier** - Formato automático (opcional)

---

## Plantilla para Nuevos Documentos

```markdown
# Título Principal

Párrafo introductorio.

## Sección 1

Contenido de la sección.

- Item 1
- Item 2
- Item 3

Más contenido.

```python
código_ejemplo = "con lenguaje especificado"
```

Explicación del código.

## Sección 2

Contenido de la segunda sección.

### Subsección

Contenido anidado.

## Referencias

- [Enlace descriptivo](https://ejemplo.com)
```

---

## Checklist antes de Commit

- [ ] ¿Todos los encabezados tienen líneas en blanco antes y después?
- [ ] ¿Todas las listas están rodeadas de líneas en blanco?
- [ ] ¿Todos los bloques de código tienen lenguaje especificado?
- [ ] ¿Todos los bloques de código están rodeados de líneas en blanco?
- [ ] ¿No hay espacios finales en las líneas?
- [ ] ¿Las tablas tienen espacios consistentes?
- [ ] ¿Los URLs están entre `[]()` o `<>`?
- [ ] ¿No hay énfasis usado como encabezados?

---

## Configuración Automática en VS Code

Añade esto a tu `.vscode/settings.json`:

```json
{
  "editor.trimAutoWhitespace": true,
  "[markdown]": {
    "editor.trimAutoWhitespace": true,
    "editor.formatOnSave": false,
    "editor.renderWhitespace": "boundary",
    "editor.insertSpaces": true,
    "editor.tabSize": 2
  },
  "markdownlint.config": {
    "MD022": {"lines": 1},
    "MD031": true,
    "MD032": true,
    "MD040": true
  }
}
```

## Extensiones Recomendadas

1. **markdownlint** (David Anson) - Validación en tiempo real
2. **Markdown Preview Enhanced** - Vista previa mejorada
3. **Prettier** - Formato automático (opcional)

