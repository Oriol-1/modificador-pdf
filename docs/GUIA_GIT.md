# 🔧 Guía de Desarrollo y Control de Versiones

## 📋 Workflow Recomendado

Para mantener esta versión estable como referencia, sigue estos pasos:

### 1. Antes de Empezar a Trabajar

```powershell
# Asegúrate de estar en main
git checkout main

# Actualiza el código (si colaboras con otros)
git pull origin main

# Verifica que los tests pasen
python -m pytest pdf_editor/tests/ -v
```

### 2. Crear una Rama para tu Cambio

```powershell
# Para una nueva característica
git checkout -b feature/nombre-caracteristica

# Para un arreglo de bug
git checkout -b fix/nombre-del-bug

# Para refactorización
git checkout -b refactor/nombre-del-modulo
```

### 3. Hacer tu Trabajo

```powershell
# Edita los archivos necesarios
# Prueba constantemente

# Ver cambios
git status

# Ver diferencias
git diff
```

### 4. Ejecutar Tests Regularmente

```powershell
# Después de cada cambio importante
python -m pytest pdf_editor/tests/ -v

# Solo un archivo de tests
python -m pytest pdf_editor/tests/test_pdf_editor.py -v

# Con cobertura (si quieres)
python -m pytest pdf_editor/tests/ --cov=pdf_editor
```

### 5. Commit con Mensajes Claros

```powershell
# Ver cambios antes de hacer commit
git status
git diff pdf_editor/core/pdf_handler.py  # para un archivo específico

# Hacer commit
git add pdf_editor/core/pdf_handler.py
git commit -m "Arreglar: Mejor manejo de PDFs dañados en pdf_handler"

# O múltiples archivos
git add pdf_editor/
git commit -m "Feature: Añadir soporte para PDFs comprimidos

- Implementada detección de compresión
- Descompresión automática
- Tests añadidos (3 casos nuevos)
"
```

### 6. Merge a Main (después de probar)

```powershell
# Cambiar a main
git checkout main

# Asegurarse que main está actualizado
git pull origin main

# Merge tu rama
git merge feature/nombre-caracteristica

# O squash los commits si hiciste muchos cambios pequeños
git merge --squash feature/nombre-caracteristica
git commit -m "Feature: Descripción completa del cambio"
```

### 7. Crear Tag si es una Versión Release

```powershell
# Para una nueva versión
git tag -a v1.0.1 -m "v1.0.1: Arreglos de bugs menores"

# Ver todos los tags
git tag -l

# Eliminar tag si cometiste error
git tag -d v1.0.1
```

## 📊 Comandos Útiles de Git

### Ver Historial

```powershell
# Últimos commits
git log --oneline -10

# Todos los commits desde v1.0.0
git log v1.0.0-stable..HEAD

# Commits de un archivo
git log --oneline pdf_editor/core/pdf_handler.py

# Ver gráfico de ramas
git log --graph --oneline --all
```

### Comparar Versiones

```powershell
# Diferencias entre esta rama y main
git diff main

# Diferencias entre esta rama y la versión estable
git diff v1.0.0-stable

# Diferencias de un archivo específico
git diff v1.0.0-stable -- pdf_editor/core/pdf_handler.py

# Cambios en staging
git diff --cached
```

### Deshacer Cambios

```powershell
# Descartar cambios locales en un archivo
git checkout -- pdf_editor/core/pdf_handler.py

# Descartar todos los cambios no staged
git checkout -- .

# Volver a un commit anterior (crea nuevo commit)
git revert abc1234

# Ir a un commit anterior (borra historia)
git reset --hard abc1234

# Recuperar cambios borrados
git reflog  # encuentra el commit
git reset --hard abc1234
```

### Limpiar

```powershell
# Ver ramas locales
git branch -a

# Eliminar rama local
git branch -d feature/nombre-caracteristica

# Eliminar rama remota
git push origin --delete feature/nombre-caracteristica

# Limpiar branches borradas remotamente
git fetch --prune
```

