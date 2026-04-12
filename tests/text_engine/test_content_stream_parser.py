"""
Tests for ContentStreamParser.

Tests cover:
- Tokenization of PDF content streams
- Parsing of text state operators (Tc, Tw, Ts, Tz, TL, Tf, Tr)
- Text positioning operators (Td, TD, Tm, T*)
- Text showing operators (Tj, TJ, ', ")
- String decoding (literal and hex)
- Matrix operations (CTM, text matrix)
- Graphics state stack (q/Q)
- Integration with PyMuPDF pages
"""

from unittest.mock import MagicMock
from core.text_engine.content_stream_parser import (
    TextOperator,
    TextState,
    TextShowOperation,
    ParsedTextBlock,
    ContentStreamParser,
    parse_content_stream,
    extract_text_state_from_page,
    get_spacing_info_for_text
)


# =============================================================================
# Test TextOperator Enum
# =============================================================================

class TestTextOperatorEnum:
    """Tests for TextOperator enum."""
    
    def test_text_state_operators_exist(self):
        """Verify all text state operators are defined."""
        assert TextOperator.Tc.value == "Tc"
        assert TextOperator.Tw.value == "Tw"
        assert TextOperator.Tz.value == "Tz"
        assert TextOperator.TL.value == "TL"
        assert TextOperator.Tf.value == "Tf"
        assert TextOperator.Tr.value == "Tr"
        assert TextOperator.Ts.value == "Ts"
    
    def test_text_object_operators_exist(self):
        """Verify text object operators are defined."""
        assert TextOperator.BT.value == "BT"
        assert TextOperator.ET.value == "ET"
    
    def test_text_positioning_operators_exist(self):
        """Verify text positioning operators are defined."""
        assert TextOperator.Td.value == "Td"
        assert TextOperator.TD.value == "TD"
        assert TextOperator.Tm.value == "Tm"
        assert TextOperator.T_star.value == "T*"
    
    def test_text_showing_operators_exist(self):
        """Verify text showing operators are defined."""
        assert TextOperator.Tj.value == "Tj"
        assert TextOperator.TJ.value == "TJ"
        assert TextOperator.quote.value == "'"
        assert TextOperator.double_quote.value == '"'


# =============================================================================
# Test TextState
# =============================================================================

class TestTextState:
    """Tests for TextState dataclass."""
    
    def test_default_values(self):
        """Verify default values match PDF spec."""
        state = TextState()
        assert state.char_spacing == 0.0
        assert state.word_spacing == 0.0
        assert state.horizontal_scale == 100.0
        assert state.leading == 0.0
        assert state.font_name is None
        assert state.font_size == 0.0
        assert state.render_mode == 0
        assert state.rise == 0.0
        assert state.text_matrix == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        assert state.line_matrix == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        assert state.ctm == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    
    def test_copy_creates_independent_copy(self):
        """Verify copy() creates an independent copy."""
        state = TextState(char_spacing=1.5, word_spacing=2.0)
        copy = state.copy()
        
        assert copy.char_spacing == 1.5
        assert copy.word_spacing == 2.0
        
        # Modify copy, original should be unchanged
        copy.char_spacing = 3.0
        assert state.char_spacing == 1.5
    
    def test_reset_text_object(self):
        """Verify reset_text_object resets matrices."""
        state = TextState()
        state.text_matrix = (2.0, 0.0, 0.0, 2.0, 100.0, 200.0)
        state.line_matrix = (2.0, 0.0, 0.0, 2.0, 100.0, 200.0)
        
        state.reset_text_object()
        
        assert state.text_matrix == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        assert state.line_matrix == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    
    def test_get_effective_position_identity(self):
        """Test effective position with identity matrices."""
        state = TextState()
        state.text_matrix = (1.0, 0.0, 0.0, 1.0, 100.0, 200.0)
        
        x, y = state.get_effective_position()
        assert x == 100.0
        assert y == 200.0
    
    def test_get_effective_position_with_ctm(self):
        """Test effective position with CTM transformation."""
        state = TextState()
        state.text_matrix = (1.0, 0.0, 0.0, 1.0, 50.0, 50.0)
        # CTM that scales by 2x
        state.ctm = (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)
        
        x, y = state.get_effective_position()
        assert x == 100.0  # 50 * 2
        assert y == 100.0  # 50 * 2
    
    def test_to_dict(self):
        """Test serialization to dict."""
        state = TextState(char_spacing=1.5, font_name="Arial", font_size=12.0)
        d = state.to_dict()
        
        assert d['char_spacing'] == 1.5
        assert d['font_name'] == "Arial"
        assert d['font_size'] == 12.0
        assert 'text_matrix' in d
        assert len(d['text_matrix']) == 6


