"""
ContentStreamParser - Parser de content streams PDF para extraer operadores de texto.

Este módulo parsea el content stream de una página PDF para extraer
información tipográfica que PyMuPDF no expone directamente:

- Tc: Character spacing (espaciado entre caracteres)
- Tw: Word spacing (espaciado entre palabras)
- Ts: Text rise (superscript/subscript offset)
- Tm: Text matrix (posición y transformación)
- TL: Text leading (interlineado)
- Tf: Font selection (fuente y tamaño)
- Tr: Text rendering mode
- Tz: Horizontal scaling

Referencia: PDF 1.7 Specification, Section 9 (Text)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class TextOperator(Enum):
    """Operadores de texto PDF según especificación PDF 1.7."""
    
    # Text state operators (Section 9.3)
    Tc = "Tc"   # Set character spacing
    Tw = "Tw"   # Set word spacing
    Tz = "Tz"   # Set horizontal scaling
    TL = "TL"   # Set text leading
    Tf = "Tf"   # Set font and size
    Tr = "Tr"   # Set text rendering mode
    Ts = "Ts"   # Set text rise
    
    # Text object operators (Section 9.4)
    BT = "BT"   # Begin text object
    ET = "ET"   # End text object
    
    # Text positioning operators (Section 9.4.2)
    Td = "Td"   # Move text position
    TD = "TD"   # Move text position and set leading
    Tm = "Tm"   # Set text matrix
    T_star = "T*"  # Move to start of next line
    
    # Text showing operators (Section 9.4.3)
    Tj = "Tj"   # Show text string
    TJ = "TJ"   # Show text with individual glyph positioning
    quote = "'"   # Move to next line and show text
    double_quote = '"'  # Set spacing, move to next line, show text


@dataclass
class TextState:
    """
    Estado actual del texto mientras se parsea el content stream.
    
    Según PDF 1.7, Section 9.3 - Text State Parameters.
    Los valores por defecto son los especificados en el estándar PDF.
    """
    # Text state parameters
    char_spacing: float = 0.0       # Tc (points, default 0)
    word_spacing: float = 0.0       # Tw (points, default 0)
    horizontal_scale: float = 100.0  # Tz (percentage, default 100)
    leading: float = 0.0            # TL (points, default 0)
    font_name: Optional[str] = None  # Current font name
    font_size: float = 0.0          # Current font size
    render_mode: int = 0            # Tr (0-7, default 0 = fill)
    rise: float = 0.0               # Ts (points, default 0)
    
    # Text matrix components (Tm)
    # Default: identity matrix [1 0 0 1 0 0]
    text_matrix: Tuple[float, float, float, float, float, float] = (
        1.0, 0.0, 0.0, 1.0, 0.0, 0.0
    )
    
    # Line matrix (set at BT, updated by positioning operators)
    line_matrix: Tuple[float, float, float, float, float, float] = (
        1.0, 0.0, 0.0, 1.0, 0.0, 0.0
    )
    
    # CTM (Current Transformation Matrix) - from graphics state
    ctm: Tuple[float, float, float, float, float, float] = (
        1.0, 0.0, 0.0, 1.0, 0.0, 0.0
    )
    
    def copy(self) -> 'TextState':
        """Create a copy of the current state."""
        return TextState(
            char_spacing=self.char_spacing,
            word_spacing=self.word_spacing,
            horizontal_scale=self.horizontal_scale,
            leading=self.leading,
            font_name=self.font_name,
            font_size=self.font_size,
            render_mode=self.render_mode,
            rise=self.rise,
            text_matrix=self.text_matrix,
            line_matrix=self.line_matrix,
            ctm=self.ctm
        )
    
    def reset_text_object(self) -> None:
        """Reset state for new text object (BT operator)."""
        self.text_matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        self.line_matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    
    def get_effective_position(self) -> Tuple[float, float]:
        """Get effective text position (x, y) considering all matrices."""
        # Text position is the translation component of text_matrix
        tx = self.text_matrix[4]
        ty = self.text_matrix[5]
        
        # Apply CTM transformation
        x = self.ctm[0] * tx + self.ctm[2] * ty + self.ctm[4]
        y = self.ctm[1] * tx + self.ctm[3] * ty + self.ctm[5]
        
        return (x, y)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            'char_spacing': self.char_spacing,
            'word_spacing': self.word_spacing,
            'horizontal_scale': self.horizontal_scale,
            'leading': self.leading,
            'font_name': self.font_name,
            'font_size': self.font_size,
            'render_mode': self.render_mode,
            'rise': self.rise,
            'text_matrix': list(self.text_matrix),
            'line_matrix': list(self.line_matrix),
            'ctm': list(self.ctm)
        }


@dataclass
class TextShowOperation:
    """
    Representa una operación de mostrar texto (Tj, TJ, ', ").
    
    Attributes:
        text: El texto a mostrar (decodificado)
        operator: El operador usado (Tj, TJ, ', ")
        state: Estado del texto en el momento de la operación
        glyph_adjustments: Lista de ajustes de glifos para TJ
        raw_operand: Operando raw sin procesar
        position_in_stream: Posición en el content stream original
    """
    text: str
    operator: str
    state: TextState
    glyph_adjustments: Optional[List[float]] = None
    raw_operand: Optional[str] = None
    position_in_stream: int = 0
    
    @property
    def char_spacing(self) -> float:
        """Get character spacing (Tc) at this operation."""
        return self.state.char_spacing
    
    @property
    def word_spacing(self) -> float:
        """Get word spacing (Tw) at this operation."""
        return self.state.word_spacing
    
    @property
    def rise(self) -> float:
        """Get text rise (Ts) at this operation."""
        return self.state.rise
    
    @property
    def font_name(self) -> Optional[str]:
        """Get font name at this operation."""
        return self.state.font_name
    
    @property
    def font_size(self) -> float:
        """Get font size at this operation."""
        return self.state.font_size
    
    @property
    def position(self) -> Tuple[float, float]:
        """Get text position (x, y)."""
        return self.state.get_effective_position()
    
    @property
    def has_char_spacing(self) -> bool:
        """Check if non-zero character spacing is set."""
        return abs(self.state.char_spacing) > 0.001
    
    @property
    def has_word_spacing(self) -> bool:
        """Check if non-zero word spacing is set."""
        return abs(self.state.word_spacing) > 0.001
    
    @property
    def has_rise(self) -> bool:
        """Check if non-zero text rise is set (super/subscript)."""
        return abs(self.state.rise) > 0.001
    
    @property
    def is_superscript(self) -> bool:
        """Check if text is likely superscript (positive rise)."""
        return self.state.rise > 0.5  # Threshold for significant rise
    
    @property
    def is_subscript(self) -> bool:
        """Check if text is likely subscript (negative rise)."""
        return self.state.rise < -0.5  # Threshold for significant drop
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'text': self.text,
            'operator': self.operator,
            'state': self.state.to_dict(),
            'glyph_adjustments': self.glyph_adjustments,
            'position_in_stream': self.position_in_stream
        }


@dataclass
class ParsedTextBlock:
    """
    Bloque de texto parseado del content stream.
    
    Representa todo el contenido entre BT y ET.
    """
    operations: List[TextShowOperation] = field(default_factory=list)
    start_position: int = 0
    end_position: int = 0
    
    @property
    def text(self) -> str:
        """Concatenate all text from operations."""
        return ''.join(op.text for op in self.operations)
    
    @property
    def has_spacing_info(self) -> bool:
        """Check if any operation has non-default spacing."""
        return any(op.has_char_spacing or op.has_word_spacing 
                   for op in self.operations)
    
    @property
    def has_rise_info(self) -> bool:
        """Check if any operation has text rise."""
        return any(op.has_rise for op in self.operations)
    
    def get_unique_fonts(self) -> List[Tuple[str, float]]:
        """Get list of unique (font_name, font_size) pairs."""
        fonts = set()
        for op in self.operations:
            if op.font_name:
                fonts.add((op.font_name, op.font_size))
        return list(fonts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'operations': [op.to_dict() for op in self.operations],
            'start_position': self.start_position,
            'end_position': self.end_position,
            'text': self.text
        }


class ContentStreamParser:
    """
    Parser de content streams PDF para extraer información de texto.
    
    Este parser lee el content stream raw de una página PDF y extrae
    todos los operadores de texto junto con sus parámetros.
    
    Usage:
        parser = ContentStreamParser()
        blocks = parser.parse(content_stream)
        for block in blocks:
            for op in block.operations:
                print(f"Text: {op.text}, Tc={op.char_spacing}, Tw={op.word_spacing}")
    """
    
    # Regex patterns for parsing
    # Number: integer or float, possibly negative
    NUMBER_PATTERN = re.compile(r'[+-]?(?:\d+\.?\d*|\.\d+)')
    
    # String: literal (parentheses) or hex <...>
    LITERAL_STRING_PATTERN = re.compile(r'\((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*\)')
    HEX_STRING_PATTERN = re.compile(r'<[0-9A-Fa-f\s]*>')
    
    # Array: [...] 
    ARRAY_PATTERN = re.compile(r'\[.*?\]', re.DOTALL)
    
    # Name: /Name
    NAME_PATTERN = re.compile(r'/[^\s\[\]<>()/%]+')
    
    # Operator: sequence of letters possibly with * or '
    OPERATOR_PATTERN = re.compile(r"[A-Za-z*'\"]+")
    
    def __init__(self):
        """Initialize the parser."""
        self.text_blocks: List[ParsedTextBlock] = []
        self.current_state: TextState = TextState()
        self.state_stack: List[TextState] = []  # For q/Q graphics state
        self.in_text_object: bool = False
        self.current_block: Optional[ParsedTextBlock] = None
        
        # Font map from page resources (optional)
        self._font_map: Dict[str, str] = {}
    
    def set_font_map(self, font_map: Dict[str, str]) -> None:
        """
        Set mapping from font reference names to actual font names.
        
        Args:
            font_map: Dict mapping /F1, /F2, etc. to actual font names
        """
        self._font_map = font_map
    
    def parse(self, content_stream: bytes | str) -> List[ParsedTextBlock]:
        """
        Parse a PDF content stream and extract text blocks.
        
        Args:
            content_stream: Raw content stream (bytes or string)
            
        Returns:
            List of ParsedTextBlock containing all text operations
        """
        # Reset state
        self.text_blocks = []
        self.current_state = TextState()
        self.state_stack = []
        self.in_text_object = False
        self.current_block = None
        
        # Convert bytes to string if needed
        if isinstance(content_stream, bytes):
            try:
                content = content_stream.decode('latin-1')  # PDF uses latin-1
            except UnicodeDecodeError:
                content = content_stream.decode('utf-8', errors='replace')
        else:
            content = content_stream
        
        # Tokenize and process
        tokens = self._tokenize(content)
        self._process_tokens(tokens, content)
        
        return self.text_blocks
    
    def _tokenize(self, content: str) -> List[Tuple[str, str, int]]:
        """
        Tokenize the content stream.
        
        Returns list of (token_type, token_value, position) tuples.
        Token types: 'number', 'string', 'hex_string', 'array', 'name', 'operator'
        """
        tokens = []
        pos = 0
        length = len(content)
        
        while pos < length:
            # Skip whitespace
            while pos < length and content[pos] in ' \t\r\n':
                pos += 1
            
            if pos >= length:
                break
            
            char = content[pos]
            
            # Comment
            if char == '%':
                end = content.find('\n', pos)
                if end == -1:
                    end = length
                pos = end + 1
                continue
            
            # Literal string
            if char == '(':
                match = self.LITERAL_STRING_PATTERN.match(content, pos)
                if match:
                    tokens.append(('string', match.group(), pos))
                    pos = match.end()
                    continue
                else:
                    # Handle unmatched - skip
                    pos += 1
                    continue
            
            # Hex string
            if char == '<':
                # Check if it's a hex string or dictionary
                if pos + 1 < length and content[pos + 1] == '<':
                    # Dictionary start - skip for now
                    pos += 2
                    continue
                match = self.HEX_STRING_PATTERN.match(content, pos)
                if match:
                    tokens.append(('hex_string', match.group(), pos))
                    pos = match.end()
                    continue
                else:
                    pos += 1
                    continue
            
            # Array
            if char == '[':
                # Find matching ]
                depth = 1
                end = pos + 1
                while end < length and depth > 0:
                    if content[end] == '[':
                        depth += 1
                    elif content[end] == ']':
                        depth -= 1
                    elif content[end] == '(':
                        # Skip literal strings inside array
                        str_match = self.LITERAL_STRING_PATTERN.match(content, end)
                        if str_match:
                            end = str_match.end()
                            continue
                    end += 1
                tokens.append(('array', content[pos:end], pos))
                pos = end
                continue
            
            # Name
            if char == '/':
                match = self.NAME_PATTERN.match(content, pos)
                if match:
                    tokens.append(('name', match.group(), pos))
                    pos = match.end()
                    continue
                else:
                    pos += 1
                    continue
            
            # Number
            if char in '+-.' or char.isdigit():
                match = self.NUMBER_PATTERN.match(content, pos)
                if match:
                    tokens.append(('number', match.group(), pos))
                    pos = match.end()
                    continue
            
            # Operator or other
            if char.isalpha() or char in "*'\"":
                match = self.OPERATOR_PATTERN.match(content, pos)
                if match:
                    tokens.append(('operator', match.group(), pos))
                    pos = match.end()
                    continue
            
            # Skip unknown characters (like >> for dict end)
            pos += 1
        
        return tokens
    
    def _process_tokens(self, tokens: List[Tuple[str, str, int]], 
                        content: str) -> None:
        """Process tokenized content stream."""
        operand_stack: List[Tuple[str, str, int]] = []
        
        for token_type, token_value, position in tokens:
            if token_type == 'operator':
                self._handle_operator(token_value, operand_stack, position)
                operand_stack = []
            else:
                operand_stack.append((token_type, token_value, position))
    
    def _handle_operator(self, operator: str, 
                         operands: List[Tuple[str, str, int]],
                         position: int) -> None:
        """Handle a PDF operator with its operands."""
        
        # Graphics state operators
        if operator == 'q':
            # Save graphics state
            self.state_stack.append(self.current_state.copy())
            return
        
        if operator == 'Q':
            # Restore graphics state
            if self.state_stack:
                self.current_state = self.state_stack.pop()
            return
        
        # CTM operators
        if operator == 'cm':
            # Modify CTM: [a b c d e f] cm
            if len(operands) >= 6:
                try:
                    a = float(operands[0][1])
                    b = float(operands[1][1])
                    c = float(operands[2][1])
                    d = float(operands[3][1])
                    e = float(operands[4][1])
                    f = float(operands[5][1])
                    # Concatenate with current CTM
                    self.current_state.ctm = self._multiply_matrices(
                        (a, b, c, d, e, f),
                        self.current_state.ctm
                    )
                except (ValueError, IndexError):
                    pass
            return
        
        # Text object operators
        if operator == 'BT':
            self.in_text_object = True
            self.current_state.reset_text_object()
            self.current_block = ParsedTextBlock(start_position=position)
            return
        
        if operator == 'ET':
            if self.current_block and self.current_block.operations:
                self.current_block.end_position = position
                self.text_blocks.append(self.current_block)
            self.current_block = None
            self.in_text_object = False
            return
        
        # Only process text operators inside text object
        if not self.in_text_object:
            return
        
        # Text state operators
        if operator == 'Tc':
            # Set character spacing
            if operands:
                try:
                    self.current_state.char_spacing = float(operands[0][1])
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'Tw':
            # Set word spacing
            if operands:
                try:
                    self.current_state.word_spacing = float(operands[0][1])
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'Tz':
            # Set horizontal scaling
            if operands:
                try:
                    self.current_state.horizontal_scale = float(operands[0][1])
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'TL':
            # Set text leading
            if operands:
                try:
                    self.current_state.leading = float(operands[0][1])
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'Tf':
            # Set font: /FontName size Tf
            if len(operands) >= 2:
                try:
                    font_ref = operands[0][1]  # e.g., "/F1"
                    font_size = float(operands[1][1])
                    
                    # Look up actual font name
                    font_name = self._font_map.get(font_ref, font_ref)
                    
                    self.current_state.font_name = font_name
                    self.current_state.font_size = font_size
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'Tr':
            # Set text rendering mode
            if operands:
                try:
                    self.current_state.render_mode = int(float(operands[0][1]))
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'Ts':
            # Set text rise
            if operands:
                try:
                    self.current_state.rise = float(operands[0][1])
                except (ValueError, IndexError):
                    pass
            return
        
        # Text positioning operators
        if operator == 'Td':
            # Move text position: tx ty Td
            if len(operands) >= 2:
                try:
                    tx = float(operands[0][1])
                    ty = float(operands[1][1])
                    self._update_text_position(tx, ty)
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'TD':
            # Move text position and set leading: tx ty TD
            if len(operands) >= 2:
                try:
                    tx = float(operands[0][1])
                    ty = float(operands[1][1])
                    self.current_state.leading = -ty
                    self._update_text_position(tx, ty)
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'Tm':
            # Set text matrix: a b c d e f Tm
            if len(operands) >= 6:
                try:
                    a = float(operands[0][1])
                    b = float(operands[1][1])
                    c = float(operands[2][1])
                    d = float(operands[3][1])
                    e = float(operands[4][1])
                    f = float(operands[5][1])
                    self.current_state.text_matrix = (a, b, c, d, e, f)
                    self.current_state.line_matrix = (a, b, c, d, e, f)
                except (ValueError, IndexError):
                    pass
            return
        
        if operator == 'T*':
            # Move to start of next line
            self._update_text_position(0, -self.current_state.leading)
            return
        
        # Text showing operators
        if operator == 'Tj':
            # Show text string
            if operands:
                text = self._decode_string(operands[0][1])
                self._add_text_operation(text, 'Tj', position, operands[0][1])
            return
        
        if operator == 'TJ':
            # Show text with glyph positioning
            if operands and operands[0][0] == 'array':
                text, adjustments = self._parse_tj_array(operands[0][1])
                self._add_text_operation(text, 'TJ', position, 
                                        operands[0][1], adjustments)
            return
        
        if operator == "'":
            # Move to next line and show text
            self._update_text_position(0, -self.current_state.leading)
            if operands:
                text = self._decode_string(operands[0][1])
                self._add_text_operation(text, "'", position, operands[0][1])
            return
        
        if operator == '"':
            # Set spacing, move to next line, show text
            if len(operands) >= 3:
                try:
                    self.current_state.word_spacing = float(operands[0][1])
                    self.current_state.char_spacing = float(operands[1][1])
                except (ValueError, IndexError):
                    pass
                self._update_text_position(0, -self.current_state.leading)
                text = self._decode_string(operands[2][1])
                self._add_text_operation(text, '"', position, operands[2][1])
            return
    
    def _update_text_position(self, tx: float, ty: float) -> None:
        """Update text position using Td-style offset."""
        lm = self.current_state.line_matrix
        # New line matrix = translate(tx, ty) * line_matrix
        new_lm = (
            lm[0], lm[1],
            lm[2], lm[3],
            lm[0] * tx + lm[2] * ty + lm[4],
            lm[1] * tx + lm[3] * ty + lm[5]
        )
        self.current_state.line_matrix = new_lm
        self.current_state.text_matrix = new_lm
    
    def _multiply_matrices(self, m1: Tuple[float, ...], 
                           m2: Tuple[float, ...]) -> Tuple[float, ...]:
        """Multiply two 3x3 transformation matrices (in PDF format)."""
        # m = [a b 0]   represented as (a, b, c, d, e, f)
        #     [c d 0]
        #     [e f 1]
        a1, b1, c1, d1, e1, f1 = m1
        a2, b2, c2, d2, e2, f2 = m2
        
        return (
            a1 * a2 + b1 * c2,
            a1 * b2 + b1 * d2,
            c1 * a2 + d1 * c2,
            c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2,
            e1 * b2 + f1 * d2 + f2
        )
    
    def _decode_string(self, string_token: str) -> str:
        """Decode a PDF string token to text."""
        if string_token.startswith('(') and string_token.endswith(')'):
            return self._decode_literal_string(string_token[1:-1])
        elif string_token.startswith('<') and string_token.endswith('>'):
            return self._decode_hex_string(string_token[1:-1])
        return string_token
    
    def _decode_literal_string(self, content: str) -> str:
        """Decode a PDF literal string (parentheses delimited)."""
        result = []
        i = 0
        while i < len(content):
            char = content[i]
            if char == '\\':
                if i + 1 < len(content):
                    next_char = content[i + 1]
                    if next_char == 'n':
                        result.append('\n')
                        i += 2
                    elif next_char == 'r':
                        result.append('\r')
                        i += 2
                    elif next_char == 't':
                        result.append('\t')
                        i += 2
                    elif next_char == 'b':
                        result.append('\b')
                        i += 2
                    elif next_char == 'f':
                        result.append('\f')
                        i += 2
                    elif next_char == '(':
                        result.append('(')
                        i += 2
                    elif next_char == ')':
                        result.append(')')
                        i += 2
                    elif next_char == '\\':
                        result.append('\\')
                        i += 2
                    elif next_char.isdigit():
                        # Octal escape
                        octal = ''
                        j = i + 1
                        while j < len(content) and j < i + 4 and content[j].isdigit():
                            octal += content[j]
                            j += 1
                        try:
                            result.append(chr(int(octal, 8)))
                        except ValueError:
                            pass
                        i = j
                    else:
                        result.append(next_char)
                        i += 2
                else:
                    i += 1
            else:
                result.append(char)
                i += 1
        return ''.join(result)
    
    def _decode_hex_string(self, content: str) -> str:
        """Decode a PDF hex string."""
        # Remove whitespace
        hex_clean = ''.join(content.split())
        # Pad with 0 if odd length
        if len(hex_clean) % 2:
            hex_clean += '0'
        
        result = []
        for i in range(0, len(hex_clean), 2):
            try:
                byte_val = int(hex_clean[i:i+2], 16)
                result.append(chr(byte_val))
            except ValueError:
                pass
        return ''.join(result)
    
    def _parse_tj_array(self, array_token: str) -> Tuple[str, List[float]]:
        """
        Parse a TJ array: [(string) adjustment (string) adjustment ...]
        
        Returns: (concatenated text, list of adjustments)
        """
        text_parts = []
        adjustments = []
        
        # Remove outer brackets
        content = array_token[1:-1].strip()
        
        pos = 0
        while pos < len(content):
            # Skip whitespace
            while pos < len(content) and content[pos] in ' \t\r\n':
                pos += 1
            
            if pos >= len(content):
                break
            
            char = content[pos]
            
            # String (literal or hex)
            if char == '(':
                match = self.LITERAL_STRING_PATTERN.match(content, pos)
                if match:
                    text_parts.append(self._decode_literal_string(match.group()[1:-1]))
                    pos = match.end()
                    continue
            elif char == '<':
                match = self.HEX_STRING_PATTERN.match(content, pos)
                if match:
                    text_parts.append(self._decode_hex_string(match.group()[1:-1]))
                    pos = match.end()
                    continue
            
            # Number (adjustment)
            if char in '+-.' or char.isdigit():
                match = self.NUMBER_PATTERN.match(content, pos)
                if match:
                    try:
                        adjustments.append(float(match.group()))
                    except ValueError:
                        pass
                    pos = match.end()
                    continue
            
            pos += 1
        
        return ''.join(text_parts), adjustments
    
    def _add_text_operation(self, text: str, operator: str, position: int,
                            raw_operand: str = None,
                            glyph_adjustments: List[float] = None) -> None:
        """Add a text show operation to the current block."""
        if self.current_block is None:
            return
        
        operation = TextShowOperation(
            text=text,
            operator=operator,
            state=self.current_state.copy(),
            glyph_adjustments=glyph_adjustments,
            raw_operand=raw_operand,
            position_in_stream=position
        )
        
        self.current_block.operations.append(operation)


def parse_content_stream(content: bytes | str,
                         font_map: Optional[Dict[str, str]] = None
                         ) -> List[ParsedTextBlock]:
    """
    Convenience function to parse a content stream.
    
    Args:
        content: Raw content stream
        font_map: Optional mapping from font references to actual names
        
    Returns:
        List of ParsedTextBlock
    """
    parser = ContentStreamParser()
    if font_map:
        parser.set_font_map(font_map)
    return parser.parse(content)


def extract_text_state_from_page(page, 
                                 target_text: str = None
                                 ) -> List[TextShowOperation]:
    """
    Extract text state information from a PyMuPDF page.
    
    Args:
        page: fitz.Page object
        target_text: Optional - only return operations containing this text
        
    Returns:
        List of TextShowOperation with full state info
    """
    # Get font map from page resources
    font_map = {}
    try:
        fonts = page.get_fonts(full=True)
        for font_info in fonts:
            xref, _, font_type, basename, name, encoding = font_info[:6]
            # Create mapping like /F1 -> actual font name
            # Note: The actual reference name needs to come from resources
            if name:
                font_map[f"/{name}"] = basename or name
    except Exception as e:
        logger.warning(f"Could not extract font map: {e}")
    
    # Get content stream
    try:
        content = page.read_contents()
        if content is None:
            return []
    except Exception as e:
        logger.warning(f"Could not read page contents: {e}")
        return []
    
    # Parse content stream
    parser = ContentStreamParser()
    parser.set_font_map(font_map)
    blocks = parser.parse(content)
    
    # Collect all operations
    operations = []
    for block in blocks:
        for op in block.operations:
            if target_text is None or target_text in op.text:
                operations.append(op)
    
    return operations


def get_spacing_info_for_text(page, text: str) -> Optional[Dict[str, Any]]:
    """
    Get spacing information (Tc, Tw, Ts) for specific text on a page.
    
    Args:
        page: fitz.Page object
        text: Text to search for
        
    Returns:
        Dict with spacing info, or None if text not found
    """
    operations = extract_text_state_from_page(page, target_text=text)
    
    if not operations:
        return None
    
    # Return info from first matching operation
    op = operations[0]
    return {
        'text': op.text,
        'char_spacing': op.char_spacing,
        'word_spacing': op.word_spacing,
        'rise': op.rise,
        'font_name': op.font_name,
        'font_size': op.font_size,
        'horizontal_scale': op.state.horizontal_scale,
        'render_mode': op.state.render_mode,
        'leading': op.state.leading,
        'position': op.position,
        'text_matrix': op.state.text_matrix,
        'has_char_spacing': op.has_char_spacing,
        'has_word_spacing': op.has_word_spacing,
        'is_superscript': op.is_superscript,
        'is_subscript': op.is_subscript
    }
