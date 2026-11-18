"""Connection between the API and the compiler/VM.

The API depends only on `Backend`, so tests can provide fixture results and
the application uses the real compiler. Imports are lazy: the web package can
be imported even before the compiler modules exist in a checkout.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


class CompiledProgram(Protocol):
    ok: bool
    instructions: list[Any]

    def to_dict(self) -> dict[str, Any]: ...


class ExecutedProgram(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class Backend:
    compile_source: Callable[..., CompiledProgram]
    execute: Callable[[list[Any]], ExecutedProgram]
    max_source_chars: int


def load_backend() -> Backend:
    """Return the backend built from the real RoboLang compiler and VM."""
    from robolang.compiler import compile_source
    from robolang.settings import MAX_SOURCE_CHARS
    from robolang.vm import execute

    return Backend(compile_source=compile_source, execute=execute, max_source_chars=MAX_SOURCE_CHARS)
