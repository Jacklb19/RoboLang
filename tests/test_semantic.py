from pathlib import Path

import pytest

from robolang.diagnostics import CompileError
from robolang.lexer import tokenize
from robolang.parser import parse
from robolang.semantic import analyze


def validate(source):
    return analyze(parse(tokenize(source)))


def test_pipeline_for_integral_example():
    example = Path(__file__).resolve().parents[1] / "examples" / "08_integral.rbl"
    program = parse(tokenize(example.read_text(encoding="utf-8")))
    result = analyze(program)
    assert [(s.name, s.type, s.scope_id, s.slot) for s in result.symbols] == [
        ("pasos", "entero", "global", "S0"),
        ("lado", "giro", "global", "S1"),
        ("pasos", "entero", "bloque_1", "S2"),
    ]
    assert [(s.decl_line, s.decl_col) for s in result.symbols] == [(1, 8), (2, 6), (6, 12)]
    steps, direction, move, turn, block = result.program.statements
    assert (steps.resolved_slot, direction.resolved_slot) == ("S0", "S1")
    assert (move.expression.resolved_slot, turn.expression.resolved_slot) == ("S0", "S1")
    assert block.statements[0].resolved_slot == "S2"
    assert block.statements[1].expression.resolved_slot == "S2"
    assert program.statements[2].expression.resolved_slot is None


def test_shadow_initializer_and_assignment_resolve_in_order():
    result = validate("entero x=1; { entero x=x+1; x=x-1; mover(x); } mover(x);")
    _, block, outer_move = result.program.statements
    declaration, assignment, inner_move = block.statements
    assert declaration.expression.left.resolved_slot == "S0"
    assert declaration.resolved_slot == assignment.resolved_slot == "S1"
    assert assignment.expression.left.resolved_slot == inner_move.expression.resolved_slot == "S1"
    assert outer_move.expression.resolved_slot == "S0"


def test_nested_assignment_can_update_the_outer_slot():
    result = validate("giro lado=izquierda; { { lado=derecha; } } girar(lado);")
    _, outer, turn = result.program.statements
    assignment = outer.statements[0].statements[0]
    assert assignment.resolved_slot == turn.expression.resolved_slot == "S0"


def test_sibling_scopes_get_distinct_slots():
    result = validate("{ entero x=1; } { entero x=2; }")
    assert [(s.scope_id, s.slot) for s in result.symbols] == [
        ("bloque_1", "S0"), ("bloque_2", "S1"),
    ]


@pytest.mark.parametrize(
    ("source", "code", "line", "column"),
    [
        ("mover(x);", "SEM_UNDECLARED", 1, 7),
        ("mover(derecha);", "SEM_TYPE_MISMATCH", 1, 1),
        ("girar(3);", "SEM_TYPE_MISMATCH", 1, 1),
        ("entero x=1;\nentero x=2;", "SEM_REDECLARATION", 2, 8),
        ("{ entero x=1; }\nmover(x);", "SEM_UNDECLARED", 2, 7),
        ("entero x=2+derecha;", "SEM_TYPE_MISMATCH", 1, 11),
        ("mover(-izquierda);", "SEM_TYPE_MISMATCH", 1, 7),
        ("entero x=x;", "SEM_UNDECLARED", 1, 10),
        ("entero x=derecha;", "SEM_TYPE_MISMATCH", 1, 8),
        ("entero x=2;\nx=izquierda;", "SEM_TYPE_MISMATCH", 2, 1),
        ("x=1;", "SEM_UNDECLARED", 1, 1),
    ],
)
def test_semantic_errors_have_stable_codes_and_locations(source, code, line, column):
    with pytest.raises(CompileError) as error:
        validate(source)
    diagnostic = error.value.diagnostic
    assert (diagnostic.phase, diagnostic.code) == ("semantic", code)
    assert (diagnostic.line, diagnostic.column) == (line, column)


@pytest.mark.parametrize("source", ["", "mover(0);", "mover(-1);", "mover(20);"])
def test_movement_values_are_checked_after_semantic_analysis(source):
    assert validate(source).symbols == []
