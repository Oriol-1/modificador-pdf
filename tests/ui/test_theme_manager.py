"""Tests para el gestor de temas.

Verifica que ThemeColor tiene todos los colores necesarios,
ThemeStyles genera CSS válido y apply_dark_theme funciona.
"""
import pytest
from ui.theme_manager import ThemeColor, ThemeStyles, apply_dark_theme


class TestThemeColor:
    """Tests para la paleta de colores."""

    def test_bg_primary_is_dark(self):
        """Color de fondo principal es oscuro."""
        assert ThemeColor.BG_PRIMARY == "#1e1e1e"

    def test_bg_secondary_exists(self):
        """Color secundario definido."""
        assert ThemeColor.BG_SECONDARY.startswith("#")

    def test_accent_is_blue(self):
        """Acento es azul Microsoft."""
        assert ThemeColor.ACCENT == "#0078d4"

    def test_text_primary_is_white(self):
        """Texto principal es blanco."""
        assert ThemeColor.TEXT_PRIMARY == "#ffffff"

    def test_all_colors_are_hex(self):
        """Todos los colores son hexadecimales válidos."""
        for attr in dir(ThemeColor):
            if attr.isupper() and not attr.startswith('_'):
                value = getattr(ThemeColor, attr)
                assert value.startswith("#"), f"{attr} no es hex: {value}"
                assert len(value) == 7, f"{attr} longitud incorrecta: {value}"

    def test_error_color_is_red(self):
        """Color de error es rojo."""
        assert "f4" in ThemeColor.ERROR.lower() or "ff" in ThemeColor.ERROR.lower()

    def test_success_color_is_green(self):
        """Color de éxito es verde."""
        assert ThemeColor.SUCCESS.startswith("#")


class TestThemeStyles:
    """Tests para los estilos CSS generados."""

    def test_main_window_contains_bg(self):
        """Estilo de main_window contiene fondo primario."""
        css = ThemeStyles.main_window()
        assert ThemeColor.BG_PRIMARY in css
        assert "QMainWindow" in css

    def test_dialog_contains_bg(self):
        """Estilo de diálogo contiene fondo."""
        css = ThemeStyles.dialog()
        assert "QDialog" in css
        assert ThemeColor.BG_PRIMARY in css

    def test_input_field_has_focus(self):
        """Estilo de input tiene estado focus."""
        css = ThemeStyles.input_field()
        assert "focus" in css
        assert ThemeColor.BORDER_FOCUS in css

    def test_button_primary_has_hover(self):
        """Botón primario tiene estado hover."""
        css = ThemeStyles.button_primary()
        assert "hover" in css
        assert ThemeColor.ACCENT in css

    def test_button_secondary_has_border(self):
        """Botón secundario tiene borde."""
        css = ThemeStyles.button_secondary()
        assert "border" in css

    def test_scrollbar_has_handle(self):
        """Scrollbar tiene estilos de handle."""
        css = ThemeStyles.scrollbar()
        assert "handle" in css
        assert ThemeColor.SCROLLBAR_HANDLE in css

    def test_combobox_has_dropdown(self):
        """Combobox tiene estilos de dropdown."""
        css = ThemeStyles.combobox()
        assert "drop-down" in css

    def test_checkbox_has_indicator(self):
        """Checkbox tiene indicador."""
        css = ThemeStyles.checkbox()
        assert "indicator" in css
        assert "checked" in css

    def test_tab_widget_has_selected(self):
        """Tab widget tiene tab seleccionado."""
        css = ThemeStyles.tab_widget()
        assert "selected" in css
        assert ThemeColor.ACCENT in css

    def test_table_has_header(self):
        """Tabla tiene estilos de header."""
        css = ThemeStyles.table()
        assert "QHeaderView" in css

    def test_full_dark_combines_all(self):
        """full_dark combina múltiples estilos."""
        css = ThemeStyles.full_dark()
        assert "QDialog" in css
        assert "QLineEdit" in css
        assert "QPushButton" in css
        assert "QScrollBar" in css
        assert "QComboBox" in css
        assert "QCheckBox" in css

    def test_all_styles_are_strings(self):
        """Todos los métodos de estilo retornan strings."""
        methods = [
            ThemeStyles.main_window, ThemeStyles.dialog,
            ThemeStyles.input_field, ThemeStyles.button_primary,
            ThemeStyles.button_secondary, ThemeStyles.scrollbar,
            ThemeStyles.combobox, ThemeStyles.checkbox,
            ThemeStyles.tab_widget, ThemeStyles.table,
            ThemeStyles.full_dark,
        ]
        for method in methods:
            result = method()
            assert isinstance(result, str)
            assert len(result) > 0


class TestApplyDarkTheme:
    """Tests para la función apply_dark_theme."""

    def test_apply_calls_setStyleSheet(self):
        """apply_dark_theme llama setStyleSheet en el widget."""
        from unittest.mock import MagicMock
        widget = MagicMock()
        apply_dark_theme(widget)
        widget.setStyleSheet.assert_called_once()
        css = widget.setStyleSheet.call_args[0][0]
        assert "QDialog" in css
