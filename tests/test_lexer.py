import pytest

from robolang.diagnostics import CompileError
from robolang.frontend_limits import MAX_INTEGER_LITERAL_DIGITS
from robolang.lexer import tokenize
from robolang.tokens import Token


def test_move_tokens_include_eof():
    assert tokenize("mover(3);") == [
        Token("KW_MOVER", "mover", 1, 1),
        Token("LPAREN", "(", 1, 6),
        Token("INT", "3", 1, 7),
        Token("RPAREN", ")", 1, 8),
        Token("SEMICOLON", ";", 1, 9),
        Token("EOF", "", 1, 10),
    ]


def test_keywords_match_whole_case_sensitive_words():
    tokens = tokenize("mover2 Mover entero giro mover girar derecha izquierda")
    assert [token.type for token in tokens] == [
        "IDENT", "IDENT", "KW_ENTERO", "KW_GIRO", "KW_MOVER", "KW_GIRAR",
        "KW_DERECHA", "KW_IZQUIERDA", "EOF",
    ]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_whitespace_and_comments_preserve_coordinates(newline):
    tokens = tokenize(f"// mover(@);{newline}\t  mover(0); // end")
    assert tokens[0] == Token("KW_MOVER", "mover", 2, 4)
    assert tokens[-1] == Token("EOF", "", 2, 20)


@pytest.mark.parametrize("character", ["@", "é", "٣", "/"])
def test_unknown_character_reports_its_position(character):
    with pytest.raises(CompileError) as error:
        tokenize(f"mover({character});")
    diagnostic = error.value.diagnostic
    assert (diagnostic.phase, diagnostic.code) == ("lexical", "LEX_UNKNOWN_CHAR")
    assert (diagnostic.line, diagnostic.column) == (1, 7)


def test_integer_literal_budget():
    assert tokenize("9" * MAX_INTEGER_LITERAL_DIGITS)[0].type == "INT"
    with pytest.raises(CompileError) as error:
        tokenize("mover(" + "9" * (MAX_INTEGER_LITERAL_DIGITS + 1) + ");")
    diagnostic = error.value.diagnostic
    assert (diagnostic.code, diagnostic.column) == ("LEX_INTEGER_TOO_LONG", 7)
