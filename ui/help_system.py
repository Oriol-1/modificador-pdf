"""
Sistema de ayuda integrado para PDF Editor Pro.
Proporciona acceso contextual al manual de usuario.
"""

import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextBrowser, QSplitter,
    QFrame, QWidget
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

from ui.theme_manager import ThemeColor


# URL base del manual online (GitHub Pages)
MANUAL_URL = "https://oriol-1.github.io/modificador-pdf/"

# Ruta a las imágenes de ayuda
import os
HELP_IMAGES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "help_images")

# Contador para IDs únicos de imágenes
_img_counter = [0]

def get_img(name, caption=""):
    """Genera tag HTML para imagen compacta con enlace para ampliar."""
    path = os.path.join(HELP_IMAGES_PATH, name).replace("\\", "/")
    file_url = f"file:///{path}"
    cap_text = f"{caption} " if caption else ""
    return f'''<div style="text-align:center; margin:20px 0; padding:15px; background:#252526; border-radius:8px;">
        <a href="{file_url}"><img src="{file_url}" style="max-width:300px; width:100%; border-radius:6px; border:2px solid #444;"></a>
        <p style="color:#888; font-size:12px; margin-top:8px;"><i>{cap_text}</i><a href="{file_url}" style="color:#0078d4;">🔍 Clic para ampliar</a></p>
    </div>'''

