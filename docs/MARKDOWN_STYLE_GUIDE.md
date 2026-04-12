# Guía de Estilo Markdown

Estándares para evitar errores comunes de markdownlint.

## Reglas

### MD022: Espacios alrededor de encabezados

Deja UNA línea en blanco ANTES y DESPUÉS de cada encabezado.

### MD032: Espacios alrededor de listas

Rodea las listas con líneas en blanco.

### MD031: Espacios alrededor de bloques de código

Deja una línea en blanco antes y después de bloques de código.

### MD040: Especificar lenguaje en bloques de código

Siempre especifica el lenguaje en los bloques de código.

```python
# Ejemplo correcto con lenguaje especificado
print("Hola mundo")
```

### MD009: Sin espacios al final de líneas

No dejes espacios al final de las líneas. Usa un editor que resalte espacios finales.

### MD060: Consistencia en tablas

Usa espacios consistentes alrededor de pipes (`|`):

| Columna 1 | Columna 2 |
| --------- | --------- |
| Dato      | Dato      |

### MD012: Una línea en blanco entre párrafos

Máximo UNA línea en blanco entre elementos. Evita múltiples líneas en blanco.

### MD034: URLs deben estar entre paréntesis o ángulos

Usa: `[texto](https://ejemplo.com)` o `<https://ejemplo.com>`

NO: `Visita https://ejemplo.com`

### MD036: No usar énfasis como encabezados

Usa `## Encabezado` en lugar de `**Encabezado**`

---

## Plantilla para Nuevos Documentos

```markdown
# Título Principal

Párrafo introductorio.

## Primera Sección

Contenido de la sección.

- Punto 1
- Punto 2

```

```python
# Código de ejemplo
resultado = calcular()
```

Explicación del código.

---

## Checklist antes de Commit

- [ ] ¿Encabezados con líneas en blanco?
- [ ] ¿Listas rodeadas de líneas en blanco?
- [ ] ¿Bloques de código con lenguaje?
- [ ] ¿Bloques de código rodeados de líneas?
- [ ] ¿Sin espacios finales?
- [ ] ¿Tablas consistentes?
- [ ] ¿URLs formateadas?
- [ ] ¿Sin énfasis como encabezados?

---

## Extensiones Recomendadas

1. **markdownlint** (David Anson) - Validación en tiempo real
2. **Markdown Preview Enhanced** - Vista previa mejorada
3. **Prettier** (opcional) - Formateador automático