# =============================================================================
# Test TextShowOperation
# =============================================================================

class TestTextShowOperation:
    """Tests for TextShowOperation dataclass."""
    
    def test_basic_creation(self):
        """Test basic creation of TextShowOperation."""
        state = TextState(char_spacing=0.5, word_spacing=1.0, rise=2.0)
        op = TextShowOperation(text="Hello", operator="Tj", state=state)
        
        assert op.text == "Hello"
        assert op.operator == "Tj"
        assert op.char_spacing == 0.5
        assert op.word_spacing == 1.0
        assert op.rise == 2.0
    
    def test_has_char_spacing(self):
        """Test has_char_spacing property."""
        state_no_spacing = TextState()
        state_with_spacing = TextState(char_spacing=0.5)
        
        op_no = TextShowOperation(text="Test", operator="Tj", state=state_no_spacing)
        op_yes = TextShowOperation(text="Test", operator="Tj", state=state_with_spacing)
        
        assert op_no.has_char_spacing is False
        assert op_yes.has_char_spacing is True
    
    def test_has_word_spacing(self):
        """Test has_word_spacing property."""
        state_no_spacing = TextState()
        state_with_spacing = TextState(word_spacing=2.0)
        
        op_no = TextShowOperation(text="Test", operator="Tj", state=state_no_spacing)
        op_yes = TextShowOperation(text="Test", operator="Tj", state=state_with_spacing)
        
        assert op_no.has_word_spacing is False
        assert op_yes.has_word_spacing is True
    
    def test_has_rise(self):
        """Test has_rise property."""
        state_no_rise = TextState()
        state_with_rise = TextState(rise=3.0)
        
        op_no = TextShowOperation(text="Test", operator="Tj", state=state_no_rise)
        op_yes = TextShowOperation(text="Test", operator="Tj", state=state_with_rise)
        
        assert op_no.has_rise is False
        assert op_yes.has_rise is True
    
    def test_is_superscript(self):
        """Test superscript detection."""
        state_super = TextState(rise=3.0)
        state_normal = TextState(rise=0.0)
        
        op_super = TextShowOperation(text="2", operator="Tj", state=state_super)
        op_normal = TextShowOperation(text="x", operator="Tj", state=state_normal)
        
        assert op_super.is_superscript is True
        assert op_normal.is_superscript is False
    
    def test_is_subscript(self):
        """Test subscript detection."""
        state_sub = TextState(rise=-3.0)
        state_normal = TextState(rise=0.0)
        
        op_sub = TextShowOperation(text="2", operator="Tj", state=state_sub)
        op_normal = TextShowOperation(text="H", operator="Tj", state=state_normal)
        
        assert op_sub.is_subscript is True
        assert op_normal.is_subscript is False
    
    def test_font_properties(self):
        """Test font name and size properties."""
        state = TextState(font_name="Helvetica", font_size=14.0)
        op = TextShowOperation(text="Test", operator="Tj", state=state)
        
        assert op.font_name == "Helvetica"
        assert op.font_size == 14.0
    
    def test_position_property(self):
        """Test position property."""
        state = TextState()
        state.text_matrix = (1.0, 0.0, 0.0, 1.0, 72.0, 720.0)
        op = TextShowOperation(text="Test", operator="Tj", state=state)
        
        x, y = op.position
        assert x == 72.0
        assert y == 720.0
    
    def test_to_dict(self):
        """Test serialization to dict."""
        state = TextState(char_spacing=1.0)
        op = TextShowOperation(
            text="Hello",
            operator="Tj",
            state=state,
            glyph_adjustments=[10, -20],
            position_in_stream=100
        )
        d = op.to_dict()
        
        assert d['text'] == "Hello"
        assert d['operator'] == "Tj"
        assert d['glyph_adjustments'] == [10, -20]
        assert d['position_in_stream'] == 100
        assert 'state' in d


