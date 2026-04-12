"""
ObjectSubstitution - Estrategia de sustitución directa de objetos PDF.

Este módulo implementa la estrategia de sustitución de objetos para
edición de texto PDF, que modifica directamente el content stream
en lugar de usar overlays.

Características:
- Localiza operadores de texto específicos en el content stream
- Modifica operandos preservando estructura del PDF
- Genera content streams válidos con los cambios aplicados
- Incluye validación y rollback para seguridad
- Preserva estado gráfico y atributos de texto

Advertencia: Esta estrategia es más arriesgada que overlay pero
produce PDFs más limpios sin capas adicionales.

PHASE3-3D02: Estrategia de sustitución de objetos (8h estimado)
Dependencia: 3A-02 (ContentStreamParser)
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid
import re
import logging

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    fitz = None

from .content_stream_parser import (
    ContentStreamParser,
)

logger = logging.getLogger(__name__)


# ================== Enums ==================


class SubstitutionType(Enum):
    """
    Tipos de sustitución de objetos PDF.
    
    Define el nivel de modificación en el content stream.
    """
    OPERAND_ONLY = auto()       # Solo cambiar operando (texto)
    OPERATOR_REPLACE = auto()   # Reemplazar operador completo
    BLOCK_REPLACE = auto()      # Reemplazar bloque BT...ET completo
    STREAM_REBUILD = auto()     # Reconstruir content stream
    
    def __str__(self) -> str:
        descriptions = {
            SubstitutionType.OPERAND_ONLY: "Solo operando",
            SubstitutionType.OPERATOR_REPLACE: "Operador completo",
            SubstitutionType.BLOCK_REPLACE: "Bloque BT/ET",
            SubstitutionType.STREAM_REBUILD: "Reconstruir stream",
        }
        return descriptions.get(self, self.name)
    
    @property
    def risk_level(self) -> int:
        """
        Nivel de riesgo (1-10) de esta estrategia.
        
        Mayor número = mayor riesgo de corrupción.
        """
        levels = {
            SubstitutionType.OPERAND_ONLY: 2,
            SubstitutionType.OPERATOR_REPLACE: 4,
            SubstitutionType.BLOCK_REPLACE: 6,
            SubstitutionType.STREAM_REBUILD: 8,
        }
        return levels.get(self, 5)
    
    @property
    def description(self) -> str:
        """Descripción detallada de la estrategia."""
        descriptions = {
            SubstitutionType.OPERAND_ONLY: (
                "Modifica solo el operando de texto sin tocar operadores. "
                "Más seguro pero limitado a textos de igual tamaño."
            ),
            SubstitutionType.OPERATOR_REPLACE: (
                "Reemplaza el operador completo incluyendo operandos. "
                "Permite cambios de tamaño de texto."
            ),
            SubstitutionType.BLOCK_REPLACE: (
                "Reemplaza todo el bloque de texto (BT...ET). "
                "Permite reestructurar el texto completamente."
            ),
            SubstitutionType.STREAM_REBUILD: (
                "Reconstruye el content stream completo. "
                "Máxima flexibilidad pero mayor riesgo."
            ),
        }
        return descriptions.get(self, "Sin descripción")


class SubstitutionStatus(Enum):
    """Estado del resultado de sustitución."""
    SUCCESS = auto()            # Sustitución exitosa
    PARTIAL_SUCCESS = auto()    # Parcialmente exitoso con warnings
    VALIDATION_FAILED = auto()  # Falló validación pre-aplicación
    ENCODING_ERROR = auto()     # Error de codificación de texto
    STRUCTURE_ERROR = auto()    # Error en estructura del PDF
    ROLLBACK_APPLIED = auto()   # Se aplicó rollback por error
    FAILED = auto()             # Falló completamente
    
    @property
    def is_success(self) -> bool:
        """Verifica si el estado indica éxito."""
        return self in (
            SubstitutionStatus.SUCCESS,
            SubstitutionStatus.PARTIAL_SUCCESS,
        )


class MatchStrategy(Enum):
    """Estrategia para localizar texto a sustituir."""
    EXACT = auto()              # Coincidencia exacta
    CONTAINS = auto()           # Texto contiene el patrón
    REGEX = auto()              # Match por expresión regular
    POSITION = auto()           # Por posición en página
    BLOCK_INDEX = auto()        # Por índice de bloque BT
    OPERATOR_INDEX = auto()     # Por índice absoluto de operador
    
    def __str__(self) -> str:
        descriptions = {
            MatchStrategy.EXACT: "Exacto",
            MatchStrategy.CONTAINS: "Contiene",
            MatchStrategy.REGEX: "Regex",
            MatchStrategy.POSITION: "Posición",
            MatchStrategy.BLOCK_INDEX: "Índice bloque",
            MatchStrategy.OPERATOR_INDEX: "Índice operador",
        }
        return descriptions.get(self, self.name)


# ================== Dataclasses ==================


@dataclass
class TextLocation:
    """
    Ubicación de un texto en el content stream.
    
    Representa la posición exacta de un operador de texto
    para poder sustituirlo.
    """
    # Identificación
    location_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Posición en página
    page_num: int = 0
    
    # Posición en content stream (bytes)
    stream_start: int = 0
    stream_end: int = 0
    
    # Índices
    block_index: int = 0        # Índice del bloque BT
    operation_index: int = 0     # Índice dentro del bloque
    
    # Texto original
    original_text: str = ""
    operator: str = "Tj"        # Operador usado (Tj, TJ, ', ")
    
    # Estado de texto en ese punto
    text_state: Optional[Dict[str, Any]] = None
    
    # Posición visual en página
    position_x: float = 0.0
    position_y: float = 0.0
    
    # Raw content del operador completo
    raw_operator: str = ""
    
    def __post_init__(self):
        """Validación post-inicialización."""
        if self.stream_end < self.stream_start:
            self.stream_end = self.stream_start
    
    @property
    def byte_length(self) -> int:
        """Longitud en bytes del operador."""
        return self.stream_end - self.stream_start
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'location_id': self.location_id,
            'page_num': self.page_num,
            'stream_start': self.stream_start,
            'stream_end': self.stream_end,
            'block_index': self.block_index,
            'operation_index': self.operation_index,
            'original_text': self.original_text,
            'operator': self.operator,
            'text_state': self.text_state,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'raw_operator': self.raw_operator,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextLocation':
        """Crea desde diccionario."""
        return cls(
            location_id=data.get('location_id', ''),
            page_num=data.get('page_num', 0),
            stream_start=data.get('stream_start', 0),
            stream_end=data.get('stream_end', 0),
            block_index=data.get('block_index', 0),
            operation_index=data.get('operation_index', 0),
            original_text=data.get('original_text', ''),
            operator=data.get('operator', 'Tj'),
            text_state=data.get('text_state'),
            position_x=data.get('position_x', 0.0),
            position_y=data.get('position_y', 0.0),
            raw_operator=data.get('raw_operator', ''),
        )


@dataclass
class TextSubstitution:
    """
    Definición de una sustitución de texto.
    
    Especifica qué texto reemplazar y con qué.
    """
    # Identificación
    substitution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Texto
    original_text: str = ""
    new_text: str = ""
    
    # Ubicación (si se conoce)
    location: Optional[TextLocation] = None
    
    # Estrategia de match
    match_strategy: MatchStrategy = MatchStrategy.EXACT
    match_pattern: str = ""     # Para REGEX o CONTAINS
    
    # Tipo de sustitución
    substitution_type: SubstitutionType = SubstitutionType.OPERAND_ONLY
    
    # Opciones de texto nuevo
    preserve_font: bool = True
    preserve_size: bool = True
    new_font: Optional[str] = None
    new_size: Optional[float] = None
    
    # Ajustes de espaciado
    adjust_char_spacing: bool = False
    char_spacing_delta: float = 0.0
    
    # Metadatos
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    applied: bool = False
    
    @property
    def text_length_change(self) -> int:
        """Cambio en longitud de texto."""
        return len(self.new_text) - len(self.original_text)
    
    @property
    def is_same_length(self) -> bool:
        """Verifica si el texto tiene la misma longitud."""
        return len(self.new_text) == len(self.original_text)
    
    @property
    def requires_reflow(self) -> bool:
        """Verifica si podría requerir reflow."""
        return (
            self.text_length_change > 0 or 
            not self.preserve_font or 
            not self.preserve_size
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'substitution_id': self.substitution_id,
            'original_text': self.original_text,
            'new_text': self.new_text,
            'location': self.location.to_dict() if self.location else None,
            'match_strategy': self.match_strategy.name,
            'match_pattern': self.match_pattern,
            'substitution_type': self.substitution_type.name,
            'preserve_font': self.preserve_font,
            'preserve_size': self.preserve_size,
            'new_font': self.new_font,
            'new_size': self.new_size,
            'adjust_char_spacing': self.adjust_char_spacing,
            'char_spacing_delta': self.char_spacing_delta,
            'created_at': self.created_at,
            'applied': self.applied,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextSubstitution':
        """Crea desde diccionario."""
        location_data = data.get('location')
        location = TextLocation.from_dict(location_data) if location_data else None
        
        match_name = data.get('match_strategy', 'EXACT')
        match_strategy = MatchStrategy[match_name] if match_name in MatchStrategy.__members__ else MatchStrategy.EXACT
        
        sub_name = data.get('substitution_type', 'OPERAND_ONLY')
        sub_type = SubstitutionType[sub_name] if sub_name in SubstitutionType.__members__ else SubstitutionType.OPERAND_ONLY
        
        return cls(
            substitution_id=data.get('substitution_id', ''),
            original_text=data.get('original_text', ''),
            new_text=data.get('new_text', ''),
            location=location,
            match_strategy=match_strategy,
            match_pattern=data.get('match_pattern', ''),
            substitution_type=sub_type,
            preserve_font=data.get('preserve_font', True),
            preserve_size=data.get('preserve_size', True),
            new_font=data.get('new_font'),
            new_size=data.get('new_size'),
            adjust_char_spacing=data.get('adjust_char_spacing', False),
            char_spacing_delta=data.get('char_spacing_delta', 0.0),
            created_at=data.get('created_at', ''),
            applied=data.get('applied', False),
        )


@dataclass
class SubstitutionResult:
    """
    Resultado de una operación de sustitución.
    """
    # Estado
    status: SubstitutionStatus = SubstitutionStatus.SUCCESS
    success: bool = True
    message: str = ""
    
    # Sustitución aplicada
    substitution: Optional[TextSubstitution] = None
    
    # Content stream
    original_stream: bytes = b""
    modified_stream: bytes = b""
    
    # Información de cambios
    bytes_changed: int = 0
    positions_shifted: bool = False
    
    # Warnings y errores
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Validación
    validation_passed: bool = True
    validation_details: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    execution_time_ms: float = 0.0
    
    def add_warning(self, warning: str) -> None:
        """Añade un warning."""
        self.warnings.append(warning)
        if self.status == SubstitutionStatus.SUCCESS:
            self.status = SubstitutionStatus.PARTIAL_SUCCESS
    
    def add_error(self, error: str) -> None:
        """Añade un error."""
        self.errors.append(error)
        self.success = False
        self.status = SubstitutionStatus.FAILED
    
    @property
    def has_warnings(self) -> bool:
        """Verifica si hay warnings."""
        return len(self.warnings) > 0
    
    @property
    def has_errors(self) -> bool:
        """Verifica si hay errores."""
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario."""
        return {
            'status': self.status.name,
            'success': self.success,
            'message': self.message,
            'substitution': self.substitution.to_dict() if self.substitution else None,
            'bytes_changed': self.bytes_changed,
            'positions_shifted': self.positions_shifted,
            'warnings': self.warnings,
            'errors': self.errors,
            'validation_passed': self.validation_passed,
            'validation_details': self.validation_details,
            'execution_time_ms': self.execution_time_ms,
        }


