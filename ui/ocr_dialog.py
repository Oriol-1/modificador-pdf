"""Diálogo de OCR para reconocimiento de texto en PDFs escaneados.

Provee interfaz para seleccionar idioma, opciones de preprocesado,
ejecutar OCR y ver resultados con barra de progreso.
"""
import logging
from typing import Optional, List

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QCheckBox, QProgressBar,
    QTextEdit, QDialogButtonBox, QSpinBox, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from ui.theme_manager import ThemeColor, ThemeStyles

logger = logging.getLogger(__name__)


# ─────────── Worker thread ───────────

class OCRWorker(QThread):
    """Worker para ejecutar OCR en un hilo separado.
    
    Signals:
        progress: (page_num, total, status_text)
        finished: (OCRDocumentResult)
        error: (str)
    """
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(
        self, doc, ocr_engine, language, preprocess_fn,
        dpi, page_indices, parent=None
    ):
        super().__init__(parent)
        self._doc = doc
        self._engine = ocr_engine
        self._language = language
        self._preprocess_fn = preprocess_fn
        self._dpi = dpi
        self._page_indices = page_indices
        self._cancelled = False
    
    def cancel(self):
        """Solicita cancelación del procesamiento."""
        self._cancelled = True
    
    def run(self):
        """Ejecuta el procesamiento OCR."""
        try:
            from core.ocr.pdf_ocr_layer import process_document_ocr
            
            def progress_cb(current, total, text):
                if self._cancelled:
                    raise InterruptedError("OCR cancelado por el usuario")
                self.progress.emit(current, total, text)
            
            result = process_document_ocr(
                doc=self._doc,
                ocr_engine=self._engine,
                language=self._language,
                preprocess_fn=self._preprocess_fn,
                dpi=self._dpi,
                page_indices=self._page_indices,
                progress_callback=progress_cb,
            )
            
            if not self._cancelled:
                self.finished.emit(result)
                
        except InterruptedError:
            self.error.emit("OCR cancelado por el usuario")
        except Exception as e:
            logger.error(f"Error en OCR worker: {e}")
            self.error.emit(str(e))


# ─────────── Diálogo principal ───────────

