"""Translate three-address code into typed virtual machine instructions."""

from dataclasses import dataclass
from typing import TypeAlias

from .diagnostics import Location
from .tac import Address, ImmInt, Immediate, ImmTurn, Operand, Quad, Slot, Temp, format_quad


@dataclass(frozen=True, slots=True)
class Register:
    name: str

    def __str__(self) -> str:
        return self.name


R0 = Register("R0")
R1 = Register("R1")

InstructionArg: TypeAlias = Register | Immediate | Address


@dataclass(frozen=True, slots=True)
class Instruction:
    opcode: str
    args: tuple[InstructionArg, ...]
    location: Location


def generate_vm_code(tac: list[Quad], *, eof_location: Location) -> list[Instruction]:
    """Translate each quadruple in order and finish with HALT at end of file."""
    code: list[Instruction] = []
    for quad in tac:
        code.extend(_translate(quad))
    code.append(Instruction("HALT", (), eof_location))
    return code


def format_instruction(instruction: Instruction) -> str:
    """Render one instruction as pseudo-assembly for display only."""
    if not instruction.args:
        return instruction.opcode
    return f"{instruction.opcode} {', '.join(str(arg) for arg in instruction.args)}"


def _load(register: Register, operand: Operand | None, location: Location) -> Instruction:
    match operand:
        case ImmInt() | ImmTurn():
            return Instruction("LOADC", (register, operand), location)
        case Slot() | Temp():
            return Instruction("LOAD", (register, operand), location)
    raise ValueError(f"Invalid TAC operand: {operand!r}")


def _store(target: Address | None, location: Location) -> Instruction:
    if not isinstance(target, Slot | Temp):
        raise ValueError(f"Invalid TAC destination: {target!r}")
    return Instruction("STORE", (target, R0), location)


def _translate(quad: Quad) -> list[Instruction]:
    location = quad.location
    match quad.op:
        case "ADD" | "SUB" | "MUL":
            return [
                _load(R0, quad.arg1, location),
                _load(R1, quad.arg2, location),
                Instruction(quad.op, (R0, R1), location),
                _store(quad.result, location),
            ]
        case "NEG":
            return [
                _load(R0, quad.arg1, location),
                Instruction("NEG", (R0,), location),
                _store(quad.result, location),
            ]
        case "COPY":
            return [_load(R0, quad.arg1, location), _store(quad.result, location)]
        case "MOVE" | "TURN":
            return [_load(R0, quad.arg1, location), Instruction(quad.op, (R0,), location)]
    raise ValueError(f"Unsupported TAC operation: {format_quad(quad)}")