# =============================================================================
# Test ParsedTextBlock
# =============================================================================

class TestParsedTextBlock:
    """Tests for ParsedTextBlock dataclass."""
    
    def test_empty_block(self):
        """Test empty text block."""
        block = ParsedTextBlock()
        assert block.text == ""
        assert block.has_spacing_info is False
        assert block.has_rise_info is False
    
    def test_text_concatenation(self):
        """Test text property concatenates all operations."""
        state = TextState()
        block = ParsedTextBlock(operations=[
            TextShowOperation(text="Hello ", operator="Tj", state=state),
            TextShowOperation(text="World", operator="Tj", state=state)
        ])
        
        assert block.text == "Hello World"
    
    def test_has_spacing_info(self):
        """Test has_spacing_info detection."""
        state_normal = TextState()
        state_spacing = TextState(char_spacing=1.0)
        
        block_no = ParsedTextBlock(operations=[
            TextShowOperation(text="Test", operator="Tj", state=state_normal)
        ])
        block_yes = ParsedTextBlock(operations=[
            TextShowOperation(text="Test", operator="Tj", state=state_spacing)
        ])
        
        assert block_no.has_spacing_info is False
        assert block_yes.has_spacing_info is True
    
    def test_has_rise_info(self):
        """Test has_rise_info detection."""
        state_normal = TextState()
        state_rise = TextState(rise=3.0)
        
        block_no = ParsedTextBlock(operations=[
            TextShowOperation(text="Test", operator="Tj", state=state_normal)
        ])
        block_yes = ParsedTextBlock(operations=[
            TextShowOperation(text="Test", operator="Tj", state=state_rise)
        ])
        
        assert block_no.has_rise_info is False
        assert block_yes.has_rise_info is True
    
    def test_get_unique_fonts(self):
        """Test unique font extraction."""
        state1 = TextState(font_name="Arial", font_size=12.0)
        state2 = TextState(font_name="Times", font_size=14.0)
        state3 = TextState(font_name="Arial", font_size=12.0)  # Duplicate
        
        block = ParsedTextBlock(operations=[
            TextShowOperation(text="A", operator="Tj", state=state1),
            TextShowOperation(text="B", operator="Tj", state=state2),
            TextShowOperation(text="C", operator="Tj", state=state3)
        ])
        
        fonts = block.get_unique_fonts()
        assert len(fonts) == 2
        assert ("Arial", 12.0) in fonts
        assert ("Times", 14.0) in fonts
    
    def test_to_dict(self):
        """Test serialization to dict."""
        state = TextState()
        block = ParsedTextBlock(
            operations=[
                TextShowOperation(text="Test", operator="Tj", state=state)
            ],
            start_position=0,
            end_position=50
        )
        d = block.to_dict()
        
        assert d['text'] == "Test"
        assert d['start_position'] == 0
        assert d['end_position'] == 50
        assert len(d['operations']) == 1


# =============================================================================
# Test ContentStreamParser - Basic Parsing
# =============================================================================

class TestContentStreamParserBasic:
    """Basic parsing tests for ContentStreamParser."""
    
    def test_empty_content(self):
        """Test parsing empty content."""
        parser = ContentStreamParser()
        blocks = parser.parse("")
        assert blocks == []
    
    def test_simple_text_object(self):
        """Test parsing simple BT/ET text object."""
        content = "BT (Hello) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].text == "Hello"
    
    def test_multiple_text_objects(self):
        """Test parsing multiple text objects."""
        content = "BT (First) Tj ET BT (Second) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 2
        assert blocks[0].text == "First"
        assert blocks[1].text == "Second"
    
    def test_no_text_outside_bt_et(self):
        """Test that text outside BT/ET is ignored."""
        content = "(Outside) Tj BT (Inside) Tj ET (OutsideAgain) Tj"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].text == "Inside"
    
    def test_bytes_input(self):
        """Test parsing bytes input."""
        content = b"BT (Hello) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].text == "Hello"


# =============================================================================
# Test ContentStreamParser - Text State Operators
# =============================================================================

