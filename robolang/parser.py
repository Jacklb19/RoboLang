"""Recursive descent parser for the RoboLang grammar."""

from typing import NoReturn

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
    TurnValue,
    UnaryOperation,
    ValueType,
    VarDeclaration,
    VariableReference,
)
from .diagnostics import CompileError
from .frontend_limits import MAX_SYNTAX_DEPTH
from .tokens import Token

_TYPES: dict[str, ValueType] = {"KW_ENTERO": "entero", "KW_GIRO": "giro"}
_TURNS: dict[str, TurnValue] = {
    "KW_DERECHA": "derecha",
    "KW_IZQUIERDA": "izquierda",
}
_PRECEDENCE = {"PLUS": 1, "MINUS": 1, "STAR": 2}
_EXPECTED_TEXT = {
    "IDENT": "an identifier", "ASSIGN": "'='", "SEMICOLON": "';'",
    "LPAREN": "'('", "RPAREN": "')'", "RBRACE": "'}'",
}


def parse(tokens: list[Token]) -> Program:
    """Parse the entire token stream produced by tokenize."""
    return _Parser(tokens).parse_program()


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current
        self.index += 1
        return token

    def expect(self, kind: str) -> Token:
        token = self.current
        if token.type != kind:
            found = "end of input" if token.type == "EOF" else repr(token.lexeme)
            self.fail(
                token, "SYN_EXPECTED_TOKEN",
                f"Expected {_EXPECTED_TEXT[kind]}, found {found}.",
            )
        return self.advance()

    @staticmethod
    def fail(token: Token, code: str, message: str) -> NoReturn:
        raise CompileError("syntax", code, message, token.location)

    def check_depth(self, depth: int, token: Token) -> None:
        if depth > MAX_SYNTAX_DEPTH:
            self.fail(
                token, "SYN_TOO_COMPLEX",
                f"Syntax nesting exceeds the limit of {MAX_SYNTAX_DEPTH}.",
            )

    def parse_program(self) -> Program:
        location = self.current.location
        statements = []
        while self.current.type != "EOF":
            statements.append(self.parse_statement(0))
        return Program(tuple(statements), location)

    def parse_statement(self, depth: int) -> Statement:
        token = self.current
        if token.type in _TYPES:
            self.advance()
            name = self.expect("IDENT")
            expression = self.parse_initializer(depth)
            return VarDeclaration(
                name.lexeme, _TYPES[token.type], expression, token.location, name.location,
            )
        if token.type == "IDENT":
            self.advance()
            expression = self.parse_initializer(depth)
            return Assignment(token.lexeme, expression, token.location, token.location)
        if token.type in {"KW_MOVER", "KW_GIRAR"}:
            self.advance()
            self.expect("LPAREN")
            expression, _ = self.parse_expression(depth)
            self.expect("RPAREN")
            self.expect("SEMICOLON")
            node = Move if token.type == "KW_MOVER" else Turn
            return node(expression, token.location)
        if token.type == "LBRACE":
            self.check_depth(depth + 1, token)
            self.advance()
            statements = []
            while self.current.type not in {"RBRACE", "EOF"}:
                statements.append(self.parse_statement(depth + 1))
            self.expect("RBRACE")
            return Block(tuple(statements), token.location)
        self.fail(token, "SYN_UNEXPECTED_TOKEN", f"Expected a statement, found {token.lexeme!r}.")

    def parse_initializer(self, depth: int) -> Expression:
        self.expect("ASSIGN")
        expression, _ = self.parse_expression(depth)
        self.expect("SEMICOLON")
        return expression

    def parse_expression(self, depth: int, minimum: int = 1) -> tuple[Expression, int]:
        left, height = self.parse_primary(depth)
        while (precedence := _PRECEDENCE.get(self.current.type, 0)) >= minimum:
            operator = self.advance()
            right, right_height = self.parse_expression(depth, precedence + 1)
            height = 1 + max(height, right_height)
            self.check_depth(depth + height, operator)
            left = BinaryOperation(operator.lexeme, left, right, operator.location)
        return left, height

    def parse_primary(self, depth: int) -> tuple[Expression, int]:
        token = self.current
        if token.type == "MINUS":
            self.check_depth(depth + 1, token)
            self.advance()
            operand, height = self.parse_primary(depth + 1)
            return UnaryOperation(token.lexeme, operand, token.location), height + 1
        if token.type == "LPAREN":
            self.check_depth(depth + 1, token)
            self.advance()
            expression = self.parse_expression(depth + 1)
            self.expect("RPAREN")
            return expression
        if token.type == "INT":
            self.advance()
            return IntLiteral(int(token.lexeme), token.location), 0
        if token.type in _TURNS:
            self.advance()
            return TurnLiteral(_TURNS[token.type], token.location), 0
        if token.type == "IDENT":
            self.advance()
            return VariableReference(token.lexeme, token.location), 0
        found = "end of input" if token.type == "EOF" else repr(token.lexeme)
        self.fail(token, "SYN_UNEXPECTED_TOKEN", f"Expected an expression, found {found}.")
