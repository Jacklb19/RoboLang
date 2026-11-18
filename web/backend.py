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
class WorldConfig:
    """What the interface needs to draw the grid before any execution."""

    max_source_chars: int
    grid_width: int
    grid_height: int
    start_x: int
    start_y: int
    start_orientation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_source_chars": self.max_source_chars,
            "grid": {"width": self.grid_width, "height": self.grid_height},
            "start": {"x": self.start_x, "y": self.start_y, "orientation": self.start_orientation},
        }


@dataclass(frozen=True, slots=True)
class Backend:
    compile_source: Callable[..., CompiledProgram]
    execute: Callable[[list[Any]], ExecutedProgram]
    world: WorldConfig


def load_backend() -> Backend:
    """Return the backend built from the real RoboLang compiler and VM."""
    from robolang import settings
    from robolang.compiler import compile_source
    from robolang.vm import execute

    world = WorldConfig(
        max_source_chars=settings.MAX_SOURCE_CHARS,
        grid_width=settings.GRID_WIDTH,
        grid_height=settings.GRID_HEIGHT,
        start_x=settings.START_X,
        start_y=settings.START_Y,
        start_orientation=settings.START_ORIENTATION,
    )
    return Backend(compile_source=compile_source, execute=execute, world=world)
