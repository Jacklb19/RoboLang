"""Check types and return an AST with resolved variable slots."""

from dataclasses import dataclass, replace

from .ast_nodes import (
    Assignment,
    BinaryOperation,
    Block,
    Expression,
    IntLiteral,
    Move,
    Program,
    Statement,
    Turn,
    TurnLiteral,
    UnaryOperation,
    ValueType,
    VarDeclaration,
    VariableReference,
)
from .diagnostics import CompileError, Location
from .symbols import Symbol, SymbolTable


@dataclass(frozen=True, slots=True)
class SemanticResult:
    program: Program
    symbols: list[Symbol]


def analyze(program: Program) -> SemanticResult:
    """Validate the parsed program without modifying the input tree."""
    analyzer = _Analyzer()
    statements = tuple(analyzer.statement(node) for node in program.statements)
    return SemanticResult(replace(program, statements=statements), analyzer.table.declarations)


def _expect_type(
    expected: ValueType, actual: ValueType, context: str, location: Location,
) -> None:
    if actual != expected:
        raise CompileError(
            "semantic", "SEM_TYPE_MISMATCH",
            f"{context} requires type '{expected}', but got '{actual}'.", location,
        )


class _Analyzer:
    def __init__(self) -> None:
        self.table = SymbolTable()

    def resolve(self, name: str, location: Location) -> Symbol:
        symbol = self.table.lookup(name)
        if symbol is None:
            raise CompileError(
                "semantic", "SEM_UNDECLARED", f"Variable '{name}' is not declared.", location,
            )
        return symbol

    def statement(self, node: Statement) -> Statement:
        match node:
            case Block():
                with self.table.block():
                    statements = tuple(self.statement(child) for child in node.statements)
                return replace(node, statements=statements)
            case VarDeclaration():
                if self.table.contains_current(node.name):
                    raise CompileError(
                        "semantic", "SEM_REDECLARATION",
                        f"Variable '{node.name}' is already declared in this scope.",
                        node.name_location,
                    )
                expression, actual = self.expression(node.expression)
                _expect_type(node.declared_type, actual, "Declaration", node.name_location)
                symbol = self.table.declare(node.name, node.declared_type, node.name_location)
                return replace(node, expression=expression, resolved_slot=symbol.slot)
            case Assignment():
                symbol = self.resolve(node.name, node.name_location)
                expression, actual = self.expression(node.expression)
                _expect_type(symbol.type, actual, "Assignment", node.name_location)
                return replace(node, expression=expression, resolved_slot=symbol.slot)
            case Move() | Turn():
                expression, actual = self.expression(node.expression)
                if isinstance(node, Move):
                    _expect_type("entero", actual, "mover()", node.location)
                else:
                    _expect_type("giro", actual, "girar()", node.location)
                return replace(node, expression=expression)
        raise TypeError(f"Unsupported statement node: {type(node).__name__}")

    def expression(self, node: Expression) -> tuple[Expression, ValueType]:
        match node:
            case IntLiteral():
                return node, "entero"
            case TurnLiteral():
                return node, "giro"
            case VariableReference():
                symbol = self.resolve(node.name, node.location)
                return replace(node, resolved_slot=symbol.slot), symbol.type
            case UnaryOperation():
                operand, actual = self.expression(node.operand)
                _expect_type("entero", actual, f"Operator '{node.operator}'", node.location)
                return replace(node, operand=operand), "entero"
            case BinaryOperation():
                left, left_type = self.expression(node.left)
                right, right_type = self.expression(node.right)
                context = f"Operator '{node.operator}'"
                _expect_type("entero", left_type, context, node.location)
                _expect_type("entero", right_type, context, node.location)
                return replace(node, left=left, right=right), "entero"
        raise TypeError(f"Unsupported expression node: {type(node).__name__}")
