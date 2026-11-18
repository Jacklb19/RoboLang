"""Token names shared by the lexer and parser."""

from dataclasses import dataclass

from .diagnostics import Location

KEYWORDS = {
    "entero": "KW_ENTERO",
    "giro": "KW_GIRO",
    "mover": "KW_MOVER",
    "girar": "KW_GIRAR",
    "derecha": "KW_DERECHA",
    "izquierda": "KW_IZQUIERDA",
}

PUNCTUATION = {
    "=": "ASSIGN",
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    "(": "LPAREN",
    ")": "RPAREN",
    "{": "LBRACE",
    "}": "RBRACE",
    ";": "SEMICOLON",
}


@dataclass(frozen=True, slots=True)
class Token:
    type: str
    lexeme: str
    line: int
    column: int

    @property
    def location(self) -> Location:
        return Location(self.line, self.column)
