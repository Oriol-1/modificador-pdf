"""Diálogo de traducción de documentos PDF.

Permite traducir páginas del documento usando IA con
vista previa y barra de progreso.
"""

import logging
from typing import List, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QRadioButton, QButtonGroup, QSpinBox,
    QPushButton, QLabel, QProgressBar, QTextEdit,
    QGroupBox, QSplitter, QWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from ui.theme_manager import ThemeColor, ThemeStyles
from core.ai.ai_config import AIConfig
from core.ai.translator import (
    TranslationLanguage, TranslationResult,
    translate_pages,
)

logger = logging.getLogger(__name__)


class TranslationWorker(QThread):
    """Worker para ejecutar traducción en segundo plano."""

    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(
        self,
        page_texts: List[str],
        source_lang: TranslationLanguage,
        target_lang: TranslationLanguage,
        config: AIConfig,
        parent=None,
    ):
        """Inicializa el worker de traducción."""
        super().__init__(parent)
        self._page_texts = page_texts
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._config = config

    def run(self):
        """Ejecuta la traducción."""
        try:
            results = translate_pages(
                self._page_texts,
                self._source_lang,
                self._target_lang,
                self._config,
                progress_callback=lambda cur, total: self.progress.emit(cur, total),
            )
            self.finished.emit(results)
        except Exception as e:
            logger.error(f"Error en traducción: {e}")
            self.error.emit(str(e))


