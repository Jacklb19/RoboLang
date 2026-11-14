import pytest

from robolang.ast_nodes import BinaryOperation, Block, IntLiteral, UnaryOperation
from robolang.diagnostics import CompileError, Location
from robolang.frontend_limits import MAX_SYNTAX_DEPTH
from robolang.lexer import tokenize
from robolang.parser import parse


def test_multiplication_binds_more_tightly_than_addition():
    (declaration,) = parse(tokenize("entero x = 2 + 3 * 4;")).statements
    expression = declaration.expression
    assert isinstance(expression, BinaryOperation)
    assert expression.operator == "+"
    assert expression.location == Location(1, 14)
    assert expression.right.operator == "*"


def test_parentheses_and_unary_minus():
    (move,) = parse(tokenize("mover(-(2 + 3) * 4);")).statements
    assert move.expression.operator == "*"
    assert isinstance(move.expression.left, UnaryOperation)
    assert move.expression.left.operand.operator == "+"


def test_subtraction_is_left_associative():
    (move,) = parse(tokenize("mover(8 - 3 - 2);")).statements
    assert move.expression.left.operator == "-"
    assert isinstance(move.expression.right, IntLiteral)
    assert move.expression.right.value == 2


def test_nested_and_empty_blocks():
    (outer,) = parse(tokenize("{\n {}\n { mover(0); }\n}")).statements
    empty, inner = outer.statements
    assert isinstance(outer, Block)
    assert isinstance(empty, Block)
    assert empty.statements == ()
    assert inner.location == Location(3, 2)
    assert inner.statements[0].location == Location(3, 4)


def test_empty_program():
    assert parse(tokenize("// empty")).statements == ()


@pytest.mark.parametrize(
    ("source", "code", "column"),
    [
        ("mover(3;", "SYN_EXPECTED_TOKEN", 8),
        ("entero x = 3", "SYN_EXPECTED_TOKEN", 13),
        ("mover();", "SYN_UNEXPECTED_TOKEN", 7),
        ("{ mover(1);", "SYN_EXPECTED_TOKEN", 12),
        ("mover(0); 1", "SYN_UNEXPECTED_TOKEN", 11),
    ],
)
def test_invalid_syntax_is_located(source, code, column):
    with pytest.raises(CompileError) as error:
        parse(tokenize(source))
    diagnostic = error.value.diagnostic
    assert (diagnostic.phase, diagnostic.code) == ("syntax", code)
    assert (diagnostic.line, diagnostic.column) == (1, column)


@pytest.mark.parametrize(
    "source",
    [
        "{" * (MAX_SYNTAX_DEPTH + 1) + "}" * (MAX_SYNTAX_DEPTH + 1),
        "mover(" + "-" * (MAX_SYNTAX_DEPTH + 1) + "0);",
        "mover(" + "(" * (MAX_SYNTAX_DEPTH + 1) + "0" + ")" * (MAX_SYNTAX_DEPTH + 1) + ");",
        "mover(" + "1+" * (MAX_SYNTAX_DEPTH + 1) + "1);",
    ],
)
def test_excessive_nesting_or_tree_height_reports_a_syntax_error(source):
    with pytest.raises(CompileError) as error:
        parse(tokenize(source))
    assert error.value.diagnostic.code == "SYN_TOO_COMPLEX"