## 🧪 Testing workflow

### Antes de Hacer Commit

```powershell
# 1. Ejecutar todos los tests
python -m pytest pdf_editor/tests/ -v

# 2. Verificar que obtuviste los mismos números que en v1.0.0
# Esperado: 46 passed, 1 warning

# 3. Si un test falla, arreglarlo antes de commitear
# Si es un bug en el test, actualizar el test
# Si es un bug en el código, arreglar el código

# 4. Solo después que TODO pase, hacer commit
git add .
git commit -m "..."
```

### Después de Merge a Main

```powershell
# 1. Cambiar a main
git checkout main

# 2. Ejecutar tests nuevamente para confirmar
python -m pytest pdf_editor/tests/ -v

# 3. Verificar que la app funciona
python pdf_editor/main.py

# 4. Si todo está bien, puedes eliminar la rama de trabajo
git branch -d feature/nombre-caracteristica
```

## 🚨 Recuperarse de Problemas

### Si Hiciste Commit pero No Deberías

```powershell
# Último commit fue un error
git reset --soft HEAD~1
# Ahora puedes re-hacer el commit sin los cambios

# O deshacer completamente
git reset --hard HEAD~1
```

### Si Mergeaste a Main Incorrectamente

```powershell
# Volver main al estado anterior
git reset --hard v1.0.0-stable

# O hacer un revert (más seguro si ya compartiste)
git revert HEAD~1  # revierte el merge
```

### Si Borraste una Rama Pero la Necesitabas

```powershell
# Ver todos los commits recientes (incluso borrados)
git reflog

# Recuperar la rama
git checkout -b feature/nombre-recuperada abc1234
```

## 📝 Plantillas de Commit Recomendadas

### Para Bugs

```text
Arreglar: Descripción breve del bug

- Qué estaba mal
- Cómo se arregló
- Tests añadidos (si corresponde)

Closes #123 (si tienes un issue tracker)
```

### Para Características Nuevas

```text
Feature: Descripción de la nueva característica

- Primer aspecto implementado
- Segundo aspecto implementado
- Tercero aspecto

Tests: Añadidos X tests nuevos
```

### Para Refactorización

```text
Refactor: Descripción del cambio estructural

Cambios principales:
- Reorganizada la estructura de X
- Mejorada la claridad de Y
- Eliminado código duplicado en Z

Tests: Todos los 46 tests siguen pasando
```

### Para Documentación

```text
Docs: Actualizada documentación de X

- Añadido ejemplo de uso
- Clarificado comportamiento de Y
- Actualizado README
```

## ✅ Checklist Pre-Push

Antes de hacer push a un servidor remoto:

- [ ] Todos los tests pasan (46/46)
- [ ] No hay cambios sin commitear (`git status` limpio)
- [ ] Commit message es descriptivo
- [ ] La app funciona sin errores
- [ ] Se probó el cambio manualmente
- [ ] Se consideraron casos límite
- [ ] No hay prints de debug (`print()`, `console.log()`)
- [ ] Se siguieron las convenciones del código

## 🎯 Resumen Rápido

| Tarea | Comando |
| --- | --- |
| Ver status | `git status` |
| Ver cambios | `git diff` |
| Crear rama | `git checkout -b nombre` |
| Hacer commit | `git commit -m "mensaje"` |
| Cambiar a main | `git checkout main` |
| Merge rama | `git merge nombre` |
| Ver historial | `git log --oneline` |
| Ir a versión estable | `git checkout v1.0.0-stable` |
| Ejecutar tests | `pytest pdf_editor/tests/ -v` |
| Recuperar cambios | `git reflog` + `git reset` |

---

**Recuerda**: Esta versión (v1.0.0) es tu punto de referencia. Siempre puedes volver a ella si algo se rompe.