class TranslationDialog(QDialog):
    """Diálogo de traducción de documentos PDF."""

    translation_completed = pyqtSignal(list)

    def __init__(
        self,
        page_texts: List[str],
        config: AIConfig,
        parent=None,
    ):
        """Inicializa el diálogo de traducción.

        Args:
            page_texts: Textos de cada página del documento.
            config: Configuración de IA.
        """
        super().__init__(parent)
        self._page_texts = page_texts
        self._config = config
        self._results: List[TranslationResult] = []
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        """Configura la interfaz."""
        self.setWindowTitle("Traducir documento")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(ThemeStyles.dialog())

        layout = QVBoxLayout(self)

        # Language selection
        lang_group = QGroupBox("Idiomas")
        lang_group.setStyleSheet(f"""
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
        lang_layout = QFormLayout(lang_group)

        self._cmb_source = QComboBox()
        self._cmb_target = QComboBox()

        for lang in TranslationLanguage:
            self._cmb_source.addItem(lang.value, lang)
            self._cmb_target.addItem(lang.value, lang)

        self._cmb_source.setCurrentIndex(0)  # Spanish
        self._cmb_target.setCurrentIndex(1)  # English

        lang_layout.addRow("Idioma origen:", self._cmb_source)
        lang_layout.addRow("Idioma destino:", self._cmb_target)

        layout.addWidget(lang_group)

        # Page range
        range_group = QGroupBox("Páginas")
        range_group.setStyleSheet(lang_group.styleSheet())
        range_layout = QHBoxLayout(range_group)

        self._radio_all = QRadioButton("Todas")
        self._radio_all.setChecked(True)
        self._radio_range = QRadioButton("Rango:")

        self._group_range = QButtonGroup()
        self._group_range.addButton(self._radio_all)
        self._group_range.addButton(self._radio_range)

        self._spn_from = QSpinBox()
        self._spn_from.setRange(1, max(1, len(self._page_texts)))
        self._spn_from.setValue(1)
        self._spn_from.setEnabled(False)

        self._spn_to = QSpinBox()
        self._spn_to.setRange(1, max(1, len(self._page_texts)))
        self._spn_to.setValue(len(self._page_texts))
        self._spn_to.setEnabled(False)

        self._radio_range.toggled.connect(self._spn_from.setEnabled)
        self._radio_range.toggled.connect(self._spn_to.setEnabled)

        range_layout.addWidget(self._radio_all)
        range_layout.addWidget(self._radio_range)
        range_layout.addWidget(self._spn_from)
        range_layout.addWidget(QLabel("a"))
        range_layout.addWidget(self._spn_to)
        range_layout.addStretch()

        layout.addWidget(range_group)

        # Preview area
        splitter = QSplitter(Qt.Horizontal)

        original_widget = QWidget()
        orig_layout = QVBoxLayout(original_widget)
        orig_layout.setContentsMargins(0, 0, 0, 0)
        orig_layout.addWidget(QLabel("Original"))
        self._txt_original = QTextEdit()
        self._txt_original.setReadOnly(True)
        self._txt_original.setStyleSheet(f"""
            QTextEdit {{
                background-color: {ThemeColor.BG_TERTIARY};
                color: {ThemeColor.TEXT_PRIMARY};
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                border-radius: 4px;
            }}
        """)
        orig_layout.addWidget(self._txt_original)
        splitter.addWidget(original_widget)

        translated_widget = QWidget()
        trans_layout = QVBoxLayout(translated_widget)
        trans_layout.setContentsMargins(0, 0, 0, 0)
        trans_layout.addWidget(QLabel("Traducción"))
        self._txt_translated = QTextEdit()
        self._txt_translated.setReadOnly(True)
        self._txt_translated.setStyleSheet(
            self._txt_original.styleSheet()
        )
        trans_layout.addWidget(self._txt_translated)
        splitter.addWidget(translated_widget)

        layout.addWidget(splitter, stretch=1)

        # Progress
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.hide()
        layout.addWidget(self._progress)

        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(f"""
            color: {ThemeColor.TEXT_SECONDARY};
            font-size: 12px;
        """)
        self._lbl_status.hide()
        layout.addWidget(self._lbl_status)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_translate = QPushButton("🌐 Traducir")
        self._btn_translate.setStyleSheet(ThemeStyles.button_primary())
        self._btn_translate.clicked.connect(self._on_translate)
        btn_layout.addWidget(self._btn_translate)

        btn_close = QPushButton("Cerrar")
        btn_close.setStyleSheet(ThemeStyles.button_secondary())
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        # Info label
        info = QLabel(
            f"📄 {len(self._page_texts)} páginas disponibles. "
            f"Requiere un proveedor de IA configurado."
        )
        info.setStyleSheet(f"""
            color: {ThemeColor.TEXT_PLACEHOLDER};
            font-size: 11px;
        """)
        layout.addWidget(info)

    def _get_selected_pages(self) -> List[str]:
        """Obtiene los textos de las páginas seleccionadas."""
        if self._radio_all.isChecked():
            return list(self._page_texts)

        start = self._spn_from.value() - 1
        end = self._spn_to.value()
        return list(self._page_texts[start:end])

    def _on_translate(self):
        """Inicia la traducción."""
        source = self._cmb_source.currentData()
        target = self._cmb_target.currentData()

        if source == target:
            self._lbl_status.setText("Los idiomas de origen y destino deben ser diferentes.")
            self._lbl_status.show()
            return

        if not self._config.has_llm:
            self._lbl_status.setText("Configure un proveedor de IA en Ajustes primero.")
            self._lbl_status.show()
            return

        pages = self._get_selected_pages()
        if not pages:
            return

        self._btn_translate.setEnabled(False)
        self._progress.show()
        self._lbl_status.setText("Traduciendo...")
        self._lbl_status.show()

        self._worker = TranslationWorker(
            pages, source, target, self._config
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int):
        """Actualiza la barra de progreso."""
        if total > 0:
            self._progress.setValue(int(current / total * 100))
        self._lbl_status.setText(f"Traduciendo página {current + 1} de {total}...")

    def _on_finished(self, results: list):
        """Procesa resultados de traducción."""
        self._results = results
        self._btn_translate.setEnabled(True)
        self._progress.setValue(100)

        success = sum(1 for r in results if r.success)
        self._lbl_status.setText(
            f"✅ Traducción completada: {success}/{len(results)} páginas"
        )

        # Show first page in preview
        if results:
            originals = []
            translations = []
            for r in results:
                originals.append(f"--- Página {r.page_num + 1} ---\n{r.original}")
                if r.success:
                    translations.append(
                        f"--- Página {r.page_num + 1} ---\n{r.translated}"
                    )
                else:
                    translations.append(
                        f"--- Página {r.page_num + 1} ---\n❌ {r.error}"
                    )

            self._txt_original.setPlainText("\n\n".join(originals))
            self._txt_translated.setPlainText("\n\n".join(translations))

        self.translation_completed.emit(results)
        self._worker = None

    def _on_error(self, error_text: str):
        """Procesa error de traducción."""
        self._btn_translate.setEnabled(True)
        self._progress.hide()
        self._lbl_status.setText(f"❌ Error: {error_text}")
        self._worker = None

    def get_results(self) -> List[TranslationResult]:
        """Retorna los resultados de traducción."""
        return self._results
