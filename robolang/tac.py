"""Three-address code: typed operands, quadruples and their generator."""

from dataclasses import dataclass
from operator import add, mul, sub
from typing import Callable, Literal, TypeAlias

from .ast_nodes import (
    Assignment,
    BinaryOperation,
    Block,
    Expression,
    IntLiteral,
    Move,
    Statement,
    Turn,
    TurnLiteral,
    UnaryOperation,
    VarDeclaration,
    VariableReference,
)
from .diagnostics import Location
from .semantic import SemanticResult

TurnDirection = Literal["RIGHT", "LEFT"]

INTEGER_OPERATIONS: dict[str, Callable[[int, int], int]] = {
    "ADD": add,
    "SUB": sub,
    "MUL": mul,
}

_BINARY_OPCODES = {"+": "ADD", "-": "SUB", "*": "MUL"}
_BINARY_SYMBOLS = {opcode: symbol for symbol, opcode in _BINARY_OPCODES.items()}
_TURN_DIRECTIONS: dict[str, TurnDirection] = {"derecha": "RIGHT", "izquierda": "LEFT"}


@dataclass(frozen=True, slots=True)
class ImmInt:
    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ImmTurn:
    value: TurnDirection

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Slot:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class Temp:
    name: str

    def __str__(self) -> str:
        return self.name


Immediate: TypeAlias = ImmInt | ImmTurn
Address: TypeAlias = Slot | Temp
Operand: TypeAlias = Immediate | Address


@dataclass(frozen=True, slots=True)
class Quad:
    op: str
    arg1: Operand | None
    arg2: Operand | None
    result: Address | None
    location: Location


def generate_tac(semantic: SemanticResult) -> list[Quad]:
    """Translate a validated program into quadruples, in source order."""
    builder = _TacBuilder()
    for statement in semantic.program.statements:
        builder.statement(statement)
    return builder.quads


def format_quad(quad: Quad) -> str:
    """Render a quadruple with the notation used in the project guide."""
    match quad.op:
        case "ADD" | "SUB" | "MUL":
            symbol = _BINARY_SYMBOLS[quad.op]
            return f"{quad.result} = {quad.arg1} {symbol} {quad.arg2}"
        case "NEG":
            return f"{quad.result} = -{quad.arg1}"
        case "COPY":
            return f"{quad.result} = {quad.arg1}"
        case "MOVE" | "TURN":
            return f"{quad.op} {quad.arg1}"
    raise ValueError(f"Unsupported TAC operation: {quad.op}")


def _resolved_slot(slot: str | None, name: str) -> Slot:
    if slot is None:
        raise ValueError(f"Variable '{name}' reached TAC generation without a slot.")
    return Slot(slot)


class _TacBuilder:
    def __init__(self) -> None:
        self.quads: list[Quad] = []
        self._next_temp = 0

    def _new_temp(self) -> Temp:
        temp = Temp(f"T{self._next_temp}")
        self._next_temp += 1
        return temp

    def _emit(
        self,
        op: str,
        arg1: Operand,
        arg2: Operand | None,
        result: Address | None,
        location: Location,
    ) -> None:
        self.quads.append(Quad(op, arg1, arg2, result, location))

    def statement(self, node: Statement) -> None:
        match node:
            case Block():
                for child in node.statements:
                    self.statement(child)
            case VarDeclaration() | Assignment():
                target = _resolved_slot(node.resolved_slot, node.name)
                self._emit("COPY", self.expression(node.expression), None, target, node.location)
            case Move():
                self._emit("MOVE", self.expression(node.expression), None, None, node.location)
            case Turn():
                self._emit("TURN", self.expression(node.expression), None, None, node.location)
            case _:
                raise TypeError(f"Unsupported statement node: {type(node).__name__}")

    def expression(self, node: Expression) -> Operand:
        match node:
            case IntLiteral():
                return ImmInt(node.value)
            case TurnLiteral():
                return ImmTurn(_TURN_DIRECTIONS[node.value])
            case VariableReference():
                return _resolved_slot(node.resolved_slot, node.name)
            case UnaryOperation():
                operand = self.expression(node.operand)
                result = self._new_temp()
                self._emit("NEG", operand, None, result, node.location)
                return result
            case BinaryOperation():
                left = self.expression(node.left)
                right = self.expression(node.right)
                result = self._new_temp()
                self._emit(_BINARY_OPCODES[node.operator], left, right, result, node.location)
                return result
        raise TypeError(f"Unsupported expression node: {type(node).__name__}")
