"""Track active lexical scopes and retain declarations in source order."""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from .ast_nodes import ValueType
from .diagnostics import Location


@dataclass(frozen=True, slots=True)
class Symbol:
    name: str
    type: ValueType
    scope_id: str
    slot: str
    decl_line: int
    decl_col: int


class SymbolTable:
    def __init__(self) -> None:
        self.declarations: list[Symbol] = []
        self._scopes: list[dict[str, Symbol]] = [{}]
        self._scope_ids = ["global"]
        self._next_block = 1

    @contextmanager
    def block(self) -> Iterator[None]:
        self._scopes.append({})
        self._scope_ids.append(f"bloque_{self._next_block}")
        self._next_block += 1
        try:
            yield
        finally:
            self._scope_ids.pop()
            self._scopes.pop()

    def contains_current(self, name: str) -> bool:
        return name in self._scopes[-1]

    def lookup(self, name: str) -> Symbol | None:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def declare(self, name: str, value_type: ValueType, location: Location) -> Symbol:
        symbol = Symbol(
            name, value_type, self._scope_ids[-1], f"S{len(self.declarations)}",
            location.line, location.column,
        )
        self._scopes[-1][name] = symbol
        self.declarations.append(symbol)
        return symbol