class TestContentStreamParserTextState:
    """Tests for text state operator parsing."""
    
    def test_tc_char_spacing(self):
        """Test Tc (character spacing) operator."""
        content = "BT 0.5 Tc (Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].operations[0].char_spacing == 0.5
    
    def test_tw_word_spacing(self):
        """Test Tw (word spacing) operator."""
        content = "BT 2.0 Tw (Test words) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].operations[0].word_spacing == 2.0
    
    def test_ts_text_rise(self):
        """Test Ts (text rise) operator."""
        content = "BT 3.0 Ts (Superscript) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].operations[0].rise == 3.0
        assert blocks[0].operations[0].is_superscript is True
    
    def test_tz_horizontal_scale(self):
        """Test Tz (horizontal scaling) operator."""
        content = "BT 80 Tz (Condensed) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].operations[0].state.horizontal_scale == 80.0
    
    def test_tl_leading(self):
        """Test TL (text leading) operator."""
        content = "BT 14 TL (Line 1) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].operations[0].state.leading == 14.0
    
    def test_tf_font_selection(self):
        """Test Tf (font and size) operator."""
        content = "BT /F1 12 Tf (Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].operations[0].font_name == "/F1"
        assert blocks[0].operations[0].font_size == 12.0
    
    def test_tf_with_font_map(self):
        """Test Tf with font name mapping."""
        content = "BT /F1 12 Tf (Test) Tj ET"
        parser = ContentStreamParser()
        parser.set_font_map({"/F1": "Helvetica"})
        blocks = parser.parse(content)
        
        assert blocks[0].operations[0].font_name == "Helvetica"
    
    def test_tr_render_mode(self):
        """Test Tr (render mode) operator."""
        content = "BT 1 Tr (Outlined) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].operations[0].state.render_mode == 1
    
    def test_multiple_state_changes(self):
        """Test multiple state changes in sequence."""
        content = "BT 0.5 Tc 1.0 Tw 2.0 Ts /F1 14 Tf (Styled) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        op = blocks[0].operations[0]
        assert op.char_spacing == 0.5
        assert op.word_spacing == 1.0
        assert op.rise == 2.0
        assert op.font_name == "/F1"
        assert op.font_size == 14.0
    
    def test_negative_values(self):
        """Test negative values for spacing and rise."""
        content = "BT -0.5 Tc -1.0 Tw -3.0 Ts (Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        op = blocks[0].operations[0]
        assert op.char_spacing == -0.5
        assert op.word_spacing == -1.0
        assert op.rise == -3.0
        assert op.is_subscript is True


# =============================================================================
# Test ContentStreamParser - Text Positioning
# =============================================================================

class TestContentStreamParserPositioning:
    """Tests for text positioning operator parsing."""
    
    def test_td_move_position(self):
        """Test Td (move text position) operator."""
        content = "BT 100 200 Td (Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        x, y = blocks[0].operations[0].position
        assert x == 100.0
        assert y == 200.0
    
    def test_td_uppercase_move_and_leading(self):
        """Test TD (move and set leading) operator."""
        content = "BT 100 -14 TD (Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # TD sets leading to negative of ty
        assert blocks[0].operations[0].state.leading == 14.0
    
    def test_tm_text_matrix(self):
        """Test Tm (set text matrix) operator."""
        content = "BT 1 0 0 1 72 720 Tm (Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        state = blocks[0].operations[0].state
        assert state.text_matrix == (1.0, 0.0, 0.0, 1.0, 72.0, 720.0)
    
    def test_tm_with_scale(self):
        """Test Tm with scaling transformation."""
        content = "BT 2 0 0 2 72 720 Tm (Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        state = blocks[0].operations[0].state
        assert state.text_matrix == (2.0, 0.0, 0.0, 2.0, 72.0, 720.0)
    
    def test_t_star_next_line(self):
        """Test T* (move to next line) operator."""
        content = "BT 14 TL 0 0 Td (Line1) Tj T* (Line2) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # T* should move down by leading amount
        assert len(blocks[0].operations) == 2
        _, y1 = blocks[0].operations[0].position
        _, y2 = blocks[0].operations[1].position
        assert y2 < y1  # Line 2 is below Line 1


# =============================================================================
# Test ContentStreamParser - Text Showing Operators
# =============================================================================

