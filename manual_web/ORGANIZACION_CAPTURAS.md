# 📷 Guía de Organización de Capturas

## Estructura de carpetas

Crea una subcarpeta `capturas/` dentro de `manual_web/`:

```text
manual_web/
├── MANUAL_VISUAL.md
├── GUIA_CAPTURAS.md
├── capturas/
│   ├── 01_icono_escritorio.png
│   ├── 02_smartscreen_aviso.png
│   ├── 03_smartscreen_ejecutar.png
│   ├── ... (resto de imágenes)
```

---

## 📋 Tabla de correspondencia: Tu captura → Nombre del archivo

Basándome en las imágenes que me has enviado, aquí tienes exactamente cómo nombrar cada una:

| Orden | Tu captura (descripción) | Nombre del archivo |
| --- | --- | --- |
| 1 | Icono pequeño del escritorio "Modificador de PDF" | `01_icono_escritorio.png` |
| 2 | Aviso SmartScreen (solo botón "No ejecutar") | `02_smartscreen_aviso.png` |
| 3 | Aviso SmartScreen (con "Ejecutar de todas formas") | `03_smartscreen_ejecutar.png` |
| 4 | Pantalla inicio "Arrastra un PDF aquí" completa | `04_pantalla_inicio.png` |
| 5 | Recorte del botón "Abrir" y panel izquierdo | `05_boton_abrir.png` |
| 6 | Diálogo "¿Qué deseas hacer?" (2 opciones) | `06_dialogo_opciones.png` |
| 7 | Interfaz con PDF abierto + tooltip "Guardar cambios" | `07_interfaz_pdf_abierto.png` |
| 8 | Diálogo "Editar texto" con campo de contenido | `08_editar_texto.png` |
| 9 | PDF con texto resaltado en amarillo "Hola Mundo" | `09_resaltar_texto.png` |
| 10 | Diálogo "Crear Grupo de Trabajo con 3 PDFs" | `10_crear_grupo.png` |
| 11 | Mismo diálogo pero con flecha roja señalando "Cambiar Ubicación" | `11_cambiar_ubicacion.png` |
| 12 | Explorador Windows con carpetas (Modificado-No, Modificado-Sí, Origen) | `12_estructura_carpetas.png` |
| 13 | Diálogo "Guardado Exitoso" con flechas rojas explicando flujo | `13_guardado_exitoso.png` |
| 14 | Diálogo "Guardado Exitoso" final (Pendientes: 0, Modificados: 3) | `14_grupo_completado.png` |
| 15 | Vista grande con las 3 columnas (ORIGEN, MODIFICADO-SÍ, MODIFICADO-NO) | `15_vista_grupo_completo.png` |

---

## ✅ Checklist de capturas

Marca cada una cuando la hayas renombrado y guardado:

- [ ] `01_icono_escritorio.png`
- [ ] `02_smartscreen_aviso.png`
- [ ] `03_smartscreen_ejecutar.png`
- [ ] `04_pantalla_inicio.png`
- [ ] `05_boton_abrir.png`
- [ ] `06_dialogo_opciones.png`
- [ ] `07_interfaz_pdf_abierto.png`
- [ ] `08_editar_texto.png`
- [ ] `09_resaltar_texto.png`
- [ ] `10_crear_grupo.png`
- [ ] `11_cambiar_ubicacion.png`
- [ ] `12_estructura_carpetas.png`
- [ ] `13_guardado_exitoso.png`
- [ ] `14_grupo_completado.png`
- [ ] `15_vista_grupo_completo.png`

---

## 🎯 Capturas adicionales recomendadas (opcionales)

Si quieres un manual aún más completo, podrías añadir:

| Descripción | Nombre sugerido |
| --- | --- |
| Herramienta ELIMINAR activa borrando contenido | `16_eliminar_contenido.png` |
| Diálogo de confirmación antes de borrar | `17_confirmar_borrado.png` |
| Menú Archivo desplegado | `18_menu_archivo.png` |
| Zoom al 200% mostrando detalle | `19_zoom_detalle.png` |

---

## 📝 Instrucciones para guardar

1. **Abre cada captura** que hiciste con `Win+Shift+S`
2. **Pégala en Paint** (`Ctrl+V`)
3. **Guarda como PNG** en `manual_web/capturas/` con el nombre correspondiente
4. Repite hasta completar las 15 capturas

---

## 🌐 Publicación web

Una vez tengas todas las imágenes, el archivo `MANUAL_VISUAL.md` estará listo para:

- Subir a GitHub (se renderiza automáticamente)
- Convertir a HTML con herramientas como Pandoc o mkdocs
- Usar en tu página web de descarga

¿Necesitas ayuda con algún paso adicional?