@dataclass
class SubstitutorConfig:
    """
    Configuración del sustituyente de objetos.
    """
    # Estrategia por defecto
    default_type: SubstitutionType = SubstitutionType.OPERAND_ONLY
    default_match: MatchStrategy = MatchStrategy.EXACT
    
    # Seguridad
    validate_before_apply: bool = True
    create_backup: bool = True
    allow_structure_change: bool = False
    max_risk_level: int = 6     # No permitir > este nivel
    
    # Codificación
    default_encoding: str = 'utf-8'
    fallback_encoding: str = 'latin-1'
    
    # Limites
    max_substitutions_per_page: int = 100
    max_stream_size_mb: float = 10.0
    
    # Opciones de texto
    auto_adjust_spacing: bool = True
    preserve_original_operators: bool = True
    
    # Logging
    verbose_logging: bool = False


# ================== Text Encoder ==================


class PDFTextEncoder:
    """
    Codificador de texto para operadores PDF.
    
    Maneja la conversión entre texto Python y operandos PDF válidos.
    """
    
    # Caracteres que necesitan escape en strings literales PDF
    ESCAPE_CHARS = {
        b'\n': b'\\n',
        b'\r': b'\\r',
        b'\t': b'\\t',
        b'\b': b'\\b',
        b'\f': b'\\f',
        b'(': b'\\(',
        b')': b'\\)',
        b'\\': b'\\\\',
    }
    
    @staticmethod
    def encode_literal_string(text: str, encoding: str = 'latin-1') -> bytes:
        """
        Codifica texto como string literal PDF (paréntesis).
        
        Args:
            text: Texto a codificar
            encoding: Codificación a usar
            
        Returns:
            Bytes del operando incluyendo paréntesis
        """
        try:
            raw = text.encode(encoding)
        except UnicodeEncodeError:
            # Fallback a UTF-16BE con BOM para Unicode
            raw = b'\xfe\xff' + text.encode('utf-16-be')
        
        # Escapar caracteres especiales
        escaped = bytearray()
        for byte in raw:
            byte_val = bytes([byte])
            if byte_val in PDFTextEncoder.ESCAPE_CHARS:
                escaped.extend(PDFTextEncoder.ESCAPE_CHARS[byte_val])
            else:
                escaped.append(byte)
        
        return b'(' + bytes(escaped) + b')'
    
    @staticmethod
    def encode_hex_string(text: str, encoding: str = 'utf-16-be') -> bytes:
        """
        Codifica texto como string hexadecimal PDF.
        
        Args:
            text: Texto a codificar
            encoding: Codificación a usar
            
        Returns:
            Bytes del operando hex incluyendo <>
        """
        try:
            raw = text.encode(encoding)
        except UnicodeEncodeError:
            raw = text.encode('utf-16-be')
        
        hex_str = raw.hex().upper()
        return b'<' + hex_str.encode('ascii') + b'>'
    
    @staticmethod
    def decode_literal_string(data: bytes) -> str:
        """
        Decodifica string literal PDF a texto.
        
        Args:
            data: Bytes incluyendo paréntesis
            
        Returns:
            Texto decodificado
        """
        # Remover paréntesis
        if data.startswith(b'(') and data.endswith(b')'):
            data = data[1:-1]
        
        # Procesar escapes
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i:i+1] == b'\\':
                if i + 1 < len(data):
                    next_byte = data[i+1:i+2]
                    if next_byte == b'n':
                        result.append(ord('\n'))
                    elif next_byte == b'r':
                        result.append(ord('\r'))
                    elif next_byte == b't':
                        result.append(ord('\t'))
                    elif next_byte in (b'(', b')', b'\\'):
                        result.append(data[i+1])
                    elif next_byte.isdigit():
                        # Octal escape
                        octal = b''
                        for j in range(3):
                            if i + 1 + j < len(data) and data[i+1+j:i+2+j].isdigit():
                                octal += data[i+1+j:i+2+j]
                            else:
                                break
                        if octal:
                            result.append(int(octal, 8))
                            i += len(octal)
                            continue
                    i += 2
                    continue
            result.append(data[i])
            i += 1
        
        # Intentar decodificar
        try:
            # Check for UTF-16BE BOM
            if result[:2] == b'\xfe\xff':
                return result[2:].decode('utf-16-be')
            return bytes(result).decode('latin-1')
        except UnicodeDecodeError:
            return bytes(result).decode('utf-8', errors='replace')
    
    @staticmethod
    def decode_hex_string(data: bytes) -> str:
        """
        Decodifica string hexadecimal PDF a texto.
        
        Args:
            data: Bytes incluyendo <>
            
        Returns:
            Texto decodificado
        """
        # Remover < >
        if data.startswith(b'<') and data.endswith(b'>'):
            data = data[1:-1]
        
        # Remover espacios
        hex_str = data.replace(b' ', b'').replace(b'\n', b'').replace(b'\r', b'')
        
        # Pad si es impar
        if len(hex_str) % 2:
            hex_str += b'0'
        
        try:
            raw = bytes.fromhex(hex_str.decode('ascii'))
            # Check for UTF-16BE BOM
            if raw[:2] == b'\xfe\xff':
                return raw[2:].decode('utf-16-be')
            return raw.decode('utf-16-be')
        except (ValueError, UnicodeDecodeError):
            return hex_str.decode('ascii', errors='replace')


