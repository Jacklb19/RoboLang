"""Compile a RoboLang file and run it on the VM, without the web interface."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from robolang.compiler import CompilationResult, compile_source  # noqa: E402
from robolang.diagnostics import Diagnostic  # noqa: E402
from robolang.vm import ExecutionResult, execute  # noqa: E402

DEFAULT_EXAMPLE = ROOT / "examples" / "08_integral.rbl"
EXIT_OK = 0
EXIT_PROGRAM_FAILED = 1
EXIT_USAGE = 2


def parse_arguments(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compila y ejecuta un programa RoboLang.")
    parser.add_argument(
        "file", nargs="?", type=Path, default=DEFAULT_EXAMPLE,
        help="archivo .rbl (por defecto, el ejemplo integral)",
    )
    parser.add_argument("--no-optimize", action="store_true", help="desactiva el plegado")
    parser.add_argument("--json", action="store_true", help="imprime el resultado serializado")
    return parser.parse_args(arguments)


def print_section(title: str, lines: list[str]) -> None:
    print(f"\n== {title} ==")
    for line in lines or ["(vacío)"]:
        print(line)


def format_diagnostic(diagnostic: Diagnostic) -> str:
    return (
        f"{diagnostic.phase} [{diagnostic.code}] "
        f"línea {diagnostic.line}, columna {diagnostic.column}: {diagnostic.message}"
    )


def print_compilation(compiled: CompilationResult) -> None:
    print_section("Tokens", [f"{len(compiled.tokens)} tokens"])
    print_section(
        "Símbolos",
        [f"{s.slot}: {s.type} {s.name} ({s.scope_id})" for s in compiled.symbols],
    )
    data = compiled.to_dict()
    print_section("TAC original", data["tac_before"])
    print_section("TAC final", data["tac_after"])
    print_section("Ensamblador", [f"{pc:>3}  {text}" for pc, text in enumerate(compiled.assembly)])


def print_execution(execution: ExecutionResult) -> None:
    print_section(
        "Ejecución",
        [
            f"PC {event.pc:>3} | línea {event.source_line}, columna {event.source_column} | "
            f"{event.action:<9} -> ({event.x},{event.y}) {event.orientation}"
            for event in execution.events
        ],
    )
    final = execution.final
    print(f"\nEstado final: ({final.x},{final.y}) {final.orientation}")


def main(arguments: list[str] | None = None) -> int:
    options = parse_arguments(arguments)
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        source = options.file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        print(f"No se pudo leer {options.file}: {error}", file=sys.stderr)
        return EXIT_USAGE

    compiled = compile_source(source, optimize=not options.no_optimize)
    execution = execute(compiled.instructions) if compiled.ok else None
    succeeded = execution is not None and execution.ok

    if options.json:
        payload = {
            **compiled.to_dict(),
            "execution": None if execution is None else execution.to_dict(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK if succeeded else EXIT_PROGRAM_FAILED

    print_compilation(compiled)
    if execution is None:
        print("\nNo se generó código objetivo. No se ejecutó el robot.")
    else:
        print_execution(execution)
    diagnostics = compiled.diagnostics + (execution.diagnostics if execution else [])
    print_section("Diagnósticos", [format_diagnostic(item) for item in diagnostics])
    return EXIT_OK if succeeded else EXIT_PROGRAM_FAILED


if __name__ == "__main__":
    sys.exit(main())