# Secciones de ayuda con contenido local
HELP_SECTIONS = {
    "inicio": {
        "title": "🏠 Inicio",
        "url": f"{MANUAL_URL}#-instalación",
        "content": lambda: f"""
<h2>🏠 Bienvenido a PDF Editor Pro</h2>

<p><b>PDF Editor Pro</b> es una herramienta profesional diseñada para modificar documentos PDF de forma rápida y sencilla. Con esta aplicación podrás realizar las tareas más comunes de edición sin necesidad de software costoso.</p>

{get_img("01_inicio.png", "Pantalla principal de la aplicación")}

<h3>🎯 ¿Qué puedes hacer con esta aplicación?</h3>

<p>La aplicación incluye <b>tres herramientas principales</b> ubicadas en la barra superior:</p>

<ul>
    <li><b>🗑️ ELIMINAR</b> - Permite borrar cualquier contenido del PDF: textos, imágenes, logos, marcas de agua, firmas no deseadas, etc. Simplemente selecciona el área y desaparecerá.</li>
    <li><b>✏️ EDITAR</b> - Modifica textos existentes en el documento. Puedes cambiar el contenido, ajustar el tamaño de letra o mover el texto a otra posición de la página.</li>
    <li><b>🖍️ Resaltar</b> - Marca texto importante con color amarillo fluorescente, ideal para destacar información relevante en contratos, informes o documentos de estudio.</li>
</ul>

<h3>📁 Modos de trabajo</h3>

<p>Puedes trabajar de dos formas diferentes según tus necesidades:</p>
<ol>
    <li><b>PDF Individual</b> - Abre y edita un solo documento cuando tienes una tarea puntual.</li>
    <li><b>Grupo de Trabajo</b> - Procesa múltiples PDFs en lote cuando tienes muchos documentos similares. El programa organiza automáticamente los archivos originales y modificados.</li>
</ol>

<h3>💡 Consejo inicial</h3>
<p>Para empezar, simplemente <b>arrastra un PDF</b> a la ventana de la aplicación, o pulsa <b>Ctrl+O</b> para abrir el menú de opciones.</p>
"""
    },
    "abrir": {
        "title": "📂 Abrir Archivos",
        "url": f"{MANUAL_URL}#-abrir-archivos",
        "content": lambda: f"""
<h2>📂 Abrir Archivos</h2>

<p>Al iniciar la aplicación o pulsar <b>Ctrl+O</b>, aparecerá un menú con dos opciones para trabajar con tus documentos PDF.</p>

{get_img("03_opciones_abrir.png", "Menú con las dos opciones disponibles")}

<h3>📄 Opción 1: Abrir UN PDF para editar</h3>

<p>Esta opción es ideal cuando necesitas <b>editar un solo documento</b>. Al seleccionarla:</p>
<ol>
    <li>Se abrirá el explorador de archivos de Windows</li>
    <li>Navega hasta la ubicación de tu PDF</li>
    <li>Selecciona el archivo y pulsa "Abrir"</li>
    <li>El documento se cargará en el editor listo para modificar</li>
</ol>

{get_img("02_pdf_abierto.png", "Documento PDF abierto en el editor")}

<p>Una vez abierto el PDF, verás el documento en el panel central. En la parte superior encontrarás las herramientas de edición (Eliminar, Editar, Resaltar) y en la parte inferior los controles de navegación entre páginas.</p>

<h3>📁 Opción 2: Crear GRUPO DE TRABAJO</h3>

<p>Esta opción está pensada para cuando tienes <b>muchos PDFs similares</b> que procesar (por ejemplo, facturas, contratos, formularios, etc.). El programa:</p>
<ul>
    <li>Te permite seleccionar múltiples archivos PDF a la vez</li>
    <li>Crea automáticamente una estructura de carpetas organizada</li>
    <li>Guarda copias de seguridad de los originales</li>
    <li>Te guía para procesar cada documento uno por uno</li>
</ul>

<p>Consulta la sección <b>"📁 Grupos de Trabajo"</b> en el menú lateral para ver todos los detalles de esta funcionalidad.</p>
"""
    },
    "eliminar": {
        "title": "🗑️ Eliminar Contenido",
        "url": f"{MANUAL_URL}#️-eliminar---borrar-contenido",
        "content": lambda: f"""
<h2>🗑️ Eliminar Contenido</h2>

<p>La herramienta <b>ELIMINAR</b> te permite borrar permanentemente cualquier elemento visible del PDF: textos, imágenes, logos, firmas, marcas de agua, tablas, gráficos... todo lo que esté dentro del área que selecciones será eliminado.</p>

{get_img("04_eliminar.png", "Selección del área a eliminar")}

<h3>📋 Cómo usar la herramienta:</h3>

<ol>
    <li><b>Activa la herramienta:</b> Haz clic en el botón <span style="background:#0078d4;color:white;padding:2px 8px;border-radius:3px;">ELIMINAR</span> de la barra superior. El botón se pondrá de color azul para indicar que está activo.</li>
    <li><b>Selecciona el área:</b> Posiciona el cursor en una esquina del contenido que quieres borrar. Mantén pulsado el botón izquierdo del ratón y <b>arrastra</b> hasta la esquina opuesta para crear un rectángulo de selección.</li>
    <li><b>Suelta el ratón:</b> Al soltar, todo el contenido dentro del rectángulo será eliminado inmediatamente.</li>
    <li><b>Repite si es necesario:</b> Puedes eliminar múltiples áreas del documento repitiendo el proceso.</li>
</ol>

<h3>⚠️ Información importante:</h3>

<ul>
    <li><b>Deshacer:</b> Si te equivocas, pulsa <b>Ctrl+Z</b> inmediatamente para deshacer la eliminación. Puedes deshacer múltiples acciones.</li>
    <li><b>Permanente al guardar:</b> Una vez que guardes el documento (<b>Ctrl+S</b>), los cambios serán permanentes y no se podrán recuperar.</li>
    <li><b>Copia de seguridad:</b> Si trabajas con Grupos de Trabajo, el programa guarda automáticamente el original antes de cualquier modificación.</li>
</ul>

<h3>💡 Casos de uso comunes:</h3>
<p>Borrar marcas de agua, eliminar logos de encabezados, quitar firmas antiguas, limpiar sellos, eliminar información personal de documentos, etc.</p>
"""
    },
    "editar": {
        "title": "✏️ Editar Texto",
        "url": f"{MANUAL_URL}#️-editar---modificar-texto",
        "content": lambda: f"""
<h2>✏️ Editar Texto</h2>

<p>La herramienta <b>EDITAR</b> permite modificar los textos existentes en el documento PDF. Puedes cambiar el contenido, ajustar el tamaño de la fuente o reposicionar el texto en otra ubicación de la página.</p>

{get_img("05_editar_texto.png", "Diálogo de edición de texto")}

<h3>📋 Cómo usar la herramienta:</h3>

<ol>
    <li><b>Activa la herramienta:</b> Haz clic en el botón <span style="background:#0078d4;color:white;padding:2px 8px;border-radius:3px;">EDITAR</span> de la barra superior.</li>
    <li><b>Selecciona el texto:</b> Haz clic directamente sobre cualquier texto del documento que quieras modificar.</li>
    <li><b>Aparecerá el diálogo de edición</b> con las siguientes opciones:
        <ul>
            <li><b>Campo de texto:</b> Muestra el contenido actual. Puedes borrarlo y escribir uno nuevo.</li>
            <li><b>Tamaño de fuente:</b> Ajusta el tamaño de la letra (en puntos).</li>
            <li><b>Posición X/Y:</b> Coordenadas para mover el texto a otra ubicación.</li>
        </ul>
    </li>
    <li><b>Aplica los cambios:</b> Pulsa <b>OK</b> para confirmar o <b>Cancelar</b> para descartar.</li>
</ol>

<h3>⚠️ Consideraciones:</h3>

<ul>
    <li><b>Fuentes:</b> El texto editado usará una fuente estándar. Si el PDF original usa fuentes especiales, el resultado puede variar ligeramente.</li>
    <li><b>Textos complejos:</b> Algunos PDFs tienen textos divididos en fragmentos pequeños. Si al hacer clic solo seleccionas parte del texto, intenta hacer clic en otra zona.</li>
    <li><b>Deshacer:</b> Usa <b>Ctrl+Z</b> si no quedas satisfecho con el cambio.</li>
</ul>

<h3>💡 Casos de uso comunes:</h3>
<p>Corregir errores tipográficos, actualizar fechas o números, cambiar nombres, modificar direcciones, actualizar precios en catálogos, etc.</p>
"""
    },
    "resaltar": {
        "title": "🖍️ Resaltar",
        "url": f"{MANUAL_URL}#️-resaltar---marcar-texto",
        "content": lambda: f"""
<h2>🖍️ Resaltar Texto</h2>

<p>La herramienta <b>Resaltar</b> permite marcar texto con un fondo amarillo fluorescente, similar a usar un subrayador físico. Es perfecta para destacar información importante en documentos.</p>

{get_img("06_resaltar.png", "Texto resaltado en amarillo")}

<h3>📋 Cómo usar la herramienta:</h3>

<ol>
    <li><b>Activa la herramienta:</b> Haz clic en el botón <span style="background:#ffc107;color:black;padding:2px 8px;border-radius:3px;">Resaltar</span> de la barra superior.</li>
    <li><b>Selecciona el texto:</b> Mantén pulsado el botón izquierdo del ratón y <b>arrastra</b> sobre el texto que quieres marcar.</li>
    <li><b>Suelta el ratón:</b> El texto quedará resaltado con fondo <span style="background-color:yellow;color:black;padding:2px 4px;">amarillo</span>.</li>
    <li><b>Repite:</b> Puedes resaltar múltiples secciones del documento.</li>
</ol>

<h3>✨ Características del resaltado:</h3>

<ul>
    <li>El color amarillo es semitransparente, permitiendo leer el texto debajo.</li>
    <li>El resaltado se mantiene al imprimir el documento.</li>
    <li>Puedes resaltar múltiples líneas arrastrando sobre varias de ellas.</li>
</ul>

<h3>💡 Casos de uso comunes:</h3>
<p>Marcar cláusulas importantes en contratos, destacar datos clave en informes, señalar información para revisar, resaltar respuestas en formularios, preparar documentos de estudio, etc.</p>

<h3>⚠️ Nota:</h3>
<p>Para eliminar un resaltado, usa la herramienta <b>ELIMINAR</b> seleccionando el área resaltada, y luego <b>Ctrl+Z</b> si también eliminaste texto por error.</p>
"""
    },
    "workspace": {
        "title": "📁 Grupos de Trabajo",
        "url": f"{MANUAL_URL}#-modo-2-grupo-de-trabajo-varios-pdfs",
        "content": lambda: f"""
<h2>📁 Sistema de Grupos de Trabajo</h2>

<p>El <b>Grupo de Trabajo</b> es una funcionalidad diseñada para cuando tienes <b>muchos documentos PDF</b> que procesar de forma similar. En lugar de abrir, editar, guardar y buscar el siguiente archivo manualmente, el programa automatiza todo el flujo de trabajo.</p>

<h3>1️⃣ Crear un nuevo grupo</h3>

<p>Para crear un grupo, pulsa <b>Ctrl+O</b> y selecciona <b>"Crear GRUPO DE TRABAJO"</b>. Se abrirá el explorador donde podrás seleccionar múltiples archivos PDF (mantén <b>Ctrl</b> pulsado para selección múltiple).</p>

{get_img("07_crear_grupo.png", "Selección de múltiples PDFs")}

<h3>2️⃣ Estructura automática de carpetas</h3>

<p>Al crear el grupo, el programa genera automáticamente <b>tres carpetas</b> para organizar tu trabajo:</p>

{get_img("09_carpetas.png", "Las tres carpetas creadas automáticamente")}

<ul>
    <li><b>📁 Origen</b> - Aquí se copian todos los PDFs pendientes de procesar. A medida que los editas, se van eliminando de esta carpeta.</li>
    <li><b>📁 Modificado - Sí</b> - Los PDFs ya editados se guardan aquí. Es tu carpeta de archivos finales.</li>
    <li><b>📁 Modificado - No</b> - Copias de seguridad de los originales. Si cometes un error, siempre tendrás el archivo original aquí.</li>
</ul>

<h3>3️⃣ Cambiar la ubicación</h3>

<p>Por defecto, las carpetas se crean en el mismo lugar donde están los PDFs originales. Si prefieres otra ubicación, usa el botón para cambiarla:</p>

{get_img("08_cambiar_ubicacion.png", "Opción para cambiar la ubicación")}

<h3>4️⃣ Flujo de trabajo al guardar</h3>

<p>Cuando terminas de editar un PDF y pulsas <b>Ctrl+S</b>, el sistema realiza automáticamente:</p>

{get_img("10_guardado_exitoso.png", "Confirmación de guardado exitoso")}

<ol>
    <li>Guarda el PDF modificado en la carpeta <b>"Modificado - Sí"</b></li>
    <li>Mueve el original a <b>"Modificado - No"</b> (copia de seguridad)</li>
    <li>Elimina el archivo de la carpeta <b>"Origen"</b></li>
    <li>Te pregunta si quieres <b>abrir el siguiente PDF</b> pendiente</li>
</ol>

<h3>5️⃣ Grupo completado</h3>

<p>Cuando hayas procesado todos los PDFs del grupo, verás un mensaje de confirmación:</p>

{get_img("11_grupo_completado.png", "Mensaje de grupo completado")}

<p>En este punto, todos tus archivos editados estarán en <b>"Modificado - Sí"</b> y tendrás copias de seguridad en <b>"Modificado - No"</b>.</p>
"""
    },
    "guardar": {
        "title": "💾 Guardar",
        "url": f"{MANUAL_URL}#-guardar-cambios",
        "content": lambda: f"""
<h2>💾 Guardar Cambios</h2>

<p>Después de realizar modificaciones en tu documento, es importante guardar los cambios. La aplicación ofrece dos opciones de guardado:</p>

<h3>⌨️ Opciones de guardado:</h3>

<table border="1" cellpadding="10" style="border-collapse:collapse; width:100%; margin:15px 0;">
    <tr style="background:#0078d4; color:white;">
        <th>Atajo</th>
        <th>Acción</th>
        <th>Descripción</th>
    </tr>
    <tr>
        <td><b>Ctrl+S</b></td>
        <td>Guardar</td>
        <td>Guarda los cambios en el archivo actual, sobrescribiéndolo.</td>
    </tr>
    <tr>
        <td><b>Ctrl+Shift+S</b></td>
        <td>Guardar como...</td>
        <td>Guarda una copia con un nuevo nombre o en otra ubicación, manteniendo el original intacto.</td>
    </tr>
</table>

<h3>📁 Guardado en modo Grupo de Trabajo</h3>

<p>Cuando trabajas con un Grupo de Trabajo, el guardado es más inteligente. Al pulsar <b>Ctrl+S</b>:</p>

{get_img("10_guardado_exitoso.png", "El sistema muestra dónde se guarda cada archivo")}

<p>El sistema automáticamente:</p>
<ol>
    <li><b>Guarda el editado</b> en la carpeta "Modificado - Sí"</li>
    <li><b>Crea backup</b> del original en "Modificado - No"</li>
    <li><b>Limpia</b> el archivo de la carpeta "Origen"</li>
    <li><b>Ofrece continuar</b> con el siguiente PDF pendiente</li>
</ol>

{get_img("12_vista_grupo.png", "Panel lateral mostrando los PDFs del grupo")}

<p>El panel lateral (si está visible) te muestra el progreso: qué archivos faltan por procesar y cuáles ya están completados.</p>

<h3>⚠️ Importante:</h3>
<ul>
    <li>Los cambios son <b>permanentes</b> una vez guardados.</li>
    <li>Si trabajas sin Grupo de Trabajo, usa <b>"Guardar como"</b> para mantener el original.</li>
    <li>Antes de guardar, puedes deshacer errores con <b>Ctrl+Z</b>.</li>
</ul>
"""
    },
    "atajos": {
        "title": "⌨️ Atajos de Teclado",
        "url": f"{MANUAL_URL}#️-atajos-de-teclado",
        "content": lambda: """
<h2>⌨️ Atajos de Teclado</h2>

<p>Dominar los atajos de teclado te permitirá trabajar mucho más rápido. Aquí tienes la lista completa de combinaciones disponibles:</p>

<h3>📂 Archivos:</h3>
<table border="1" cellpadding="10" style="border-collapse:collapse; width:100%; margin:10px 0;">
    <tr style="background:#0078d4; color:white;"><th>Atajo</th><th>Acción</th></tr>
    <tr><td><b>Ctrl + O</b></td><td>Abrir archivo o crear grupo</td></tr>
    <tr><td><b>Ctrl + S</b></td><td>Guardar cambios</td></tr>
    <tr><td><b>Ctrl + Shift + S</b></td><td>Guardar como nuevo archivo</td></tr>
    <tr><td><b>Ctrl + W</b></td><td>Cerrar el PDF actual</td></tr>
</table>

<h3>✏️ Edición:</h3>
<table border="1" cellpadding="10" style="border-collapse:collapse; width:100%; margin:10px 0;">
    <tr style="background:#0078d4; color:white;"><th>Atajo</th><th>Acción</th></tr>
    <tr><td><b>Ctrl + Z</b></td><td>Deshacer última acción</td></tr>
    <tr><td><b>Ctrl + Y</b></td><td>Rehacer acción deshecha</td></tr>
</table>

<h3>🔍 Visualización:</h3>
<table border="1" cellpadding="10" style="border-collapse:collapse; width:100%; margin:10px 0;">
    <tr style="background:#0078d4; color:white;"><th>Atajo</th><th>Acción</th></tr>
    <tr><td><b>Ctrl + +</b></td><td>Aumentar zoom (acercar)</td></tr>
    <tr><td><b>Ctrl + -</b></td><td>Reducir zoom (alejar)</td></tr>
    <tr><td><b>Ctrl + 0</b></td><td>Zoom al 100%</td></tr>
</table>

<h3>❓ Ayuda:</h3>
<table border="1" cellpadding="10" style="border-collapse:collapse; width:100%; margin:10px 0;">
    <tr style="background:#0078d4; color:white;"><th>Atajo</th><th>Acción</th></tr>
    <tr><td><b>F1</b></td><td>Abrir esta ventana de ayuda</td></tr>
</table>

<h3>💡 Consejo:</h3>
<p>Los atajos más útiles para memorizar son: <b>Ctrl+O</b> (abrir), <b>Ctrl+S</b> (guardar) y <b>Ctrl+Z</b> (deshacer). Con estos tres dominarás el flujo básico de trabajo.</p>
"""
    }
}