# ================== Content Stream Modifier ==================


class ContentStreamModifier:
    """
    Modificador de content streams PDF.
    
    Permite modificar operadores de texto de forma segura.
    """
    
    def __init__(self, config: Optional[SubstitutorConfig] = None):
        """
        Inicializa el modificador.
        
        Args:
            config: Configuración opcional
        """
        self.config = config or SubstitutorConfig()
        self._parser = ContentStreamParser()
        self._encoder = PDFTextEncoder()
    
    def find_text_locations(
        self,
        stream: bytes,
        search_text: str,
        strategy: MatchStrategy = MatchStrategy.EXACT,
        pattern: str = "",
    ) -> List[TextLocation]:
        """
        Encuentra ubicaciones de texto en el content stream.
        
        Args:
            stream: Content stream raw
            search_text: Texto a buscar
            strategy: Estrategia de búsqueda
            pattern: Patrón para REGEX o CONTAINS
            
        Returns:
            Lista de ubicaciones encontradas
        """
        locations: List[TextLocation] = []
        
        try:
            # Parsear el stream
            blocks = self._parser.parse(stream.decode('latin-1', errors='replace'))
            
            for block_idx, block in enumerate(blocks):
                for op_idx, operation in enumerate(block.operations):
                    matches = self._check_match(
                        operation.text,
                        search_text,
                        strategy,
                        pattern
                    )
                    
                    if matches:
                        location = TextLocation(
                            page_num=0,  # Se actualiza externamente
                            stream_start=operation.position_in_stream,
                            stream_end=operation.position_in_stream + len(operation.raw_operand or ''),
                            block_index=block_idx,
                            operation_index=op_idx,
                            original_text=operation.text,
                            operator=operation.operator,
                            text_state=operation.state.to_dict() if operation.state else None,
                            position_x=operation.position[0] if operation.position else 0.0,
                            position_y=operation.position[1] if operation.position else 0.0,
                            raw_operator=operation.raw_operand or '',
                        )
                        locations.append(location)
                        
        except Exception as e:
            logger.error(f"Error buscando texto en stream: {e}")
        
        return locations
    
    def _check_match(
        self,
        text: str,
        search: str,
        strategy: MatchStrategy,
        pattern: str,
    ) -> bool:
        """Verifica si el texto coincide según la estrategia."""
        if strategy == MatchStrategy.EXACT:
            return text == search
        elif strategy == MatchStrategy.CONTAINS:
            return (pattern or search) in text
        elif strategy == MatchStrategy.REGEX:
            try:
                return bool(re.search(pattern or search, text))
            except re.error:
                return False
        return False
    
    def substitute_at_location(
        self,
        stream: bytes,
        location: TextLocation,
        new_text: str,
        substitution_type: SubstitutionType = SubstitutionType.OPERAND_ONLY,
    ) -> Tuple[bytes, int]:
        """
        Sustituye texto en una ubicación específica.
        
        Args:
            stream: Content stream original
            location: Ubicación del texto
            new_text: Nuevo texto
            substitution_type: Tipo de sustitución
            
        Returns:
            Tuple de (stream modificado, diferencia de bytes)
        """
        if substitution_type == SubstitutionType.OPERAND_ONLY:
            return self._substitute_operand(stream, location, new_text)
        elif substitution_type == SubstitutionType.OPERATOR_REPLACE:
            return self._substitute_operator(stream, location, new_text)
        else:
            # Para tipos más complejos, usar operand por defecto
            return self._substitute_operand(stream, location, new_text)
    
    def _substitute_operand(
        self,
        stream: bytes,
        location: TextLocation,
        new_text: str,
    ) -> Tuple[bytes, int]:
        """
        Sustituye solo el operando de texto.
        
        Busca el string (literal o hex) y lo reemplaza.
        """
        stream_str = stream.decode('latin-1', errors='replace')
        
        # Determinar tipo de string original
        raw = location.raw_operator
        
        if raw.startswith('('):
            # String literal
            new_operand = self._encoder.encode_literal_string(new_text).decode('latin-1')
            old_operand = self._find_literal_string(raw)
        elif raw.startswith('<'):
            # String hex
            new_operand = self._encoder.encode_hex_string(new_text).decode('latin-1')
            old_operand = self._find_hex_string(raw)
        else:
            # Intentar encontrar el patrón
            old_operand = self._extract_string_operand(raw)
            new_operand = self._encoder.encode_literal_string(new_text).decode('latin-1')
        
        if not old_operand:
            return stream, 0
        
        # Buscar y reemplazar en el stream
        start = location.stream_start
        end = location.stream_end
        
        if start < len(stream_str) and end <= len(stream_str):
            segment = stream_str[start:end]
            new_segment = segment.replace(old_operand, new_operand, 1)
            
            modified = stream_str[:start] + new_segment + stream_str[end:]
            byte_diff = len(new_operand) - len(old_operand)
            
            return modified.encode('latin-1'), byte_diff
        
        return stream, 0
    
    def _substitute_operator(
        self,
        stream: bytes,
        location: TextLocation,
        new_text: str,
    ) -> Tuple[bytes, int]:
        """
        Sustituye el operador completo.
        
        Genera un nuevo operador con el texto y atributos.
        """
        stream_str = stream.decode('latin-1', errors='replace')
        
        # Generar nuevo operador
        operator = location.operator
        new_operand = self._encoder.encode_literal_string(new_text).decode('latin-1')
        
        # Construir nuevo operador según tipo
        if operator in ('Tj', "'"):
            new_operator_str = f"{new_operand} {operator}"
        elif operator == '"':
            # " necesita word spacing y char spacing antes
            word_sp = location.text_state.get('word_spacing', 0) if location.text_state else 0
            char_sp = location.text_state.get('char_spacing', 0) if location.text_state else 0
            new_operator_str = f"{word_sp} {char_sp} {new_operand} \""
        else:
            new_operator_str = f"{new_operand} Tj"
        
        # Reemplazar
        start = location.stream_start
        end = location.stream_end
        
        if start < len(stream_str) and end <= len(stream_str):
            original_len = end - start
            modified = stream_str[:start] + new_operator_str + stream_str[end:]
            byte_diff = len(new_operator_str) - original_len
            
            return modified.encode('latin-1'), byte_diff
        
        return stream, 0
    
    def _find_literal_string(self, raw: str) -> str:
        """Extrae string literal de raw operator."""
        match = re.search(r'\((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*\)', raw)
        return match.group(0) if match else ""
    
    def _find_hex_string(self, raw: str) -> str:
        """Extrae string hex de raw operator."""
        match = re.search(r'<[0-9A-Fa-f\s]*>', raw)
        return match.group(0) if match else ""
    
    def _extract_string_operand(self, raw: str) -> str:
        """Extrae cualquier tipo de operando string."""
        literal = self._find_literal_string(raw)
        if literal:
            return literal
        return self._find_hex_string(raw)
    
    def generate_text_operator(
        self,
        text: str,
        operator: str = "Tj",
        font_name: Optional[str] = None,
        font_size: Optional[float] = None,
        position: Optional[Tuple[float, float]] = None,
        char_spacing: Optional[float] = None,
        word_spacing: Optional[float] = None,
    ) -> str:
        """
        Genera operadores PDF para mostrar texto.
        
        Args:
            text: Texto a mostrar
            operator: Operador a usar (Tj, TJ, ', ")
            font_name: Nombre de fuente (genera Tf si se provee)
            font_size: Tamaño de fuente
            position: Posición (genera Td si se provee)
            char_spacing: Espaciado de caracteres (genera Tc)
            word_spacing: Espaciado de palabras (genera Tw)
            
        Returns:
            String con los operadores PDF
        """
        parts = []
        
        # Font
        if font_name and font_size:
            parts.append(f"/{font_name} {font_size} Tf")
        
        # Spacing
        if char_spacing is not None:
            parts.append(f"{char_spacing} Tc")
        if word_spacing is not None:
            parts.append(f"{word_spacing} Tw")
        
        # Position
        if position:
            parts.append(f"{position[0]} {position[1]} Td")
        
        # Text
        encoded = self._encoder.encode_literal_string(text).decode('latin-1')
        parts.append(f"{encoded} {operator}")
        
        return '\n'.join(parts)


