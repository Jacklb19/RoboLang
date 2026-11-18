"""Run every compilation phase and expose results for the CLI and the API."""

from dataclasses import asdict, dataclass, field, fields, is_dataclass

from .ast_nodes import Program
from .codegen import Instruction, format_instruction, generate_vm_code
from .diagnostics import CompileError, Diagnostic, Location
from .lexer import tokenize
from .optimizer import optimize as fold_constants
from .parser import parse
from .semantic import analyze
from .settings import MAX_SOURCE_CHARS
from .symbols import Symbol
from .tac import Quad, format_quad, generate_tac
from .tokens import Token


@dataclass(frozen=True, slots=True)
class CompilationResult:
    ok: bool
    tokens: list[Token] = field(default_factory=list)
    ast: Program | None = None
    symbols: list[Symbol] = field(default_factory=list)
    tac_before: list[Quad] = field(default_factory=list)
    tac_after: list[Quad] = field(default_factory=list)
    instructions: list[Instruction] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def assembly(self) -> list[str]:
        """Text view derived from the instructions the VM receives."""
        return [format_instruction(instruction) for instruction in self.instructions]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "tokens": [asdict(token) for token in self.tokens],
            "ast": None if self.ast is None else _serialize_node(self.ast),
            "symbols": [asdict(symbol) for symbol in self.symbols],
            "tac_before": [format_quad(quad) for quad in self.tac_before],
            "tac_after": [format_quad(quad) for quad in self.tac_after],
            "assembly": self.assembly,
            "diagnostics": [asdict(diagnostic) for diagnostic in self.diagnostics],
        }


def compile_source(source: str, *, optimize: bool = True) -> CompilationResult:
    """Compile source text, stopping at the first diagnostic."""
    if not isinstance(source, str):
        raise TypeError("source must be a string.")
    if not isinstance(optimize, bool):
        raise TypeError("optimize must be a boolean.")

    tokens: list[Token] = []
    ast: Program | None = None
    try:
        _check_source_size(source)
        tokens = tokenize(source)
        ast = parse(tokens)
        semantic = analyze(ast)
    except CompileError as error:
        return CompilationResult(False, tokens, ast, diagnostics=[error.diagnostic])

    tac_before = generate_tac(semantic)
    tac_after = fold_constants(tac_before) if optimize else list(tac_before)
    instructions = generate_vm_code(tac_after, eof_location=tokens[-1].location)
    return CompilationResult(
        True, tokens, semantic.program, semantic.symbols, tac_before, tac_after, instructions,
    )


def _check_source_size(source: str) -> None:
    if len(source) > MAX_SOURCE_CHARS:
        raise CompileError(
            "lexical", "LEX_SOURCE_TOO_LONG",
            f"Source code may contain at most {MAX_SOURCE_CHARS} characters.",
            Location(1, 1),
        )


def _serialize_node(value: object) -> object:
    if isinstance(value, Location):
        return {"line": value.line, "column": value.column}
    if isinstance(value, tuple):
        return [_serialize_node(item) for item in value]
    if is_dataclass(value):
        members = {item.name: _serialize_node(getattr(value, item.name)) for item in fields(value)}
        return {"node": type(value).__name__, **members}
    return value
