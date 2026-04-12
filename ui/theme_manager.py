"""Gestor centralizado de temas para PDF Editor Pro.

Provee constantes de color, estilos CSS reutilizables y métodos
para aplicar el tema oscuro de forma consistente a toda la UI.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ThemeColor:
    """Paleta de colores del tema oscuro."""
    
    # Backgrounds
    BG_PRIMARY = "#1e1e1e"
    BG_SECONDARY = "#2d2d30"
    BG_TERTIARY = "#252526"
    BG_INPUT = "#3c3c3c"
    BG_HOVER = "#3e3e42"
    BG_SELECTED = "#094771"
    
    # Accent
    ACCENT = "#0078d4"
    ACCENT_HOVER = "#1a8ad4"
    ACCENT_PRESSED = "#005a9e"
    
    # Text
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#cccccc"
    TEXT_DISABLED = "#666666"
    TEXT_PLACEHOLDER = "#888888"
    
    # Borders
    BORDER = "#3e3e42"
    BORDER_FOCUS = "#0078d4"
    BORDER_LIGHT = "#555555"
    
    # Status
    SUCCESS = "#89d185"
    WARNING = "#ffcc00"
    ERROR = "#f44747"
    INFO = "#3794ff"
    
    # Viewer
    VIEWER_BG = "#323232"
    
    # Scrollbar
    SCROLLBAR_BG = "#2d2d30"
    SCROLLBAR_HANDLE = "#5a5a5a"
    SCROLLBAR_HOVER = "#787878"


class ThemeStyles:
    """Estilos CSS reutilizables para widgets comunes."""
    
    @staticmethod
    def main_window() -> str:
        """Estilo para QMainWindow."""
        c = ThemeColor
        return f"""
            QMainWindow {{ background-color: {c.BG_PRIMARY}; }}
            QMenuBar {{ background-color: {c.BG_SECONDARY}; color: {c.TEXT_SECONDARY}; }}
            QMenuBar::item:selected {{ background-color: {c.ACCENT}; }}
            QMenu {{ background-color: {c.BG_SECONDARY}; color: {c.TEXT_SECONDARY}; border: 1px solid {c.BORDER_LIGHT}; }}
            QMenu::item:selected {{ background-color: {c.ACCENT}; }}
            QToolBar {{ background-color: {c.BG_SECONDARY}; border: none; spacing: 5px; padding: 5px; }}
            QToolButton {{ background-color: transparent; color: {c.TEXT_SECONDARY}; border: none; padding: 8px 12px; border-radius: 4px; font-size: 13px; }}
            QToolButton:hover {{ background-color: {c.BG_HOVER}; }}
            QToolButton:checked {{ background-color: {c.ACCENT}; color: white; }}
            QStatusBar {{ background-color: #007acc; color: white; }}
            QSplitter::handle {{ background-color: {c.BG_HOVER}; }}
        """
    
    @staticmethod
    def dialog() -> str:
        """Estilo base para diálogos."""
        c = ThemeColor
        return f"""
            QDialog {{ background-color: {c.BG_PRIMARY}; color: {c.TEXT_PRIMARY}; }}
            QGroupBox {{
                border: 1px solid {c.BORDER}; border-radius: 4px;
                margin-top: 8px; padding-top: 12px;
                color: {c.TEXT_PRIMARY}; font-weight: bold;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 8px; color: {c.ACCENT}; }}
            QLabel {{ color: {c.TEXT_SECONDARY}; }}
        """
    
    @staticmethod
    def input_field() -> str:
        """Estilo para campos de entrada."""
        c = ThemeColor
        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {c.BG_INPUT}; color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER}; border-radius: 3px;
                padding: 4px 8px;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {c.BORDER_FOCUS};
            }}
        """
    
    @staticmethod
    def button_primary() -> str:
        """Estilo para botones primarios."""
        c = ThemeColor
        return f"""
            QPushButton {{
                background-color: {c.ACCENT}; color: {c.TEXT_PRIMARY};
                border: none; border-radius: 3px;
                padding: 6px 16px; min-width: 80px;
            }}
            QPushButton:hover {{ background-color: {c.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {c.ACCENT_PRESSED}; }}
            QPushButton:disabled {{ background-color: {c.BG_HOVER}; color: {c.TEXT_DISABLED}; }}
        """
    
    @staticmethod
    def button_secondary() -> str:
        """Estilo para botones secundarios."""
        c = ThemeColor
        return f"""
            QPushButton {{
                background-color: {c.BG_HOVER}; color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER}; border-radius: 3px;
                padding: 6px 16px; min-width: 80px;
            }}
            QPushButton:hover {{ background-color: {c.BORDER_LIGHT}; }}
        """
    
    @staticmethod
    def scrollbar() -> str:
        """Estilo para scrollbars."""
        c = ThemeColor
        return f"""
            QScrollBar:vertical {{
                background: {c.SCROLLBAR_BG}; width: 12px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {c.SCROLLBAR_HANDLE}; border-radius: 6px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {c.SCROLLBAR_HOVER}; }}
            QScrollBar:horizontal {{
                background: {c.SCROLLBAR_BG}; height: 12px; border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {c.SCROLLBAR_HANDLE}; border-radius: 6px; min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{ background: {c.SCROLLBAR_HOVER}; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
        """
    
    @staticmethod
    def combobox() -> str:
        """Estilo para combobox."""
        c = ThemeColor
        return f"""
            QComboBox {{
                background-color: {c.BG_INPUT}; color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER}; border-radius: 3px;
                padding: 4px 8px;
            }}
            QComboBox:focus {{ border-color: {c.BORDER_FOCUS}; }}
            QComboBox::drop-down {{
                border: none; width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c.BG_SECONDARY}; color: {c.TEXT_PRIMARY};
                selection-background-color: {c.ACCENT};
                border: 1px solid {c.BORDER};
            }}
        """
    
    @staticmethod
    def checkbox() -> str:
        """Estilo para checkboxes."""
        c = ThemeColor
        return f"""
            QCheckBox {{ color: {c.TEXT_SECONDARY}; spacing: 4px; }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border: 1px solid {c.BORDER}; border-radius: 3px;
                background-color: {c.BG_INPUT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {c.ACCENT};
                border-color: {c.ACCENT};
            }}
        """
    
    @staticmethod
    def tab_widget() -> str:
        """Estilo para QTabWidget."""
        c = ThemeColor
        return f"""
            QTabWidget::pane {{ border: 1px solid {c.BORDER}; }}
            QTabBar::tab {{
                background: {c.BG_SECONDARY}; color: {c.TEXT_SECONDARY};
                padding: 6px 12px; border: 1px solid {c.BORDER};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                background: {c.BG_PRIMARY}; color: {c.TEXT_PRIMARY};
                border-bottom: 2px solid {c.ACCENT};
            }}
            QTabBar::tab:hover {{ background: {c.BG_HOVER}; }}
        """
    
    @staticmethod
    def table() -> str:
        """Estilo para QTableWidget."""
        c = ThemeColor
        return f"""
            QTableWidget {{
                background: {c.BG_PRIMARY};
                gridline-color: {c.BORDER};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
            }}
            QHeaderView::section {{
                background: {c.BG_SECONDARY}; color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER}; padding: 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {c.BG_SELECTED};
            }}
        """
    
    @staticmethod
    def message_box() -> str:
        """Estilo para QMessageBox."""
        c = ThemeColor
        return f"""
            QMessageBox {{ background-color: {c.BG_SECONDARY}; }}
            QMessageBox QLabel {{ color: {c.TEXT_PRIMARY}; font-size: 13px; }}
            QPushButton {{
                background-color: {c.ACCENT}; color: white;
                border: none; padding: 8px 20px;
                border-radius: 4px; font-size: 12px; min-width: 80px;
            }}
            QPushButton:hover {{ background-color: {c.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {c.ACCENT_PRESSED}; }}
        """
    
    @staticmethod
    def full_dark() -> str:
        """Combinación completa de todos los estilos para un widget."""
        return (
            ThemeStyles.dialog()
            + ThemeStyles.input_field()
            + ThemeStyles.button_primary()
            + ThemeStyles.scrollbar()
            + ThemeStyles.combobox()
            + ThemeStyles.checkbox()
        )


def apply_dark_theme(widget) -> None:
    """Aplica el tema oscuro completo a cualquier widget.
    
    Args:
        widget: QWidget al que aplicar el tema.
    """
    widget.setStyleSheet(ThemeStyles.full_dark())
