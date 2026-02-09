"""
Elementos gráficos personalizados para el visor de PDF.
Incluye rectángulos de selección, items de texto editables y diálogos.
"""

from PyQt5.QtWidgets import (
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsDropShadowEffect,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QCheckBox, QDialogButtonBox, QGroupBox, QMenu, QToolButton
)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPen, QBrush, QColor, QCursor, QFont


class SelectionRect(QGraphicsRectItem):
    """Rectángulo de selección visual mejorado."""
    
    def __init__(self, rect=QRectF(), mode='select'):
        super().__init__(rect)
        self.mode = mode
        self.update_style()
        self.setZValue(100)
    
    def update_style(self):
        if self.mode == 'delete':
            # Rojo para eliminación
            self.setPen(QPen(QColor(255, 80, 80), 2, Qt.SolidLine))
            self.setBrush(QBrush(QColor(255, 0, 0, 40)))
        elif self.mode == 'highlight':
            # Amarillo para resaltado
            self.setPen(QPen(QColor(255, 200, 0), 2, Qt.SolidLine))
            self.setBrush(QBrush(QColor(255, 255, 0, 60)))
        else:
            # Azul para selección normal
            self.setPen(QPen(QColor(0, 120, 215), 2, Qt.DashLine))
            self.setBrush(QBrush(QColor(0, 120, 215, 40)))
    
    def set_mode(self, mode):
        self.mode = mode
        self.update_style()


class DeletePreviewRect(QGraphicsRectItem):
    """Rectángulo de previsualización de borrado con animación."""
    
    def __init__(self, rect=QRectF()):
        super().__init__(rect)
        self.setPen(QPen(QColor(255, 50, 50), 3, Qt.SolidLine))
        self.setBrush(QBrush(QColor(255, 0, 0, 80)))
        self.setZValue(90)
        
        # Efecto de sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(255, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)


class FloatingLabel(QGraphicsTextItem):
    """Etiqueta flotante para mostrar información."""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setDefaultTextColor(QColor(255, 255, 255))
        font = QFont("Segoe UI", 10, QFont.Bold)
        self.setFont(font)
        self.setZValue(200)
    
    def set_background(self, color):
        pass  # Se maneja en paint


class HighlightRect(QGraphicsRectItem):
    """Rectángulo de resaltado."""
    
    def __init__(self, rect=QRectF(), color=QColor(255, 255, 0, 100)):
        super().__init__(rect)
        self.setPen(QPen(Qt.NoPen))
        self.setBrush(QBrush(color))
        self.setZValue(50)