class HelpDialog(QDialog):
    """Diálogo de ayuda con navegación por secciones."""
    
    def __init__(self, parent=None, section: str = None):
        super().__init__(parent)
        self.setWindowTitle("📘 Ayuda - PDF Editor Pro")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)
        
        self.setup_ui()
        
        # Si se especifica una sección, navegarla
        if section and section in HELP_SECTIONS:
            self.navigate_to_section(section)
        else:
            self.navigate_to_section("inicio")
    
    def setup_ui(self):
        """Configura la interfaz del diálogo."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ThemeColor.BG_PRIMARY};
            }}
            QListWidget {{
                background-color: {ThemeColor.BG_TERTIARY};
                color: {ThemeColor.TEXT_SECONDARY};
                border: none;
                font-size: 14px;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                border-bottom: 1px solid #333;
            }}
            QListWidget::item:selected {{
                background-color: {ThemeColor.ACCENT};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: #2a2d2e;
            }}
            QTextBrowser {{
                background-color: {ThemeColor.BG_PRIMARY};
                color: #d4d4d4;
                border: none;
                font-size: 14px;
                padding: 20px;
            }}
            QPushButton {{
                background-color: {ThemeColor.ACCENT};
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 4px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {ThemeColor.ACCENT_HOVER};
            }}
            QPushButton#secondaryBtn {{
                background-color: #3d3d40;
            }}
            QPushButton#secondaryBtn:hover {{
                background-color: #4d4d50;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo - Lista de secciones
        left_panel = QFrame()
        left_panel.setStyleSheet(f"background-color: {ThemeColor.BG_TERTIARY};")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título del panel
        title = QLabel("  📚 Contenido")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {ThemeColor.ACCENT};
            padding: 16px;
            background-color: {ThemeColor.BG_TERTIARY};
        """)
        left_layout.addWidget(title)
        
        # Lista de secciones
        self.section_list = QListWidget()
        for key, section in HELP_SECTIONS.items():
            item = QListWidgetItem(section["title"])
            item.setData(Qt.UserRole, key)
            self.section_list.addItem(item)
        
        self.section_list.itemClicked.connect(self.on_section_clicked)
        left_layout.addWidget(self.section_list)
        
        left_panel.setMinimumWidth(200)
        left_panel.setMaximumWidth(250)
        splitter.addWidget(left_panel)
        
        # Panel derecho - Contenido
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(False)  # Manejamos los enlaces manualmente
        self.content_browser.setOpenLinks(False)  # Evitar que navegue a los enlaces
        self.content_browser.anchorClicked.connect(self.on_link_clicked)
        right_layout.addWidget(self.content_browser)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([220, 680])
        
        layout.addWidget(splitter)
        
        # Sin barra inferior - el diálogo se cierra con la X de la ventana
    
    def on_link_clicked(self, url: QUrl):
        """Maneja clics en enlaces - abre imágenes o URLs externas."""
        url_string = url.toString()
        
        # Si es un archivo local (imagen), abrirlo con el visor del sistema
        if url_string.startswith("file:///"):
            # Convertir URL a ruta de archivo
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                os.startfile(file_path)  # Windows: abre con programa predeterminado
        else:
            # URLs externas: abrir en navegador
            QDesktopServices.openUrl(url)
    
    def on_section_clicked(self, item: QListWidgetItem):
        """Maneja clic en una sección."""
        section_key = item.data(Qt.UserRole)
        self.navigate_to_section(section_key)
    
    def navigate_to_section(self, section_key: str):
        """Navega a una sección específica."""
        if section_key in HELP_SECTIONS:
            section = HELP_SECTIONS[section_key]
            # Obtener contenido (puede ser lambda o string)
            content = section["content"]
            if callable(content):
                content = content()
            self.content_browser.setHtml(f"""
                <html>
                <head>
                    <style>
                        body {{ 
                            font-family: 'Segoe UI', Arial, sans-serif;
                            line-height: 1.7;
                            color: #d4d4d4;
                            padding: 10px;
                        }}
                        h2 {{ 
                            color: #0078d4;
                            border-bottom: 2px solid #0078d4;
                            padding-bottom: 8px;
                            margin-top: 0;
                        }}
                        h3 {{ 
                            color: #4fc3f7; 
                            margin-top: 25px;
                        }}
                        p {{ margin: 12px 0; }}
                        ul, ol {{ padding-left: 25px; }}
                        li {{ margin: 10px 0; }}
                        b {{ color: #fff; }}
                        a {{ color: #0078d4; }}
                        a:hover {{ color: #4fc3f7; }}
                        img {{ 
                            border-radius: 6px;
                            border: 2px solid #444;
                        }}
                        img:hover {{
                            border-color: #0078d4;
                        }}
                        table {{ 
                            border: 1px solid #555;
                            margin: 16px 0;
                            width: 100%;
                        }}
                        th {{ 
                            background-color: #0078d4;
                            color: white;
                            padding: 10px;
                        }}
                        td {{ 
                            padding: 10px 12px; 
                            border-bottom: 1px solid #444;
                        }}
                        code {{ 
                            background-color: #333;
                            padding: 2px 6px;
                            border-radius: 3px;
                        }}
                    </style>
                </head>
                <body>
                    {content}
                </body>
                </html>
            """)
            
            # Seleccionar en la lista
            for i in range(self.section_list.count()):
                item = self.section_list.item(i)
                if item.data(Qt.UserRole) == section_key:
                    self.section_list.setCurrentItem(item)
                    break
    
    def open_online_manual(self):
        """Abre el manual online en el navegador."""
        QDesktopServices.openUrl(QUrl(MANUAL_URL))


def show_help(parent=None, section: str = None):
    """Función helper para mostrar la ayuda."""
    dialog = HelpDialog(parent, section)
    dialog.exec_()


def open_online_manual():
    """Abre el manual online en el navegador."""
    webbrowser.open(MANUAL_URL)