# ================== Object Substitutor (Main Class) ==================


class ObjectSubstitutor:
    """
    Sustituyente de objetos PDF.
    
    Implementa la estrategia de sustitución directa de
    operadores de texto en el content stream.
    
    Esta estrategia es más riesgosa que overlay pero produce
    PDFs más limpios sin capas adicionales.
    
    Usage:
        substitutor = ObjectSubstitutor()
        
        # Crear sustitución
        sub = substitutor.create_substitution(
            original="Hello",
            new_text="World",
        )
        
        # Localizar en stream
        locations = substitutor.find_text(stream, "Hello")
        if locations:
            sub.location = locations[0]
        
        # Aplicar
        result = substitutor.apply(page, sub)
    """
    
    def __init__(self, config: Optional[SubstitutorConfig] = None):
        """
        Inicializa el sustituyente.
        
        Args:
            config: Configuración opcional
        """
        self._config = config or SubstitutorConfig()
        self._modifier = ContentStreamModifier(self._config)
        self._encoder = PDFTextEncoder()
        
        # Registro de sustituciones
        self._substitutions: Dict[str, TextSubstitution] = {}
        self._page_substitutions: Dict[int, List[str]] = {}
        
        # Backup para rollback
        self._backups: Dict[str, bytes] = {}
    
    @property
    def config(self) -> SubstitutorConfig:
        """Obtiene configuración."""
        return self._config
    
    def create_substitution(
        self,
        original: str,
        new_text: str,
        substitution_type: Optional[SubstitutionType] = None,
        match_strategy: Optional[MatchStrategy] = None,
        **kwargs
    ) -> TextSubstitution:
        """
        Crea una definición de sustitución.
        
        Args:
            original: Texto original
            new_text: Nuevo texto
            substitution_type: Tipo de sustitución
            match_strategy: Estrategia de búsqueda
            **kwargs: Argumentos adicionales para TextSubstitution
            
        Returns:
            TextSubstitution configurada
        """
        sub = TextSubstitution(
            original_text=original,
            new_text=new_text,
            substitution_type=substitution_type or self._config.default_type,
            match_strategy=match_strategy or self._config.default_match,
            **kwargs
        )
        
        # Registrar
        self._substitutions[sub.substitution_id] = sub
        
        return sub
    
    def find_text(
        self,
        stream: bytes,
        search_text: str,
        strategy: Optional[MatchStrategy] = None,
        pattern: str = "",
        page_num: int = 0,
    ) -> List[TextLocation]:
        """
        Busca texto en un content stream.
        
        Args:
            stream: Content stream raw
            search_text: Texto a buscar
            strategy: Estrategia de búsqueda
            pattern: Patrón para búsquedas REGEX/CONTAINS
            page_num: Número de página (para metadata)
            
        Returns:
            Lista de ubicaciones encontradas
        """
        locations = self._modifier.find_text_locations(
            stream,
            search_text,
            strategy or self._config.default_match,
            pattern,
        )
        
        # Actualizar page_num
        for loc in locations:
            loc.page_num = page_num
        
        return locations
    
    def find_in_page(
        self,
        page: Any,  # fitz.Page
        search_text: str,
        strategy: Optional[MatchStrategy] = None,
        pattern: str = "",
    ) -> List[TextLocation]:
        """
        Busca texto en una página PyMuPDF.
        
        Args:
            page: Objeto fitz.Page
            search_text: Texto a buscar
            strategy: Estrategia de búsqueda
            pattern: Patrón para búsquedas
            
        Returns:
            Lista de ubicaciones
        """
        if not HAS_FITZ:
            logger.error("PyMuPDF no disponible")
            return []
        
        try:
            # Obtener content stream
            stream = page.read_contents()
            
            if not stream:
                return []
            
            return self.find_text(
                stream,
                search_text,
                strategy,
                pattern,
                page.number,
            )
            
        except Exception as e:
            logger.error(f"Error buscando en página: {e}")
            return []
    
    def validate_substitution(
        self,
        substitution: TextSubstitution,
    ) -> Tuple[bool, List[str]]:
        """
        Valida una sustitución antes de aplicarla.
        
        Args:
            substitution: Sustitución a validar
            
        Returns:
            Tuple de (es_válida, lista_de_razones)
        """
        issues: List[str] = []
        
        # Verificar nivel de riesgo
        if substitution.substitution_type.risk_level > self._config.max_risk_level:
            issues.append(
                f"Nivel de riesgo ({substitution.substitution_type.risk_level}) "
                f"excede máximo permitido ({self._config.max_risk_level})"
            )
        
        # Verificar si tiene ubicación
        if not substitution.location and substitution.match_strategy == MatchStrategy.POSITION:
            issues.append("Estrategia por posición requiere ubicación definida")
        
        # Verificar cambios estructurales
        if substitution.requires_reflow and not self._config.allow_structure_change:
            issues.append("Cambio requiere reflow pero no está permitido")
        
        # Verificar codificación de texto
        try:
            _ = substitution.new_text.encode('latin-1')
        except UnicodeEncodeError:
            # Puede necesitar UTF-16, no es error pero warning
            pass
        
        return len(issues) == 0, issues
    
    def apply(
        self,
        page: Any,  # fitz.Page
        substitution: TextSubstitution,
    ) -> SubstitutionResult:
        """
        Aplica una sustitución a una página.
        
        Args:
            page: Página PyMuPDF
            substitution: Sustitución a aplicar
            
        Returns:
            Resultado de la operación
        """
        import time
        start_time = time.time()
        
        result = SubstitutionResult(substitution=substitution)
        
        if not HAS_FITZ:
            result.add_error("PyMuPDF no disponible")
            return result
        
        try:
            # Validar si está configurado
            if self._config.validate_before_apply:
                is_valid, issues = self.validate_substitution(substitution)
                if not is_valid:
                    result.status = SubstitutionStatus.VALIDATION_FAILED
                    result.validation_passed = False
                    result.validation_details['issues'] = issues
                    result.add_error(f"Validación fallida: {', '.join(issues)}")
                    return result
            
            # Obtener stream
            stream = page.read_contents()
            if not stream:
                result.add_error("No se pudo leer content stream")
                return result
            
            # Backup si está configurado
            if self._config.create_backup:
                backup_key = f"page_{page.number}_{substitution.substitution_id}"
                self._backups[backup_key] = stream
                result.original_stream = stream
            
            # Encontrar ubicación si no está definida
            location = substitution.location
            if not location:
                locations = self.find_text(
                    stream,
                    substitution.original_text,
                    substitution.match_strategy,
                    substitution.match_pattern,
                    page.number,
                )
                
                if not locations:
                    result.add_error(f"Texto '{substitution.original_text}' no encontrado")
                    return result
                
                location = locations[0]
                substitution.location = location
                
                if len(locations) > 1:
                    result.add_warning(
                        f"Se encontraron {len(locations)} coincidencias, "
                        "usando la primera"
                    )
            
            # Aplicar sustitución
            modified_stream, byte_diff = self._modifier.substitute_at_location(
                stream,
                location,
                substitution.new_text,
                substitution.substitution_type,
            )
            
            if byte_diff == 0 and substitution.original_text != substitution.new_text:
                result.add_warning("No se detectó cambio en el stream")
            
            # Escribir stream modificado
            self._write_stream_to_page(page, modified_stream)
            
            # Actualizar resultado
            result.modified_stream = modified_stream
            result.bytes_changed = abs(byte_diff)
            result.positions_shifted = byte_diff != 0
            
            substitution.applied = True
            result.status = SubstitutionStatus.SUCCESS
            result.message = f"Sustitución aplicada ({byte_diff:+d} bytes)"
            
            # Registrar en página
            if page.number not in self._page_substitutions:
                self._page_substitutions[page.number] = []
            self._page_substitutions[page.number].append(substitution.substitution_id)
            
        except Exception as e:
            result.add_error(f"Error aplicando sustitución: {str(e)}")
            
            # Rollback si hay backup
            if self._config.create_backup:
                self._attempt_rollback(page, substitution.substitution_id, result)
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        return result
    
    def _write_stream_to_page(self, page: Any, new_stream: bytes) -> None:
        """
        Escribe un content stream modificado a una página.
        
        Args:
            page: Página PyMuPDF
            new_stream: Nuevo content stream
        """
        if not HAS_FITZ:
            return
        
        # En PyMuPDF, para escribir el content stream necesitamos
        # usar el xref del objeto contents
        doc = page.parent
        xref = page.xref
        
        # Obtener el xref del contents
        contents_xref = doc.xref_get_key(xref, "Contents")
        
        if contents_xref[0] == "xref":
            # Es una referencia directa
            contents_obj_xref = int(contents_xref[1].split()[0])
            doc.update_stream(contents_obj_xref, new_stream)
        elif contents_xref[0] == "array":
            # Array de streams - necesita manejo especial
            # Por simplicidad, usamos el primer elemento
            logger.warning("Página con múltiples content streams, usando primero")
            # TODO: Manejar arrays de streams
            pass
        else:
            # Crear nuevo stream
            doc.update_stream(xref, new_stream, new=True)
    
    def _attempt_rollback(
        self,
        page: Any,
        substitution_id: str,
        result: SubstitutionResult,
    ) -> None:
        """Intenta hacer rollback de una sustitución fallida."""
        backup_key = f"page_{page.number}_{substitution_id}"
        
        if backup_key in self._backups:
            try:
                self._write_stream_to_page(page, self._backups[backup_key])
                result.status = SubstitutionStatus.ROLLBACK_APPLIED
                result.add_warning("Rollback aplicado por error")
            except Exception as e:
                result.add_error(f"Rollback también falló: {str(e)}")
    
    def substitute_text(
        self,
        page: Any,
        original: str,
        new_text: str,
        substitution_type: Optional[SubstitutionType] = None,
        match_strategy: Optional[MatchStrategy] = None,
    ) -> SubstitutionResult:
        """
        Método de conveniencia para sustitución rápida.
        
        Args:
            page: Página PyMuPDF
            original: Texto original
            new_text: Nuevo texto
            substitution_type: Tipo de sustitución
            match_strategy: Estrategia de búsqueda
            
        Returns:
            Resultado de la operación
        """
        sub = self.create_substitution(
            original,
            new_text,
            substitution_type,
            match_strategy,
        )
        return self.apply(page, sub)
    
    def get_substitution(self, substitution_id: str) -> Optional[TextSubstitution]:
        """Obtiene una sustitución por ID."""
        return self._substitutions.get(substitution_id)
    
    def get_page_substitutions(self, page_num: int) -> List[TextSubstitution]:
        """Obtiene sustituciones aplicadas a una página."""
        ids = self._page_substitutions.get(page_num, [])
        return [self._substitutions[sid] for sid in ids if sid in self._substitutions]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sustituyente."""
        total = len(self._substitutions)
        applied = sum(1 for s in self._substitutions.values() if s.applied)
        
        by_type: Dict[str, int] = {}
        for sub in self._substitutions.values():
            type_name = sub.substitution_type.name
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        return {
            'total_substitutions': total,
            'applied': applied,
            'pending': total - applied,
            'pages_affected': len(self._page_substitutions),
            'by_type': by_type,
            'backups_stored': len(self._backups),
        }
    
    def clear(self) -> None:
        """Limpia todas las sustituciones y backups."""
        self._substitutions.clear()
        self._page_substitutions.clear()
        self._backups.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa el estado a diccionario."""
        return {
            'config': {
                'default_type': self._config.default_type.name,
                'default_match': self._config.default_match.name,
                'validate_before_apply': self._config.validate_before_apply,
                'create_backup': self._config.create_backup,
                'allow_structure_change': self._config.allow_structure_change,
                'max_risk_level': self._config.max_risk_level,
            },
            'substitutions': {
                sid: sub.to_dict() 
                for sid, sub in self._substitutions.items()
            },
            'page_substitutions': self._page_substitutions,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ObjectSubstitutor':
        """Crea desde diccionario."""
        config_data = data.get('config', {})
        
        type_name = config_data.get('default_type', 'OPERAND_ONLY')
        match_name = config_data.get('default_match', 'EXACT')
        
        config = SubstitutorConfig(
            default_type=SubstitutionType[type_name] if type_name in SubstitutionType.__members__ else SubstitutionType.OPERAND_ONLY,
            default_match=MatchStrategy[match_name] if match_name in MatchStrategy.__members__ else MatchStrategy.EXACT,
            validate_before_apply=config_data.get('validate_before_apply', True),
            create_backup=config_data.get('create_backup', True),
            allow_structure_change=config_data.get('allow_structure_change', False),
            max_risk_level=config_data.get('max_risk_level', 6),
        )
        
        substitutor = cls(config)
        
        # Restaurar sustituciones
        for sid, sub_data in data.get('substitutions', {}).items():
            sub = TextSubstitution.from_dict(sub_data)
            substitutor._substitutions[sid] = sub
        
        substitutor._page_substitutions = data.get('page_substitutions', {})
        
        return substitutor


# ================== Factory Functions ==================


def create_substitutor(
    substitution_type: Optional[SubstitutionType] = None,
    match_strategy: Optional[MatchStrategy] = None,
    validate: bool = True,
    allow_structure_change: bool = False,
    **kwargs
) -> ObjectSubstitutor:
    """
    Crea un sustituyente de objetos configurado.
    
    Args:
        substitution_type: Tipo de sustitución por defecto
        match_strategy: Estrategia de búsqueda por defecto
        validate: Si validar antes de aplicar
        allow_structure_change: Si permitir cambios estructurales
        **kwargs: Argumentos adicionales para config
        
    Returns:
        ObjectSubstitutor configurado
    """
    config = SubstitutorConfig(
        default_type=substitution_type or SubstitutionType.OPERAND_ONLY,
        default_match=match_strategy or MatchStrategy.EXACT,
        validate_before_apply=validate,
        allow_structure_change=allow_structure_change,
        **kwargs
    )
    return ObjectSubstitutor(config)


def substitute_text_in_page(
    page: Any,  # fitz.Page
    original: str,
    new_text: str,
    substitution_type: Optional[SubstitutionType] = None,
) -> SubstitutionResult:
    """
    Sustituye texto en una página (función de conveniencia).
    
    Args:
        page: Página PyMuPDF
        original: Texto original
        new_text: Nuevo texto
        substitution_type: Tipo de sustitución
        
    Returns:
        Resultado de la sustitución
    """
    substitutor = ObjectSubstitutor()
    return substitutor.substitute_text(
        page,
        original,
        new_text,
        substitution_type,
    )


def get_recommended_substitution_type(
    original: str,
    new_text: str,
    preserve_layout: bool = True,
) -> SubstitutionType:
    """
    Recomienda un tipo de sustitución basado en los textos.
    
    Args:
        original: Texto original
        new_text: Nuevo texto
        preserve_layout: Si se debe preservar el layout
        
    Returns:
        Tipo de sustitución recomendado
    """
    length_diff = len(new_text) - len(original)
    
    if length_diff == 0:
        # Mismo tamaño, operand_only es seguro
        return SubstitutionType.OPERAND_ONLY
    
    if preserve_layout:
        if abs(length_diff) <= 3:
            # Pequeña diferencia, operator_replace puede ajustar
            return SubstitutionType.OPERATOR_REPLACE
        else:
            # Gran diferencia, necesita reconstruir bloque
            return SubstitutionType.BLOCK_REPLACE
    
    # Sin restricción de layout
    return SubstitutionType.OPERATOR_REPLACE


__all__ = [
    # Enums
    'SubstitutionType',
    'SubstitutionStatus',
    'MatchStrategy',
    # Dataclasses
    'TextLocation',
    'TextSubstitution',
    'SubstitutionResult',
    'SubstitutorConfig',
    # Classes
    'PDFTextEncoder',
    'ContentStreamModifier',
    'ObjectSubstitutor',
    # Factory functions
    'create_substitutor',
    'substitute_text_in_page',
    'get_recommended_substitution_type',
]
