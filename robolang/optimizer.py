"""Constant folding over three-address code.

Only operations whose operands are immediates are folded. Values are not
propagated through temporaries or variables, and robot orders stay in place.
"""

from .settings import integer_within_budget
from .tac import INTEGER_OPERATIONS, ImmInt, Quad


def optimize(tac: list[Quad]) -> list[Quad]:
    """Return a new list with constant operations replaced by COPY."""
    return [_fold(quad) for quad in tac]


def _fold(quad: Quad) -> Quad:
    value = _constant_result(quad)
    # An out-of-budget operation stays so the VM reports it in both modes.
    if value is None or not integer_within_budget(value):
        return quad
    return Quad("COPY", ImmInt(value), None, quad.result, quad.location)


def _constant_result(quad: Quad) -> int | None:
    match quad.op, quad.arg1, quad.arg2:
        case "NEG", ImmInt(value), None if integer_within_budget(value):
            return -value
        case ("ADD" | "SUB" | "MUL"), ImmInt(left), ImmInt(right) if (
            integer_within_budget(left) and integer_within_budget(right)
        ):
            return INTEGER_OPERATIONS[quad.op](left, right)
    return None
