"""Diálogo de configuración del asistente de IA.

Permite configurar proveedor LLM, API keys, modelos
y parámetros de búsqueda RAG.
"""

import logging

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QLabel, QGroupBox, QMessageBox,
    QTabWidget, QWidget,
)
from PyQt5.QtCore import Qt

from ui.theme_manager import ThemeColor, ThemeStyles
from core.ai.ai_config import AIConfig, LLMProvider, EmbeddingProvider

logger = logging.getLogger(__name__)


class AISettingsDialog(QDialog):
    """Diálogo de configuración del asistente de IA."""

    def __init__(self, config: AIConfig, parent=None):
        """Inicializa el diálogo de configuración.

        Args:
            config: Configuración actual de IA.
        """
        super().__init__(parent)
        self._config = AIConfig.from_dict(config.to_dict())
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """Configura la interfaz."""
        self.setWindowTitle("Ajustes de IA")
        self.setMinimumWidth(480)
        self.setStyleSheet(ThemeStyles.dialog())

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {ThemeColor.BORDER_LIGHT};
                background-color: {ThemeColor.BG_PRIMARY};
            }}
            QTabBar::tab {{
                background-color: {ThemeColor.BG_SECONDARY};
                color: {ThemeColor.TEXT_PRIMARY};
                padding: 8px 16px;
                border: 1px solid {ThemeColor.BORDER_LIGHT};
            }}
            QTabBar::tab:selected {{
                background-color: {ThemeColor.ACCENT};
                color: white;
            }}
        """)

        tabs.addTab(self._create_provider_tab(), "Proveedor")
        tabs.addTab(self._create_search_tab(), "Búsqueda")

        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_test = QPushButton("🔌 Probar conexión")
        self._btn_test.setStyleSheet(ThemeStyles.button_secondary())
        self._btn_test.clicked.connect(self._test_connection)
        btn_layout.addWidget(self._btn_test)

        self._btn_save = QPushButton("Guardar")
        self._btn_save.setStyleSheet(ThemeStyles.button_primary())
        self._btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self._btn_save)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(ThemeStyles.button_secondary())
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _create_provider_tab(self) -> QWidget:
        """Crea la pestaña de proveedor LLM."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # LLM Provider
        group_llm = QGroupBox("Modelo de lenguaje (LLM)")
        group_llm.setStyleSheet(f"""
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
        llm_layout = QFormLayout(group_llm)

        self._cmb_provider = QComboBox()
        self._cmb_provider.addItems(["Ninguno", "OpenAI", "Ollama"])
        self._cmb_provider.currentIndexChanged.connect(
            self._on_provider_changed
        )
        llm_layout.addRow("Proveedor:", self._cmb_provider)

        # OpenAI settings
        self._txt_api_key = QLineEdit()
        self._txt_api_key.setEchoMode(QLineEdit.Password)
        self._txt_api_key.setPlaceholderText("sk-...")
        llm_layout.addRow("API Key:", self._txt_api_key)

        self._cmb_openai_model = QComboBox()
        self._cmb_openai_model.setEditable(True)
        self._cmb_openai_model.addItems([
            "gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"
        ])
        llm_layout.addRow("Modelo OpenAI:", self._cmb_openai_model)

        # Ollama settings
        self._txt_ollama_url = QLineEdit()
        self._txt_ollama_url.setPlaceholderText("http://localhost:11434")
        llm_layout.addRow("URL Ollama:", self._txt_ollama_url)

        self._cmb_ollama_model = QComboBox()
        self._cmb_ollama_model.setEditable(True)
        self._cmb_ollama_model.addItems([
            "llama3.2", "llama3.1", "mistral", "codellama", "phi3"
        ])
        llm_layout.addRow("Modelo Ollama:", self._cmb_ollama_model)

        layout.addWidget(group_llm)

        # Temperature
        group_gen = QGroupBox("Generación")
        group_gen.setStyleSheet(group_llm.styleSheet())
        gen_layout = QFormLayout(group_gen)

        self._spn_temperature = QDoubleSpinBox()
        self._spn_temperature.setRange(0.0, 2.0)
        self._spn_temperature.setSingleStep(0.1)
        self._spn_temperature.setDecimals(1)
        gen_layout.addRow("Temperatura:", self._spn_temperature)

        layout.addWidget(group_gen)
        layout.addStretch()

        return widget

    def _create_search_tab(self) -> QWidget:
        """Crea la pestaña de búsqueda RAG."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Parámetros de búsqueda RAG")
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

        self._spn_chunk_size = QSpinBox()
        self._spn_chunk_size.setRange(100, 2000)
        self._spn_chunk_size.setSingleStep(50)
        self._spn_chunk_size.setSuffix(" caracteres")
        form.addRow("Tamaño de chunk:", self._spn_chunk_size)

        self._spn_overlap = QSpinBox()
        self._spn_overlap.setRange(0, 200)
        self._spn_overlap.setSingleStep(10)
        self._spn_overlap.setSuffix(" caracteres")
        form.addRow("Solapamiento:", self._spn_overlap)

        self._spn_top_k = QSpinBox()
        self._spn_top_k.setRange(1, 20)
        form.addRow("Resultados (top-k):", self._spn_top_k)

        self._cmb_embedding = QComboBox()
        self._cmb_embedding.addItems(["TF-IDF (local)", "OpenAI", "Sentence Transformers"])
        form.addRow("Embeddings:", self._cmb_embedding)

        layout.addWidget(group)
        layout.addStretch()

        return widget

    def _load_config(self):
        """Carga la configuración en los controles."""
        provider_map = {
            LLMProvider.NONE: 0,
            LLMProvider.OPENAI: 1,
            LLMProvider.OLLAMA: 2,
        }
        self._cmb_provider.setCurrentIndex(
            provider_map.get(self._config.llm_provider, 0)
        )

        self._txt_api_key.setText(self._config.openai_api_key)
        self._cmb_openai_model.setCurrentText(self._config.openai_model)
        self._txt_ollama_url.setText(self._config.ollama_url)
        self._cmb_ollama_model.setCurrentText(self._config.ollama_model)
        self._spn_temperature.setValue(self._config.temperature)

        self._spn_chunk_size.setValue(self._config.chunk_size)
        self._spn_overlap.setValue(self._config.chunk_overlap)
        self._spn_top_k.setValue(self._config.top_k)

        embed_map = {
            EmbeddingProvider.TFIDF: 0,
            EmbeddingProvider.OPENAI: 1,
            EmbeddingProvider.SENTENCE_TRANSFORMERS: 2,
        }
        self._cmb_embedding.setCurrentIndex(
            embed_map.get(self._config.embedding_provider, 0)
        )

        self._on_provider_changed(self._cmb_provider.currentIndex())

    def _on_provider_changed(self, index: int):
        """Actualiza visibilidad de campos según proveedor."""
        is_openai = index == 1
        is_ollama = index == 2

        self._txt_api_key.setEnabled(is_openai)
        self._cmb_openai_model.setEnabled(is_openai)
        self._txt_ollama_url.setEnabled(is_ollama)
        self._cmb_ollama_model.setEnabled(is_ollama)

    def _build_config(self) -> AIConfig:
        """Construye AIConfig desde los controles."""
        provider_map = {0: LLMProvider.NONE, 1: LLMProvider.OPENAI, 2: LLMProvider.OLLAMA}
        embed_map = {
            0: EmbeddingProvider.TFIDF,
            1: EmbeddingProvider.OPENAI,
            2: EmbeddingProvider.SENTENCE_TRANSFORMERS,
        }

        return AIConfig(
            llm_provider=provider_map.get(
                self._cmb_provider.currentIndex(), LLMProvider.NONE
            ),
            embedding_provider=embed_map.get(
                self._cmb_embedding.currentIndex(), EmbeddingProvider.TFIDF
            ),
            openai_api_key=self._txt_api_key.text().strip(),
            openai_model=self._cmb_openai_model.currentText().strip(),
            ollama_url=self._txt_ollama_url.text().strip(),
            ollama_model=self._cmb_ollama_model.currentText().strip(),
            chunk_size=self._spn_chunk_size.value(),
            chunk_overlap=self._spn_overlap.value(),
            top_k=self._spn_top_k.value(),
            temperature=self._spn_temperature.value(),
        )

    def _test_connection(self):
        """Prueba la conexión al proveedor configurado."""
        config = self._build_config()

        if config.llm_provider == LLMProvider.NONE:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Test de conexión")
            msg.setText("No hay proveedor LLM configurado.")
            msg.setStyleSheet(ThemeStyles.message_box())
            msg.exec_()
            return

        try:
            if config.llm_provider == LLMProvider.OPENAI:
                from core.ai.chat_engine import call_openai
                call_openai(
                    [{"role": "user", "content": "test"}], config
                )
            elif config.llm_provider == LLMProvider.OLLAMA:
                import urllib.request
                url = f"{config.ollama_url}/api/tags"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5):
                    pass

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Test de conexión")
            msg.setText("✅ Conexión exitosa.")
            msg.setStyleSheet(ThemeStyles.message_box())
            msg.exec_()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Test de conexión")
            msg.setText(f"❌ Error de conexión:\n{e}")
            msg.setStyleSheet(ThemeStyles.message_box())
            msg.exec_()

    def _on_save(self):
        """Guarda la configuración y cierra."""
        self._config = self._build_config()
        self.accept()

    def get_config(self) -> AIConfig:
        """Retorna la configuración resultante."""
        return self._config
