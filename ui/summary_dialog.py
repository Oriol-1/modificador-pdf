"""
SummaryDialog - Diálogo de resumen de cambios para PDF Editor Pro

PHASE2-203: Summary Dialog
Muestra análisis de métricas, fuentes usadas y cambios por página.
"""

from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QTextEdit, QProgressBar,
    QScrollArea, QFrame
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

from core.change_report import ChangeReport, ChangeType, get_change_report

import logging
logger = logging.getLogger(__name__)


class StatWidget(QFrame):
    """Widget para mostrar una estadística."""
    
    def __init__(
        self,
        title: str,
        value: str,
        icon: str = "📊",
        color: str = "#0078d4",
        parent=None
    ):
        super().__init__(parent)
        self.setStyleSheet(f"""
            StatWidget {{
                background-color: #2d2d30;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        # Icono y título
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 20px; background: transparent;")
        header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Valor
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold; background: transparent;")
        layout.addWidget(value_label)
        
        self.value_label = value_label
    
    def set_value(self, value: str):
        """Actualiza el valor."""
        self.value_label.setText(value)


class FontUsageTable(QTableWidget):
    """Tabla de uso de fuentes."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Fuente", "Usos", "Porcentaje"])
        
        self.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d30;
                color: white;
                border: 1px solid #555;
                gridline-color: #444;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: white;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #555;
            }
        """)
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
    
    def set_data(self, font_usage: Dict[str, int]):
        """Establece los datos de uso de fuentes."""
        self.setRowCount(0)
        
        if not font_usage:
            return
        
        total = sum(font_usage.values())
        
        # Ordenar por uso
        sorted_fonts = sorted(font_usage.items(), key=lambda x: x[1], reverse=True)
        
        for font_name, count in sorted_fonts:
            row = self.rowCount()
            self.insertRow(row)
            
            # Nombre
            self.setItem(row, 0, QTableWidgetItem(font_name))
            
            # Usos
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 1, count_item)
            
            # Porcentaje
            percentage = (count / total * 100) if total > 0 else 0
            pct_item = QTableWidgetItem(f"{percentage:.1f}%")
            pct_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 2, pct_item)


class ChangesByPageTable(QTableWidget):
    """Tabla de cambios por página."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Página", "Ediciones", "Añadidos", "Eliminados"])
        
        self.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d30;
                color: white;
                border: 1px solid #555;
                gridline-color: #444;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: white;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #555;
            }
        """)
        
        header = self.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
    
    def set_data(self, changes_by_page: Dict[int, Dict[str, int]]):
        """Establece los datos de cambios por página."""
        self.setRowCount(0)
        
        for page, changes in sorted(changes_by_page.items()):
            row = self.rowCount()
            self.insertRow(row)
            
            # Página (1-indexed para usuario)
            page_item = QTableWidgetItem(str(page + 1))
            page_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 0, page_item)
            
            # Ediciones
            edits = changes.get("edits", 0)
            edit_item = QTableWidgetItem(str(edits))
            edit_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 1, edit_item)
            
            # Añadidos
            adds = changes.get("adds", 0)
            add_item = QTableWidgetItem(str(adds))
            add_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 2, add_item)
            
            # Eliminados
            deletes = changes.get("deletes", 0)
            del_item = QTableWidgetItem(str(deletes))
            del_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 3, del_item)


class SummaryDialog(QDialog):
    """
    Diálogo de resumen de cambios.
    
    Muestra:
    - Estadísticas generales
    - Cambios por página
    - Fuentes utilizadas
    - Detalle de cambios
    """
    
    def __init__(
        self,
        parent=None,
        report: Optional[ChangeReport] = None,
        document_path: Optional[str] = None
    ):
        super().__init__(parent)
        
        self.report = report or get_change_report()
        self.document_path = document_path
        
        self.setWindowTitle("📊 Resumen de Cambios")
        self.setMinimumSize(700, 550)
        self._setup_style()
        self._setup_ui()
        self._load_data()
    
    def _setup_style(self):
        """Configura el estilo."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #252526;
            }
            QTabBar::tab {
                background-color: #2d2d30;
                color: #888;
                padding: 10px 20px;
                border: none;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                color: white;
                border-bottom: 2px solid #0078d4;
            }
            QTabBar::tab:hover {
                color: #ccc;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton#exportBtn {
                background-color: #3d3d3d;
                border: 1px solid #555;
            }
            QPushButton#exportBtn:hover {
                background-color: #4d4d4d;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTextEdit {
                background-color: #2d2d30;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
    
    def _setup_ui(self):
        """Configura la interfaz."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header con info del documento
        header_layout = QHBoxLayout()
        
        doc_label = QLabel(f"📄 {self.document_path or 'Documento sin guardar'}")
        doc_label.setStyleSheet("font-size: 14px; color: #ccc;")
        header_layout.addWidget(doc_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Estadísticas rápidas
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.total_stat = StatWidget("Total Cambios", "0", "📝", "#0078d4")
        self.edits_stat = StatWidget("Ediciones", "0", "✏️", "#4CAF50")
        self.adds_stat = StatWidget("Añadidos", "0", "➕", "#2196F3")
        self.deletes_stat = StatWidget("Eliminados", "0", "🗑️", "#f44336")
        
        stats_layout.addWidget(self.total_stat)
        stats_layout.addWidget(self.edits_stat)
        stats_layout.addWidget(self.adds_stat)
        stats_layout.addWidget(self.deletes_stat)
        
        layout.addLayout(stats_layout)
        
        # Tabs
        tabs = QTabWidget()
        
        # Tab 1: Por página
        page_tab = QWidget()
        page_layout = QVBoxLayout(page_tab)
        self.pages_table = ChangesByPageTable()
        page_layout.addWidget(self.pages_table)
        tabs.addTab(page_tab, "📄 Por Página")
        
        # Tab 2: Fuentes
        fonts_tab = QWidget()
        fonts_layout = QVBoxLayout(fonts_tab)
        self.fonts_table = FontUsageTable()
        fonts_layout.addWidget(self.fonts_table)
        tabs.addTab(fonts_tab, "🔤 Fuentes")
        
        # Tab 3: Detalle
        detail_tab = QWidget()
        detail_layout = QVBoxLayout(detail_tab)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        tabs.addTab(detail_tab, "📋 Detalle")
        
        layout.addWidget(tabs)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        export_btn = QPushButton("📥 Exportar JSON")
        export_btn.setObjectName("exportBtn")
        export_btn.clicked.connect(self._export_json)
        btn_layout.addWidget(export_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_data(self):
        """Carga los datos del reporte."""
        if not self.report:
            return
        
        stats = self.report.get_statistics()
        
        # Estadísticas generales
        total = stats.get("total_changes", 0)
        self.total_stat.set_value(str(total))
        
        by_type = stats.get("changes_by_type", {})
        edits = by_type.get("text_edit", 0)
        adds = by_type.get("text_add", 0)
        deletes = by_type.get("text_delete", 0)
        
        self.edits_stat.set_value(str(edits))
        self.adds_stat.set_value(str(adds))
        self.deletes_stat.set_value(str(deletes))
        
        # Cambios por página (formato detallado)
        changes_by_page = self._calculate_detailed_by_page()
        self.pages_table.set_data(changes_by_page)
        
        # Fuentes
        font_usage = self._calculate_font_usage()
        self.fonts_table.set_data(font_usage)
        
        # Detalle
        self.detail_text.setPlainText(self.report.generate_summary())
    
    def _calculate_detailed_by_page(self) -> Dict[int, Dict[str, int]]:
        """Calcula cambios detallados por página."""
        result = {}
        
        for change in self.report.changes:
            page = change.position.page
            
            if page not in result:
                result[page] = {"edits": 0, "adds": 0, "deletes": 0}
            
            if change.change_type == ChangeType.TEXT_EDIT:
                result[page]["edits"] += 1
            elif change.change_type == ChangeType.TEXT_ADD:
                result[page]["adds"] += 1
            elif change.change_type == ChangeType.TEXT_DELETE:
                result[page]["deletes"] += 1
        
        return result
    
    def _calculate_font_usage(self) -> Dict[str, int]:
        """Calcula uso de fuentes."""
        result = {}
        
        for change in self.report.changes:
            if change.font_info:
                font_name = change.font_info.name
                result[font_name] = result.get(font_name, 0) + 1
        
        return result
    
    def _export_json(self):
        """Exporta el reporte a JSON."""
        from PyQt5.QtWidgets import QFileDialog
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Reporte",
            "change_report.json",
            "JSON Files (*.json)"
        )
        
        if filepath:
            if self.report.export_json(filepath):
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "Exportación Exitosa",
                    f"Reporte exportado a:\n{filepath}"
                )
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se pudo exportar el reporte."
                )
    
    @staticmethod
    def show_summary(
        parent=None,
        report: Optional[ChangeReport] = None,
        document_path: Optional[str] = None
    ):
        """
        Muestra el diálogo de resumen.
        
        Args:
            parent: Widget padre
            report: ChangeReport (usa global si None)
            document_path: Ruta del documento
        """
        dialog = SummaryDialog(parent, report, document_path)
        dialog.exec_()


class QuickStatsWidget(QWidget):
    """
    Widget compacto de estadísticas para la barra de estado.
    
    Muestra un resumen rápido de cambios pendientes.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.report = None
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        self.changes_label = QLabel("📝 0 cambios")
        self.changes_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.changes_label)
        
        self.setVisible(False)
    
    def update_stats(self, report: Optional[ChangeReport] = None):
        """Actualiza las estadísticas."""
        self.report = report or get_change_report()
        
        count = len(self.report)
        
        if count > 0:
            self.changes_label.setText(f"📝 {count} cambio{'s' if count != 1 else ''}")
            self.changes_label.setStyleSheet("color: #0078d4; font-size: 11px;")
            self.setVisible(True)
        else:
            self.setVisible(False)
    
    def clear(self):
        """Limpia el widget."""
        self.changes_label.setText("📝 0 cambios")
        self.setVisible(False)
