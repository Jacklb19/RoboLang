"""TAC tests driven by the real lexer, parser and semantic analyzer."""

from pathlib import Path

import pytest

from robolang.diagnostics import Location
from robolang.lexer import tokenize
from robolang.parser import parse
from robolang.semantic import analyze
from robolang.tac import ImmInt, ImmTurn, Quad, Slot, Temp, format_quad, generate_tac

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def tac_for(source):
    return generate_tac(analyze(parse(tokenize(source))))


def text_for(source):
    return [format_quad(quad) for quad in tac_for(source)]


def test_i01_declaration_uses_temporary_and_copy():
    add, copy = tac_for("entero x=2+1;")
    assert (add.op, add.arg1, add.arg2, add.result) == ("ADD", ImmInt(2), ImmInt(1), Temp("T0"))
    assert (copy.op, copy.arg1, copy.arg2, copy.result) == ("COPY", Temp("T0"), None, Slot("S0"))


def test_i03_dependent_operations_keep_evaluation_order():
    assert text_for("mover((2+3)*4);") == ["T0 = 2 + 3", "T1 = T0 * 4", "MOVE T1"]


def test_precedence_and_left_associativity_come_from_the_tree():
    assert text_for("entero x=8-3-2*2;") == [
        "T0 = 8 - 3",
        "T1 = 2 * 2",
        "T2 = T0 - T1",
        "S0 = T2",
    ]


def test_unary_negation_uses_neg():
    assert text_for("entero x=1; mover(-x);") == ["S0 = 1", "T0 = -S0", "MOVE T0"]


@pytest.mark.parametrize(("word", "direction"), [("derecha", "RIGHT"), ("izquierda", "LEFT")])
def test_turn_literals_become_typed_directions(word, direction):
    [turn] = tac_for(f"girar({word});")
    assert (turn.op, turn.arg1) == ("TURN", ImmTurn(direction))


def test_shadowing_and_assignment_use_resolved_slots():
    assert text_for("entero x=1; { entero x=x+1; x=x; mover(x); } mover(x);") == [
        "S0 = 1",
        "T0 = S0 + 1",
        "S1 = T0",
        "S1 = S1",
        "MOVE S1",
        "MOVE S0",
    ]


def test_integral_example_matches_guide():
    source = (EXAMPLES / "08_integral.rbl").read_text(encoding="utf-8")
    assert text_for(source) == [
        "T0 = 2 + 1",
        "S0 = T0",
        "S1 = RIGHT",
        "MOVE S0",
        "TURN S1",
        "S2 = 2",
        "MOVE S2",
    ]


def test_quads_keep_line_and_column_from_the_source():
    add, copy, move = tac_for("entero x = 2 + 1;\n  mover(x);")
    assert add.location == Location(1, 14)
    assert copy.location == Location(1, 1)
    assert move.location == Location(2, 3)


def test_empty_program_has_no_quads():
    assert tac_for("") == []


def test_unknown_operation_cannot_be_formatted():
    with pytest.raises(ValueError):
        format_quad(Quad("JUMP", None, None, None, Location(1, 1)))
