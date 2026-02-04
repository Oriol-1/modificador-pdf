"""
Ventana principal del editor de PDF.
"""

import os
import shutil
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QStatusBar, QLabel, QProgressBar,
    QApplication, QFrame, QAction
)
from PyQt5.QtCore import Qt, QTimer, QMimeData
from PyQt5.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QFont

from core.pdf_handler import PDFDocument
from ui.pdf_viewer import PDFPageView
from ui.thumbnail_panel import ThumbnailPanel
from ui.toolbar import EditorToolBar
from ui.workspace_manager import (
    WorkspaceManager, WorkspaceSetupDialog, 
    WorkspaceStatusWidget, PendingPDFsDialog,
    WorkspaceVisualDialog, GroupVisualDialog
)
from ui.help_system import HelpDialog, show_help, open_online_manual


class DropZoneWidget(QFrame):
    """Widget de zona de arrastre cuando no hay PDF abierto."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            DropZoneWidget {
                background-color: #2d2d30;
                border: 3px dashed #555;
                border-radius: 20px;
            }
            DropZoneWidget:hover {
                border-color: #0078d4;
                background-color: #333;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Icono grande
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 72px; background: transparent; border: none;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Texto principal
        text_label = QLabel("Arrastra un PDF aquí")
        text_label.setStyleSheet("font-size: 24px; color: #ccc; font-weight: bold; background: transparent; border: none;")
        text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(text_label)
        
        # Texto secundario
        sub_label = QLabel("o haz clic en 'Abrir' (Ctrl+O)")
        sub_label.setStyleSheet("font-size: 14px; color: #888; background: transparent; border: none;")
        sub_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_label)


class MainWindow(QMainWindow):
    """Ventana principal del editor de PDF."""
    
    def __init__(self):
        super().__init__()
        
        self.pdf_doc = PDFDocument()
        self.current_file = None
        self.original_file_path = None  # Para el flujo de workspace
        
        # Gestor de workspace
        self.workspace_manager = WorkspaceManager()
        
        # Habilitar drag & drop
        self.setAcceptDrops(True)
        
        self.setup_ui()
        self.connect_signals()
        
        # Estado inicial
        self.update_title()
        self.toolbar.set_document_loaded(False)
        self.show_drop_zone()
    
    def setup_ui(self):
        """Configura la interfaz de usuario."""
        self.setWindowTitle("PDF Editor Pro")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Estilo oscuro moderno
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QMenuBar {
                background-color: #2d2d30;
                color: #ccc;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
            }
            QMenu {
                background-color: #2d2d30;
                color: #ccc;
                border: 1px solid #555;
            }
            QMenu::item:selected {
                background-color: #0078d4;
            }
            QToolBar {
                background-color: #2d2d30;
                border: none;
                spacing: 5px;
                padding: 5px;
            }
            QToolButton {
                background-color: transparent;
                color: #ccc;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 13px;
            }
            QToolButton:hover {
                background-color: #3d3d40;
            }
            QToolButton:checked {
                background-color: #0078d4;
                color: white;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
            }
            QSplitter::handle {
                background-color: #3d3d40;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Zona de arrastre (visible cuando no hay PDF)
        self.drop_zone = DropZoneWidget()
        self.main_layout.addWidget(self.drop_zone)
        
        # Contenedor principal (oculto inicialmente)
        self.main_container = QWidget()
        container_layout = QHBoxLayout(self.main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter para panel de miniaturas y visor
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Panel de miniaturas
        self.thumbnail_panel = ThumbnailPanel()
        self.thumbnail_panel.setMinimumWidth(150)
        self.thumbnail_panel.setMaximumWidth(250)
        self.splitter.addWidget(self.thumbnail_panel)
        
        # Contenedor del visor
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Visor de PDF
        self.pdf_viewer = PDFPageView()
        viewer_layout.addWidget(self.pdf_viewer)
        
        self.splitter.addWidget(viewer_container)
        
        # Proporciones del splitter
        self.splitter.setSizes([180, 1020])
        
        container_layout.addWidget(self.splitter)
        self.main_layout.addWidget(self.main_container)
        self.main_container.hide()
        
        # Barra de herramientas
        self.toolbar = EditorToolBar()
        self.addToolBar(self.toolbar)
        
        # Widget de estado del workspace (se agrega a la toolbar)
        self.workspace_status = WorkspaceStatusWidget(self.workspace_manager)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.workspace_status)
        
        # Barra de estado
        self.setup_status_bar()
        
        # Menú
        self.setup_menu()
    
    def setup_status_bar(self):
        """Configura la barra de estado."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Labels de información
        self.status_label = QLabel("Arrastra un PDF o usa Ctrl+O para abrir")
        self.status_bar.addWidget(self.status_label, 1)
        
        self.zoom_label = QLabel("Zoom: 100%")
        self.status_bar.addPermanentWidget(self.zoom_label)
        
        self.page_label = QLabel("")
        self.status_bar.addPermanentWidget(self.page_label)
        
        self.modified_label = QLabel("")
        self.status_bar.addPermanentWidget(self.modified_label)
    
    def show_drop_zone(self):
        """Muestra la zona de arrastre."""
        self.drop_zone.show()
        self.main_container.hide()
    
    def show_pdf_viewer(self):
        """Muestra el visor de PDF."""
        self.drop_zone.hide()
        self.main_container.show()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Maneja cuando se arrastra algo sobre la ventana."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            # Verificar si hay al menos un PDF
            pdf_files = [u.toLocalFile() for u in urls if u.toLocalFile().lower().endswith('.pdf')]
            if pdf_files:
                event.acceptProposedAction()
                # Color diferente según cantidad de PDFs
                if len(pdf_files) > 1:
                    # Múltiples PDFs - indicar creación de grupo
                    self.drop_zone.setStyleSheet("""
                        DropZoneWidget {
                            background-color: #1a2a4a;
                            border: 3px dashed #0078d4;
                            border-radius: 20px;
                        }
                    """)
                else:
                    # Un solo PDF
                    self.drop_zone.setStyleSheet("""
                        DropZoneWidget {
                            background-color: #1a3a1a;
                            border: 3px dashed #4CAF50;
                            border-radius: 20px;
                        }
                    """)
    
    def dragLeaveEvent(self, event):
        """Maneja cuando el arrastre sale de la ventana."""
        self.drop_zone.setStyleSheet("""
            DropZoneWidget {
                background-color: #2d2d30;
                border: 3px dashed #555;
                border-radius: 20px;
            }
            DropZoneWidget:hover {
                border-color: #0078d4;
                background-color: #333;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        """Maneja cuando se sueltan archivos - soporta múltiples PDFs."""
        urls = event.mimeData().urls()
        if urls:
            # Obtener todos los PDFs arrastrados
            pdf_files = [u.toLocalFile() for u in urls if u.toLocalFile().lower().endswith('.pdf')]
            
            if not pdf_files:
                self._reset_drop_zone_style()
                return
            
            event.acceptProposedAction()
            
            # Si hay un documento abierto con cambios, preguntar
            if self.pdf_doc.is_open() and self.pdf_doc.modified:
                reply = QMessageBox.question(
                    self,
                    "Cambios sin guardar",
                    "El documento actual tiene cambios sin guardar.\n\n"
                    "¿Qué deseas hacer?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                    QMessageBox.Save
                )
                
                if reply == QMessageBox.Save:
                    self.save_file()
                elif reply == QMessageBox.Cancel:
                    self._reset_drop_zone_style()
                    return
            
            # MÚLTIPLES PDFs → Crear nuevo grupo de trabajo
            if len(pdf_files) > 1:
                self._handle_multiple_pdfs_drop(pdf_files)
            else:
                # Un solo PDF → abrir directamente
                self.load_pdf(pdf_files[0])
        
        self._reset_drop_zone_style()
    
    def _reset_drop_zone_style(self):
        """Restaura el estilo de la zona de arrastre."""
        self.drop_zone.setStyleSheet("""
            DropZoneWidget {
                background-color: #2d2d30;
                border: 3px dashed #555;
                border-radius: 20px;
            }
            DropZoneWidget:hover {
                border-color: #0078d4;
                background-color: #333;
            }
        """)
    
    def _select_or_create_folder(self, pdf_count: int = 0) -> str:
        """
        Muestra un diálogo mejorado para seleccionar o crear una carpeta.
        Explica claramente el proceso de grupos de trabajo.
        """
        import os
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📁 Configurar Ubicación de Grupos de Trabajo")
        dialog.setMinimumSize(650, 550)
        dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #ffffff; font-size: 13px; }
            QLineEdit {
                background-color: #3d3d3d; color: #ffffff;
                border: 1px solid #555; border-radius: 4px;
                padding: 8px; font-size: 13px;
            }
            QPushButton {
                background-color: #0078d4; color: white;
                border: none; padding: 10px 20px;
                border-radius: 4px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1084d8; }
            QPushButton.secondary { background-color: #3d3d3d; }
            QPushButton.secondary:hover { background-color: #4d4d4d; }
            QListWidget {
                background-color: #2d2d30; color: #ffffff;
                border: 1px solid #555; border-radius: 4px; font-size: 12px;
            }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #0078d4; }
            QListWidget::item:hover { background-color: #3d3d3d; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título con cantidad de PDFs
        if pdf_count > 0:
            title = QLabel(f"📁 Crear Grupo de Trabajo con {pdf_count} PDFs")
        else:
            title = QLabel("📁 Configurar Ubicación de Grupos de Trabajo")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)
        
        # Explicación clara del proceso
        explanation_frame = QFrame()
        explanation_frame.setStyleSheet("background: #252526; border-radius: 8px; padding: 12px;")
        exp_layout = QVBoxLayout(explanation_frame)
        
        exp_title = QLabel("📋 ¿Cómo funciona?")
        exp_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffcc00;")
        exp_layout.addWidget(exp_title)
        
        exp_text = QLabel(
            "1️⃣ <b>Elige o crea una carpeta</b> donde se guardarán tus grupos de trabajo\n\n"
            "2️⃣ <b>Se creará automáticamente</b> una carpeta con la estructura:\n"
            "     📁 <span style='color:#4CAF50'>Grupo_[fecha]_[cantidad]pdfs/</span>\n"
            "         ├── 📥 Origen (tus PDFs pendientes)\n"
            "         ├── ✅ Modificado - Sí (PDFs editados)\n"
            "         └── 📦 Modificado - No (originales respaldados)\n\n"
            "3️⃣ <b>Cada vez que importes más PDFs</b> → Nueva carpeta de grupo"
        )
        exp_text.setWordWrap(True)
        exp_text.setStyleSheet("color: #ccc; font-size: 12px; line-height: 1.5;")
        exp_layout.addWidget(exp_text)
        
        layout.addWidget(explanation_frame)
        
        # Sección: Elegir carpeta existente
        section1 = QLabel("📂 Opción 1: Seleccionar carpeta existente")
        section1.setStyleSheet("font-size: 13px; font-weight: bold; color: #0078d4; margin-top: 10px;")
        layout.addWidget(section1)
        
        path_layout = QHBoxLayout()
        
        # Valor por defecto: Descargas
        default_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(default_path):
            default_path = os.path.expanduser("~")
        
        path_edit = QLineEdit(default_path)
        path_edit.setReadOnly(True)
        path_edit.setPlaceholderText("Carpeta donde se crearán los grupos...")
        path_layout.addWidget(path_edit)
        
        btn_browse = QPushButton("📂 Examinar")
        btn_browse.setProperty("class", "secondary")
        path_layout.addWidget(btn_browse)
        
        layout.addLayout(path_layout)
        
        # Sugerencias rápidas
        suggestions_layout = QHBoxLayout()
        
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        documents = os.path.join(os.path.expanduser("~"), "Documents")
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        
        for path, name, icon in [(downloads, "Descargas", "📥"), (documents, "Documentos", "📄"), (desktop, "Escritorio", "🖥️")]:
            if os.path.exists(path):
                btn = QPushButton(f"{icon} {name}")
                btn.setProperty("class", "secondary")
                btn.setMaximumWidth(150)
                btn.clicked.connect(lambda checked, p=path: path_edit.setText(p))
                suggestions_layout.addWidget(btn)
        
        suggestions_layout.addStretch()
        layout.addLayout(suggestions_layout)
        
        # Sección: Crear nueva carpeta
        section2 = QLabel("➕ Opción 2: Crear nueva carpeta en la ubicación seleccionada")
        section2.setStyleSheet("font-size: 13px; font-weight: bold; color: #4CAF50; margin-top: 15px;")
        layout.addWidget(section2)
        
        new_folder_layout = QHBoxLayout()
        new_folder_edit = QLineEdit()
        new_folder_edit.setPlaceholderText("Nombre de nueva carpeta (ej: Trabajo PDFs, Proyectos...)")
        new_folder_layout.addWidget(new_folder_edit)
        
        btn_create = QPushButton("➕ Crear Carpeta")
        btn_create.setStyleSheet("background-color: #4CAF50;")
        new_folder_layout.addWidget(btn_create)
        
        layout.addLayout(new_folder_layout)
        
        # Espacio
        layout.addStretch()
        
        # Botones finales
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "secondary")
        buttons_layout.addWidget(btn_cancel)
        
        btn_select = QPushButton("✅ Usar Esta Carpeta y Crear Grupo")
        buttons_layout.addWidget(btn_select)
        
        layout.addLayout(buttons_layout)
        
        # Variable para resultado
        result = {'path': None}
        
        # Funciones de los botones
        def browse_folder():
            folder = QFileDialog.getExistingDirectory(
                dialog, "Seleccionar carpeta para grupos de trabajo", path_edit.text(),
                QFileDialog.ShowDirsOnly
            )
            if folder:
                path_edit.setText(folder)
        
        def create_new_folder():
            folder_name = new_folder_edit.text().strip()
            if not folder_name:
                QMessageBox.warning(dialog, "Nombre requerido", 
                    "Escribe un nombre para la nueva carpeta.\n\n"
                    "Ejemplo: Trabajo PDFs, Proyectos 2026, etc.")
                return
            
            # Validar caracteres inválidos
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                if char in folder_name:
                    QMessageBox.warning(dialog, "Nombre inválido", 
                        f"El nombre no puede contener el carácter: {char}")
                    return
            
            # Crear carpeta
            new_path = os.path.join(path_edit.text(), folder_name)
            try:
                os.makedirs(new_path, exist_ok=True)
                path_edit.setText(new_path)
                QMessageBox.information(dialog, "✅ Carpeta Creada", 
                    f"Carpeta creada exitosamente:\n\n📁 {new_path}\n\n"
                    f"Aquí se crearán tus grupos de trabajo.")
                new_folder_edit.clear()
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"No se pudo crear la carpeta:\n{e}")
        
        def confirm_selection():
            path = path_edit.text().strip()
            if path and os.path.exists(path):
                result['path'] = path
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Carpeta no válida", 
                    "La carpeta seleccionada no existe.\n\n"
                    "Selecciona una carpeta existente o crea una nueva.")
        
        # Conectar señales
        btn_browse.clicked.connect(browse_folder)
        btn_create.clicked.connect(create_new_folder)
        btn_cancel.clicked.connect(dialog.reject)
        btn_select.clicked.connect(confirm_selection)
        new_folder_edit.returnPressed.connect(create_new_folder)
        
        if dialog.exec_() == QDialog.Accepted:
            return result['path']
        return None
    
    def _handle_multiple_pdfs_selection(self, pdf_files: list):
        """Maneja la selección de múltiples PDFs desde el diálogo Abrir."""
        self._create_workgroup_from_pdfs(pdf_files, source="selección")

    def _handle_multiple_pdfs_drop(self, pdf_files: list):
        """Maneja el arrastre de múltiples PDFs creando un grupo de trabajo."""
        self._create_workgroup_from_pdfs(pdf_files, source="arrastre")
    
    def _create_workgroup_from_pdfs(self, pdf_files: list, source: str = "importación"):
        from ui.workspace_manager import GroupVisualDialog
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
        
        pdf_count = len(pdf_files)
        
        # Siempre mostrar diálogo de confirmación antes de crear grupo
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("📁 Crear Grupo de Trabajo")
        confirm_dialog.setMinimumWidth(600)
        confirm_dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #ffffff; }
            QPushButton {
                background-color: #0078d4; color: white;
                border: none; padding: 12px 20px;
                border-radius: 6px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1084d8; }
            QPushButton.secondary { background-color: #3d3d3d; }
            QPushButton.secondary:hover { background-color: #4d4d4d; }
            QPushButton.green { background-color: #4CAF50; }
            QPushButton.green:hover { background-color: #5CBF60; }
        """)
        
        layout = QVBoxLayout(confirm_dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Título
        title = QLabel(f"📁 Crear Grupo de Trabajo con {pdf_count} PDFs")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)
        
        # Lista de archivos seleccionados
        files_frame = QFrame()
        files_frame.setStyleSheet("background: #252526; border-radius: 8px; padding: 10px;")
        files_layout = QVBoxLayout(files_frame)
        
        files_title = QLabel("📄 Archivos seleccionados:")
        files_title.setStyleSheet("font-weight: bold; color: #ffcc00;")
        files_layout.addWidget(files_title)
        
        files_text = ""
        for i, f in enumerate(pdf_files[:8]):
            files_text += f"  {i+1}. {os.path.basename(f)}\n"
        if pdf_count > 8:
            files_text += f"  ... y {pdf_count - 8} más"
        
        files_label = QLabel(files_text.strip())
        files_label.setStyleSheet("color: #ccc; font-size: 12px;")
        files_layout.addWidget(files_label)
        
        layout.addWidget(files_frame)
        
        # Explicación del proceso
        explain_frame = QFrame()
        explain_frame.setStyleSheet("background: #1a3a1a; border-radius: 8px; padding: 12px; border: 1px solid #4CAF50;")
        explain_layout = QVBoxLayout(explain_frame)
        
        explain_title = QLabel("✨ ¿Qué pasará?")
        explain_title.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 14px;")
        explain_layout.addWidget(explain_title)
        
        explain_text = QLabel(
            "1. Se creará una <b>nueva carpeta de grupo</b> con fecha y hora\n"
            "2. Tus PDFs se <b>copiarán</b> a la carpeta 'Origen'\n"
            "3. Cuando guardes cambios, se organizarán automáticamente:\n"
            "   • El modificado → carpeta 'Modificado - Sí'\n"
            "   • El original → carpeta 'Modificado - No' (respaldo)"
        )
        explain_text.setWordWrap(True)
        explain_text.setStyleSheet("color: #aaffaa; font-size: 12px;")
        explain_layout.addWidget(explain_text)
        
        layout.addWidget(explain_frame)
        
        # Mostrar carpeta base actual o pedir una nueva
        location_frame = QFrame()
        location_frame.setStyleSheet("background: #252526; border-radius: 8px; padding: 12px;")
        location_layout = QVBoxLayout(location_frame)
        
        if self.workspace_manager.base_path:
            location_title = QLabel("📍 Ubicación actual:")
            location_title.setStyleSheet("font-weight: bold; color: #0078d4;")
            location_layout.addWidget(location_title)
            
            location_path = QLabel(self.workspace_manager.base_path)
            location_path.setStyleSheet("color: #888; font-size: 11px;")
            location_path.setWordWrap(True)
            location_layout.addWidget(location_path)
            
            btn_change = QPushButton("📂 Cambiar Ubicación")
            btn_change.setProperty("class", "secondary")
            btn_change.setMaximumWidth(200)
            location_layout.addWidget(btn_change)
        else:
            location_title = QLabel("⚠️ No hay ubicación configurada")
            location_title.setStyleSheet("font-weight: bold; color: #ffcc00;")
            location_layout.addWidget(location_title)
            
            location_info = QLabel("Necesitas elegir dónde guardar los grupos de trabajo.")
            location_info.setStyleSheet("color: #888;")
            location_layout.addWidget(location_info)
        
        layout.addWidget(location_frame)
        
        # Botones
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "secondary")
        buttons_layout.addWidget(btn_cancel)
        
        btn_create = QPushButton("✅ Crear Grupo de Trabajo")
        btn_create.setProperty("class", "green")
        buttons_layout.addWidget(btn_create)
        
        layout.addLayout(buttons_layout)
        
        # Variables para resultado
        result = {'action': None, 'change_folder': False}
        
        def on_change_folder():
            result['change_folder'] = True
            confirm_dialog.accept()
        
        def on_cancel():
            result['action'] = 'cancel'
            confirm_dialog.reject()
        
        def on_create():
            result['action'] = 'create'
            confirm_dialog.accept()
        
        btn_cancel.clicked.connect(on_cancel)
        btn_create.clicked.connect(on_create)
        
        if self.workspace_manager.base_path:
            btn_change.clicked.connect(on_change_folder)
        
        # Mostrar diálogo
        if confirm_dialog.exec_() != QDialog.Accepted:
            return
        
        # Si quiere cambiar carpeta o no hay ninguna configurada
        if result['change_folder'] or not self.workspace_manager.base_path:
            folder = self._select_or_create_folder(pdf_count)
            if not folder:
                return
            self.workspace_manager.set_base_path(folder)
        
        # Crear nuevo grupo con los PDFs
        group = self.workspace_manager.create_new_group(pdf_files)
        
        if group:
            # Actualizar widget de estado
            self.workspace_status.update_status()
            
            # Mostrar diálogo de confirmación con vista del grupo
            msg = QMessageBox(self)
            msg.setWindowTitle("✅ Grupo de Trabajo Creado")
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"<h3>¡Grupo de trabajo creado exitosamente!</h3>")
            
            # Construir lista de archivos importados
            files_list = "\n".join([f"• {os.path.basename(p)}" for p in pdf_files[:5]])
            if pdf_count > 5:
                files_list += f"\n... y {pdf_count - 5} más"
            
            msg.setInformativeText(
                f"📁 <b>Carpeta:</b> {group.name}\n\n"
                f"📄 <b>PDFs importados ({pdf_count}):</b>\n{files_list}\n\n"
                f"📍 <b>Ubicación:</b> {group.path}\n\n"
                f"<b>¿Qué deseas hacer ahora?</b>"
            )
            
            btn_open = msg.addButton("📖 Abrir Primer PDF", QMessageBox.AcceptRole)
            btn_view = msg.addButton("📂 Ver Carpetas del Grupo", QMessageBox.ActionRole)
            btn_later = msg.addButton("⏰ Más Tarde", QMessageBox.RejectRole)
            
            msg.setDefaultButton(btn_open)
            msg.exec_()
            
            if msg.clickedButton() == btn_view:
                # Mostrar diálogo visual del grupo
                dialog = GroupVisualDialog(self.workspace_manager, group, self)
                dialog.pdfSelected.connect(self.load_pdf)
                dialog.exec_()
            elif msg.clickedButton() == btn_open:
                # Abrir el primer PDF pendiente
                pending = group.get_pending_pdfs()
                if pending:
                    self.load_pdf(pending[0])
        else:
            QMessageBox.critical(
                self,
                "Error",
                "No se pudo crear el grupo de trabajo.\n"
                "Verifica que tienes permisos de escritura en la carpeta."
            )
    
    def setup_menu(self):
        """Configura el menú principal."""
        menubar = self.menuBar()
        
        # Menú Archivo
        file_menu = menubar.addMenu("&Archivo")
        
        file_menu.addAction(self.toolbar.action_open)
        file_menu.addAction(self.toolbar.action_save)
        file_menu.addAction(self.toolbar.action_save_as)
        file_menu.addSeparator()
        
        # === Opciones de Workspace ===
        workspace_menu = file_menu.addMenu("📁 Espacio de Trabajo")
        
        self.action_setup_workspace = QAction("⚙️ Configurar Workspace...", self)
        self.action_setup_workspace.triggered.connect(self.show_workspace_setup)
        workspace_menu.addAction(self.action_setup_workspace)
        
        self.action_import_pdfs = QAction("📥 Importar PDFs...", self)
        self.action_import_pdfs.triggered.connect(self.import_pdfs_to_workspace)
        workspace_menu.addAction(self.action_import_pdfs)
        
        self.action_view_pending = QAction("📋 Ver cola de pendientes...", self)
        self.action_view_pending.triggered.connect(self.show_pending_pdfs)
        workspace_menu.addAction(self.action_view_pending)
        
        workspace_menu.addSeparator()
        
        self.action_open_origin = QAction("📂 Abrir carpeta Origen", self)
        self.action_open_origin.triggered.connect(lambda: self.open_workspace_folder('origin'))
        workspace_menu.addAction(self.action_open_origin)
        
        self.action_open_modified = QAction("📂 Abrir carpeta Modificados", self)
        self.action_open_modified.triggered.connect(lambda: self.open_workspace_folder('modified'))
        workspace_menu.addAction(self.action_open_modified)
        
        file_menu.addSeparator()
        file_menu.addAction(self.toolbar.action_close)
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Salir")
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        
        # Menú Editar
        edit_menu = menubar.addMenu("&Editar")
        edit_menu.addAction(self.toolbar.action_undo)
        edit_menu.addAction(self.toolbar.action_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.toolbar.action_delete)
        edit_menu.addAction(self.toolbar.action_edit)
        edit_menu.addAction(self.toolbar.action_highlight)
        
        # Menú Ver
        view_menu = menubar.addMenu("&Ver")
        view_menu.addAction(self.toolbar.action_zoom_in)
        view_menu.addAction(self.toolbar.action_zoom_out)
        view_menu.addAction(self.toolbar.action_fit_width)
        view_menu.addAction(self.toolbar.action_fit_page)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("A&yuda")
        
        # Ayuda general (F1)
        help_action = QAction("📘 Manual de Ayuda", self)
        help_action.setShortcut("F1")
        help_action.setToolTip("Abrir el manual de ayuda (F1)")
        help_action.triggered.connect(lambda: show_help(self))
        help_menu.addAction(help_action)
        
        help_menu.addSeparator()
        
        # Ayuda contextual por secciones
        help_open = QAction("📂 Cómo abrir archivos", self)
        help_open.triggered.connect(lambda: show_help(self, "abrir"))
        help_menu.addAction(help_open)
        
        help_delete = QAction("🗑️ Cómo eliminar contenido", self)
        help_delete.triggered.connect(lambda: show_help(self, "eliminar"))
        help_menu.addAction(help_delete)
        
        help_edit = QAction("✏️ Cómo editar texto", self)
        help_edit.triggered.connect(lambda: show_help(self, "editar"))
        help_menu.addAction(help_edit)
        
        help_workspace = QAction("📁 Cómo usar Grupos de Trabajo", self)
        help_workspace.triggered.connect(lambda: show_help(self, "workspace"))
        help_menu.addAction(help_workspace)
        
        help_shortcuts = QAction("⌨️ Atajos de teclado", self)
        help_shortcuts.triggered.connect(lambda: show_help(self, "atajos"))
        help_menu.addAction(help_shortcuts)
        
        help_menu.addSeparator()
        
        # Manual online
        online_action = QAction("🌐 Manual Online (Web)", self)
        online_action.triggered.connect(open_online_manual)
        help_menu.addAction(online_action)
        
        help_menu.addSeparator()
        
        # Licencia
        license_action = QAction("📜 Ver Licencia", self)
        license_action.triggered.connect(self.show_license)
        help_menu.addAction(license_action)
        
        about_action = help_menu.addAction("ℹ️ Acerca de...")
        about_action.triggered.connect(self.show_about)
    
    def connect_signals(self):
        """Conecta todas las señales."""
        # Toolbar
        self.toolbar.openFile.connect(self.open_file)
        self.toolbar.saveFile.connect(self.save_file)
        self.toolbar.saveFileAs.connect(self.save_file_as)
        self.toolbar.closeFile.connect(self.close_file)
        
        self.toolbar.zoomIn.connect(self.pdf_viewer.zoom_in)
        self.toolbar.zoomOut.connect(self.pdf_viewer.zoom_out)
        self.toolbar.zoomChanged.connect(self.pdf_viewer.set_zoom)
        self.toolbar.fitWidth.connect(self.pdf_viewer.fit_width)
        self.toolbar.fitPage.connect(self.pdf_viewer.fit_page)
        
        self.toolbar.toolSelected.connect(self.pdf_viewer.set_tool_mode)
        
        self.toolbar.undoAction.connect(self.undo)
        self.toolbar.redoAction.connect(self.redo)
        
        self.toolbar.pageChanged.connect(self.go_to_page)
        
        # Visor
        self.pdf_viewer.zoomChanged.connect(self.on_zoom_changed)
        self.pdf_viewer.textSelected.connect(self.on_text_selected)
        self.pdf_viewer.documentModified.connect(self.on_document_modified)
        
        # Panel de miniaturas
        self.thumbnail_panel.pageSelected.connect(self.go_to_page)
        
        # Workspace
        self.workspace_status.openPending.connect(self.show_pending_pdfs)
        self.workspace_status.configureWorkspace.connect(self.show_workspace_setup)
    
    def open_file(self):
        """Abre un archivo PDF o múltiples para crear un grupo de trabajo."""
        # Verificar cambios sin guardar
        if not self.check_save():
            return
        
        # Mostrar diálogo para elegir modo
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
        
        mode_dialog = QDialog(self)
        mode_dialog.setWindowTitle("📂 Abrir PDF")
        mode_dialog.setMinimumWidth(450)
        mode_dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #ffffff; }
            QPushButton {
                background-color: #3d3d3d; color: white;
                border: none; padding: 15px 20px;
                border-radius: 8px; font-size: 13px;
                text-align: left;
            }
            QPushButton:hover { background-color: #4d4d4d; }
            QPushButton.primary { background-color: #0078d4; }
            QPushButton.primary:hover { background-color: #1084d8; }
        """)
        
        layout = QVBoxLayout(mode_dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        title = QLabel("¿Qué deseas hacer?")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)
        
        # Opción 1: Abrir un solo PDF
        btn_single = QPushButton("📄 Abrir UN PDF para editar\n     Selecciona un archivo para editarlo directamente")
        btn_single.setMinimumHeight(60)
        layout.addWidget(btn_single)
        
        # Opción 2: Crear grupo de trabajo
        btn_group = QPushButton("📁 Crear GRUPO DE TRABAJO\n     Selecciona varios PDFs y se organizarán en carpetas")
        btn_group.setProperty("class", "primary")
        btn_group.setMinimumHeight(60)
        layout.addWidget(btn_group)
        
        # Cancelar
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setMaximumWidth(100)
        layout.addWidget(btn_cancel, alignment=Qt.AlignRight)
        
        result = {'mode': None}
        
        def on_single():
            result['mode'] = 'single'
            mode_dialog.accept()
        
        def on_group():
            result['mode'] = 'group'
            mode_dialog.accept()
        
        btn_single.clicked.connect(on_single)
        btn_group.clicked.connect(on_group)
        btn_cancel.clicked.connect(mode_dialog.reject)
        
        if mode_dialog.exec_() != QDialog.Accepted:
            return
        
        if result['mode'] == 'single':
            # Modo normal: un solo archivo
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Abrir PDF",
                "",
                "Archivos PDF (*.pdf);;Todos los archivos (*.*)"
            )
            if file_path:
                self.load_pdf(file_path)
        else:
            # Modo grupo: múltiples archivos
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Selecciona los PDFs para el grupo de trabajo (Ctrl+Click para seleccionar varios)",
                "",
                "Archivos PDF (*.pdf)"
            )
            
            if not file_paths:
                return
            
            if len(file_paths) == 1:
                # Solo seleccionó uno, preguntar si quiere abrirlo o buscar más
                reply = QMessageBox.question(
                    self,
                    "Solo un PDF seleccionado",
                    f"Seleccionaste solo 1 PDF:\n{os.path.basename(file_paths[0])}\n\n"
                    "¿Deseas abrirlo directamente para editar?\n\n"
                    "Si quieres crear un grupo, selecciona 'No' y elige varios archivos.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.load_pdf(file_paths[0])
            else:
                # Múltiples archivos: crear grupo de trabajo
                self._handle_multiple_pdfs_selection(file_paths)
    
    def load_pdf(self, file_path: str):
        """Carga un archivo PDF."""
        self.status_label.setText("Cargando PDF...")
        QApplication.processEvents()
        
        # Cerrar documento anterior si existe
        if self.pdf_doc.is_open():
            self.pdf_doc.close()
        
        # Limpiar estado del visor
        self.pdf_viewer.clear_all_state()
        
        if self.pdf_doc.open(file_path):
            self.current_file = file_path
            # Guardar ruta original para el flujo de workspace
            self.original_file_path = file_path
            
            # Mostrar visor y ocultar zona de arrastre
            self.show_pdf_viewer()
            
            # Actualizar interfaz
            self.pdf_viewer.set_pdf_document(self.pdf_doc)
            self.thumbnail_panel.set_pdf_document(self.pdf_doc)
            
            self.toolbar.set_document_loaded(True)
            self.toolbar.set_page_count(self.pdf_doc.page_count())
            self.toolbar.set_current_page(0)
            
            # Activar herramienta de borrado por defecto
            self.toolbar.set_tool('delete')
            self.pdf_viewer.set_tool_mode('delete')
            
            # Verificar si está en workspace
            if self.workspace_manager.is_file_in_origin(file_path):
                self.status_label.setText(f"📁 [Workspace] {os.path.basename(file_path)} - Al guardar se moverá automáticamente")
            # Verificar si el PDF tiene texto real o es imagen
            elif not self.pdf_doc.has_real_text():
                QMessageBox.information(
                    self,
                    "PDF basado en imagen",
                    "📷 Este PDF parece ser una imagen escaneada.\n\n"
                    "Puedes usar la herramienta 🗑️ ELIMINAR para:\n"
                    "• Seleccionar áreas y borrarlas (pintándolas de blanco)\n"
                    "• Ocultar información en cualquier parte del documento\n\n"
                    "Simplemente arrastra sobre el área que quieras borrar."
                )
                self.status_label.setText(f"📷 {os.path.basename(file_path)} - PDF de imagen (usa Eliminar para borrar áreas)")
            else:
                self.status_label.setText(f"✓ {os.path.basename(file_path)} - Arrastra sobre el texto para eliminarlo")
            
            # Reiniciar estado de deshacer/rehacer
            self.update_undo_redo_state()
            
            self.update_title()
            self.update_status()
        else:
            error_detail = self.pdf_doc.get_last_error()
            error_msg = f"No se pudo abrir el archivo:\n{file_path}"
            if error_detail:
                error_msg += f"\n\nDetalle: {error_detail}"
            error_msg += "\n\nPosibles causas:\n• El archivo está dañado o corrupto\n• El PDF está protegido\n• El formato no es compatible"
            
            QMessageBox.critical(
                self,
                "Error al abrir PDF",
                error_msg
            )
            self.status_label.setText("Error al cargar PDF")
    
    def save_file(self):
        """Guarda el archivo actual."""
        if not self.pdf_doc.is_open():
            return
        
        if not self.current_file:
            self.save_file_as()
            return
        
        self.status_label.setText("Guardando...")
        QApplication.processEvents()
        
        # IMPORTANTE: Escribir textos overlay pendientes al PDF antes de guardar
        if hasattr(self.pdf_viewer, 'commit_overlay_texts'):
            self.pdf_viewer.commit_overlay_texts()
        
        # Verificar si el archivo está en el workspace
        is_from_workspace = (self.original_file_path and 
                            self.workspace_manager.is_file_in_origin(self.original_file_path))
        
        if is_from_workspace:
            # Flujo de workspace: guardar modificado y mover original
            self._save_with_workspace_flow()
        else:
            # Flujo normal
            if self.pdf_doc.save():
                self.update_title()
                self.update_status()
                self.update_undo_redo_state()
                self.status_label.setText("✓ Archivo guardado - Puedes arrastrar otro PDF para editarlo")
                
                QMessageBox.information(
                    self,
                    "Guardado exitoso",
                    f"El archivo se guardó correctamente.\n\n"
                    f"📁 {os.path.basename(self.current_file)}\n\n"
                    f"Ahora puedes:\n"
                    f"• Continuar editando este PDF\n"
                    f"• Arrastrar otro PDF para editarlo"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo guardar el archivo.\n\n"
                    "Intenta usar 'Guardar como' para guardarlo con otro nombre."
                )
                self.status_label.setText("Error al guardar")
    
    def _save_with_workspace_flow(self):
        """Guarda el archivo usando el flujo de workspace."""
        try:
            # Obtener el contenido modificado del PDF
            modified_content = self.pdf_doc.doc.tobytes()
            
            # Guardar la ruta original antes de procesar
            original_src = self.original_file_path
            
            # Procesar con el workspace manager (guarda el modificado y calcula destino del original)
            result = self.workspace_manager.process_saved_pdf(
                original_src,
                modified_content
            )
            
            if result and result['modified']:
                # 1. Cerrar el documento actual para liberar el archivo
                self.pdf_doc.close()
                
                # 2. Ahora que el archivo está liberado, mover el original
                if result.get('original_src') and result.get('original_dest'):
                    self.workspace_manager.move_original_to_archive(
                        result['original_src'],
                        result['original_dest']
                    )
                
                # 3. Actualizar variables de estado
                self.original_file_path = None
                self.current_file = result['modified']
                
                # 4. Reabrir el archivo modificado
                self.pdf_doc.open(result['modified'])
                self.pdf_viewer.set_pdf_document(self.pdf_doc)
                self.thumbnail_panel.set_pdf_document(self.pdf_doc)
                
                self.update_title()
                self.update_status()
                self.update_undo_redo_state()
                
                # Actualizar widget de estado del workspace
                self.workspace_status.update_status()
                self.workspace_status.update_status()
                
                # Obtener stats actualizados
                stats = self.workspace_manager.get_stats()
                
                # Mostrar diálogo visual del resultado
                self._show_save_result_dialog(result, stats)
                
                self.status_label.setText(f"✅ Guardado en workspace - {stats['pending']} pendientes")
                
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo procesar el archivo en el workspace.\n"
                    "Intenta usar 'Guardar como' para guardarlo manualmente."
                )
                self.status_label.setText("Error al guardar en workspace")
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al guardar: {str(e)}\n\n"
                "Intenta usar 'Guardar como' para guardarlo manualmente."
            )
            self.status_label.setText("Error al guardar")
    
    def _show_save_result_dialog(self, result: dict, stats: dict):
        """Muestra un diálogo visual con el resultado del guardado."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("✅ Guardado Exitoso")
        dialog.setMinimumWidth(550)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton.secondary {
                background-color: #3d3d3d;
            }
            QPushButton.secondary:hover {
                background-color: #4d4d4d;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Título con icono grande
        title = QLabel("✅ PDF Procesado Correctamente")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # === Diagrama visual del movimiento ===
        flow_frame = QFrame()
        flow_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        flow_layout = QVBoxLayout(flow_frame)
        
        # Fila 1: Origen (tachado)
        row1 = QHBoxLayout()
        origin_icon = QLabel("📥")
        origin_icon.setStyleSheet("font-size: 24px;")
        row1.addWidget(origin_icon)
        
        origin_label = QLabel("ORIGEN")
        origin_label.setStyleSheet("color: #ffcc00; font-weight: bold; font-size: 14px;")
        row1.addWidget(origin_label)
        
        origin_file = QLabel(f"<s>{os.path.basename(result['original'])}</s>")
        origin_file.setStyleSheet("color: #888; font-size: 12px;")
        row1.addWidget(origin_file)
        
        row1.addStretch()
        
        removed_badge = QLabel("❌ Removido")
        removed_badge.setStyleSheet("color: #ff5555; font-size: 11px;")
        row1.addWidget(removed_badge)
        
        flow_layout.addLayout(row1)
        
        # Flecha
        arrow = QLabel("          ⬇️ Al guardar se movió automáticamente")
        arrow.setStyleSheet("color: #888; font-size: 12px;")
        flow_layout.addWidget(arrow)
        
        # Fila 2: Modificado - Sí
        row2 = QHBoxLayout()
        mod_icon = QLabel("✅")
        mod_icon.setStyleSheet("font-size: 24px;")
        row2.addWidget(mod_icon)
        
        mod_label = QLabel("MODIFICADO - SÍ")
        mod_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
        row2.addWidget(mod_label)
        
        mod_file = QLabel(os.path.basename(result['modified']))
        mod_file.setStyleSheet("color: #4CAF50; font-size: 12px;")
        row2.addWidget(mod_file)
        
        row2.addStretch()
        
        new_badge = QLabel("✨ Nuevo")
        new_badge.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;")
        row2.addWidget(new_badge)
        
        flow_layout.addLayout(row2)
        
        # Fila 3: Modificado - No (original)
        row3 = QHBoxLayout()
        orig_icon = QLabel("📦")
        orig_icon.setStyleSheet("font-size: 24px;")
        row3.addWidget(orig_icon)
        
        orig_label = QLabel("MODIFICADO - NO")
        orig_label.setStyleSheet("color: #9E9E9E; font-weight: bold; font-size: 14px;")
        row3.addWidget(orig_label)
        
        orig_file = QLabel(os.path.basename(result['original']))
        orig_file.setStyleSheet("color: #9E9E9E; font-size: 12px;")
        row3.addWidget(orig_file)
        
        row3.addStretch()
        
        backup_badge = QLabel("🔒 Backup")
        backup_badge.setStyleSheet("color: #9E9E9E; font-size: 11px;")
        row3.addWidget(backup_badge)
        
        flow_layout.addLayout(row3)
        
        layout.addWidget(flow_frame)
        
        # === Estadísticas ===
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        stats_layout = QHBoxLayout(stats_frame)
        
        pending_label = QLabel(f"📥 Pendientes: {stats['pending']}")
        pending_label.setStyleSheet("color: #ffcc00; font-size: 13px;")
        stats_layout.addWidget(pending_label)
        
        stats_layout.addStretch()
        
        modified_label = QLabel(f"✅ Modificados: {stats['modified']}")
        modified_label.setStyleSheet("color: #4CAF50; font-size: 13px;")
        stats_layout.addWidget(modified_label)
        
        stats_layout.addStretch()
        
        archived_label = QLabel(f"📦 Archivados: {stats['archived']}")
        archived_label.setStyleSheet("color: #9E9E9E; font-size: 13px;")
        stats_layout.addWidget(archived_label)
        
        layout.addWidget(stats_frame)
        
        # === Botones ===
        buttons_layout = QHBoxLayout()
        
        if stats['pending'] > 0:
            btn_next = QPushButton(f"📂 Abrir siguiente ({stats['pending']} pendientes)")
            btn_next.clicked.connect(lambda: (dialog.accept(), self.open_next_pending()))
            buttons_layout.addWidget(btn_next)
        
        btn_view = QPushButton("📁 Ver carpetas")
        btn_view.setProperty("class", "secondary")
        btn_view.clicked.connect(lambda: (dialog.accept(), self.show_pending_pdfs()))
        buttons_layout.addWidget(btn_view)
        
        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("class", "secondary")
        btn_close.clicked.connect(dialog.accept)
        buttons_layout.addWidget(btn_close)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec_()
    
    def open_next_pending(self):
        """Abre el siguiente PDF pendiente del workspace."""
        pending = self.workspace_manager.get_pending_pdfs()
        if pending:
            # Cerrar documento actual si hay cambios
            if self.pdf_doc.is_open() and self.pdf_doc.modified:
                if not self.check_save():
                    return
            self.load_pdf(pending[0])
    
    def save_file_as(self):
        """Guarda el archivo con un nuevo nombre."""
        if not self.pdf_doc.is_open():
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF como",
            self.current_file or "",
            "Archivos PDF (*.pdf)"
        )
        
        if file_path:
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
            
            self.status_label.setText("Guardando...")
            QApplication.processEvents()
            
            # IMPORTANTE: Escribir textos overlay pendientes al PDF antes de guardar
            if hasattr(self.pdf_viewer, 'commit_overlay_texts'):
                self.pdf_viewer.commit_overlay_texts()
            
            if self.pdf_doc.save_as(file_path):
                self.current_file = file_path
                self.update_title()
                self.update_status()
                self.status_label.setText(f"Guardado como: {os.path.basename(file_path)}")
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "No se pudo guardar el archivo."
                )
                self.status_label.setText("Error al guardar")
    
    def close_file(self):
        """Cierra el PDF actual para poder abrir otro."""
        if not self.pdf_doc.is_open():
            return
        
        # Verificar cambios sin guardar
        if self.pdf_doc.modified:
            reply = QMessageBox.question(
                self,
                "Cambios sin guardar",
                "El documento tiene cambios sin guardar.\n\n"
                "¿Deseas guardar antes de cerrar?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.save_file()
                if self.pdf_doc.modified:  # Si sigue modificado, hubo error
                    return
            elif reply == QMessageBox.Cancel:
                return
            # Si es Discard, continuar cerrando
        
        # Cerrar el documento
        self.pdf_doc.close()
        self.current_file = None
        
        # Limpiar visor
        self.pdf_viewer.clear_all_state()
        
        # Limpiar miniaturas
        self.thumbnail_panel.clear()
        
        # Mostrar zona de arrastre
        self.show_drop_zone()
        
        # Actualizar interfaz
        self.toolbar.set_document_loaded(False)
        self.update_title()
        self.update_undo_redo_state()
        
        self.status_label.setText("PDF cerrado - Arrastra otro PDF o usa Ctrl+O para abrir")
        self.page_label.setText("")
        self.modified_label.setText("")
    
    def go_to_page(self, page_num: int):
        """Navega a una página específica."""
        if self.pdf_doc.is_open():
            self.pdf_viewer.load_page(page_num)
            self.toolbar.set_current_page(page_num)
            self.thumbnail_panel.select_page(page_num)
            self.update_status()
    
    def undo(self):
        """Deshace la última acción."""
        if self.pdf_doc.undo():
            current_page = self.pdf_viewer.current_page
            # Los overlays se restauran automáticamente via callback en pdf_doc.undo()
            # Solo necesitamos limpiar los items visuales para que se recreen
            self.pdf_viewer.editable_text_items = []
            self.pdf_viewer.selected_text_item = None
            self.pdf_viewer.render_page()
            self.thumbnail_panel.refresh_thumbnail(current_page)
            self.update_undo_redo_state()
            self.status_label.setText("Acción deshecha")
    
    def redo(self):
        """Rehace la última acción."""
        if self.pdf_doc.redo():
            current_page = self.pdf_viewer.current_page
            # Los overlays se restauran automáticamente via callback en pdf_doc.redo()
            # Solo necesitamos limpiar los items visuales para que se recreen
            self.pdf_viewer.editable_text_items = []
            self.pdf_viewer.selected_text_item = None
            self.pdf_viewer.render_page()
            self.thumbnail_panel.refresh_thumbnail(current_page)
            self.update_undo_redo_state()
            self.status_label.setText("Acción rehecha")
    
    def update_undo_redo_state(self):
        """Actualiza el estado de los botones deshacer/rehacer."""
        self.toolbar.update_undo_redo(
            self.pdf_doc.can_undo(),
            self.pdf_doc.can_redo()
        )
    
    def on_zoom_changed(self, zoom: float):
        """Maneja el cambio de zoom."""
        self.toolbar.update_zoom_display(zoom)
        self.zoom_label.setText(f"Zoom: {int(zoom * 100)}%")
    
    def on_text_selected(self, text: str, rect):
        """Maneja la selección de texto."""
        if text:
            self.status_label.setText(f"Seleccionado: \"{text[:50]}{'...' if len(text) > 50 else ''}\"")
    
    def on_document_modified(self):
        """Maneja cuando el documento es modificado."""
        self.update_undo_redo_state()
        self.update_title()
        self.update_status()
        current_page = self.pdf_viewer.current_page
        self.thumbnail_panel.refresh_thumbnail(current_page)
    
    def update_title(self):
        """Actualiza el título de la ventana."""
        title = "PDF Editor Pro"
        
        if self.current_file:
            filename = os.path.basename(self.current_file)
            if self.pdf_doc.modified:
                title = f"*{filename} - {title}"
            else:
                title = f"{filename} - {title}"
        
        self.setWindowTitle(title)
    
    def update_status(self):
        """Actualiza la barra de estado."""
        if self.pdf_doc.is_open():
            page = self.pdf_viewer.current_page + 1
            total = self.pdf_doc.page_count()
            self.page_label.setText(f"Página {page} de {total}")
            
            if self.pdf_doc.modified:
                self.modified_label.setText("● Modificado")
                self.modified_label.setStyleSheet("color: orange;")
            else:
                self.modified_label.setText("")
        else:
            self.page_label.setText("")
            self.modified_label.setText("")
    
    def check_save(self) -> bool:
        """
        Verifica si hay cambios sin guardar.
        Retorna True si se puede continuar, False si se canceló.
        """
        if self.pdf_doc.is_open() and self.pdf_doc.modified:
            reply = QMessageBox.question(
                self,
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Desea guardarlos?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.save_file()
                return not self.pdf_doc.modified  # Si sigue modificado, hubo error
            elif reply == QMessageBox.Cancel:
                return False
            else:
                # Discard - limpiar estado de modificado
                self.pdf_doc.modified = False
        
        return True
    
    def show_about(self):
        """Muestra el diálogo Acerca de."""
        QMessageBox.about(
            self,
            "Acerca de PDF Editor Pro",
            "<h2>PDF Editor Pro</h2>"
            "<p>Versión 1.0.0</p>"
            "<p>Editor de PDF con capacidades de:</p>"
            "<ul>"
            "<li>Selección de texto</li>"
            "<li>Resaltado de texto</li>"
            "<li>Eliminación de texto</li>"
            "<li>Edición de texto con formato original</li>"
            "<li>Sistema de workspace para flujo de trabajo</li>"
            "</ul>"
            "<p>Preserva formularios y estructura del documento.</p>"
            "<hr>"
            "<p><b>© 2026 Oriol Alonso Esplugas</b></p>"
            "<p>Todos los derechos reservados</p>"
            "<p><small>Gratuito para uso personal. "
            "Uso comercial requiere autorización.</small></p>"
        )
    
    def show_license(self):
        """Muestra el diálogo de licencia."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QComboBox, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📜 Licencia - PDF Editor Pro")
        dialog.setMinimumSize(700, 500)
        dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QTextEdit { 
                background-color: #2d2d30; 
                color: #ffffff; 
                border: 1px solid #555;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            QLabel { color: #ffffff; }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1084d8; }
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px 10px;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Selector de idioma
        lang_layout = QHBoxLayout()
        lang_label = QLabel("Idioma / Language:")
        lang_combo = QComboBox()
        lang_combo.addItem("🇪🇸 Español", "es")
        lang_combo.addItem("🇬🇧 English", "en")
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(lang_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # Área de texto para la licencia
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        
        # Cargar licencia según idioma
        def load_license(lang):
            import sys
            import os
            
            # Determinar la ruta base
            if getattr(sys, 'frozen', False):
                # Ejecutable compilado
                base_path = sys._MEIPASS
            else:
                # Desarrollo
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            if lang == "es":
                license_file = os.path.join(base_path, "LICENSE.txt")
            else:
                license_file = os.path.join(base_path, "LICENSE_EN.txt")
            
            try:
                with open(license_file, 'r', encoding='utf-8') as f:
                    text_edit.setPlainText(f.read())
            except FileNotFoundError:
                text_edit.setPlainText(self._get_embedded_license(lang))
        
        lang_combo.currentIndexChanged.connect(
            lambda: load_license(lang_combo.currentData())
        )
        
        # Cargar licencia inicial en español
        load_license("es")
        
        # Botón cerrar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def _get_embedded_license(self, lang="es"):
        """Devuelve la licencia embebida en caso de que no se encuentre el archivo."""
        if lang == "es":
            return """
================================================================================
                    PDF EDITOR PRO - LICENCIA DE USO
================================================================================

Copyright (c) 2026 Oriol Alonso Esplugas
Todos los derechos reservados.

LICENCIA PROPIETARIA CON USO PERSONAL GRATUITO

Este software es GRATUITO para uso personal y no comercial.

PROHIBIDO SIN AUTORIZACIÓN:
- Vender el software
- Uso comercial o empresarial  
- Monetizar de cualquier forma
- Reclamar autoría

Para uso comercial o ventas, contactar:
- Email: alonsoesplugas@gmail.com
- GitHub: https://github.com/Oriol-1

Cualquier venta requiere retribución acordada al autor.

EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO.

================================================================================
          PDF Editor Pro © 2026 Oriol Alonso Esplugas
================================================================================
"""
        else:
            return """
================================================================================
                    PDF EDITOR PRO - LICENSE AGREEMENT
================================================================================

Copyright (c) 2026 Oriol Alonso Esplugas
All rights reserved.

PROPRIETARY LICENSE WITH FREE PERSONAL USE

This software is FREE for personal and non-commercial use.

PROHIBITED WITHOUT AUTHORIZATION:
- Selling the software
- Commercial or business use
- Monetizing in any way
- Claiming authorship

For commercial use or sales, contact:
- Email: alonsoesplugas@gmail.com
- GitHub: https://github.com/Oriol-1

Any sale requires agreed compensation to the author.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

================================================================================
          PDF Editor Pro © 2026 Oriol Alonso Esplugas
================================================================================
"""
    
    # ==================== MÉTODOS DE WORKSPACE ====================
    
    def show_workspace_setup(self):
        """Muestra el diálogo de configuración del workspace."""
        dialog = WorkspaceSetupDialog(self, self.workspace_manager)
        dialog.workspaceCreated.connect(self.on_workspace_created)
        dialog.exec_()
    
    def on_workspace_created(self, workspace_path):
        """Callback cuando se crea un workspace."""
        self.workspace_status.update_status()
        
        # Preguntar si quiere abrir el primer PDF pendiente
        pending = self.workspace_manager.get_pending_pdfs()
        if pending:
            reply = QMessageBox.question(
                self,
                "Abrir PDF",
                f"Se importaron {len(pending)} PDFs.\n\n"
                f"¿Deseas abrir el primero para comenzar a editarlo?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.load_pdf(pending[0])
    
    def show_pending_pdfs(self):
        """Muestra el diálogo de PDFs pendientes."""
        if not self.workspace_manager.is_workspace_active():
            QMessageBox.information(
                self,
                "Sin workspace",
                "No hay un espacio de trabajo configurado.\n\n"
                "Usa Archivo > Espacio de Trabajo > Configurar Workspace para crear uno."
            )
            return
        
        # Usar el nuevo diálogo visual
        dialog = WorkspaceVisualDialog(self.workspace_manager, self)
        dialog.pdfSelected.connect(self.open_pdf_from_workspace)
        dialog.exec_()
    
    def open_pdf_from_workspace(self, pdf_path):
        """Abre un PDF desde el workspace."""
        if not self.check_save():
            return
        self.load_pdf(pdf_path)
    
    def import_pdfs_to_workspace(self):
        """Importa PDFs al workspace."""
        if not self.workspace_manager.is_workspace_active():
            reply = QMessageBox.question(
                self,
                "Sin workspace",
                "No hay un espacio de trabajo configurado.\n\n"
                "¿Deseas configurar uno ahora?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.show_workspace_setup()
            return
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar PDFs para importar",
            "",
            "Archivos PDF (*.pdf)"
        )
        
        if files:
            success, failed = self.workspace_manager.import_pdfs(files)
            
            self.workspace_status.update_status()
            
            msg = ""
            if success > 0:
                msg += f"✅ {success} PDF{'s' if success != 1 else ''} importado{'s' if success != 1 else ''}\n"
            if failed > 0:
                msg += f"⚠️ {failed} archivo{'s' if failed != 1 else ''} no se pudo importar"
            
            QMessageBox.information(self, "Importación completada", msg)
            
            # Preguntar si quiere abrir el primero si no hay documento abierto
            if success > 0 and not self.pdf_doc.is_open():
                pending = self.workspace_manager.get_pending_pdfs()
                if pending:
                    reply = QMessageBox.question(
                        self,
                        "Abrir PDF",
                        "¿Deseas abrir el primer PDF pendiente?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if reply == QMessageBox.Yes:
                        self.load_pdf(pending[0])
    
    def open_workspace_folder(self, folder_type):
        """Abre una carpeta del workspace en el explorador."""
        if not self.workspace_manager.is_workspace_active():
            QMessageBox.information(
                self,
                "Sin workspace",
                "No hay un espacio de trabajo configurado."
            )
            return
        
        if folder_type == 'origin':
            folder = self.workspace_manager.get_origin_folder()
        elif folder_type == 'modified':
            folder = self.workspace_manager.get_modified_folder()
        else:
            folder = self.workspace_manager.workspace_path
        
        if folder and os.path.exists(folder):
            os.startfile(folder)
    
    def closeEvent(self, event: QCloseEvent):
        """Maneja el evento de cierre de ventana."""
        if self.check_save():
            self.pdf_doc.close()
            event.accept()
        else:
            event.ignore()