class TestContentStreamParserTextShowing:
    """Tests for text showing operator parsing."""
    
    def test_tj_simple_string(self):
        """Test Tj operator with simple string."""
        content = "BT (Hello World) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hello World"
        assert blocks[0].operations[0].operator == "Tj"
    
    def test_tj_array_with_adjustments(self):
        """Test TJ operator with glyph adjustments."""
        content = "BT [(H) -10 (ello)] TJ ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hello"
        assert blocks[0].operations[0].operator == "TJ"
        assert blocks[0].operations[0].glyph_adjustments == [-10.0]
    
    def test_quote_operator(self):
        """Test ' (single quote) operator."""
        content = "BT 14 TL 0 0 Td (Line1) Tj (Line2) ' ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks[0].operations) == 2
        assert blocks[0].operations[1].operator == "'"
        assert blocks[0].operations[1].text == "Line2"
    
    def test_double_quote_operator(self):
        """Test " (double quote) operator with spacing."""
        content = "BT 1.5 0.5 (Spaced) \" ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        op = blocks[0].operations[0]
        assert op.operator == '"'
        assert op.word_spacing == 1.5
        assert op.char_spacing == 0.5
    
    def test_multiple_tj_in_block(self):
        """Test multiple Tj operators in same text block."""
        content = "BT (Part1) Tj ( ) Tj (Part2) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks[0].operations) == 3
        assert blocks[0].text == "Part1 Part2"


# =============================================================================
# Test ContentStreamParser - String Decoding
# =============================================================================

class TestContentStreamParserStringDecoding:
    """Tests for string decoding functionality."""
    
    def test_literal_string_basic(self):
        """Test basic literal string decoding."""
        content = "BT (Hello) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hello"
    
    def test_literal_string_with_escapes(self):
        """Test literal string with escape sequences."""
        content = r"BT (Line1\nLine2) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Line1\nLine2"
    
    def test_literal_string_escaped_parens(self):
        """Test literal string with escaped parentheses."""
        content = r"BT (Hello \(World\)) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hello (World)"
    
    def test_literal_string_escaped_backslash(self):
        """Test literal string with escaped backslash."""
        content = r"BT (Path\\Name) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Path\\Name"
    
    def test_literal_string_octal_escape(self):
        """Test literal string with octal escape."""
        content = "BT (A\\101B) Tj ET"  # \101 = 'A' in octal
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "AAB"
    
    def test_hex_string_basic(self):
        """Test basic hex string decoding."""
        content = "BT <48656C6C6F> Tj ET"  # "Hello" in hex
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hello"
    
    def test_hex_string_with_spaces(self):
        """Test hex string with whitespace."""
        content = "BT <48 65 6C 6C 6F> Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hello"
    
    def test_hex_string_odd_length(self):
        """Test hex string with odd length (padded with 0)."""
        content = "BT <4865> Tj ET"  # "He"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "He"
    
    def test_nested_parentheses(self):
        """Test literal string with nested parentheses."""
        content = "BT (Hello (nested) World) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hello (nested) World"


# =============================================================================
# Test ContentStreamParser - Graphics State
# =============================================================================

class TestContentStreamParserGraphicsState:
    """Tests for graphics state handling (q/Q)."""
    
    def test_q_q_save_restore_state(self):
        """Test q/Q save and restore state."""
        content = """
        q
        BT 0.5 Tc (Before) Tj ET
        Q
        BT (After) Tj ET
        """
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # State should be restored after Q
        # But since we're not in a text object when Q executes,
        # it affects only the graphics state, not text state in new BT
        assert len(blocks) == 2
    
    def test_cm_transformation_matrix(self):
        """Test cm (concat matrix) operator."""
        content = "2 0 0 2 0 0 cm BT 50 50 Td (Scaled) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # With CTM scale of 2, position should be transformed
        x, y = blocks[0].operations[0].position
        assert x == 100.0  # 50 * 2
        assert y == 100.0  # 50 * 2
    
    def test_nested_state_push_pop(self):
        """Test nested q/Q operations."""
        content = """
        q
          1.5 0 0 1.5 0 0 cm
          q
            2 0 0 2 0 0 cm
            BT 10 10 Td (Inner) Tj ET
          Q
          BT 10 10 Td (Outer) Tj ET
        Q
        BT 10 10 Td (Outside) Tj ET
        """
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # CTM should be cumulative in inner, then restored
        assert len(blocks) == 3


