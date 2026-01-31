# 📦 Guía de Instalación y Actualizaciones

## Información sobre la Actualización v1.0.0 → v1.0.1

### Cambios incluidos en v1.0.1
- ✅ Refactor de imágenes en manual web (nombres limpios, URLs sin espacios)
- ✅ Actualización de referencias en HTML
- ✅ Mejora de accesibilidad en alt text
- ✅ Documentación mejorada
- ✅ Rendimiento estable

---

## ❓ Preguntas Frecuentes: Actualización de Versiones

### P: ¿Necesito desinstalar v1.0.0 antes de instalar v1.0.1?

**R: Depende del tipo de instalación:**

#### 1. **Si tienes la versión INSTALADA (ModificadorPDF_Setup_v1.0.0.exe)**

**Opción A - Recomendado (Sin desinstalar)**
```
1. Ejecuta directamente: ModificadorPDF_Setup_v1.0.1.exe
2. El instalador detectará la versión anterior
3. Selecciona "Reparar" o "Actualizar"
4. El instalador preservará:
   - Archivo guardados
   - Configuración del usuario
   - Grupos de trabajo creados
5. Listo - ¡Sin perder nada!
```

**Opción B - Más segura (Con desinstalación)**
```
1. Panel de Control → Programas → Desinstalar un programa
2. Busca "Modificador de PDF" o "PDF Editor Pro"
3. Haz clic en Desinstalar
4. Selecciona "Sí" cuando se te pida confirmación
5. El instalador preservará:
   - Archivos en carpetas de usuario
   - Documentos del sistema
6. Instala ModificadorPDF_Setup_v1.0.1.exe
```

**Opción C - Limpia (Desinstalación completa)**
```
1. Desinstala como en Opción B
2. Busca y elimina manualmente (si deseas):
   - C:\Users\[TuUsuario]\AppData\Local\Modificador PDF
   - C:\Users\[TuUsuario]\AppData\Roaming\PDF Editor
3. Vacía la papelera de reciclaje
4. Instala ModificadorPDF_Setup_v1.0.1.exe (instalación fresca)
```

#### 2. **Si tienes la versión PORTABLE (ModificadorPDF_v1.0.0_portable.exe)**

**Opción A - Recomendado (Simplemente reemplazar)**
```
1. Descarga ModificadorPDF_v1.0.1_portable.exe
2. Copia el nuevo ejecutable a la carpeta donde tenías el v1.0.0
3. ANTES de borrar, copia cualquier carpeta importante:
   - workspace/ (tus grupos de trabajo)
   - Documents/ (archivos guardados)
4. Borra ModificadorPDF_v1.0.0_portable.exe
5. ¡Usa el nuevo v1.0.1!
```

**Opción B - Ultra-segura (Mantener ambas versiones)**
```
1. Crea dos carpetas separadas:
   - Carpeta_v1.0.0/
   - Carpeta_v1.0.1/
2. Coloca cada ejecutable en su carpeta respectiva
3. Esto permite volver atrás si es necesario
4. Nota: Ocuparán ~300-400 MB cada una
```

---

## ✅ Validación Post-Instalación

Después de instalar v1.0.1, verifica:

### 1. **Versión Correcta**
```
Abre la aplicación → Menú (≡) → Acerca de
Debe mostrar: "PDF Editor Pro v1.0.1"
```

### 2. **Archivos Recuperados**
```
Si tenías archivos guardados o grupos de trabajo:
- ✓ Deben estar disponibles en la aplicación
- ✓ Las rutas deben ser accesibles
- ✓ No debe haber mensajes de error
```

### 3. **Funcionalidad Básica**
```
1. Abre un PDF
2. Edita contenido (text, highlight, delete)
3. Guarda los cambios
4. Crea un grupo de trabajo
5. Procesa múltiples PDFs
```

### 4. **Windows SmartScreen**
```
Si aparece aviso:
1. Haz clic en "Más información"
2. Luego en "Ejecutar de todas formas"
3. En futuras ejecuciones NO debería aparecer
```

---

## 🔄 Comparación: Instalada vs Portable

| Aspecto | Versión Instalada | Versión Portable |
|--------|-------------------|------------------|
| **Instalación** | Requiere permisos de admin | Sin instalación necesaria |
| **Ubicación** | `C:\Program Files\...` | Donde descargues el .exe |
| **Actualización** | Auto-detección de versión | Manual (descargar nuevo .exe) |
| **Espacio usado** | ~350 MB en disco | ~350 MB (archivo único) |
| **Archivos guardados** | `AppData\Roaming\...` | Carpeta del .exe |
| **Desinstalación** | Panel de Control | Solo borrar el .exe |
| **Portabilidad** | Solo en este PC | Llévalo en USB a cualquier lado |
| **Permisos de archivo** | Más restricciones | Acceso más directo |

### 📌 **Recomendación:**
- **Usuarios comunes** → Versión instalada (más fácil de actualizar)
- **Power users / USB portable** → Versión portable (más flexible)

---

## 🐧 Instalación en macOS

### Versión Instalada (.dmg)
```bash
1. Descarga ModificadorPDF_v1.0.1.dmg
2. Doble clic para montar
3. Arrastra "PDF Editor Pro" a "Aplicaciones"
4. Automáticamente actualizará si ya existe
```

