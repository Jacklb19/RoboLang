"""Source locations and expected compiler errors."""

from dataclasses import dataclass
from typing import Literal

Phase = Literal["lexical", "syntax", "semantic", "runtime"]


@dataclass(frozen=True, slots=True)
class Location:
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class Diagnostic:
    phase: Phase
    code: str
    message: str
    line: int
    column: int


class CompileError(Exception):
    """Stop compilation at the first source error."""

    def __init__(self, phase: Phase, code: str, message: str, location: Location):
        self.diagnostic = Diagnostic(
            phase, code, message, location.line, location.column
        )
        super().__init__(message)
