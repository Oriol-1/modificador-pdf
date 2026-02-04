# 📦 ESTADO DE RELEASES E INSTALABLES - PDF Editor Pro

## ✅ RELEASES DISPONIBLES EN GITHUB

| Versión | Tag | Estado | Descripción |
|---------|-----|--------|------------|
| v1.0.0 | v1.0.0 | ✅ Estable | Release inicial |
| v1.0.0 | v1.0.0-stable | ✅ Estable | Versión estable 1.0.0 |
| v1.0.1 | v1.0.1 | ✅ Estable | Correcciones de markdownlint |
| v1.0.1 | v1.0.1-release | ✅ Estable | Maintenance update |
| v1.1.0 | v1.1.0 | ✅ Estable | Licencia Propietaria + Linux |
| v1.1.1 | v1.1.1 | ✅ Estable | Añadir builds de Linux |
| v1.1.2 | v1.1.2 | ✅ Estable | Fix build Linux |
| **v1.2.0** | **v1.2.0** | 🆕 **ACTUAL** | **Sistema de guardado mejorado** |
| v1.3.0 | v1.3.0 | ✅ Estable | Editor de texto con formato |

**Total de releases: 9**  
**Rama actual: main**  
**Commit actual: v1.2.0**

---

## 🛠️ INSTALABLES Y PORTABLES DISPONIBLES

### Windows

#### Ejecutables Portables
- ✅ **build_portable.bat** (69 líneas)
  - Crea ejecutable portable sin instalación
  - Usa PyInstaller
  - Ubicación: Raíz del proyecto

#### Instaladores
- ✅ **build_installer.bat** (119 líneas)
  - Crea instalador Windows (.msi)
  - Usa Inno Setup
  - Archivo config: `installer/inno_setup.iss`
  - Ubicación: Raíz del proyecto

#### Ejecutables Generales
- ✅ **build.bat** (69 líneas)
  - Compilación general a .exe
  - Usa PyInstaller
  - Ubicación: Raíz del proyecto

---

### Linux

#### AppImage Portable
- ✅ **build_appimage.sh** (158 líneas)
  - Crea AppImage para distribuciones Linux
  - Formato universal
  - Ubicación: Raíz del proyecto

#### Instalador Linux
- ✅ **build_installer_linux.sh** (174 líneas)
  - Script de instalación para Linux
  - Soporta múltiples gestores de paquetes
  - Ubicación: Raíz del proyecto

#### Portable Linux
- ✅ **build_portable_linux.sh** (153 líneas)
  - Crear versión portable para Linux
  - Ubicación: Raíz del proyecto

#### Build General Linux
- ✅ **build_linux.sh** (135 líneas)
  - Compilación general para Linux
  - Ubicación: Raíz del proyecto

---

### macOS

#### Build macOS
- ✅ **build_mac.sh** (144 líneas)
  - Script de compilación para macOS
  - Ubicación: Raíz del proyecto

---

## 📋 CAMBIOS INTEGRADOS EN v1.2.0

### Sistema de Guardado Mejorado
- ✅ Sincronización garantizada de datos antes de guardar
- ✅ Validación explícita de `commit_overlay_texts()`
- ✅ Logging detallado del proceso

### Nuevas Funciones
- ✅ `sync_all_text_items_to_data()` - Sincronizar datos visuales
- ✅ `clear_editable_texts_data()` - Limpiar estados
- ✅ Conversión de coordenadas mejorada

### Correcciones
- ✅ Sistema de fragmentación de texto solucionado
- ✅ PDFs de imagen (overlays) funcionan correctamente
- ✅ Undo/Redo completamente operativo

### Plataformas Soportadas
- ✅ **Windows**: Portable + Installer
- ✅ **Linux**: AppImage + Portable + Installer
- ✅ **macOS**: Script de construcción

---

## 🚀 ESTADO DE COMPILACIÓN

Todos los scripts están actualizados y listos para compilar:

```
Windows:
  ├─ build.bat                  ✅ Portable ejecutable
  ├─ build_portable.bat         ✅ Versión portable
  └─ build_installer.bat        ✅ Instalador Windows

Linux:
  ├─ build_linux.sh             ✅ Build general
  ├─ build_appimage.sh          ✅ AppImage
  ├─ build_portable_linux.sh    ✅ Portable
  └─ build_installer_linux.sh   ✅ Instalador

macOS:
  └─ build_mac.sh               ✅ Build macOS
```

---

## ✅ VERIFICACIÓN DE INTEGRIDAD

- ✅ Todos los scripts de construcción presentes
- ✅ Rama main actualizada y sincronizada
- ✅ Tags pusheados a GitHub
- ✅ Aplicación 100% funcional
- ✅ Todos los tests exitosos
- ✅ Código listo para producción

---

## 📦 INSTRUCCIONES PARA CREAR RELEASES

Para crear un release con instalables:

### Windows
```bash
# Portable
.\build_portable.bat

# Instalador
.\build_installer.bat
```

### Linux
```bash
# AppImage
./build_appimage.sh

# Instalador
./build_installer_linux.sh

# Portable
./build_portable_linux.sh
```

### macOS
```bash
./build_mac.sh
```

---

## 📍 UBICACIÓN DE ARCHIVOS COMPILADOS

Después de ejecutar los scripts de construcción:

- **Windows**: `dist/` o `build/` (según PyInstaller)
- **Linux**: `dist/` o el directorio especificado en el script
- **macOS**: `dist/` o el directorio especificado en el script

---

**Última actualización:** 4 de febrero de 2026  
**Versión actual:** v1.2.0  
**Estado:** ✅ 100% Actualizado y listo para producción