### Versión Portable (.app)
```bash
1. Descarga PDF_Editor_Pro_v1.0.1_portable.app.zip
2. Descomprime con doble clic
3. Mueve a la carpeta donde quieras (Desktop, ~/Applications, USB, etc.)
4. Doble clic para ejecutar
5. Si macOS lo bloquea: 
   - Control (o cmd) + clic en el .app
   - Selecciona "Abrir"
```

### ⚠️ Aviso de Gatekeeper en macOS
```
Si ves: "No se puede verificar el desarrollador"

Solución:
1. Abre Preferencias del Sistema → Seguridad y Privacidad
2. Busca la aplicación bloqueada
3. Haz clic en "Permitir de todas formas"
4. En futuras ejecuciones NO aparecerá el aviso
```

---

## 🔧 Comparación de Comportamiento v1.0.0 vs v1.0.1

| Función | v1.0.0 | v1.0.1 | Cambio |
|---------|--------|--------|--------|
| **Edición de PDF** | ✓ | ✓ | Idéntico |
| **Eliminación de contenido** | ✓ | ✓ | Idéntico |
| **Resaltado** | ✓ | ✓ | Idéntico |
| **Grupos de trabajo** | ✓ | ✓ | Idéntico |
| **Manual web** | Con espacios en URLs | URLs limpias | ⬆️ Mejorado |
| **Accesibilidad** | Básica | Mejorada | ⬆️ Mejorado |
| **Rendimiento** | Estable | Estable | ✅ Mantiene |
| **Compatibilidad** | Windows/macOS | Windows/macOS | ✅ Igual |

---

## 📋 Checklist de Actualización

### Antes de actualizar
- [ ] Backup de archivos importantes (opcional pero recomendado)
- [ ] Nota los grupos de trabajo que tienes creados
- [ ] Cierra la aplicación v1.0.0

### Durante la instalación
- [ ] Ejecuta el instalador con permisos de administrador
- [ ] Permite que complete la instalación
- [ ] NO interrumpas el proceso

### Después de instalar
- [ ] Abre la aplicación
- [ ] Verifica que aparezca v1.0.1
- [ ] Abre un PDF de prueba
- [ ] Verifica que tus grupos de trabajo sigan ahí
- [ ] Prueba editar, eliminar y resaltar

### Troubleshooting
- Si no ves tus archivos → Busca en `C:\Users\[Usuario]\AppData\Roaming\PDF Editor`
- Si falla al abrir PDF → Intenta con otro PDF más pequeño
- Si sigue fallando → Reinstala desde cero (Opción C arriba)

---

## 💾 Backup y Recuperación

### Dónde están mis archivos guardados

**Windows:**
```
- Archivos editados: Donde los guardaste (Desktop, Documents, etc.)
- Configuración: C:\Users\[Usuario]\AppData\Roaming\PDF Editor\
- Grupos de trabajo: C:\Users\[Usuario]\Documents\PDF_Editor_Workspace\
```

**macOS:**
```
- Archivos editados: Donde los guardaste
- Configuración: ~/Library/Application Support/PDF Editor/
- Grupos de trabajo: ~/Documents/PDF_Editor_Workspace/
```

### Hacer backup antes de actualizar
```powershell
# Windows PowerShell
Copy-Item -Path "$env:APPDATA\PDF Editor" -Destination "D:\Backup_PDF_Editor" -Recurse
Copy-Item -Path "$env:USERPROFILE\Documents\PDF_Editor_Workspace" -Destination "D:\Backup_Workspace" -Recurse
```

```bash
# macOS Terminal
cp -r ~/Library/Application\ Support/PDF\ Editor ~/Desktop/Backup_PDF_Editor
cp -r ~/Documents/PDF_Editor_Workspace ~/Desktop/Backup_Workspace
```

---

## ❌ Si Algo Sale Mal

### Problema: "El archivo está corrupto"
```
1. Desinstala v1.0.1
2. Ejecuta el archivo instalador nuevamente
3. Si sigue fallando, descarga de nuevo desde la fuente original
```

### Problema: "No puedo abrir PDFs que antes funcionaban"
```
1. Intenta con un PDF diferente
2. Si solo ese PDF falla, es un problema del archivo, no de la app
3. Si todos fallan: Reinstala (Opción C arriba)
```

### Problema: "Quiero volver a v1.0.0"
```
Windows:
1. Control Panel → Programas → Desinstalar
2. Busca "Modificador de PDF"
3. Desinstala
4. Descarga e instala ModificadorPDF_Setup_v1.0.0.exe

macOS:
1. Abre Finder → Aplicaciones
2. Arrastra "PDF Editor Pro" a la papelera
3. Vaciala
4. Descarga e instala la v1.0.0 .dmg
```

---

## 📞 Resumen Rápido

```
La recomendación general es:
✓ NO necesitas desinstalar la v1.0.0 antes de instalar la v1.0.1
✓ Simplemente ejecuta el nuevo instalador
✓ Tus archivos y configuración se preservarán automáticamente
✓ La actualización es segura y reversible
```

---

**Última actualización**: 31 de enero de 2026  
**Versiones cubiertas**: v1.0.0 → v1.0.1  
**Plataformas**: Windows 10/11, macOS 10.13+
