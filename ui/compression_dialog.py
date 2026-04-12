"""Diálogo de compresión de PDF.

Permite seleccionar nivel de compresión, tamaño objetivo
y ver resultados con barra de progreso.
"""
import logging
import os
import tempfile
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QRadioButton, QButtonGroup,
    QProgressBar, QSpinBox, QFileDialog, QMessageBox,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from ui.theme_manager import ThemeColor, ThemeStyles

logger = logging.getLogger(__name__)


# ─────────── Worker thread ───────────

class CompressionWorker(QThread):
    """Worker para comprimir PDF en hilo separado."""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)  # CompressionResult
    error = pyqtSignal(str)
    
    def __init__(self, input_path, output_path, config, parent=None):
        super().__init__(parent)
        self._input_path = input_path
        self._output_path = output_path
        self._config = config
    
    def run(self):
        try:
            from core.compression_engine import compress_pdf
            
            def progress_cb(step, total, desc):
                self.progress.emit(step, total, desc)
            
            result = compress_pdf(
                self._input_path,
                self._output_path,
                config=self._config,
                progress_callback=progress_cb,
            )
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Error en compression worker: {e}")
            self.error.emit(str(e))


# ─────────── Diálogo principal ───────────

class CompressionDialog(QDialog):
    """Diálogo para comprimir un PDF."""
    
    compression_completed = pyqtSignal(str)  # Ruta del archivo comprimido
    
    PRESETS = [
        ("📧 Email (≤5 MB)", "email"),
        ("🌐 Web (≤1 MB)", "web"),
        ("📦 Mínimo (≤400 KB)", "minimum"),
        ("⚙️ Personalizado", "custom"),
    ]
    
    def __init__(self, file_path: str, parent=None):
        """Inicializa el diálogo de compresión.
        
        Args:
            file_path: Ruta del PDF a comprimir.
            parent: Widget padre.
        """
        super().__init__(parent)
        self._file_path = file_path
        self._file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
        self._worker: Optional[CompressionWorker] = None
        self._result = None
        self._output_path = ""
        
        self.setWindowTitle("Comprimir PDF")
        self.setMinimumSize(480, 420)
        self.setModal(True)
        
        self._setup_style()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_style(self):
        self.setStyleSheet(
            ThemeStyles.dialog() +
            ThemeStyles.input_field() +
            ThemeStyles.button_primary() +
            ThemeStyles.button_secondary() +
            ThemeStyles.combobox() +
            ThemeStyles.scrollbar()
        )
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # ── Info del archivo
        from core.compression_engine import _format_size
        info = QLabel(
            f"<b>Archivo:</b> {os.path.basename(self._file_path)}<br>"
            f"<b>Tamaño actual:</b> {_format_size(self._file_size)}"
        )
        info.setStyleSheet(f"color: {ThemeColor.TEXT_PRIMARY}; padding: 4px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # ── Preset de compresión
        preset_group = QGroupBox("Modo de compresión")
        preset_layout = QVBoxLayout(preset_group)
        
        self._btn_group = QButtonGroup(self)
        self._radio_buttons = {}
        
        for i, (label, key) in enumerate(self.PRESETS):
            radio = QRadioButton(label)
            radio.setStyleSheet(f"color: {ThemeColor.TEXT_PRIMARY};")
            self._btn_group.addButton(radio, i)
            self._radio_buttons[key] = radio
            preset_layout.addWidget(radio)
        
        self._radio_buttons["email"].setChecked(True)
        
        # Custom options
        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Tamaño objetivo:"))
        self._spin_target = QSpinBox()
        self._spin_target.setRange(100, 50000)
        self._spin_target.setValue(5120)
        self._spin_target.setSuffix(" KB")
        self._spin_target.setSingleStep(100)
        self._spin_target.setEnabled(False)
        custom_row.addWidget(self._spin_target)
        
        self._combo_quality = QComboBox()
        self._combo_quality.addItems(["Calidad alta", "Calidad media", "Calidad baja"])
        self._combo_quality.setCurrentIndex(1)
        self._combo_quality.setEnabled(False)
        custom_row.addWidget(self._combo_quality)
        
        preset_layout.addLayout(custom_row)
        layout.addWidget(preset_group)
        
        # ── Progreso
        self._lbl_status = QLabel("Seleccione un modo y pulse Comprimir")
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
        
        # ── Resultado
        self._lbl_result = QLabel("")
        self._lbl_result.setStyleSheet(f"color: {ThemeColor.TEXT_PRIMARY}; padding: 4px;")
        self._lbl_result.setWordWrap(True)
        self._lbl_result.hide()
        layout.addWidget(self._lbl_result)
        
        # ── Botones
        btn_layout = QHBoxLayout()
        
        self._btn_compress = QPushButton("🗜️ Comprimir")
        self._btn_compress.setObjectName("primaryButton")
        self._btn_compress.setMinimumHeight(32)
        
        self._btn_save_as = QPushButton("💾 Guardar como...")
        self._btn_save_as.setMinimumHeight(32)
        self._btn_save_as.setEnabled(False)
        
        self._btn_close = QPushButton("Cerrar")
        self._btn_close.setMinimumHeight(32)
        
        btn_layout.addWidget(self._btn_compress)
        btn_layout.addWidget(self._btn_save_as)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_close)
        layout.addLayout(btn_layout)
    
    def _connect_signals(self):
        self._btn_compress.clicked.connect(self._on_compress)
        self._btn_save_as.clicked.connect(self._on_save_as)
        self._btn_close.clicked.connect(self.reject)
        self._btn_group.buttonClicked.connect(self._on_preset_changed)
    
    def _on_preset_changed(self):
        is_custom = self._radio_buttons["custom"].isChecked()
        self._spin_target.setEnabled(is_custom)
        self._combo_quality.setEnabled(is_custom)
    
    def _build_config(self):
        from core.compression_engine import CompressionConfig, CompressionLevel
        
        if self._radio_buttons["email"].isChecked():
            return CompressionConfig.for_email()
        elif self._radio_buttons["web"].isChecked():
            return CompressionConfig.for_web()
        elif self._radio_buttons["minimum"].isChecked():
            return CompressionConfig.for_minimum()
        else:
            # Custom
            quality_map = {0: 85, 1: 70, 2: 50}
            dpi_map = {0: 200, 1: 150, 2: 72}
            idx = self._combo_quality.currentIndex()
            return CompressionConfig(
                target_size_kb=self._spin_target.value(),
                image_max_dpi=dpi_map.get(idx, 150),
                image_quality=quality_map.get(idx, 70),
            )
    
    def _on_compress(self):
        config = self._build_config()
        
        # Generar output path temporal
        base, ext = os.path.splitext(self._file_path)
        self._output_path = f"{base}_compressed{ext}"
        
        self._btn_compress.setEnabled(False)
        self._progress.setValue(0)
        self._lbl_result.hide()
        self._lbl_status.setText("Comprimiendo...")
        
        self._worker = CompressionWorker(
            self._file_path, self._output_path, config, parent=self
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
    
    def _on_progress(self, step, total, desc):
        if total > 0:
            self._progress.setValue(int((step / total) * 100))
        self._lbl_status.setText(desc)
    
    def _on_finished(self, result):
        self._result = result
        self._progress.setValue(100)
        self._btn_compress.setEnabled(True)
        
        if result.success:
            self._btn_save_as.setEnabled(True)
            self._lbl_status.setText("✓ Compresión completada")
            self._lbl_status.setStyleSheet(
                f"color: {ThemeColor.SUCCESS}; padding: 4px;"
            )
            
            techniques = ", ".join(t.name.lower().replace("_", " ") for t in result.techniques_applied)
            self._lbl_result.setText(
                f"<b>Resultado:</b><br>"
                f"Original: {result.original_size_str}<br>"
                f"Comprimido: {result.compressed_size_str}<br>"
                f"Reducción: {result.reduction_percent:.1f}%<br>"
                f"Técnicas: {techniques}"
            )
            self._lbl_result.show()
        else:
            self._lbl_status.setText(f"Error: {result.error}")
            self._lbl_status.setStyleSheet(
                f"color: {ThemeColor.ERROR}; padding: 4px;"
            )
    
    def _on_error(self, error_text):
        self._btn_compress.setEnabled(True)
        self._lbl_status.setText(f"Error: {error_text}")
        self._lbl_status.setStyleSheet(
            f"color: {ThemeColor.ERROR}; padding: 4px;"
        )
    
    def _on_save_as(self):
        if not self._output_path or not os.path.isfile(self._output_path):
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF comprimido",
            self._output_path, "PDF (*.pdf)"
        )
        
        if save_path:
            import shutil
            try:
                shutil.copy2(self._output_path, save_path)
                self.compression_completed.emit(save_path)
                self._lbl_status.setText(f"✓ Guardado: {os.path.basename(save_path)}")
            except Exception as e:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("Error")
                msg.setText(f"Error guardando archivo:\n{e}")
                msg.setStyleSheet(ThemeStyles.message_box())
                msg.exec_()
