# 📘 Manual de Usuario - PDF Editor Pro

> La herramienta profesional para editar y organizar tus documentos PDF

---

## 📥 Instalación

### Paso 1: Descargar e instalar

Descarga el instalador `ModificadorPDF_Setup_v1.0.0.exe` y ejecútalo.

![Icono de la aplicación](capturas/icono%20de%20la%20descarga.png)

### Paso 2: Aviso de Windows SmartScreen

Al ejecutar por primera vez, Windows mostrará un aviso de seguridad. Esto es normal para aplicaciones nuevas sin certificado digital.

![Aviso de SmartScreen](capturas/primer%20mensaje%20de%20seguridad.png)

**¿Qué hacer?**

1. Haz clic en **"Más información"**
2. Aparecerá el botón **"Ejecutar de todas formas"**
3. Haz clic en él para continuar

![SmartScreen - Ejecutar de todas formas](capturas/segundo%20mensaje%20de%20adbertencia.png)

> ⚠️ **Nota:** Este aviso aparece porque la aplicación no tiene un certificado de firma digital (costoso). El software es completamente seguro.

---

## 🖥️ Interfaz Principal

Al abrir la aplicación, verás la pantalla de bienvenida:

![Pantalla de inicio](capturas/01_inicio.png.png)

### Elementos de la interfaz

| Zona | Descripción |
| --- | --- |
| **Barra superior** | Todas las herramientas y acciones disponibles |
| **Área central** | Zona de arrastrar y soltar PDFs |
| **Barra inferior** | Información de estado y zoom |

---

## 📂 Abrir Archivos

### Dos formas de trabajar

Haz clic en **"Abrir"** en la barra de herramientas. Aparecerá un diálogo con dos opciones:

![Diálogo de opciones](capturas/se%20puede%20subir%20un%20%20pdf%20suelto%20o%20un%20grupo%20de%20pdf.png)

| Opción | Cuándo usarla |
| --- | --- |
| **📄 Abrir UN PDF para editar** | Cuando solo necesitas modificar un archivo |
| **📁 Crear GRUPO DE TRABAJO** | Cuando tienes varios PDFs que procesar en lote |

---

## 🔵 MODO 1: Archivo Individual

### Abrir y editar un solo PDF

1. Selecciona **"Abrir UN PDF para editar"**
2. Elige tu archivo en el explorador
3. El PDF se cargará en el visor principal

![PDF abierto en el editor](capturas/al%20abrir%20el%20archivo.png)

### Panel de páginas

A la izquierda verás las miniaturas de todas las páginas del documento. Haz clic en cualquiera para navegar.

---

## 🛠️ Herramientas de Edición

### 🗑️ ELIMINAR - Borrar contenido

Selecciona esta herramienta (resaltada en azul) y arrastra sobre el área que quieres eliminar. El contenido se borrará permanentemente del PDF.

![Herramienta Eliminar](capturas/elimina%20remarca%20lo%20que%20quieres%20eliminar.png)

### ✏️ EDITAR - Modificar texto

1. Haz clic en **"EDITAR"** en la barra
2. Haz clic sobre cualquier texto del documento
3. Aparecerá el diálogo de edición:

![Diálogo de edición de texto](capturas/Al%20editar,%20haciendo%20clic%20en%20el%20texto,%20puedes%20cambiar%20el%20tamaño%20y%20mover%20el%20contenido%20por%20la%20página.png)

**Opciones disponibles:**

* Cambiar el contenido del texto
* Ajustar el tamaño (en puntos)
* Aplicar negrita

### 🖍️ RESALTAR - Marcar texto

Selecciona texto y se resaltará en amarillo, como un subrayador:

![Texto resaltado](capturas/resaltar.png)

---

## 💾 Guardar Cambios

Cuando hayas terminado de editar, haz clic en **"Guardar"** o pulsa `Ctrl+S`.

---

## 🟢 MODO 2: Grupo de Trabajo (Varios PDFs)

### ¿Para qué sirve?

Si tienes **muchos PDFs** que necesitan el mismo tratamiento (por ejemplo, eliminar un logo de 50 documentos), el **Grupo de Trabajo** te permite:

* Procesarlos uno a uno de forma ordenada
* Organizar automáticamente los archivos
* Mantener siempre una copia de seguridad del original