# =============================================================================
# Test ContentStreamParser - TJ Array Parsing
# =============================================================================

class TestContentStreamParserTJArray:
    """Tests for TJ array parsing with glyph adjustments."""
    
    def test_tj_array_strings_only(self):
        """Test TJ array with strings only."""
        content = "BT [(Hello)(World)] TJ ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "HelloWorld"
    
    def test_tj_array_with_positive_adjustment(self):
        """Test TJ array with positive adjustment (move left)."""
        content = "BT [(A) 100 (B)] TJ ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "AB"
        assert 100.0 in blocks[0].operations[0].glyph_adjustments
    
    def test_tj_array_with_negative_adjustment(self):
        """Test TJ array with negative adjustment (move right)."""
        content = "BT [(A) -100 (B)] TJ ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "AB"
        assert -100.0 in blocks[0].operations[0].glyph_adjustments
    
    def test_tj_array_multiple_adjustments(self):
        """Test TJ array with multiple adjustments."""
        content = "BT [(H) -10 (e) -20 (l) -15 (lo)] TJ ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hello"
        adj = blocks[0].operations[0].glyph_adjustments
        assert adj == [-10.0, -20.0, -15.0]
    
    def test_tj_array_hex_strings(self):
        """Test TJ array with hex strings."""
        content = "BT [<48> 50 <69>] TJ ET"  # H, adjustment, i
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "Hi"


# =============================================================================
# Test Convenience Functions
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_parse_content_stream_basic(self):
        """Test parse_content_stream function."""
        content = "BT (Hello) Tj ET"
        blocks = parse_content_stream(content)
        
        assert len(blocks) == 1
        assert blocks[0].text == "Hello"
    
    def test_parse_content_stream_with_font_map(self):
        """Test parse_content_stream with font map."""
        content = "BT /F1 12 Tf (Test) Tj ET"
        font_map = {"/F1": "Arial"}
        blocks = parse_content_stream(content, font_map)
        
        assert blocks[0].operations[0].font_name == "Arial"
    
    def test_extract_text_state_from_page_mock(self):
        """Test extract_text_state_from_page with mock page."""
        mock_page = MagicMock()
        mock_page.get_fonts.return_value = []
        mock_page.read_contents.return_value = b"BT 0.5 Tc (Test) Tj ET"
        
        operations = extract_text_state_from_page(mock_page)
        
        assert len(operations) == 1
        assert operations[0].text == "Test"
        assert operations[0].char_spacing == 0.5
    
    def test_extract_text_state_with_target_text(self):
        """Test extract_text_state_from_page with target text filter."""
        mock_page = MagicMock()
        mock_page.get_fonts.return_value = []
        mock_page.read_contents.return_value = b"BT (Hello) Tj (World) Tj ET"
        
        operations = extract_text_state_from_page(mock_page, target_text="World")
        
        assert len(operations) == 1
        assert operations[0].text == "World"
    
    def test_extract_text_state_no_content(self):
        """Test extract_text_state_from_page when content is None."""
        mock_page = MagicMock()
        mock_page.get_fonts.return_value = []
        mock_page.read_contents.return_value = None
        
        operations = extract_text_state_from_page(mock_page)
        
        assert operations == []
    
    def test_get_spacing_info_for_text_found(self):
        """Test get_spacing_info_for_text when text is found."""
        mock_page = MagicMock()
        mock_page.get_fonts.return_value = []
        mock_page.read_contents.return_value = b"BT 0.5 Tc 1.0 Tw 2.0 Ts (Test) Tj ET"
        
        info = get_spacing_info_for_text(mock_page, "Test")
        
        assert info is not None
        assert info['text'] == "Test"
        assert info['char_spacing'] == 0.5
        assert info['word_spacing'] == 1.0
        assert info['rise'] == 2.0
        assert info['has_char_spacing'] is True
        assert info['has_word_spacing'] is True
    
    def test_get_spacing_info_for_text_not_found(self):
        """Test get_spacing_info_for_text when text is not found."""
        mock_page = MagicMock()
        mock_page.get_fonts.return_value = []
        mock_page.read_contents.return_value = b"BT (Other) Tj ET"
        
        info = get_spacing_info_for_text(mock_page, "Missing")
        
        assert info is None


