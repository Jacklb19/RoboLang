"""Constant-folding tests built from hand-written quadruples (fixtures)."""

import pytest

from robolang.diagnostics import Location
from robolang.frontend_limits import MAX_INTEGER_LITERAL_DIGITS
from robolang.optimizer import optimize
from robolang.settings import MAX_INTEGER_BITS, integer_within_budget
from robolang.tac import ImmInt, ImmTurn, Quad, Slot, Temp, format_quad

HERE = Location(3, 7)
T0 = Temp("T0")
TOO_LARGE = 1 << MAX_INTEGER_BITS
LARGEST = TOO_LARGE - 1


@pytest.mark.parametrize(
    ("op", "left", "right", "expected"),
    [("ADD", 2, 1, 3), ("SUB", 2, 5, -3), ("MUL", 4, -3, -12), ("MUL", 0, 9, 0)],
)
def test_binary_constants_fold_to_copy(op, left, right, expected):
    [quad] = optimize([Quad(op, ImmInt(left), ImmInt(right), T0, HERE)])
    assert quad == Quad("COPY", ImmInt(expected), None, T0, HERE)


@pytest.mark.parametrize(("value", "expected"), [(5, -5), (0, 0), (-2, 2)])
def test_negation_of_constant_folds(value, expected):
    [quad] = optimize([Quad("NEG", ImmInt(value), None, T0, HERE)])
    assert quad == Quad("COPY", ImmInt(expected), None, T0, HERE)


def test_i02_guide_notation_after_folding():
    tac = [Quad("ADD", ImmInt(2), ImmInt(1), T0, HERE), Quad("MOVE", T0, None, None, HERE)]
    assert [format_quad(quad) for quad in optimize(tac)] == ["T0 = 3", "MOVE T0"]


@pytest.mark.parametrize(
    "quad",
    [
        Quad("ADD", Slot("S0"), ImmInt(1), T0, HERE),
        Quad("MUL", ImmInt(2), Temp("T1"), T0, HERE),
        Quad("NEG", Slot("S0"), None, T0, HERE),
        Quad("COPY", ImmInt(1), None, Slot("S0"), HERE),
        Quad("MOVE", ImmInt(1), None, None, HERE),
        Quad("TURN", ImmTurn("LEFT"), None, None, HERE),
    ],
)
def test_non_constant_operations_and_orders_are_unchanged(quad):
    assert optimize([quad]) == [quad]


def test_values_are_not_propagated_through_temporaries():
    tac = [
        Quad("ADD", ImmInt(1), ImmInt(1), T0, HERE),
        Quad("COPY", T0, None, Slot("S0"), HERE),
        Quad("MUL", T0, ImmInt(2), Temp("T1"), HERE),
    ]
    assert [format_quad(quad) for quad in optimize(tac)] == ["T0 = 2", "S0 = T0", "T1 = T0 * 2"]


def test_robot_orders_keep_their_relative_order():
    tac = [
        Quad("MOVE", ImmInt(1), None, None, HERE),
        Quad("ADD", ImmInt(1), ImmInt(1), T0, HERE),
        Quad("TURN", ImmTurn("RIGHT"), None, None, HERE),
        Quad("MOVE", T0, None, None, HERE),
    ]
    assert [quad.op for quad in optimize(tac)] == ["MOVE", "COPY", "TURN", "MOVE"]


def test_input_list_is_preserved():
    tac = [Quad("ADD", ImmInt(2), ImmInt(1), T0, HERE)]
    optimized = optimize(tac)
    assert tac == [Quad("ADD", ImmInt(2), ImmInt(1), T0, HERE)]
    assert optimized is not tac


@pytest.mark.parametrize(
    "quad",
    [
        Quad("MUL", ImmInt(LARGEST), ImmInt(LARGEST), T0, HERE),
        Quad("ADD", ImmInt(LARGEST), ImmInt(1), T0, HERE),
        Quad("SUB", ImmInt(TOO_LARGE), ImmInt(TOO_LARGE), T0, HERE),
        Quad("NEG", ImmInt(TOO_LARGE), None, T0, HERE),
    ],
)
def test_operations_outside_the_budget_are_left_for_the_vm(quad):
    assert optimize([quad]) == [quad]


def test_result_exactly_at_the_budget_folds():
    [quad] = optimize([Quad("ADD", ImmInt(LARGEST - 1), ImmInt(1), T0, HERE)])
    assert quad.arg1 == ImmInt(LARGEST)


def test_budget_holds_every_literal_the_lexer_accepts():
    assert integer_within_budget(10**MAX_INTEGER_LITERAL_DIGITS - 1)