### Paso 1: Crear el Grupo

1. Haz clic en **"Abrir"** → **"Crear GRUPO DE TRABAJO"**
2. Selecciona varios archivos PDF
3. Aparecerá el diálogo de configuración:

![Crear Grupo de Trabajo](capturas/al%20crear%20un%20grupo%20de%20pdf.png)

### Paso 2: Elegir ubicación

Por defecto, el grupo se creará en tu carpeta de Descargas. Puedes cambiar la ubicación haciendo clic en **"Cambiar Ubicación"**:

![Cambiar ubicación del grupo](capturas/canbiar%20de%20ubicacion.PNG)

### Paso 3: Entender la estructura

Al crear el grupo, se generan **3 carpetas automáticamente**:

![Estructura de carpetas](capturas/dentro%20de%20la%20carpeta%20principal%20se%20crearan%20tres%20carpetas.png)

| Carpeta | Contenido |
| --- | --- |
| 📁 **Origen** | PDFs pendientes de procesar |
| 📁 **Modificado - Sí** | PDFs ya editados y guardados |
| 📁 **Modificado - No** | Copia de seguridad de los originales |

---

## 🔄 Flujo de Trabajo Automático

### ¿Qué pasa cuando guardas?

Cada vez que editas un PDF y lo guardas, el sistema organiza automáticamente:

![Flujo de guardado](capturas/Al%20guardar%20dentro%20del%20grupo%20de%20trabajo,%20se%20te%20indicará%20en%20todo%20momento%20cómo%20se%20distribuye%20tu%20archivo%20modificado%20y,%20cuando%20pulses%20Abrir,%20se%20abrirá%20el%20siguiente%20PDF.PNG)

1. ❌ **ORIGEN** → El archivo pendiente se **elimina** de esta carpeta
2. ✅ **MODIFICADO - SÍ** → Se guarda el archivo **editado** (nuevo)
3. 📦 **MODIFICADO - NO** → Se guarda el archivo **original** (backup)

### Continuar con el siguiente

Después de guardar, puedes hacer clic en **"Abrir siguiente (X pendientes)"** para continuar con el próximo PDF de la cola.

---

## ✅ Grupo Completado

Cuando hayas procesado todos los PDFs del grupo, verás:

![Grupo completado](capturas/cuando%20termina.png)

* **Pendientes: 0** → No quedan archivos por procesar
* **Modificados: 3** → Total de archivos editados
* **Archivados: 3** → Total de copias de seguridad

### Vista detallada del grupo

Puedes ver el estado completo de las 3 carpetas en cualquier momento:

![Vista completa del grupo](capturas/terminas%20todo%20el%20grupo%20de%20pdf.png)

Esta vista te permite:

* Ver qué archivos hay en cada carpeta
* Abrir cualquier carpeta directamente
* Continuar procesando si quedan pendientes

---

## ⌨️ Atajos de Teclado

| Atajo | Acción |
| --- | --- |
| `Ctrl + O` | Abrir archivo |
| `Ctrl + S` | Guardar cambios |
| `Ctrl + Shift + S` | Guardar como... |
| `Ctrl + W` | Cerrar PDF actual |
| `Ctrl + Z` | Deshacer |
| `Ctrl + Y` | Rehacer |
| `Ctrl + +` | Acercar zoom |
| `Ctrl + -` | Alejar zoom |

---

## ❓ Preguntas Frecuentes

### ¿Por qué Windows dice que la aplicación es desconocida?

Es normal. Las aplicaciones nuevas sin certificado digital (que cuesta dinero) muestran este aviso. Simplemente haz clic en "Más información" y luego "Ejecutar de todas formas".

### ¿Puedo recuperar un archivo original después de editarlo?

¡Sí! Si usaste un **Grupo de Trabajo**, el original siempre está en la carpeta **"Modificado - No"**.

### ¿Qué pasa si cierro sin guardar?

La aplicación te preguntará si quieres guardar los cambios antes de cerrar.

### ¿Puedo editar PDFs protegidos con contraseña?

Sí, el programa te pedirá la contraseña al abrir el archivo.

---

## 📞 Soporte

Si tienes problemas o sugerencias, puedes contactar a través del repositorio del proyecto en GitHub.

---

PDF Editor Pro v1.0.0 - Desarrollado con ❤️
