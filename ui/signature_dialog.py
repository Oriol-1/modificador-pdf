"""Diálogo de firma digital para documentos PDF.

Permite firmar PDFs con certificados PFX/P12 y verificar
firmas existentes.
"""

import logging
import os
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QPushButton, QLabel, QLineEdit,
    QFileDialog, QGroupBox, QFormLayout,
    QSpinBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from ui.theme_manager import ThemeColor, ThemeStyles

logger = logging.getLogger(__name__)


class SignWorker(QThread):
    """Worker para firmar en segundo plano."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, operation, kwargs, parent=None):
        super().__init__(parent)
        self._operation = operation
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._operation(**self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Error en operación de firma: {e}")
            self.error.emit(str(e))


class SignatureDialog(QDialog):
    """Diálogo de firma digital."""

    signature_applied = pyqtSignal(str)

    def __init__(self, file_path: str, page_count: int, parent=None):
        """Inicializa el diálogo.

        Args:
            file_path: Ruta del PDF.
            page_count: Número de páginas.
        """
        super().__init__(parent)
        self._file_path = file_path
        self._page_count = page_count
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        """Configura la interfaz."""
        self.setWindowTitle("Firma digital")
        self.setMinimumSize(520, 440)
        self.setStyleSheet(ThemeStyles.dialog())

        layout = QVBoxLayout(self)

        info = QLabel(
            f"🔐 {os.path.basename(self._file_path)} — "
            f"{self._page_count} páginas"
        )
        info.setStyleSheet(f"""
            color: {ThemeColor.TEXT_SECONDARY};
            font-size: 13px;
            font-weight: bold;
            padding: 4px;
        """)
        layout.addWidget(info)

        # Availability check
        from core.digital_signature import is_available
        if not is_available():
            warn = QLabel(
                "⚠️ pyhanko no está instalado.\n"
                "Instale: pip install pyhanko[pkcs11]\n"
                "Solo la verificación básica está disponible."
            )
            warn.setStyleSheet(f"""
                color: {ThemeColor.WARNING};
                font-size: 12px;
                padding: 8px;
                border: 1px solid {ThemeColor.WARNING};
                border-radius: 4px;
            """)
            layout.addWidget(warn)

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

        tabs.addTab(self._create_sign_tab(), "✍️ Firmar")
        tabs.addTab(self._create_verify_tab(), "✅ Verificar")

        layout.addWidget(tabs)

        # Status
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(f"""
            color: {ThemeColor.TEXT_SECONDARY};
            font-size: 12px;
            padding: 4px;
        """)
        layout.addWidget(self._lbl_status)

        # Close
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.setStyleSheet(ThemeStyles.button_secondary())
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    # ─── Tab: Firmar ───

    def _create_sign_tab(self) -> QWidget:
        """Crea la pestaña de firma."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Certificate group
        cert_group = QGroupBox("Certificado (PFX/P12)")
        cert_group.setStyleSheet(f"""
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
        cert_form = QFormLayout(cert_group)

        cert_row = QHBoxLayout()
        self._txt_pfx_path = QLineEdit()
        self._txt_pfx_path.setPlaceholderText("Seleccione archivo .pfx o .p12")
        self._txt_pfx_path.setStyleSheet(ThemeStyles.input_field())
        cert_row.addWidget(self._txt_pfx_path, stretch=1)

        btn_browse = QPushButton("📂")
        btn_browse.setFixedWidth(36)
        btn_browse.clicked.connect(self._browse_certificate)
        cert_row.addWidget(btn_browse)
        cert_form.addRow("Archivo:", cert_row)

        self._txt_password = QLineEdit()
        self._txt_password.setEchoMode(QLineEdit.Password)
        self._txt_password.setPlaceholderText("Contraseña del certificado")
        self._txt_password.setStyleSheet(ThemeStyles.input_field())
        cert_form.addRow("Contraseña:", self._txt_password)

        layout.addWidget(cert_group)

        # Signature details
        details_group = QGroupBox("Detalles de firma")
        details_group.setStyleSheet(cert_group.styleSheet())
        details_form = QFormLayout(details_group)

        self._txt_reason = QLineEdit()
        self._txt_reason.setPlaceholderText("Ej: Aprobación del documento")
        self._txt_reason.setStyleSheet(ThemeStyles.input_field())
        details_form.addRow("Motivo:", self._txt_reason)

        self._txt_location = QLineEdit()
        self._txt_location.setPlaceholderText("Ej: Madrid, España")
        self._txt_location.setStyleSheet(ThemeStyles.input_field())
        details_form.addRow("Ubicación:", self._txt_location)

        self._chk_visible = QCheckBox("Firma visible en el documento")
        self._chk_visible.setStyleSheet(f"color: {ThemeColor.TEXT_PRIMARY};")
        details_form.addRow("", self._chk_visible)

        self._spn_page = QSpinBox()
        self._spn_page.setMinimum(1)
        self._spn_page.setMaximum(self._page_count)
        self._spn_page.setValue(1)
        details_form.addRow("Página:", self._spn_page)

        layout.addWidget(details_group)

        layout.addStretch()

        # Certificate info button
        btn_info = QPushButton("ℹ️ Ver certificado")
        btn_info.setStyleSheet(ThemeStyles.button_secondary())
        btn_info.clicked.connect(self._show_cert_info)

        btn_sign = QPushButton("✍️ Firmar PDF")
        btn_sign.setStyleSheet(ThemeStyles.button_primary())
        btn_sign.clicked.connect(self._on_sign)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_info)
        btn_row.addStretch()
        btn_row.addWidget(btn_sign)
        layout.addLayout(btn_row)

        return widget

    # ─── Tab: Verificar ───

    def _create_verify_tab(self) -> QWidget:
        """Crea la pestaña de verificación."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._sig_table = QTableWidget()
        self._sig_table.setColumnCount(4)
        self._sig_table.setHorizontalHeaderLabels([
            "Firmante", "Fecha", "Estado", "Campo"
        ])
        self._sig_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self._sig_table.setStyleSheet(ThemeStyles.table())
        self._sig_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._sig_table, stretch=1)

        self._lbl_verify_status = QLabel("")
        self._lbl_verify_status.setStyleSheet(
            f"color: {ThemeColor.TEXT_SECONDARY}; padding: 4px;"
        )
        layout.addWidget(self._lbl_verify_status)

        btn_verify = QPushButton("🔍 Verificar firmas")
        btn_verify.setStyleSheet(ThemeStyles.button_primary())
        btn_verify.clicked.connect(self._on_verify)
        layout.addWidget(btn_verify, alignment=Qt.AlignRight)

        return widget

    # ─── Actions ───

    def _browse_certificate(self):
        """Abre diálogo para seleccionar certificado."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar certificado",
            "", "Certificados (*.pfx *.p12);;Todos (*)",
        )
        if path:
            self._txt_pfx_path.setText(path)

    def _show_cert_info(self):
        """Muestra información del certificado seleccionado."""
        pfx_path = self._txt_pfx_path.text().strip()
        password = self._txt_password.text()

        if not pfx_path:
            self._lbl_status.setText("Seleccione un certificado primero.")
            return

        from core.digital_signature import load_certificate_info

        info = load_certificate_info(pfx_path, password)
        if info is None:
            self._lbl_status.setText(
                "❌ No se pudo leer el certificado. Verifique la contraseña."
            )
            return

        expired_text = " ⚠️ EXPIRADO" if info.is_expired else " ✅"
        self._lbl_status.setText(
            f"Titular: {info.subject}\n"
            f"Emisor: {info.issuer}\n"
            f"Válido: {info.not_before} → {info.not_after}{expired_text}"
        )

    def _on_sign(self):
        """Ejecuta la firma del PDF."""
        pfx_path = self._txt_pfx_path.text().strip()
        password = self._txt_password.text()

        if not pfx_path:
            self._lbl_status.setText("Seleccione un certificado.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF firmado", "", "PDF (*.pdf)"
        )
        if not output_path:
            return

        from core.digital_signature import sign_pdf, SigningConfig

        config = SigningConfig(
            pfx_path=pfx_path,
            pfx_password=password,
            reason=self._txt_reason.text().strip(),
            location=self._txt_location.text().strip(),
            visible=self._chk_visible.isChecked(),
            page=self._spn_page.value() - 1,
        )

        self._worker = SignWorker(
            sign_pdf,
            {
                "input_path": self._file_path,
                "output_path": output_path,
                "config": config,
            },
        )
        self._worker.finished.connect(self._on_sign_done)
        self._worker.error.connect(self._on_sign_error)
        self._worker.start()

    def _on_sign_done(self, result):
        """Procesa resultado de firma."""
        if result.success:
            self._lbl_status.setText(
                f"✅ {result.message}\nFirmante: {result.signer_name}"
            )
            self.signature_applied.emit(result.output_path)
        else:
            self._lbl_status.setText(f"❌ {result.message}")
        self._worker = None

    def _on_sign_error(self, error_text: str):
        """Procesa error de firma."""
        self._lbl_status.setText(f"❌ Error: {error_text}")
        self._worker = None

    def _on_verify(self):
        """Verifica las firmas del PDF."""
        from core.digital_signature import verify_signatures

        result = verify_signatures(self._file_path)

        self._sig_table.setRowCount(0)

        if not result.has_signatures:
            self._lbl_verify_status.setText("📄 Este PDF no tiene firmas.")
            return

        for sig in result.signatures:
            row = self._sig_table.rowCount()
            self._sig_table.insertRow(row)

            self._sig_table.setItem(
                row, 0, QTableWidgetItem(sig.signer_name or "Desconocido")
            )
            self._sig_table.setItem(
                row, 1, QTableWidgetItem(sig.signing_time or "—")
            )

            status_icons = {
                "valid": "✅ Válida",
                "invalid": "❌ Inválida",
                "unknown": "❓ Desconocida",
                "error": "⚠️ Error",
            }
            self._sig_table.setItem(
                row, 2, QTableWidgetItem(
                    status_icons.get(sig.status.value, sig.status.value)
                )
            )
            self._sig_table.setItem(
                row, 3, QTableWidgetItem(sig.field_name or "—")
            )

        self._lbl_verify_status.setText(result.message)
