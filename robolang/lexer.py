"""Turn RoboLang source into tokens with one-based coordinates."""

import re

from .diagnostics import CompileError, Location
from .frontend_limits import MAX_INTEGER_LITERAL_DIGITS
from .tokens import KEYWORDS, PUNCTUATION, Token

_PATTERN = re.compile(
    r"(?P<newline>\r\n|\r|\n)|(?P<comment>//[^\r\n]*)|(?P<space>[ \t\f\v]+)"
    r"|(?P<word>[A-Za-z_][A-Za-z0-9_]*)|(?P<integer>[0-9]+)"
)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    line = column = 1

    while index < len(source):
        match = _PATTERN.match(source, index)
        if match is None:
            character = source[index]
            token_type = PUNCTUATION.get(character)
            if token_type is None:
                raise CompileError(
                    "lexical", "LEX_UNKNOWN_CHAR",
                    f"Unexpected character {character!r}.", Location(line, column),
                )
            tokens.append(Token(token_type, character, line, column))
            index += 1
            column += 1
            continue

        lexeme = match.group()
        index = match.end()
        if match.lastgroup == "newline":
            line += 1
            column = 1
            continue
        if match.lastgroup == "word":
            tokens.append(Token(KEYWORDS.get(lexeme, "IDENT"), lexeme, line, column))
        elif match.lastgroup == "integer":
            if len(lexeme) > MAX_INTEGER_LITERAL_DIGITS:
                raise CompileError(
                    "lexical", "LEX_INTEGER_TOO_LONG",
                    f"Integer literals may contain at most {MAX_INTEGER_LITERAL_DIGITS} digits.",
                    Location(line, column),
                )
            tokens.append(Token("INT", lexeme, line, column))
        column += len(lexeme)

    tokens.append(Token("EOF", "", line, column))
    return tokens
