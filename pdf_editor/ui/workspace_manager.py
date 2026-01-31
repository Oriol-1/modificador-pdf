"""
Gestor de espacios de trabajo para el flujo de PDFs.
Sistema de grupos de trabajo aislados con carpetas únicas por importación.

Estructura:
📁 Workspace Base (ej: Descargas)
  └── 📁 Grupo_2026-01-28_143052_5pdfs
      ├── 📥 Origen           (PDFs pendientes)
      ├── ✅ Modificado - Sí  (PDFs editados)
      └── 📦 Modificado - No  (Originales archivados)

Flujo visual:
📥 ORIGEN          →  ❌ Eliminado (al guardar)
✅ MODIFICADO - SÍ →  ✨ Nuevo (archivo editado)
📦 MODIFICADO - NO →  🔒 Backup (original archivado)
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QListWidget, QListWidgetItem,
    QMessageBox, QGroupBox, QCheckBox, QFrame, QProgressBar,
    QAbstractItemView, QWidget, QScrollArea, QSizePolicy,
    QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor


class WorkGroup:
    """Representa un grupo de trabajo aislado con su propia estructura de carpetas."""
    
    FOLDER_ORIGIN = "Origen"
    FOLDER_MODIFIED = "Modificado - Sí"
    FOLDER_ORIGINAL = "Modificado - No"
    
    def __init__(self, group_path: str, created_at: str = None):
        self.path = group_path
        self.created_at = created_at or datetime.now().isoformat()
        self.name = os.path.basename(group_path)
        
    @property
    def origin_folder(self) -> str:
        return os.path.join(self.path, self.FOLDER_ORIGIN)
    
    @property
    def modified_folder(self) -> str:
        return os.path.join(self.path, self.FOLDER_MODIFIED)
    
    @property
    def original_folder(self) -> str:
        return os.path.join(self.path, self.FOLDER_ORIGINAL)
    
    def get_pending_count(self) -> int:
        """Cuenta PDFs pendientes en Origen."""
        if not os.path.exists(self.origin_folder):
            return 0
        return len([f for f in os.listdir(self.origin_folder) if f.lower().endswith('.pdf')])
    
    def get_modified_count(self) -> int:
        """Cuenta PDFs modificados."""
        if not os.path.exists(self.modified_folder):
            return 0
        return len([f for f in os.listdir(self.modified_folder) if f.lower().endswith('.pdf')])
    
    def get_archived_count(self) -> int:
        """Cuenta PDFs archivados (originales)."""
        if not os.path.exists(self.original_folder):
            return 0
        return len([f for f in os.listdir(self.original_folder) if f.lower().endswith('.pdf')])
    
    def get_pending_pdfs(self) -> List[str]:
        """Obtiene lista de PDFs pendientes ordenados."""
        if not os.path.exists(self.origin_folder):
            return []
        pdfs = [os.path.join(self.origin_folder, f) 
                for f in os.listdir(self.origin_folder) 
                if f.lower().endswith('.pdf')]
        return sorted(pdfs)
    
    def is_complete(self) -> bool:
        """Verifica si el grupo está completo (sin pendientes)."""
        return self.get_pending_count() == 0 and self.get_modified_count() > 0
    
    def to_dict(self) -> dict:
        return {
            'path': self.path,
            'created_at': self.created_at,
            'name': self.name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WorkGroup':
        return cls(data['path'], data.get('created_at'))


class WorkspaceManager:
    """Gestor principal del espacio de trabajo con grupos aislados."""
    
    # Compatibilidad con código anterior
    FOLDER_ORIGIN = "Origen"
    FOLDER_MODIFIED = "Modificado - Sí"
    FOLDER_ORIGINAL = "Modificado - No"
    
    def __init__(self):
        self.base_path: Optional[str] = None  # Carpeta base (ej: Descargas)
        self.work_groups: List[WorkGroup] = []
        self.current_group: Optional[WorkGroup] = None
        self.config_file = self._get_config_path()
        self._load_config()
    
    def _get_config_path(self) -> str:
        """Obtiene la ruta del archivo de configuración."""
        app_data = os.path.join(os.path.expanduser("~"), ".pdf_editor")
        os.makedirs(app_data, exist_ok=True)
        return os.path.join(app_data, "workspace_config_v2.json")
    
    def _load_config(self):
        """Carga la configuración guardada."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.base_path = config.get('base_path')
                    
                    # Validar que la ruta base existe
                    if self.base_path and not os.path.exists(self.base_path):
                        self.base_path = None
                    
                    # Cargar grupos de trabajo
                    groups_data = config.get('work_groups', [])
                    self.work_groups = []
                    for g in groups_data:
                        if os.path.exists(g.get('path', '')):
                            self.work_groups.append(WorkGroup.from_dict(g))
                    
                    # Cargar grupo actual
                    current_path = config.get('current_group_path')
                    if current_path:
                        self.current_group = next(
                            (g for g in self.work_groups if g.path == current_path), 
                            None
                        )
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            self.base_path = None
            self.work_groups = []
            self.current_group = None
    
    def _save_config(self):
        """Guarda la configuración actual."""
        try:
            config = {
                'base_path': self.base_path,
                'work_groups': [g.to_dict() for g in self.work_groups],
                'current_group_path': self.current_group.path if self.current_group else None
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error guardando configuración: {e}")
    
    def is_workspace_active(self) -> bool:
        """Verifica si hay un workspace base activo."""
        return self.base_path is not None and os.path.exists(self.base_path)
    
    def has_active_group(self) -> bool:
        """Verifica si hay un grupo de trabajo activo."""
        return self.current_group is not None
    
    def set_base_path(self, path: str) -> bool:
        """Establece la carpeta base para los grupos de trabajo."""
        if os.path.exists(path):
            self.base_path = path
            self._scan_existing_groups()
            self._save_config()
            return True
        return False
    
    def _scan_existing_groups(self):
        """Busca grupos de trabajo existentes en la carpeta base."""
        if not self.base_path:
            return
        
        existing_paths = {g.path for g in self.work_groups}
        
        for item in os.listdir(self.base_path):
            item_path = os.path.join(self.base_path, item)
            if os.path.isdir(item_path) and item.startswith("Grupo_"):
                # Verificar estructura válida
                origin = os.path.join(item_path, WorkGroup.FOLDER_ORIGIN)
                if os.path.exists(origin) and item_path not in existing_paths:
                    self.work_groups.append(WorkGroup(item_path))
        
        # Ordenar por fecha de creación (más reciente primero)
        self.work_groups.sort(key=lambda g: g.created_at, reverse=True)
    
    def _generate_group_name(self, pdf_count: int) -> str:
        """Genera un nombre único para un nuevo grupo."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return f"Grupo_{timestamp}_{pdf_count}pdfs"
    
    def create_new_group(self, pdf_paths: List[str]) -> Optional[WorkGroup]:
        """
        Crea un nuevo grupo de trabajo e importa los PDFs.
        SIEMPRE crea una carpeta nueva, nunca reutiliza.
        
        Args:
            pdf_paths: Lista de rutas de PDFs a importar
            
        Returns:
            El nuevo WorkGroup creado o None si falla
        """
        if not self.base_path or not pdf_paths:
            return None
        
        try:
            # Generar nombre único
            group_name = self._generate_group_name(len(pdf_paths))
            group_path = os.path.join(self.base_path, group_name)
            
            # Asegurar que no existe (añadir sufijo si es necesario)
            counter = 1
            while os.path.exists(group_path):
                group_path = os.path.join(self.base_path, f"{group_name}_{counter}")
                counter += 1
            
            # Crear estructura de carpetas
            os.makedirs(group_path)
            os.makedirs(os.path.join(group_path, WorkGroup.FOLDER_ORIGIN))
            os.makedirs(os.path.join(group_path, WorkGroup.FOLDER_MODIFIED))
            os.makedirs(os.path.join(group_path, WorkGroup.FOLDER_ORIGINAL))
            
            # Crear grupo
            new_group = WorkGroup(group_path)
            
            # Importar PDFs manteniendo el orden
            for idx, pdf_path in enumerate(pdf_paths):
                if os.path.exists(pdf_path) and pdf_path.lower().endswith('.pdf'):
                    filename = os.path.basename(pdf_path)
                    # Prefijo numérico para mantener orden de importación
                    prefix = f"{idx+1:03d}_"
                    dest_path = os.path.join(new_group.origin_folder, prefix + filename)
                    
                    # Evitar duplicados
                    if os.path.exists(dest_path):
                        base, ext = os.path.splitext(prefix + filename)
                        c = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(new_group.origin_folder, f"{base}_{c}{ext}")
                            c += 1
                    
                    shutil.copy2(pdf_path, dest_path)
            
            # Agregar a la lista y establecer como actual
            self.work_groups.insert(0, new_group)
            self.current_group = new_group
            self._save_config()
            
            return new_group
            
        except Exception as e:
            print(f"Error creando grupo: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def set_current_group(self, group: WorkGroup):
        """Establece el grupo de trabajo actual."""
        if group in self.work_groups:
            self.current_group = group
            self._save_config()
    
    def get_pending_pdfs(self) -> List[str]:
        """Obtiene PDFs pendientes del grupo actual."""
        if self.current_group:
            return self.current_group.get_pending_pdfs()
        return []
    
    def get_all_pending_count(self) -> int:
        """Cuenta todos los PDFs pendientes en todos los grupos."""
        return sum(g.get_pending_count() for g in self.work_groups)
    
    def get_groups_with_pending(self) -> List[WorkGroup]:
        """Obtiene grupos que tienen PDFs pendientes."""
        return [g for g in self.work_groups if g.get_pending_count() > 0]
    
    # =====================================================
    # Propiedades y métodos de compatibilidad
    # =====================================================
    
    @property
    def workspace_path(self) -> Optional[str]:
        """Compatibilidad: retorna la ruta del grupo actual."""
        return self.current_group.path if self.current_group else None
    
    def get_origin_folder(self) -> Optional[str]:
        """Obtiene la carpeta Origen del grupo actual."""
        return self.current_group.origin_folder if self.current_group else None
    
    def get_modified_folder(self) -> Optional[str]:
        """Obtiene la carpeta Modificado - Sí del grupo actual."""
        return self.current_group.modified_folder if self.current_group else None
    
    def get_original_folder(self) -> Optional[str]:
        """Obtiene la carpeta Modificado - No del grupo actual."""
        return self.current_group.original_folder if self.current_group else None
    
    def is_file_in_origin(self, file_path: str) -> bool:
        """Verifica si un archivo está en alguna carpeta Origen."""
        if not file_path:
            return False
        
        file_path_norm = os.path.normpath(os.path.abspath(file_path)).lower()
        
        # Buscar en todos los grupos
        for group in self.work_groups:
            origin_norm = os.path.normpath(os.path.abspath(group.origin_folder)).lower()
            if file_path_norm.startswith(origin_norm):
                # Establecer este grupo como actual
                self.current_group = group
                self._save_config()
                return True
        
        return False
    
    def find_group_for_file(self, file_path: str) -> Optional[WorkGroup]:
        """Encuentra el grupo al que pertenece un archivo."""
        if not file_path:
            return None
        
        file_path_norm = os.path.normpath(os.path.abspath(file_path)).lower()
        
        for group in self.work_groups:
            group_norm = os.path.normpath(os.path.abspath(group.path)).lower()
            if file_path_norm.startswith(group_norm):
                return group
        
        return None
    
    def process_saved_pdf(self, original_path: str, modified_content: bytes = None) -> Optional[dict]:
        """
        Procesa un PDF guardado: guarda el modificado y prepara mover el original.
        
        Args:
            original_path: Ruta del PDF original en Origen
            modified_content: Contenido del PDF modificado (bytes)
            
        Returns:
            Dict con rutas o None si falla
        """
        # Encontrar el grupo correcto
        group = self.find_group_for_file(original_path)
        if not group:
            print(f"DEBUG: No se encontró grupo para: {original_path}")
            return None
        
        # Establecer como grupo actual
        self.current_group = group
        
        filename = os.path.basename(original_path)
        
        result = {
            'modified': None,
            'original': None,
            'original_src': original_path,
            'original_dest': None,
            'group_name': group.name
        }
        
        try:
            # 1. Guardar contenido modificado en "Modificado - Sí"
            modified_dest = os.path.join(group.modified_folder, filename)
            
            if os.path.exists(modified_dest):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(modified_dest):
                    modified_dest = os.path.join(group.modified_folder, f"{base}_v{counter}{ext}")
                    counter += 1
            
            if modified_content:
                with open(modified_dest, 'wb') as f:
                    f.write(modified_content)
                result['modified'] = modified_dest
                print(f"DEBUG: ✅ Modificado guardado en: {modified_dest}")
            
            # 2. Calcular destino para el original (se moverá después de cerrar)
            original_dest = os.path.join(group.original_folder, filename)
            
            if os.path.exists(original_dest):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(original_dest):
                    original_dest = os.path.join(group.original_folder, f"{base}_bak{counter}{ext}")
                    counter += 1
            
            result['original_dest'] = original_dest
            result['original'] = original_dest
            
            return result
            
        except Exception as e:
            print(f"Error procesando PDF: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def move_original_to_archive(self, src_path: str, dest_path: str) -> bool:
        """
        Mueve el archivo original a la carpeta de archivados.
        Llamar DESPUÉS de cerrar el documento PDF.
        """
        try:
            if os.path.exists(src_path):
                shutil.move(src_path, dest_path)
                print(f"DEBUG: 📦 Original movido de {src_path} a {dest_path}")
                self._save_config()
                return True
            else:
                print(f"DEBUG: ⚠️ Archivo no existe: {src_path}")
                return False
        except Exception as e:
            print(f"Error moviendo archivo: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_stats(self) -> dict:
        """Obtiene estadísticas del grupo actual."""
        if not self.current_group:
            return {'pending': 0, 'modified': 0, 'archived': 0}
        
        return {
            'pending': self.current_group.get_pending_count(),
            'modified': self.current_group.get_modified_count(),
            'archived': self.current_group.get_archived_count()
        }
    
    def get_global_stats(self) -> dict:
        """Obtiene estadísticas globales de todos los grupos."""
        total_pending = sum(g.get_pending_count() for g in self.work_groups)
        total_modified = sum(g.get_modified_count() for g in self.work_groups)
        total_archived = sum(g.get_archived_count() for g in self.work_groups)
        
        return {
            'groups': len(self.work_groups),
            'pending': total_pending,
            'modified': total_modified,
            'archived': total_archived,
            'completed_groups': len([g for g in self.work_groups if g.is_complete()])
        }
    
    def clear_completed_groups(self):
        """Elimina grupos completados de la lista (no borra archivos)."""
        self.work_groups = [g for g in self.work_groups if not g.is_complete()]
        if self.current_group and self.current_group not in self.work_groups:
            self.current_group = self.work_groups[0] if self.work_groups else None
        self._save_config()
    
    def import_pdfs(self, pdf_paths: List[str]) -> Tuple[int, int]:
        """
        Compatibilidad: importa PDFs creando un nuevo grupo.
        
        Returns:
            Tupla (exitosos, fallidos)
        """
        if not pdf_paths:
            return (0, 0)
        
        group = self.create_new_group(pdf_paths)
        if group:
            return (group.get_pending_count(), len(pdf_paths) - group.get_pending_count())
        return (0, len(pdf_paths))
    
    # Compatibilidad adicional
    def create_workspace(self, parent_folder: str, workspace_name: str) -> bool:
        """Compatibilidad: crea el workspace en la carpeta especificada."""
        return self.set_base_path(parent_folder)
    
    def set_workspace(self, workspace_path: str) -> bool:
        """Compatibilidad: establece un workspace existente."""
        return self.set_base_path(workspace_path)
    
    def clear_workspace(self):
        """Desactiva el workspace actual."""
        self.current_group = None
        self._save_config()


# ============================================================
# Diálogos y Widgets de interfaz
# ============================================================

class WorkspaceSetupDialog(QDialog):
    """Diálogo para configurar el espacio de trabajo."""
    
    workspaceCreated = pyqtSignal(str)
    
    def __init__(self, parent=None, workspace_manager=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.selected_pdfs = []
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("📁 Configurar Espacio de Trabajo")
        self.setMinimumSize(750, 700)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #ffffff; font-size: 13px; }
            QLineEdit {
                background-color: #3d3d3d; color: #ffffff;
                border: 1px solid #555; border-radius: 4px;
                padding: 8px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #0078d4; }
            QPushButton {
                background-color: #0078d4; color: white;
                border: none; padding: 10px 20px;
                border-radius: 4px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1084d8; }
            QPushButton:disabled { background-color: #555; color: #888; }
            QPushButton.secondary { background-color: #3d3d3d; }
            QPushButton.secondary:hover { background-color: #4d4d4d; }
            QGroupBox {
                color: #ffffff; font-size: 14px; font-weight: bold;
                border: 1px solid #555; border-radius: 8px;
                margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QListWidget {
                background-color: #2d2d30; color: #ffffff;
                border: 1px solid #555; border-radius: 4px; font-size: 12px;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #3d3d3d; }
            QListWidget::item:selected { background-color: #0078d4; }
            QListWidget::item:hover { background-color: #3d3d3d; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("📁 Configurar Espacio de Trabajo")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)
        
        # Descripción del nuevo sistema
        desc_frame = QFrame()
        desc_frame.setStyleSheet("background: #252526; padding: 15px; border-radius: 8px;")
        desc_layout = QVBoxLayout(desc_frame)
        
        desc_title = QLabel("🆕 Sistema de Grupos de Trabajo Aislados")
        desc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
        desc_layout.addWidget(desc_title)
        
        desc = QLabel(
            "Cada vez que importes PDFs, se creará una <b>carpeta nueva y única</b> "
            "que contendrá las 3 subcarpetas del flujo de trabajo.<br><br>"
            "<b>Estados visuales:</b><br>"
            "📥 <span style='color:#ffcc00'>ORIGEN</span> → documento.pdf → ❌ Eliminado (al guardar)<br>"
            "✅ <span style='color:#4CAF50'>MODIFICADO - SÍ</span> → documento.pdf → ✨ Nuevo<br>"
            "📦 <span style='color:#9E9E9E'>MODIFICADO - NO</span> → documento.pdf → 🔒 Backup"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaa; font-size: 12px;")
        desc_layout.addWidget(desc)
        
        layout.addWidget(desc_frame)
        
        # === Sección 1: Carpeta base ===
        group1 = QGroupBox("1️⃣ Carpeta Base (donde se crearán los grupos)")
        group1_layout = QVBoxLayout(group1)
        
        folder_layout = QHBoxLayout()
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("Selecciona la carpeta donde se crearán los grupos de trabajo...")
        self.folder_path_edit.setReadOnly(True)
        
        # Si ya hay una base configurada, mostrarla
        if self.workspace_manager.base_path:
            self.folder_path_edit.setText(self.workspace_manager.base_path)
        
        folder_layout.addWidget(self.folder_path_edit)
        
        btn_browse = QPushButton("📂 Examinar")
        btn_browse.setProperty("class", "secondary")
        btn_browse.clicked.connect(self.browse_folder)
        folder_layout.addWidget(btn_browse)
        group1_layout.addLayout(folder_layout)
        
        # Sugerencia de Descargas
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(downloads_path):
            btn_downloads = QPushButton("📥 Usar carpeta Descargas")
            btn_downloads.setProperty("class", "secondary")
            btn_downloads.clicked.connect(lambda: self.folder_path_edit.setText(downloads_path))
            group1_layout.addWidget(btn_downloads)
        
        layout.addWidget(group1)
        
        # === Sección 2: Selección de PDFs ===
        group2 = QGroupBox("2️⃣ Crear Nuevo Grupo (arrastrar o seleccionar PDFs)")
        group2_layout = QVBoxLayout(group2)
        
        pdf_buttons_layout = QHBoxLayout()
        
        btn_add_files = QPushButton("📄 Agregar PDFs")
        btn_add_files.setProperty("class", "secondary")
        btn_add_files.clicked.connect(self.add_pdf_files)
        pdf_buttons_layout.addWidget(btn_add_files)
        
        btn_add_folder = QPushButton("📁 Agregar carpeta")
        btn_add_folder.setProperty("class", "secondary")
        btn_add_folder.clicked.connect(self.add_pdf_folder)
        pdf_buttons_layout.addWidget(btn_add_folder)
        
        btn_clear = QPushButton("🗑️ Limpiar")
        btn_clear.setProperty("class", "secondary")
        btn_clear.clicked.connect(self.clear_pdf_list)
        pdf_buttons_layout.addWidget(btn_clear)
        
        pdf_buttons_layout.addStretch()
        group2_layout.addLayout(pdf_buttons_layout)
        
        # Info sobre orden
        order_label = QLabel("💡 Los PDFs se importarán en el orden en que los selecciones")
        order_label.setStyleSheet("color: #888; font-size: 11px; font-style: italic;")
        group2_layout.addWidget(order_label)
        
        # Lista de PDFs
        self.pdf_list = QListWidget()
        self.pdf_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.pdf_list.setMinimumHeight(150)
        self.pdf_list.setAcceptDrops(True)
        group2_layout.addWidget(self.pdf_list)
        
        # Contador
        self.pdf_count_label = QLabel("0 PDFs seleccionados")
        self.pdf_count_label.setStyleSheet("color: #888;")
        group2_layout.addWidget(self.pdf_count_label)
        
        layout.addWidget(group2)
        
        # === Botones de acción ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("class", "secondary")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        
        self.btn_create = QPushButton("✅ Crear Grupo de Trabajo")
        self.btn_create.clicked.connect(self.create_workspace)
        self.btn_create.setEnabled(False)
        buttons_layout.addWidget(self.btn_create)
        
        layout.addLayout(buttons_layout)
        
        # Validación
        self.folder_path_edit.textChanged.connect(self.validate_inputs)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta base", os.path.expanduser("~")
        )
        if folder:
            self.folder_path_edit.setText(folder)
    
    def add_pdf_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar PDFs", "", "Archivos PDF (*.pdf)"
        )
        for file in files:
            if file not in self.selected_pdfs:
                self.selected_pdfs.append(file)
                idx = len(self.selected_pdfs)
                item = QListWidgetItem(f"{idx:03d}. 📄 {os.path.basename(file)}")
                item.setData(Qt.UserRole, file)
                self.pdf_list.addItem(item)
        self.update_pdf_count()
    
    def add_pdf_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con PDFs", "")
        if folder:
            pdf_files = sorted([f for f in os.listdir(folder) if f.lower().endswith('.pdf')])
            for file in pdf_files:
                full_path = os.path.join(folder, file)
                if full_path not in self.selected_pdfs:
                    self.selected_pdfs.append(full_path)
                    idx = len(self.selected_pdfs)
                    item = QListWidgetItem(f"{idx:03d}. 📄 {file}")
                    item.setData(Qt.UserRole, full_path)
                    self.pdf_list.addItem(item)
        self.update_pdf_count()
    
    def clear_pdf_list(self):
        self.selected_pdfs.clear()
        self.pdf_list.clear()
        self.update_pdf_count()
    
    def update_pdf_count(self):
        count = len(self.selected_pdfs)
        self.pdf_count_label.setText(f"{count} PDF{'s' if count != 1 else ''} seleccionado{'s' if count != 1 else ''}")
        self.validate_inputs()
    
    def validate_inputs(self):
        folder_ok = bool(self.folder_path_edit.text().strip())
        pdfs_ok = len(self.selected_pdfs) > 0
        self.btn_create.setEnabled(folder_ok and pdfs_ok)
    
    def create_workspace(self):
        base_path = self.folder_path_edit.text().strip()
        
        # Establecer la carpeta base
        if not self.workspace_manager.set_base_path(base_path):
            QMessageBox.critical(self, "Error", "No se pudo acceder a la carpeta seleccionada.")
            return
        
        # Crear nuevo grupo con los PDFs
        group = self.workspace_manager.create_new_group(self.selected_pdfs)
        
        if group:
            msg = f"✅ <b>Grupo de trabajo creado exitosamente</b><br><br>"
            msg += f"📁 <b>{group.name}</b><br><br>"
            msg += f"📄 {group.get_pending_count()} PDFs importados a Origen<br><br>"
            msg += f"<i>Abre los PDFs desde la vista de carpetas para editarlos.</i>"
            
            QMessageBox.information(self, "Éxito", msg)
            self.workspaceCreated.emit(group.path)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "No se pudo crear el grupo de trabajo.")


class WorkspaceStatusWidget(QFrame):
    """Widget que muestra el estado del workspace en la toolbar."""
    
    openPending = pyqtSignal()
    configureWorkspace = pyqtSignal()
    
    def __init__(self, workspace_manager: WorkspaceManager, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.setup_ui()
        self.update_status()
    
    def setup_ui(self):
        self.setStyleSheet("""
            WorkspaceStatusWidget {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QLabel { color: #ccc; font-size: 11px; }
            QPushButton {
                background-color: transparent;
                color: #0078d4;
                border: none;
                font-size: 11px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-radius: 3px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)
        
        self.status_label = QLabel("📁 Sin workspace")
        layout.addWidget(self.status_label)
        
        self.pending_label = QLabel("")
        self.pending_label.setStyleSheet("color: #ffcc00; font-weight: bold;")
        layout.addWidget(self.pending_label)
        
        self.btn_pending = QPushButton("📋 Ver grupos")
        self.btn_pending.clicked.connect(self.openPending.emit)
        self.btn_pending.hide()
        layout.addWidget(self.btn_pending)
        
        self.btn_config = QPushButton("⚙️ Configurar")
        self.btn_config.clicked.connect(self.configureWorkspace.emit)
        layout.addWidget(self.btn_config)
    
    def update_status(self):
        if self.workspace_manager.is_workspace_active():
            stats = self.workspace_manager.get_global_stats()
            
            if self.workspace_manager.current_group:
                group_name = self.workspace_manager.current_group.name
                # Truncar nombre si es muy largo
                display_name = group_name[:30] + "..." if len(group_name) > 30 else group_name
                self.status_label.setText(f"📁 {display_name}")
            else:
                self.status_label.setText(f"📁 {stats['groups']} grupo(s)")
            
            if stats['pending'] > 0:
                self.pending_label.setText(f"⏳ {stats['pending']} pendiente{'s' if stats['pending'] != 1 else ''}")
                self.pending_label.setStyleSheet("color: #ffcc00; font-weight: bold;")
                self.pending_label.show()
                self.btn_pending.show()
            else:
                self.pending_label.setText("✅ Todo completado")
                self.pending_label.setStyleSheet("color: #4CAF50;")
                self.pending_label.show()
                self.btn_pending.show()
            
            self.btn_config.setText("⚙️")
        else:
            self.status_label.setText("📁 Sin workspace")
            self.pending_label.hide()
            self.btn_pending.hide()
            self.btn_config.setText("⚙️ Configurar")


class PendingPDFsDialog(QDialog):
    """Diálogo para ver y gestionar grupos de trabajo."""
    
    pdfSelected = pyqtSignal(str)
    
    def __init__(self, workspace_manager: WorkspaceManager, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.setup_ui()
        self.load_groups()
    
    def setup_ui(self):
        self.setWindowTitle("📋 Grupos de Trabajo")
        self.setMinimumSize(750, 550)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #ffffff; font-size: 13px; }
            QPushButton {
                background-color: #0078d4; color: white;
                border: none; padding: 10px 20px;
                border-radius: 4px; font-size: 13px;
            }
            QPushButton:hover { background-color: #1084d8; }
            QPushButton.secondary { background-color: #3d3d3d; }
            QPushButton.secondary:hover { background-color: #4d4d4d; }
            QListWidget {
                background-color: #2d2d30; color: #ffffff;
                border: 1px solid #555; border-radius: 4px; font-size: 13px;
            }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #3d3d3d; }
            QListWidget::item:selected { background-color: #0078d4; }
            QListWidget::item:hover { background-color: #3d3d3d; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("📋 Grupos de Trabajo")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        layout.addWidget(title)
        
        # Leyenda de estados
        legend_frame = QFrame()
        legend_frame.setStyleSheet("background: #252526; border-radius: 6px; padding: 10px;")
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.addWidget(QLabel("📥 <span style='color:#ffcc00'>Pendiente</span>"))
        legend_layout.addWidget(QLabel("✅ <span style='color:#4CAF50'>Completado</span>"))
        legend_layout.addWidget(QLabel("📦 <span style='color:#9E9E9E'>Vacío</span>"))
        legend_layout.addStretch()
        layout.addWidget(legend_frame)
        
        # Stats globales
        stats = self.workspace_manager.get_global_stats()
        self.stats_label = QLabel(
            f"📊 {stats['groups']} grupos | {stats['pending']} pendientes | "
            f"{stats['modified']} modificados | {stats['archived']} archivados"
        )
        self.stats_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.stats_label)
        
        # Lista de grupos
        self.group_list = QListWidget()
        self.group_list.itemDoubleClicked.connect(self.open_group)
        layout.addWidget(self.group_list)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.setProperty("class", "secondary")
        btn_refresh.clicked.connect(self.load_groups)
        buttons_layout.addWidget(btn_refresh)
        
        btn_new_group = QPushButton("📥 Nuevo Grupo")
        btn_new_group.clicked.connect(self.create_new_group)
        buttons_layout.addWidget(btn_new_group)
        
        buttons_layout.addStretch()
        
        btn_open = QPushButton("📂 Ver Grupo Seleccionado")
        btn_open.clicked.connect(self.open_group)
        buttons_layout.addWidget(btn_open)
        
        layout.addLayout(buttons_layout)
    
    def load_groups(self):
        self.group_list.clear()
        
        groups = self.workspace_manager.work_groups
        
        if not groups:
            item = QListWidgetItem("📭 No hay grupos de trabajo.\n    Crea uno importando PDFs.")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self.group_list.addItem(item)
        else:
            for group in groups:
                pending = group.get_pending_count()
                modified = group.get_modified_count()
                archived = group.get_archived_count()
                
                # Estado del grupo
                if pending == 0 and modified > 0:
                    status_icon = "✅"
                    status_text = "Completado"
                elif pending > 0:
                    status_icon = "⏳"
                    status_text = f"{pending} pendiente{'s' if pending != 1 else ''}"
                else:
                    status_icon = "📦"
                    status_text = "Vacío"
                
                text = f"{status_icon} {group.name}\n"
                text += f"    📥 {pending} | ✅ {modified} | 📦 {archived}  —  {status_text}"
                
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, group)
                
                # Marcar grupo actual
                if group == self.workspace_manager.current_group:
                    item.setBackground(QColor(0, 120, 212, 50))
                
                self.group_list.addItem(item)
        
        # Actualizar stats
        stats = self.workspace_manager.get_global_stats()
        self.stats_label.setText(
            f"📊 {stats['groups']} grupos | {stats['pending']} pendientes | "
            f"{stats['modified']} modificados | {stats['archived']} archivados"
        )
    
    def open_group(self):
        current_item = self.group_list.currentItem()
        if current_item:
            group = current_item.data(Qt.UserRole)
            if group:
                self.workspace_manager.set_current_group(group)
                
                # Abrir diálogo visual del grupo
                dialog = GroupVisualDialog(self.workspace_manager, group, self.parent())
                dialog.pdfSelected.connect(self._on_pdf_selected)
                if dialog.exec_() == QDialog.Accepted:
                    self.accept()
                else:
                    self.load_groups()
    
    def _on_pdf_selected(self, path):
        self.pdfSelected.emit(path)
    
    def create_new_group(self):
        if not self.workspace_manager.is_workspace_active():
            QMessageBox.warning(
                self, "Sin carpeta base",
                "Primero debes configurar una carpeta base.\n\n"
                "Ve a Archivo → Espacio de Trabajo → Configurar Workspace"
            )
            return
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar PDFs para nuevo grupo", "", "Archivos PDF (*.pdf)"
        )
        
        if files:
            group = self.workspace_manager.create_new_group(files)
            if group:
                QMessageBox.information(
                    self, "Éxito",
                    f"✅ Grupo '<b>{group.name}</b>' creado<br><br>"
                    f"📄 {group.get_pending_count()} PDFs importados"
                )
                self.load_groups()


class FolderPanel(QFrame):
    """Panel visual para una carpeta del workspace con estados."""
    
    fileSelected = pyqtSignal(str)
    openFolder = pyqtSignal()
    
    def __init__(self, title: str, icon: str, color: str, description: str, 
                 status_icon: str = "", parent=None):
        super().__init__(parent)
        self.folder_path = None
        self.title = title
        self.color = color
        self.status_icon = status_icon
        
        self.setStyleSheet(f"""
            FolderPanel {{
                background-color: #252526;
                border: 2px solid {color};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Cabecera
        header = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 28px; color: {color}; background: transparent;")
        header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color}; background: transparent;")
        header.addWidget(title_label)
        
        header.addStretch()
        
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet(f"""
            background-color: {color};
            color: white;
            font-size: 14px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 12px;
        """)
        header.addWidget(self.count_label)
        
        layout.addLayout(header)
        
        # Descripción con estado
        desc_text = f"{status_icon} {description}" if status_icon else description
        desc_label = QLabel(desc_text)
        desc_label.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Lista de archivos
        self.file_list = QListWidget()
        self.file_list.setStyleSheet(f"""
            QListWidget {{
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                color: white;
                font-size: 12px;
            }}
            QListWidget::item {{ padding: 8px; border-bottom: 1px solid #333; }}
            QListWidget::item:selected {{ background-color: {color}; }}
            QListWidget::item:hover {{ background-color: #3d3d3d; }}
        """)
        self.file_list.setMinimumHeight(150)
        self.file_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.file_list)
        
        # Botón abrir carpeta
        btn_open = QPushButton(f"📂 Abrir carpeta")
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {color};
                border: 1px solid {color};
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: white;
            }}
        """)
        btn_open.clicked.connect(self.openFolder.emit)
        layout.addWidget(btn_open)
    
    def set_folder(self, folder_path: str):
        self.folder_path = folder_path
        self.refresh()
    
    def refresh(self):
        self.file_list.clear()
        
        if not self.folder_path or not os.path.exists(self.folder_path):
            self.count_label.setText("0")
            return
        
        files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.pdf')]
        files.sort()
        
        self.count_label.setText(str(len(files)))
        
        if not files:
            item = QListWidgetItem("(vacío)")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setForeground(Qt.gray)
            self.file_list.addItem(item)
        else:
            for filename in files:
                filepath = os.path.join(self.folder_path, filename)
                size = os.path.getsize(filepath) / 1024
                size_str = f"{size/1024:.1f} MB" if size > 1024 else f"{size:.0f} KB"
                
                # Estado visual según la carpeta
                if self.status_icon:
                    display = f"{self.status_icon} {filename} ({size_str})"
                else:
                    display = f"📄 {filename} ({size_str})"
                
                item = QListWidgetItem(display)
                item.setData(Qt.UserRole, filepath)
                self.file_list.addItem(item)
    
    def _on_item_double_clicked(self, item):
        filepath = item.data(Qt.UserRole)
        if filepath and os.path.exists(filepath):
            self.fileSelected.emit(filepath)


class GroupVisualDialog(QDialog):
    """Diálogo visual de un grupo de trabajo específico con estados."""
    
    pdfSelected = pyqtSignal(str)
    
    def __init__(self, workspace_manager: WorkspaceManager, group: WorkGroup, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.group = group
        self.setup_ui()
        self.refresh_all()
    
    def setup_ui(self):
        self.setWindowTitle(f"📁 {self.group.name}")
        self.setMinimumSize(1050, 650)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #ffffff; }
            QPushButton {
                background-color: #0078d4; color: white;
                border: none; padding: 10px 20px;
                border-radius: 4px; font-size: 13px;
            }
            QPushButton:hover { background-color: #1084d8; }
            QPushButton.secondary { background-color: #3d3d3d; }
            QPushButton.secondary:hover { background-color: #4d4d4d; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Cabecera
        header = QHBoxLayout()
        
        title = QLabel(f"📁 {self.group.name}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Estado del grupo
        if self.group.is_complete():
            status = QLabel("✅ COMPLETADO")
            status.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
        elif self.group.get_pending_count() > 0:
            status = QLabel(f"⏳ {self.group.get_pending_count()} PENDIENTES")
            status.setStyleSheet("color: #ffcc00; font-weight: bold; font-size: 14px;")
        else:
            status = QLabel("📦 VACÍO")
            status.setStyleSheet("color: #9E9E9E; font-weight: bold; font-size: 14px;")
        header.addWidget(status)
        
        layout.addLayout(header)
        
        # Diagrama de flujo visual mejorado
        flow_frame = QFrame()
        flow_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        flow_layout = QHBoxLayout(flow_frame)
        flow_layout.setContentsMargins(20, 15, 20, 15)
        flow_layout.setSpacing(10)
        
        # Estados con iconos claros
        state1 = QLabel("📥 ORIGEN\ndocumento.pdf\n❌ <i>Al guardar → Eliminado</i>")
        state1.setAlignment(Qt.AlignCenter)
        state1.setStyleSheet("color: #ffcc00; font-size: 11px; font-weight: bold;")
        flow_layout.addWidget(state1)
        
        arrow1 = QLabel("⬇️\nGuardar")
        arrow1.setAlignment(Qt.AlignCenter)
        arrow1.setStyleSheet("font-size: 16px; color: #888;")
        flow_layout.addWidget(arrow1)
        
        state2 = QLabel("✅ MODIFICADO - SÍ\ndocumento.pdf\n✨ <i>Nuevo (editado)</i>")
        state2.setAlignment(Qt.AlignCenter)
        state2.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;")
        flow_layout.addWidget(state2)
        
        plus_label = QLabel("+")
        plus_label.setStyleSheet("font-size: 20px; color: #888;")
        flow_layout.addWidget(plus_label)
        
        state3 = QLabel("📦 MODIFICADO - NO\ndocumento.pdf\n🔒 <i>Backup (original)</i>")
        state3.setAlignment(Qt.AlignCenter)
        state3.setStyleSheet("color: #9E9E9E; font-size: 11px; font-weight: bold;")
        flow_layout.addWidget(state3)
        
        layout.addWidget(flow_frame)
        
        # Paneles de las 3 carpetas con estados
        folders_layout = QHBoxLayout()
        folders_layout.setSpacing(15)
        
        self.panel_origin = FolderPanel(
            "ORIGEN", "📥", "#ffcc00",
            "PDFs pendientes. Doble clic para abrir.",
            "❌", self  # Status icon para archivos
        )
        self.panel_origin.fileSelected.connect(self._open_pdf)
        self.panel_origin.openFolder.connect(lambda: self._open_folder('origin'))
        folders_layout.addWidget(self.panel_origin)
        
        self.panel_modified = FolderPanel(
            "MODIFICADO - SÍ", "✅", "#4CAF50",
            "PDFs editados y guardados.",
            "✨", self
        )
        self.panel_modified.fileSelected.connect(self._open_pdf)
        self.panel_modified.openFolder.connect(lambda: self._open_folder('modified'))
        folders_layout.addWidget(self.panel_modified)
        
        self.panel_original = FolderPanel(
            "MODIFICADO - NO", "📦", "#9E9E9E",
            "Originales archivados (backup).",
            "🔒", self
        )
        self.panel_original.fileSelected.connect(self._open_pdf)
        self.panel_original.openFolder.connect(lambda: self._open_folder('original'))
        folders_layout.addWidget(self.panel_original)
        
        layout.addLayout(folders_layout)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.setProperty("class", "secondary")
        btn_refresh.clicked.connect(self.refresh_all)
        buttons_layout.addWidget(btn_refresh)
        
        buttons_layout.addStretch()
        
        btn_open = QPushButton("📂 Abrir siguiente pendiente")
        btn_open.clicked.connect(self._open_next_pending)
        buttons_layout.addWidget(btn_open)
        
        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("class", "secondary")
        btn_close.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_close)
        
        layout.addLayout(buttons_layout)
    
    def refresh_all(self):
        self.panel_origin.set_folder(self.group.origin_folder)
        self.panel_modified.set_folder(self.group.modified_folder)
        self.panel_original.set_folder(self.group.original_folder)
    
    def _open_pdf(self, filepath):
        self.pdfSelected.emit(filepath)
        self.accept()
    
    def _open_folder(self, folder_type):
        if folder_type == 'origin':
            folder = self.group.origin_folder
        elif folder_type == 'modified':
            folder = self.group.modified_folder
        else:
            folder = self.group.original_folder
        
        if folder and os.path.exists(folder):
            os.startfile(folder)
    
    def _open_next_pending(self):
        pending = self.group.get_pending_pdfs()
        if pending:
            self._open_pdf(pending[0])
        else:
            QMessageBox.information(
                self, "Sin pendientes",
                "✅ No hay PDFs pendientes en este grupo.\n\n"
                "Todos los archivos han sido procesados."
            )


# Alias para compatibilidad con código existente
class WorkspaceVisualDialog(PendingPDFsDialog):
    """Alias para mantener compatibilidad."""
    pass