# =============================================================================
# Test Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_text_object(self):
        """Test empty BT/ET block (no Tj)."""
        content = "BT 12 Tf ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # Empty block should not be added
        assert blocks == []
    
    def test_malformed_number(self):
        """Test handling of malformed numbers."""
        content = "BT abc Tc (Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # Should not crash, char_spacing should remain default
        assert len(blocks) == 1
        assert blocks[0].operations[0].char_spacing == 0.0
    
    def test_missing_operands(self):
        """Test handling of missing operands."""
        content = "BT Tc (Test) Tj ET"  # Tc without number
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # Should not crash
        assert len(blocks) == 1
    
    def test_comments_ignored(self):
        """Test that PDF comments are ignored."""
        content = "BT % This is a comment\n(Test) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].text == "Test"
    
    def test_unicode_in_string(self):
        """Test handling of unicode characters."""
        content = "BT (Caf\\351) Tj ET"  # é as octal \351
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert blocks[0].text == "Café"
    
    def test_special_characters_in_string(self):
        """Test special characters in strings."""
        content = r"BT (Tab\tNewline\n) Tj ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert "\t" in blocks[0].text
        assert "\n" in blocks[0].text
    
    def test_very_long_content_stream(self):
        """Test parsing of long content stream."""
        # Generate a long content stream
        operations = " ".join([f"({i}) Tj" for i in range(1000)])
        content = f"BT {operations} ET"
        
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert len(blocks[0].operations) == 1000
    
    def test_deeply_nested_arrays(self):
        """Test TJ with complex array structure."""
        content = "BT [(Outer) 10 [(Inner)] 20 (End)] TJ ET"
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        # Parser should handle this without crashing
        assert len(blocks) == 1


# =============================================================================
# Test Real-World Content Streams
# =============================================================================

class TestRealWorldContentStreams:
    """Tests with realistic PDF content streams."""
    
    def test_typical_paragraph(self):
        """Test typical paragraph structure."""
        content = """
        BT
        /F1 12 Tf
        14 TL
        72 720 Td
        (This is a paragraph of text that spans) Tj
        T*
        (multiple lines in the PDF document.) Tj
        ET
        """
        parser = ContentStreamParser()
        parser.set_font_map({"/F1": "Helvetica"})
        blocks = parser.parse(content)
        
        assert len(blocks) == 1
        assert len(blocks[0].operations) == 2
        assert blocks[0].operations[0].font_name == "Helvetica"
        assert blocks[0].operations[0].font_size == 12.0
    
    def test_mixed_styles(self):
        """Test text with mixed styles (different Tc/Tw)."""
        content = """
        BT
        0 Tc
        (Normal text ) Tj
        0.5 Tc
        (tracked text ) Tj
        -0.2 Tc
        (tight text) Tj
        ET
        """
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        ops = blocks[0].operations
        assert ops[0].char_spacing == 0.0
        assert ops[1].char_spacing == 0.5
        assert ops[2].char_spacing == -0.2
    
    def test_superscript_subscript(self):
        """Test super/subscript detection."""
        content = """
        BT
        (H) Tj
        3 Ts
        6 Tf /F1
        (2) Tj
        0 Ts
        (O) Tj
        ET
        """
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        ops = blocks[0].operations
        assert ops[0].is_superscript is False
        assert ops[0].is_subscript is False
        assert ops[1].is_superscript is True
        assert ops[2].is_superscript is False
    
    def test_justified_text_with_word_spacing(self):
        """Test justified text with word spacing."""
        content = """
        BT
        2.5 Tw
        (This text is justified with extra word spacing.) Tj
        ET
        """
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].operations[0].word_spacing == 2.5
        assert blocks[0].operations[0].has_word_spacing is True
    
    def test_kerned_text_tj(self):
        """Test kerned text with TJ operator."""
        content = """
        BT
        [(A) -80 (V) -80 (A)] TJ
        ET
        """
        parser = ContentStreamParser()
        blocks = parser.parse(content)
        
        assert blocks[0].text == "AVA"
        adj = blocks[0].operations[0].glyph_adjustments
        assert adj == [-80.0, -80.0]