class TextEditDialog(QDialog):
    """
    Diálogo personalizado para editar texto con opciones de formato.
    """
    def __init__(self, text: str = "", font_size: int = 12, is_bold: bool = False, 
                 title: str = "Editar texto", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        
        # Estilo general del diálogo
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d30;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #0078d4;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
            QSpinBox {
                background: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
                min-width: 70px;
            }
            QSpinBox:focus {
                border: 2px solid #0078d4;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #555;
                background: #1e1e1e;
            }
            QCheckBox::indicator:hover {
                border-color: #0078d4;
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a8cff, stop:1 #0066cc);
                border: 2px solid #00aaff;
            }
            QCheckBox::indicator:checked:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3399ff, stop:1 #0078d4);
            }
            QPushButton {
                background: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 16px;
                color: white;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #4a4a4a;
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: #0078d4;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Grupo de texto
        text_group = QGroupBox("Contenido")
        text_layout = QHBoxLayout(text_group)
        
        self.text_edit = QLineEdit(text)
        self.text_edit.setPlaceholderText("Escribe el texto aquí...")
        self.text_edit.selectAll()
        text_layout.addWidget(self.text_edit)
        
        # Botón de símbolos
        self.symbol_btn = QToolButton()
        self.symbol_btn.setText("☐")
        self.symbol_btn.setToolTip("Insertar símbolo")
        self.symbol_btn.setPopupMode(QToolButton.InstantPopup)
        self.symbol_btn.setFixedSize(36, 36)
        self.symbol_btn.setStyleSheet("""
            QToolButton {
                font-size: 16px;
                background: #3d3d3d;
                border: 2px solid #555;
                border-radius: 6px;
                color: #cccccc;
            }
            QToolButton:hover {
                background: #4a4a4a;
                border-color: #0078d4;
                color: white;
            }
            QToolButton::menu-indicator { right: 2px; }
        """)
        
        symbol_menu = QMenu(self)
        symbol_menu.setStyleSheet("""
            QMenu { background: #2d2d30; border: 1px solid #555; border-radius: 4px; padding: 5px; color: white; }
            QMenu::item { padding: 6px 16px; border-radius: 3px; }
            QMenu::item:selected { background: #0078d4; }
        """)
        
        # Símbolos rápidos
        symbols = [
            ("☐", "Casilla vacía"), ("☑", "Casilla marcada"), ("☒", "Casilla X"),
            None,  # Separador
            ("•", "Viñeta"), ("◦", "Círculo"), ("➤", "Flecha"), ("★", "Estrella"),
            None,
            ("→", "Flecha der."), ("←", "Flecha izq."), ("↑", "Flecha arriba"), ("↓", "Flecha abajo"),
            None,
            ("✓", "Check"), ("✔", "Check grueso"), ("✗", "Cruz"), ("⚠", "Advertencia"),
            None,
            ("©", "Copyright"), ("®", "Registrado"), ("™", "Trademark"), ("°", "Grado"), ("€", "Euro"),
        ]
        for item in symbols:
            if item is None:
                symbol_menu.addSeparator()
            else:
                sym, desc = item
                action = symbol_menu.addAction(f"{sym}  {desc}")
                action.triggered.connect(lambda checked, s=sym: self._insert_symbol(s))
        
        self.symbol_btn.setMenu(symbol_menu)
        text_layout.addWidget(self.symbol_btn)
        
        layout.addWidget(text_group)
        
        # Grupo de formato
        format_group = QGroupBox("Formato")
        format_layout = QHBoxLayout(format_group)
        
        # Tamaño de fuente - permitir desde 1pt para máxima flexibilidad
        size_layout = QHBoxLayout()
        size_label = QLabel("Tamaño:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 144)  # Rango ampliado: 1pt a 144pt
        self.size_spin.setValue(int(font_size))
        self.size_spin.setSuffix(" pt")
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        format_layout.addLayout(size_layout)
        
        # Checkbox para negrita con mejor estilo visual
        self.bold_check = QCheckBox("Negrita")
        self.bold_check.setChecked(is_bold)
        format_layout.addWidget(self.bold_check)
        
        format_layout.addStretch()
        layout.addWidget(format_group)
        
        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Foco inicial en el texto
        self.text_edit.setFocus()
    
    def _insert_symbol(self, symbol: str):
        """Inserta un símbolo en la posición actual del cursor."""
        cursor_pos = self.text_edit.cursorPosition()
        current_text = self.text_edit.text()
        new_text = current_text[:cursor_pos] + symbol + current_text[cursor_pos:]
        self.text_edit.setText(new_text)
        self.text_edit.setCursorPosition(cursor_pos + len(symbol))
        self.text_edit.setFocus()
    
    def get_values(self):
        """Retorna los valores del diálogo."""
        return {
            'text': self.text_edit.text(),
            'font_size': self.size_spin.value(),
            'is_bold': self.bold_check.isChecked()
        }


class EditableTextItem(QGraphicsRectItem):
    """
    Representa un texto editable añadido al PDF.
    Permite seleccionar, mover y editar el texto.
    
    IMPORTANTE - INDEPENDENCIA DE MÓDULOS:
    - Cada EditableTextItem es un módulo de texto COMPLETAMENTE INDEPENDIENTE
    - El texto editado SIEMPRE pertenece a su módulo, aunque crezca fuera del área inicial
    - El área de selección (rect) se adapta AUTOMÁTICAMENTE al contenido del texto
    - Los módulos de texto NUNCA se mezclan entre sí, cada uno tiene un ID único
    
    CRÍTICO - CAJA = TEXTO:
    - La caja SIEMPRE tiene el tamaño exacto del texto que contiene
    - Si el texto crece, la caja crece automáticamente
    - Si el texto se reduce, la caja se reduce automáticamente
    - Esto evita el desbordamiento visual
    
    Para PDFs de imagen: el texto se muestra visualmente como capa superpuesta
    y solo se escribe al PDF cuando se "confirma" (al guardar o deseleccionar).
    """
    
    # Contador estático para generar IDs únicos
    _next_id = 1
    
    def __init__(self, rect: QRectF, text: str, font_size: float = 12, 
                 color: tuple = (0, 0, 0), page_num: int = 0, 
                 font_name: str = "helv", is_bold: bool = False, 
                 zoom_level: float = 1.0, line_spacing: float = 0.0, parent=None):
        # Inicializar con rect temporal - se ajustará al contenido después
        super().__init__(rect, parent)
        
        # ID único del módulo - NUNCA se mezcla con otros módulos
        self.module_id = EditableTextItem._next_id
        EditableTextItem._next_id += 1
        
        self._text = text  # Usar propiedad para auto-ajustar
        self.font_size = font_size  # Tamaño de fuente en puntos PDF (sin zoom)
        self.text_color = color
        self.page_num = page_num
        self.font_name = font_name  # Nombre de la fuente
        self.is_bold = is_bold  # Si es negrita
        self.pdf_rect = None  # Se establece después de añadir al PDF
        self.zoom_level = zoom_level  # Nivel de zoom para escalar al dibujar
        self.line_spacing = line_spacing  # Interlineado original del PDF (en puntos)
        
        # NUEVO: Flags para manejo en PDFs de imagen
        self.is_overlay = False  # True = solo visual, no escrito al PDF aún
        self.pending_write = False  # True = necesita escribirse al PDF
        
        # Soporte para múltiples estilos (text_runs)
        self.text_runs = None  # Lista de runs con estilos individuales
        self.has_mixed_styles = False  # True si hay múltiples estilos
        
        # Estado visual
        self.is_selected = False
        self.is_hovered = False
        
        # Configuración visual base (invisible hasta hover/select)
        self._update_visual()
        self.setZValue(150)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Flags para interacción
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
        
        # CRÍTICO: Ajustar la caja al tamaño real del texto
        # La caja SIEMPRE debe tener el tamaño del contenido
        if self._text:
            self.adjust_rect_to_content()
    
    @property
    def text(self):
        """Obtiene el texto del módulo."""
        return self._text
    
    @text.setter
    def text(self, value):
        """Establece el texto y ajusta automáticamente el rect al contenido.
        
        CRÍTICO: Cuando el texto cambia, el rect del módulo se adapta automáticamente
        para contener todo el texto. El texto SIEMPRE pertenece a este módulo.
        Soporta tabulaciones que se expanden a espacios.
        """
        self._text = value
        # CRÍTICO: Auto-ajustar el rect al nuevo contenido SIEMPRE
        if value:
            self.adjust_rect_to_content()
    
    def set_text_and_adjust(self, value):
        """Establece el texto y FUERZA el ajuste del rect inmediatamente.
        
        Usar este método cuando se necesita asegurar que el rect se actualice
        inmediatamente después de cambiar el texto.
        """
        self._text = value
        if value:
            self.adjust_rect_to_content()
    
    def _map_pdf_font_to_system(self, pdf_font_name: str) -> str:
        """Mapea un nombre de fuente del PDF a una fuente del sistema.
        
        Los PDFs usan nombres como "ArialMT", "Helvetica-Bold", "TimesNewRomanPSMT", etc.
        Esta función los convierte a nombres de fuentes del sistema.
        
        Args:
            pdf_font_name: Nombre de la fuente en el PDF
            
        Returns:
            Nombre de la fuente del sistema más cercana
        """
        if not pdf_font_name:
            return "Arial"
        
        # Normalizar el nombre (lowercase, sin guiones ni espacios)
        name_lower = pdf_font_name.lower().replace('-', '').replace(' ', '')
        
        # Mapeo de nombres comunes de PDF a fuentes del sistema
        font_mappings = {
            # Arial y variantes
            'arial': 'Arial',
            'arialmt': 'Arial',
            'arialmtbold': 'Arial',
            'arialbold': 'Arial',
            'arialitalic': 'Arial',
            'arialbolditalic': 'Arial',
            'arialnarrow': 'Arial Narrow',
            'arialblack': 'Arial Black',
            
            # Helvetica y variantes
            'helvetica': 'Arial',  # Helvetica se mapea a Arial en Windows
            'helveticaneue': 'Arial',
            'helveticabold': 'Arial',
            'helveticaoblique': 'Arial',
            'helv': 'Arial',
            'hebo': 'Arial',
            
            # Times y variantes
            'times': 'Times New Roman',
            'timesnewroman': 'Times New Roman',
            'timesnewromanpsmt': 'Times New Roman',
            'timesnewromanbold': 'Times New Roman',
            'timesroman': 'Times New Roman',
            
            # Courier y variantes
            'courier': 'Courier New',
            'couriernew': 'Courier New',
            'couriernewpsmt': 'Courier New',
            
            # Calibri
            'calibri': 'Calibri',
            'calibribold': 'Calibri',
            'calibrilight': 'Calibri Light',
            
            # Cambria
            'cambria': 'Cambria',
            'cambriabold': 'Cambria',
            
            # Georgia
            'georgia': 'Georgia',
            'georgiabold': 'Georgia',
            
            # Verdana
            'verdana': 'Verdana',
            'verdanabold': 'Verdana',
            
            # Tahoma
            'tahoma': 'Tahoma',
            'tahomabold': 'Tahoma',
            
            # Trebuchet
            'trebuchet': 'Trebuchet MS',
            'trebuchetms': 'Trebuchet MS',
            
            # Segoe UI
            'segoeui': 'Segoe UI',
            'segoeuibold': 'Segoe UI',
            
            # Symbol
            'symbol': 'Symbol',
            'wingdings': 'Wingdings',
            
            # OpenSans
            'opensans': 'Open Sans',
            'opensansbold': 'Open Sans',
            
            # Roboto
            'roboto': 'Roboto',
            'robotobold': 'Roboto',
        }
        
        # Buscar coincidencia exacta
        if name_lower in font_mappings:
            return font_mappings[name_lower]
        
        # Buscar coincidencia parcial
        for pdf_name, system_name in font_mappings.items():
            if pdf_name in name_lower or name_lower in pdf_name:
                return system_name
        
        # Si no hay coincidencia, intentar detectar familia base
        if 'arial' in name_lower:
            return 'Arial'
        if 'helvetica' in name_lower or 'helv' in name_lower:
            return 'Arial'
        if 'times' in name_lower:
            return 'Times New Roman'
        if 'courier' in name_lower:
            return 'Courier New'
        if 'calibri' in name_lower:
            return 'Calibri'
        if 'georgia' in name_lower:
            return 'Georgia'
        if 'verdana' in name_lower:
            return 'Verdana'
        if 'tahoma' in name_lower:
            return 'Tahoma'
        if 'segoe' in name_lower:
            return 'Segoe UI'
        
        # Por defecto usar Arial (equivalente a Helvetica en Windows)
        return 'Arial'
    
    def adjust_rect_to_content(self):
        """Ajusta el rect del item para que se adapte al contenido del texto.
        
        Usa QFontMetrics con el zoom aplicado para calcular el tamaño correcto.
        CRÍTICO: Normaliza el rect a x=0, y=0 para que la posición esté en pos().
        Considera text_runs para calcular correctamente el tamaño con múltiples estilos.
        """
        from PyQt5.QtGui import QFontMetrics
        
        if not self.text:
            return
        
        current_rect = self.rect()
        
        # Si hay text_runs, calcular tamaño basado en ellos (más preciso)
        if self.text_runs and len(self.text_runs) > 0:
            new_width, new_height = self._calculate_size_from_runs()
        else:
            # Calcular tamaño con estilo uniforme
            new_width, new_height = self._calculate_size_uniform()
        
        # CRÍTICO: Normalizar el rect a x=0, y=0
        # La posición real del item se controla con pos(), no con el rect
        # Esto evita el bug de posición duplicada cuando se llama setPos()
        self.setRect(QRectF(0, 0, new_width, new_height))
    
    def _calculate_size_uniform(self):
        """Calcula el tamaño para texto con estilo uniforme.
        
        CRÍTICO: Expande las tabulaciones a espacios para calcular el ancho correctamente.
        Las tabulaciones típicamente equivalen a 4-8 espacios.
        """
        from PyQt5.QtGui import QFontMetrics
        
        # Constante: cada tabulación equivale a 4 espacios
        TAB_SIZE = 4
        
        # Aplicar zoom al tamaño de fuente
        scaled_font_size = self.font_size * self.zoom_level
        
        # Crear fuente para calcular métricas - usar fuente real del PDF
        font_family = self._map_pdf_font_to_system(self.font_name)
        font = QFont(font_family, int(scaled_font_size))
        if self.is_bold:
            font.setBold(True)
        metrics = QFontMetrics(font)
        
        # Calcular ancho de un espacio para expandir tabulaciones
        space_width = metrics.horizontalAdvance(' ')
        tab_width = space_width * TAB_SIZE
        
        # Calcular ancho y alto basado en el texto
        lines = self._text.split('\n')
        max_line_width = 0
        
        for line in lines:
            # Expandir tabulaciones a espacios equivalentes para medir correctamente
            if '\t' in line:
                # Reemplazar tabs por espacios equivalentes
                expanded_line = line.replace('\t', ' ' * TAB_SIZE)
                line_width = metrics.horizontalAdvance(expanded_line)
            else:
                line_width = metrics.horizontalAdvance(line)
            
            if line_width > max_line_width:
                max_line_width = line_width
        
        # Usar interlineado del PDF si está disponible, si no usar height de métricas
        if self.line_spacing > 0:
            effective_line_height = self.line_spacing * self.zoom_level
        else:
            effective_line_height = metrics.height()
        
        # Agregar padding generoso para asegurar que todo el texto cabe
        new_width = max_line_width + 20  # Padding aumentado
        new_height = effective_line_height * len(lines) + 10  # Padding aumentado
        
        return new_width, new_height
    
    def _calculate_size_from_runs(self):
        """Calcula el tamaño para texto con múltiples estilos (text_runs).
        
        Simula el algoritmo de _paint_with_runs() para calcular el tamaño correcto.
        Usa line_spacing del PDF si está disponible para un interlineado preciso.
        CRÍTICO: Expande tabulaciones a espacios para calcular el ancho correctamente.
        """
        from PyQt5.QtGui import QFontMetrics
        
        # Constante: cada tabulación equivale a 4 espacios
        TAB_SIZE = 4
        
        # Obtener fuente base para line_height - usar fuente real del PDF
        scaled_base_size = self.font_size * self.zoom_level
        base_font_family = self._map_pdf_font_to_system(self.font_name)
        base_font = QFont(base_font_family, int(scaled_base_size))
        base_metrics = QFontMetrics(base_font)
        
        # Usar interlineado del PDF si está disponible
        if self.line_spacing > 0:
            line_height = self.line_spacing * self.zoom_level
        else:
            line_height = base_metrics.height()
        
        # Variables para calcular dimensiones totales
        max_total_width = 0
        current_line_width = 0
        num_lines = 1
        last_line_y = None
        
        for run in self.text_runs:
            run_text = run.get('text', '')
            if not run_text:
                continue
            
            # Detectar cambio de línea usando needs_newline o line_y 
            needs_newline = run.get('needs_newline', False)
            line_y = run.get('line_y', 0)
            
            # Nueva línea si: needs_newline=True O cambio en line_y
            if needs_newline or (last_line_y is not None and line_y != last_line_y):
                # Guardar ancho de línea anterior
                if current_line_width > max_total_width:
                    max_total_width = current_line_width
                current_line_width = 0
                num_lines += 1
            last_line_y = line_y
            
            # Configurar fuente del run - aplicar zoom
            run_font_size = run.get('font_size', self.font_size)
            scaled_font_size = run_font_size * self.zoom_level
            is_bold = run.get('is_bold', False)
            is_italic = run.get('is_italic', False)
            
            run_font_name = run.get('font_name', self.font_name)
            font_family = self._map_pdf_font_to_system(run_font_name)
            font = QFont(font_family, int(scaled_font_size))
            if is_bold:
                font.setBold(True)
            if is_italic:
                font.setItalic(True)
            metrics = QFontMetrics(font)
            
            # Manejar saltos de línea internos en el texto del run
            run_lines = run_text.split('\n')
            for i, line in enumerate(run_lines):
                if i > 0:
                    # Salto de línea interno
                    if current_line_width > max_total_width:
                        max_total_width = current_line_width
                    current_line_width = 0
                    num_lines += 1
                
                # CRÍTICO: Expandir tabulaciones a espacios para medir correctamente
                if '\t' in line:
                    expanded_line = line.replace('\t', ' ' * TAB_SIZE)
                    current_line_width += metrics.horizontalAdvance(expanded_line)
                else:
                    current_line_width += metrics.horizontalAdvance(line)
        
        # Guardar la última línea
        if current_line_width > max_total_width:
            max_total_width = current_line_width
        
        # Agregar padding generoso para asegurar que todo el texto cabe
        new_width = max_total_width + 20  # Padding aumentado
        new_height = line_height * num_lines + 10  # Padding aumentado
        
        return new_width, new_height
    
    def _update_visual(self):
        """Actualiza el estilo visual según el estado."""
        if self.is_selected:
            # Seleccionado: borde azul sólido
            self.setPen(QPen(QColor(0, 120, 215), 2, Qt.SolidLine))
            self.setBrush(QBrush(QColor(0, 120, 215, 30)))
        elif self.is_hovered:
            # Hover: borde azul punteado
            self.setPen(QPen(QColor(0, 120, 215), 1, Qt.DashLine))
            self.setBrush(QBrush(QColor(0, 120, 215, 15)))
        else:
            # Normal: invisible
            self.setPen(QPen(Qt.NoPen))
            self.setBrush(QBrush(Qt.NoBrush))
    
    def set_selected(self, selected: bool):
        """Establece el estado de selección."""
        self.is_selected = selected
        self._update_visual()
    
    def hoverEnterEvent(self, event):
        """Mouse entra en el área."""
        self.is_hovered = True
        self._update_visual()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Mouse sale del área."""
        self.is_hovered = False
        self._update_visual()
        super().hoverLeaveEvent(event)
    
    def paint(self, painter, option, widget=None):
        """Dibuja el item. Si es overlay o está siendo arrastrado, dibuja el texto.
        
        CRÍTICO para PDFs de imagen: asegurar que el rect sea lo suficientemente
        grande y que el texto se dibuje COMPLETAMENTE sin fragmentación.
        Soporta texto multilínea con saltos de línea (\n).
        Si tiene text_runs, dibuja cada run con su estilo individual.
        """
        # Primero dibujar el rectángulo base (bordes de selección)
        super().paint(painter, option, widget)
        
        # Dibujar el texto si:
        # - Es overlay (texto visual no escrito al PDF)
        # - O está seleccionado (puede estar siendo arrastrado)
        # - O tiene pending_write (editado pero no guardado)
        should_draw_text = (
            getattr(self, 'is_overlay', False) or 
            getattr(self, 'is_selected', False) or
            getattr(self, 'pending_write', False)
        )
        
        if should_draw_text and self.text:
            rect = self.rect()
            
            from PyQt5.QtGui import QFontMetrics
            
            # Verificar si tiene text_runs (prioridad sobre has_mixed_styles)
            text_runs = getattr(self, 'text_runs', None)
            
            # Usar text_runs si existen y tienen contenido
            if text_runs and len(text_runs) > 0:
                # Dibujar con múltiples estilos usando text_runs
                self._paint_with_runs(painter, rect, text_runs)
            else:
                # Dibujar con estilo uniforme
                self._paint_uniform(painter, rect)
    
    def _paint_uniform(self, painter, rect):
        """Dibuja el texto con estilo uniforme.
        
        CRÍTICO: Expande tabulaciones a espacios para dibujar correctamente.
        """
        from PyQt5.QtGui import QFontMetrics
        
        # Constante: cada tabulación equivale a 4 espacios
        TAB_SIZE = 4
        
        # Configurar fuente - aplicar zoom al tamaño
        scaled_font_size = self.font_size * self.zoom_level
        # Usar la fuente real del PDF, mapeada a una fuente del sistema
        font_family = self._map_pdf_font_to_system(self.font_name)
        font = QFont(font_family, int(scaled_font_size))
        if self.is_bold:
            font.setBold(True)
        painter.setFont(font)
        
        metrics = QFontMetrics(font)
        
        # Configurar color
        r, g, b = self.text_color
        # Convertir de 0-1 a 0-255 si es necesario
        if max(r, g, b) <= 1:
            r, g, b = int(r * 255), int(g * 255), int(b * 255)
        painter.setPen(QColor(r, g, b))
        
        # Dibujar texto multilínea línea por línea
        lines = self._text.split('\n')
        line_height = metrics.height()
        y_offset = metrics.ascent()  # Empezar desde el baseline de la primera línea
        
        for i, line in enumerate(lines):
            if line:  # Solo dibujar si la línea tiene contenido
                # CRÍTICO: Expandir tabulaciones a espacios para dibujar
                display_line = line.replace('\t', ' ' * TAB_SIZE) if '\t' in line else line
                painter.drawText(
                    int(rect.x()), 
                    int(rect.y() + y_offset + i * line_height), 
                    display_line
                )
    
    def _paint_with_runs(self, painter, rect, text_runs):
        """Dibuja el texto usando runs con estilos individuales."""
        from PyQt5.QtGui import QFontMetrics
        
        x_offset = int(rect.x())
        current_line_y = 0
        last_line_y = None
        
        # Aplicar zoom al tamaño de fuente base
        scaled_base_size = self.font_size * self.zoom_level
        base_font_family = self._map_pdf_font_to_system(self.font_name)
        base_font = QFont(base_font_family, int(scaled_base_size))
        base_metrics = QFontMetrics(base_font)
        
        # Usar interlineado del PDF si está disponible
        if self.line_spacing > 0:
            line_height = self.line_spacing * self.zoom_level
        else:
            line_height = base_metrics.height()
        y_offset = base_metrics.ascent()
        
        for run in text_runs:
            run_text = run.get('text', '')
            if not run_text:
                continue
            
            # Detectar cambio de línea usando needs_newline o line_y
            needs_newline = run.get('needs_newline', False)
            line_y = run.get('line_y', 0)
            
            # Nueva línea si: needs_newline=True O cambio en line_y
            if needs_newline or (last_line_y is not None and line_y != last_line_y):
                # Nueva línea - reiniciar x y avanzar y
                x_offset = int(rect.x())
                current_line_y += line_height
            last_line_y = line_y
            
            # Configurar fuente del run - aplicar zoom
            run_font_size = run.get('font_size', self.font_size)
            scaled_font_size = run_font_size * self.zoom_level
            is_bold = run.get('is_bold', False)
            is_italic = run.get('is_italic', False)
            run_font_name = run.get('font_name', self.font_name)
            
            # Usar la fuente real del PDF, mapeada a una fuente del sistema
            font_family = self._map_pdf_font_to_system(run_font_name)
            font = QFont(font_family, int(scaled_font_size))
            if is_bold:
                font.setBold(True)
            if is_italic:
                font.setItalic(True)
            painter.setFont(font)
            
            metrics = QFontMetrics(font)
            
            # Configurar color del run
            color_str = run.get('color', '#000000')
            try:
                if isinstance(color_str, str):
                    color = QColor(color_str)
                else:
                    r, g, b = color_str
                    if max(r, g, b) <= 1:
                        r, g, b = int(r * 255), int(g * 255), int(b * 255)
                    color = QColor(r, g, b)
            except:
                color = QColor(0, 0, 0)
            painter.setPen(color)
            
            # Dibujar el texto del run (manejar saltos de línea internos)
            # CRÍTICO: Expandir tabulaciones a espacios
            TAB_SIZE = 4
            run_lines = run_text.split('\n')
            for i, line in enumerate(run_lines):
                if i > 0:
                    # Salto de línea interno - nueva línea
                    x_offset = int(rect.x())
                    current_line_y += line_height
                
                if line:
                    # Expandir tabulaciones para dibujar correctamente
                    display_line = line.replace('\t', ' ' * TAB_SIZE) if '\t' in line else line
                    painter.drawText(
                        x_offset, 
                        int(rect.y() + y_offset + current_line_y), 
                        display_line
                    )
                    x_offset += metrics.horizontalAdvance(display_line)

