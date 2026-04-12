"""Diálogo de gestión de páginas del PDF.

Permite unir, dividir, extraer, eliminar y reordenar
páginas del documento PDF.
"""

import logging
import os
from typing import List, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QListWidget, QListWidgetItem, QPushButton,
    QLabel, QFileDialog, QLineEdit, QProgressBar,
    QGroupBox, QFormLayout, QSpinBox, QMessageBox,
    QAbstractItemView, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from ui.theme_manager import ThemeColor, ThemeStyles

logger = logging.getLogger(__name__)


class PageOperationWorker(QThread):
    """Worker para ejecutar operaciones de página en segundo plano."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, operation, kwargs, parent=None):
        """Inicializa el worker.

        Args:
            operation: Función de operación a ejecutar.
            kwargs: Argumentos para la operación.
        """
        super().__init__(parent)
        self._operation = operation
        self._kwargs = kwargs

    def run(self):
        """Ejecuta la operación."""
        try:
            result = self._operation(**self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Error en operación de página: {e}")
            self.error.emit(str(e))


class PageManagerDialog(QDialog):
    """Diálogo principal de gestión de páginas."""

    operation_completed = pyqtSignal(str)

    def __init__(self, file_path: str, page_count: int, parent=None):
        """Inicializa el diálogo.

        Args:
            file_path: Ruta del PDF actual.
            page_count: Número de páginas del documento.
        """
        super().__init__(parent)
        self._file_path = file_path
        self._page_count = page_count
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        """Configura la interfaz."""
        self.setWindowTitle("Gestión de páginas")
        self.setMinimumSize(550, 450)
        self.setStyleSheet(ThemeStyles.dialog())

        layout = QVBoxLayout(self)

        # Info
        info = QLabel(
            f"📄 {os.path.basename(self._file_path)} — "
            f"{self._page_count} páginas"
        )
        info.setStyleSheet(f"""
            color: {ThemeColor.TEXT_SECONDARY};
            font-size: 13px;
            font-weight: bold;
            padding: 4px;
        """)
        layout.addWidget(info)

        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                background-color: {ThemeColor.BG_PRIMARY};
            }}
            QTabBar::tab {{
                background-color: {ThemeColor.BG_SECONDARY};
                color: {ThemeColor.TEXT_PRIMARY};
                padding: 8px 14px;
                border: 1px solid {ThemeColor.BORDER_LIGHT};
            }}
            QTabBar::tab:selected {{
                background-color: {ThemeColor.ACCENT};
                color: white;
            }}
        """)

        tabs.addTab(self._create_merge_tab(), "📎 Unir")
        tabs.addTab(self._create_split_tab(), "✂️ Dividir")
        tabs.addTab(self._create_extract_tab(), "📤 Extraer")
        tabs.addTab(self._create_delete_tab(), "🗑️ Eliminar")
        tabs.addTab(self._create_reorder_tab(), "🔀 Reordenar")

        layout.addWidget(tabs)

        # Status
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(f"""
            color: {ThemeColor.TEXT_SECONDARY};
            font-size: 12px;
            padding: 4px;
        """)
        layout.addWidget(self._lbl_status)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.setStyleSheet(ThemeStyles.button_secondary())
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    # ─── Tab: Unir ───

    def _create_merge_tab(self) -> QWidget:
        """Crea la pestaña de unión de PDFs."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._merge_list = QListWidget()
        self._merge_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {ThemeColor.BG_TERTIARY};
                color: {ThemeColor.TEXT_PRIMARY};
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self._merge_list, stretch=1)

        btn_row = QHBoxLayout()

        btn_add = QPushButton("➕ Añadir PDF")
        btn_add.setStyleSheet(ThemeStyles.button_secondary())
        btn_add.clicked.connect(self._on_merge_add)
        btn_row.addWidget(btn_add)

        btn_remove = QPushButton("➖ Quitar")
        btn_remove.setStyleSheet(ThemeStyles.button_secondary())
        btn_remove.clicked.connect(self._on_merge_remove)
        btn_row.addWidget(btn_remove)

        btn_up = QPushButton("⬆")
        btn_up.setFixedWidth(40)
        btn_up.clicked.connect(lambda: self._move_merge_item(-1))
        btn_row.addWidget(btn_up)

        btn_down = QPushButton("⬇")
        btn_down.setFixedWidth(40)
        btn_down.clicked.connect(lambda: self._move_merge_item(1))
        btn_row.addWidget(btn_down)

        btn_row.addStretch()

        btn_merge = QPushButton("📎 Unir todos")
        btn_merge.setStyleSheet(ThemeStyles.button_primary())
        btn_merge.clicked.connect(self._on_merge)
        btn_row.addWidget(btn_merge)

        layout.addLayout(btn_row)

        # Pre-add current file
        self._merge_list.addItem(self._file_path)

        return widget

    def _on_merge_add(self):
        """Añade archivos PDF a la lista de unión."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar PDFs", "", "PDF (*.pdf)"
        )
        for path in paths:
            self._merge_list.addItem(path)

    def _on_merge_remove(self):
        """Quita el archivo seleccionado de la lista."""
        row = self._merge_list.currentRow()
        if row >= 0:
            self._merge_list.takeItem(row)

    def _move_merge_item(self, direction: int):
        """Mueve un item en la lista de unión."""
        row = self._merge_list.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if 0 <= new_row < self._merge_list.count():
            item = self._merge_list.takeItem(row)
            self._merge_list.insertItem(new_row, item)
            self._merge_list.setCurrentRow(new_row)

    def _on_merge(self):
        """Ejecuta la unión de PDFs."""
        if self._merge_list.count() < 2:
            self._lbl_status.setText("Añada al menos 2 PDFs para unir.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF unido", "", "PDF (*.pdf)"
        )
        if not output_path:
            return

        from core.page_manager import merge_pdfs

        paths = [
            self._merge_list.item(i).text()
            for i in range(self._merge_list.count())
        ]

        self._worker = PageOperationWorker(
            merge_pdfs, {"input_paths": paths, "output_path": output_path}
        )
        self._worker.finished.connect(self._on_operation_done)
        self._worker.error.connect(self._on_operation_error)
        self._worker.start()

    # ─── Tab: Dividir ───

    def _create_split_tab(self) -> QWidget:
        """Crea la pestaña de división."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Opciones de división")
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {ThemeColor.TEXT_PRIMARY};
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                padding: 0 6px;
            }}
        """)
        form = QFormLayout(group)

        self._txt_split_ranges = QLineEdit()
        self._txt_split_ranges.setPlaceholderText(
            "Ej: 1-3, 4-6, 7-10 (vacío = páginas individuales)"
        )
        self._txt_split_ranges.setStyleSheet(ThemeStyles.input_field())
        form.addRow("Rangos:", self._txt_split_ranges)

        layout.addWidget(group)

        info = QLabel(
            f"Total: {self._page_count} páginas. "
            "Deje vacío para dividir en páginas individuales."
        )
        info.setStyleSheet(f"color: {ThemeColor.TEXT_PLACEHOLDER}; font-size: 11px;")
        layout.addWidget(info)

        layout.addStretch()

        btn_split = QPushButton("✂️ Dividir")
        btn_split.setStyleSheet(ThemeStyles.button_primary())
        btn_split.clicked.connect(self._on_split)
        layout.addWidget(btn_split, alignment=Qt.AlignRight)

        return widget

    def _on_split(self):
        """Ejecuta la división del PDF."""
        output_dir = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de salida"
        )
        if not output_dir:
            return

        from core.page_manager import split_pdf, PageRange

        ranges_text = self._txt_split_ranges.text().strip()
        ranges = None

        if ranges_text:
            try:
                ranges = []
                for part in ranges_text.split(','):
                    ranges.append(
                        PageRange.from_string(part, self._page_count)
                    )
            except ValueError as e:
                self._lbl_status.setText(f"Error en rango: {e}")
                return

        self._worker = PageOperationWorker(
            split_pdf,
            {
                "input_path": self._file_path,
                "output_dir": output_dir,
                "ranges": ranges,
            },
        )
        self._worker.finished.connect(self._on_operation_done)
        self._worker.error.connect(self._on_operation_error)
        self._worker.start()

    # ─── Tab: Extraer ───

    def _create_extract_tab(self) -> QWidget:
        """Crea la pestaña de extracción."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Páginas a extraer")
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {ThemeColor.TEXT_PRIMARY};
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                padding: 0 6px;
            }}
        """)
        form = QFormLayout(group)

        self._txt_extract_pages = QLineEdit()
        self._txt_extract_pages.setPlaceholderText(
            "Ej: 1, 3, 5-8, 10"
        )
        self._txt_extract_pages.setStyleSheet(ThemeStyles.input_field())
        form.addRow("Páginas:", self._txt_extract_pages)

        layout.addWidget(group)
        layout.addStretch()

        btn_extract = QPushButton("📤 Extraer")
        btn_extract.setStyleSheet(ThemeStyles.button_primary())
        btn_extract.clicked.connect(self._on_extract)
        layout.addWidget(btn_extract, alignment=Qt.AlignRight)

        return widget

    def _on_extract(self):
        """Ejecuta la extracción de páginas."""
        indices = self._parse_page_list(self._txt_extract_pages.text())
        if indices is None:
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar páginas extraídas", "", "PDF (*.pdf)"
        )
        if not output_path:
            return

        from core.page_manager import extract_pages

        self._worker = PageOperationWorker(
            extract_pages,
            {
                "input_path": self._file_path,
                "output_path": output_path,
                "page_indices": indices,
            },
        )
        self._worker.finished.connect(self._on_operation_done)
        self._worker.error.connect(self._on_operation_error)
        self._worker.start()

    # ─── Tab: Eliminar ───

    def _create_delete_tab(self) -> QWidget:
        """Crea la pestaña de eliminación."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Páginas a eliminar")
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {ThemeColor.TEXT_PRIMARY};
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                padding: 0 6px;
            }}
        """)
        form = QFormLayout(group)

        self._txt_delete_pages = QLineEdit()
        self._txt_delete_pages.setPlaceholderText(
            "Ej: 2, 4, 7-9"
        )
        self._txt_delete_pages.setStyleSheet(ThemeStyles.input_field())
        form.addRow("Páginas:", self._txt_delete_pages)

        layout.addWidget(group)

        warn = QLabel(
            "⚠️ Esta operación guardará el resultado en un nuevo archivo."
        )
        warn.setStyleSheet(f"color: {ThemeColor.WARNING}; font-size: 11px;")
        layout.addWidget(warn)

        layout.addStretch()

        btn_delete = QPushButton("🗑️ Eliminar páginas")
        btn_delete.setStyleSheet(f"""
            QPushButton {{
                background-color: {ThemeColor.ERROR};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #d32f2f;
            }}
        """)
        btn_delete.clicked.connect(self._on_delete)
        layout.addWidget(btn_delete, alignment=Qt.AlignRight)

        return widget

    def _on_delete(self):
        """Ejecuta la eliminación de páginas."""
        indices = self._parse_page_list(self._txt_delete_pages.text())
        if indices is None:
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF sin páginas eliminadas", "", "PDF (*.pdf)"
        )
        if not output_path:
            return

        from core.page_manager import delete_pages

        self._worker = PageOperationWorker(
            delete_pages,
            {
                "input_path": self._file_path,
                "output_path": output_path,
                "page_indices": indices,
            },
        )
        self._worker.finished.connect(self._on_operation_done)
        self._worker.error.connect(self._on_operation_error)
        self._worker.start()

    # ─── Tab: Reordenar ───

    def _create_reorder_tab(self) -> QWidget:
        """Crea la pestaña de reordenamiento."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel("Arrastra las páginas para reordenar:")
        label.setStyleSheet(f"color: {ThemeColor.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(label)

        self._reorder_list = QListWidget()
        self._reorder_list.setDragDropMode(QAbstractItemView.InternalMove)
        self._reorder_list.setDefaultDropAction(Qt.MoveAction)
        self._reorder_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {ThemeColor.BG_TERTIARY};
                color: {ThemeColor.TEXT_PRIMARY};
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 4px;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {ThemeColor.BORDER_LIGHT};
            }}
            QListWidget::item:selected {{
                background-color: {ThemeColor.ACCENT};
                color: white;
            }}
        """)

        for i in range(self._page_count):
            self._reorder_list.addItem(f"Página {i + 1}")

        layout.addWidget(self._reorder_list, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_reorder = QPushButton("🔀 Aplicar nuevo orden")
        btn_reorder.setStyleSheet(ThemeStyles.button_primary())
        btn_reorder.clicked.connect(self._on_reorder)
        btn_row.addWidget(btn_reorder)

        layout.addLayout(btn_row)

        return widget

    def _on_reorder(self):
        """Ejecuta el reordenamiento de páginas."""
        new_order = []
        for i in range(self._reorder_list.count()):
            text = self._reorder_list.item(i).text()
            page_num = int(text.replace("Página ", "")) - 1
            new_order.append(page_num)

        if new_order == list(range(self._page_count)):
            self._lbl_status.setText("El orden no ha cambiado.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF reordenado", "", "PDF (*.pdf)"
        )
        if not output_path:
            return

        from core.page_manager import reorder_pages

        self._worker = PageOperationWorker(
            reorder_pages,
            {
                "input_path": self._file_path,
                "output_path": output_path,
                "new_order": new_order,
            },
        )
        self._worker.finished.connect(self._on_operation_done)
        self._worker.error.connect(self._on_operation_error)
        self._worker.start()

    # ─── Helpers ───

    def _parse_page_list(self, text: str) -> Optional[List[int]]:
        """Parsea una lista de páginas del input del usuario.

        Args:
            text: Texto como '1, 3, 5-8'.

        Returns:
            Lista de índices 0-based, o None si hay error.
        """
        text = text.strip()
        if not text:
            self._lbl_status.setText("Especifique las páginas.")
            return None

        try:
            indices = []
            for part in text.split(','):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-', 1)
                    start = int(a.strip())
                    end = int(b.strip())
                    if start < 1 or end < 1:
                        raise ValueError(f"Página inválida: {part}")
                    if start > self._page_count or end > self._page_count:
                        raise ValueError(f"Fuera de rango: {part}")
                    indices.extend(range(start - 1, end))
                else:
                    num = int(part)
                    if num < 1 or num > self._page_count:
                        raise ValueError(f"Fuera de rango: {num}")
                    indices.append(num - 1)

            return sorted(set(indices))
        except ValueError as e:
            self._lbl_status.setText(f"Error: {e}")
            return None

    def _on_operation_done(self, result):
        """Procesa el resultado de una operación."""
        if result.success:
            self._lbl_status.setText(f"✅ {result.message}")
            self.operation_completed.emit(result.output_path)
        else:
            self._lbl_status.setText(f"❌ {result.message}")
        self._worker = None

    def _on_operation_error(self, error_text: str):
        """Procesa un error de operación."""
        self._lbl_status.setText(f"❌ Error: {error_text}")
        self._worker = None
