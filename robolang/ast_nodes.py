"""Typed nodes shared by the parser, semantic analyzer and TAC generator."""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from .diagnostics import Location

ValueType = Literal["entero", "giro"]
TurnValue = Literal["derecha", "izquierda"]


@dataclass(frozen=True, slots=True)
class Program:
    statements: tuple["Statement", ...]
    location: Location


@dataclass(frozen=True, slots=True)
class Block:
    statements: tuple["Statement", ...]
    location: Location


@dataclass(frozen=True, slots=True)
class VarDeclaration:
    name: str
    declared_type: ValueType
    expression: "Expression"
    location: Location
    name_location: Location
    resolved_slot: str | None = field(default=None, kw_only=True)


@dataclass(frozen=True, slots=True)
class Assignment:
    name: str
    expression: "Expression"
    location: Location
    name_location: Location
    resolved_slot: str | None = field(default=None, kw_only=True)


@dataclass(frozen=True, slots=True)
class Move:
    expression: "Expression"
    location: Location


@dataclass(frozen=True, slots=True)
class Turn:
    expression: "Expression"
    location: Location


@dataclass(frozen=True, slots=True)
class BinaryOperation:
    operator: str
    left: "Expression"
    right: "Expression"
    location: Location


@dataclass(frozen=True, slots=True)
class UnaryOperation:
    operator: str
    operand: "Expression"
    location: Location


@dataclass(frozen=True, slots=True)
class IntLiteral:
    value: int
    location: Location


@dataclass(frozen=True, slots=True)
class TurnLiteral:
    value: TurnValue
    location: Location


@dataclass(frozen=True, slots=True)
class VariableReference:
    name: str
    location: Location
    resolved_slot: str | None = field(default=None, kw_only=True)


Statement: TypeAlias = VarDeclaration | Assignment | Move | Turn | Block
Expression: TypeAlias = BinaryOperation | UnaryOperation | IntLiteral | TurnLiteral | VariableReference