class OCRDialog(QDialog):
    """Diálogo para configurar y ejecutar OCR en un PDF.
    
    Signals:
        ocr_completed: Emitida cuando el OCR finaliza exitosamente.
    """
    ocr_completed = pyqtSignal(object)  # OCRDocumentResult
    
    # Idiomas disponibles
    LANGUAGES = [
        ("Español", "spa"),
        ("Inglés", "eng"),
        ("Francés", "fra"),
        ("Alemán", "deu"),
        ("Portugués", "por"),
        ("Catalán", "cat"),
        ("Italiano", "ita"),
        ("Español + Inglés", "spa+eng"),
    ]
    
    def __init__(self, doc, scanned_pages: List[int], parent=None):
        """Inicializa el diálogo OCR.
        
        Args:
            doc: Documento fitz.Document abierto.
            scanned_pages: Índices de páginas escaneadas detectadas.
            parent: Widget padre.
        """
        super().__init__(parent)
        self._doc = doc
        self._scanned_pages = scanned_pages
        self._worker: Optional[OCRWorker] = None
        self._result = None
        
        self.setWindowTitle("OCR — Reconocimiento de Texto")
        self.setMinimumSize(520, 500)
        self.setModal(True)
        
        self._setup_style()
        self._setup_ui()
        self._connect_signals()
    
    # ─── Setup ───
    
    def _setup_style(self):
        """Aplica estilos del tema oscuro."""
        self.setStyleSheet(
            ThemeStyles.dialog() +
            ThemeStyles.input_field() +
            ThemeStyles.button_primary() +
            ThemeStyles.button_secondary() +
            ThemeStyles.combobox() +
            ThemeStyles.checkbox() +
            ThemeStyles.scrollbar()
        )
    
    def _setup_ui(self):
        """Construye la interfaz del diálogo."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # ── Info
        info_label = QLabel(
            f"Se detectaron <b>{len(self._scanned_pages)}</b> páginas "
            f"escaneadas de <b>{len(self._doc)}</b> totales."
        )
        info_label.setStyleSheet(f"color: {ThemeColor.TEXT_PRIMARY};")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # ── Grupo: Idioma
        lang_group = QGroupBox("Idioma")
        lang_layout = QHBoxLayout(lang_group)
        
        self._combo_language = QComboBox()
        for display, code in self.LANGUAGES:
            self._combo_language.addItem(display, code)
        self._combo_language.setCurrentIndex(0)  # Español por defecto
        lang_layout.addWidget(QLabel("Idioma OCR:"))
        lang_layout.addWidget(self._combo_language, 1)
        layout.addWidget(lang_group)
        
        # ── Grupo: Preprocesado
        preproc_group = QGroupBox("Preprocesado de imagen")
        preproc_layout = QVBoxLayout(preproc_group)
        
        self._chk_deskew = QCheckBox("Corrección de inclinación (deskew)")
        self._chk_deskew.setChecked(True)
        self._chk_denoise = QCheckBox("Reducción de ruido")
        self._chk_denoise.setChecked(True)
        self._chk_binarize = QCheckBox("Binarización adaptativa")
        self._chk_binarize.setChecked(True)
        self._chk_contrast = QCheckBox("Mejora de contraste (CLAHE)")
        self._chk_contrast.setChecked(False)
        self._chk_rescale = QCheckBox("Reescalar a DPI óptimo")
        self._chk_rescale.setChecked(True)
        
        preproc_layout.addWidget(self._chk_deskew)
        preproc_layout.addWidget(self._chk_denoise)
        preproc_layout.addWidget(self._chk_binarize)
        preproc_layout.addWidget(self._chk_contrast)
        preproc_layout.addWidget(self._chk_rescale)
        
        # DPI
        dpi_row = QHBoxLayout()
        dpi_row.addWidget(QLabel("DPI de renderizado:"))
        self._spin_dpi = QSpinBox()
        self._spin_dpi.setRange(150, 600)
        self._spin_dpi.setValue(300)
        self._spin_dpi.setSingleStep(50)
        dpi_row.addWidget(self._spin_dpi)
        dpi_row.addStretch()
        preproc_layout.addLayout(dpi_row)
        
        layout.addWidget(preproc_group)
        
        # ── Progreso
        self._lbl_status = QLabel("Listo para iniciar OCR")
        self._lbl_status.setStyleSheet(
            f"color: {ThemeColor.TEXT_SECONDARY}; padding: 4px;"
        )
        layout.addWidget(self._lbl_status)
        
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(22)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {ThemeColor.BORDER};
                border-radius: 3px;
                background: {ThemeColor.BG_INPUT};
                text-align: center;
                color: {ThemeColor.TEXT_PRIMARY};
            }}
            QProgressBar::chunk {{
                background: {ThemeColor.ACCENT};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self._progress)
        
        # ── Resultados
        self._txt_results = QTextEdit()
        self._txt_results.setReadOnly(True)
        self._txt_results.setMaximumHeight(120)
        self._txt_results.setPlaceholderText("Los resultados aparecerán aquí...")
        self._txt_results.setStyleSheet(f"""
            QTextEdit {{
                background: {ThemeColor.BG_INPUT};
                color: {ThemeColor.TEXT_PRIMARY};
                border: 1px solid {ThemeColor.BORDER};
                border-radius: 3px;
                padding: 4px;
            }}
        """)
        layout.addWidget(self._txt_results)
        
        # ── Botones
        btn_layout = QHBoxLayout()
        
        self._btn_start = QPushButton("▶ Iniciar OCR")
        self._btn_start.setObjectName("primaryButton")
        self._btn_start.setMinimumHeight(32)
        
        self._btn_cancel = QPushButton("Cancelar")
        self._btn_cancel.setMinimumHeight(32)
        
        self._btn_save = QPushButton("💾 Guardar PDF")
        self._btn_save.setObjectName("primaryButton")
        self._btn_save.setMinimumHeight(32)
        self._btn_save.setEnabled(False)
        
        btn_layout.addWidget(self._btn_start)
        btn_layout.addWidget(self._btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_save)
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        """Conecta señales de los widgets."""
        self._btn_start.clicked.connect(self._on_start_ocr)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._btn_save.clicked.connect(self._on_save)
    
    # ─── Slots ───
    
    def _on_start_ocr(self):
        """Inicia el procesamiento OCR."""
        if not self._check_dependencies():
            return
        
        language = self._combo_language.currentData()
        dpi = self._spin_dpi.value()
        
        # Construir función de preprocesado
        preprocess_fn = self._build_preprocess_fn()
        
        # Deshabilitar controles
        self._btn_start.setEnabled(False)
        self._set_controls_enabled(False)
        self._progress.setValue(0)
        self._txt_results.clear()
        self._lbl_status.setText("Iniciando OCR...")
        
        # Crear worker
        from core.ocr.ocr_engine import TesseractEngine
        engine = TesseractEngine()
        
        self._worker = OCRWorker(
            doc=self._doc,
            ocr_engine=engine,
            language=language,
            preprocess_fn=preprocess_fn,
            dpi=dpi,
            page_indices=self._scanned_pages,
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_ocr_finished)
        self._worker.error.connect(self._on_ocr_error)
        self._worker.start()
    
    def _on_cancel(self):
        """Cancela OCR o cierra el diálogo."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._lbl_status.setText("Cancelando...")
            self._worker.wait(3000)
            self._btn_start.setEnabled(True)
            self._set_controls_enabled(True)
            self._lbl_status.setText("OCR cancelado")
        else:
            self.reject()
    
    def _on_save(self):
        """Acepta el resultado y cierra el diálogo."""
        if self._result:
            self.ocr_completed.emit(self._result)
        self.accept()
    
    def _on_progress(self, current: int, total: int, text: str):
        """Actualiza la barra de progreso."""
        if total > 0:
            percent = int((current / total) * 100)
            self._progress.setValue(percent)
        self._lbl_status.setText(text)
    
    def _on_ocr_finished(self, result):
        """Maneja la finalización exitosa de OCR."""
        self._result = result
        self._progress.setValue(100)
        self._btn_start.setEnabled(True)
        self._btn_save.setEnabled(True)
        self._set_controls_enabled(True)
        
        # Mostrar resumen
        summary = (
            f"OCR completado exitosamente.\n\n"
            f"Páginas procesadas: {result.processed_pages}/{result.scanned_pages}\n"
            f"Palabras reconocidas: {result.total_words}\n"
            f"Confianza promedio: {result.avg_confidence:.1f}%\n\n"
        )
        
        # Mostrar texto de primera página como preview
        if result.pages and result.pages[0].ocr_result:
            preview = result.pages[0].ocr_result.text[:500]
            summary += f"--- Vista previa (página {result.pages[0].page_num + 1}) ---\n"
            summary += preview
        
        self._txt_results.setText(summary)
        self._lbl_status.setText(
            f"✓ OCR completado: {result.total_words} palabras, "
            f"confianza {result.avg_confidence:.1f}%"
        )
        self._lbl_status.setStyleSheet(
            f"color: {ThemeColor.SUCCESS}; padding: 4px;"
        )
    
    def _on_ocr_error(self, error_text: str):
        """Maneja errores de OCR."""
        self._btn_start.setEnabled(True)
        self._set_controls_enabled(True)
        self._lbl_status.setText(f"Error: {error_text}")
        self._lbl_status.setStyleSheet(
            f"color: {ThemeColor.ERROR}; padding: 4px;"
        )
        self._txt_results.setText(f"Error durante OCR:\n{error_text}")
    
    # ─── Helpers ───
    
    def _check_dependencies(self) -> bool:
        """Verifica que las dependencias OCR estén disponibles."""
        from core.ocr import is_ocr_available
        
        available, missing = is_ocr_available()
        if not available:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Dependencias faltantes")
            msg.setText(
                "No se pueden ejecutar OCR. Faltan dependencias:\n\n"
                + "\n".join(f"  • {m}" for m in missing)
                + "\n\nInstale las dependencias necesarias."
            )
            msg.setStyleSheet(ThemeStyles.message_box())
            msg.exec_()
            return False
        return True
    
    def _build_preprocess_fn(self):
        """Construye la función de preprocesado según las opciones."""
        from core.ocr.image_preprocessor import (
            PreprocessConfig, preprocess_image
        )
        
        has_any = (
            self._chk_deskew.isChecked() or
            self._chk_denoise.isChecked() or
            self._chk_binarize.isChecked() or
            self._chk_contrast.isChecked() or
            self._chk_rescale.isChecked()
        )
        
        if not has_any:
            return None
        
        config = PreprocessConfig(
            deskew=self._chk_deskew.isChecked(),
            denoise=self._chk_denoise.isChecked(),
            binarize=self._chk_binarize.isChecked(),
            contrast=self._chk_contrast.isChecked(),
            target_dpi=self._spin_dpi.value() if self._chk_rescale.isChecked() else 0,
        )
        
        def fn(image):
            return preprocess_image(image, config)
        
        return fn
    
    def _set_controls_enabled(self, enabled: bool):
        """Habilita o deshabilita controles de configuración."""
        self._combo_language.setEnabled(enabled)
        self._chk_deskew.setEnabled(enabled)
        self._chk_denoise.setEnabled(enabled)
        self._chk_binarize.setEnabled(enabled)
        self._chk_contrast.setEnabled(enabled)
        self._chk_rescale.setEnabled(enabled)
        self._spin_dpi.setEnabled(enabled)
