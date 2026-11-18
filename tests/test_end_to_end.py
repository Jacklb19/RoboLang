"""End-to-end tests through the real compiler pipeline and VM."""

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from robolang.compiler import compile_source
from robolang.frontend_limits import MAX_INTEGER_LITERAL_DIGITS, MAX_SYNTAX_DEPTH
from robolang.settings import MAX_ROBOT_STEPS, MAX_SOURCE_CHARS
from robolang.tac import ImmInt
from robolang.vm import RobotConfig, execute

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SAMPLES = ROOT / "docs" / "muestras"
INTEGRAL = (EXAMPLES / "08_integral.rbl").read_text(encoding="utf-8")
HUGE = "9" * MAX_INTEGER_LITERAL_DIGITS


def run(source, *, optimize=True, config=None):
    compiled = compile_source(source, optimize=optimize)
    assert compiled.ok, compiled.diagnostics
    return execute(compiled.instructions, config)


def position(result):
    return result.final.x, result.final.y, result.final.orientation


def observable(result):
    """Everything the user can observe; only the PC may differ between modes."""
    events = [
        (e.source_line, e.source_column, e.action, e.x, e.y, e.orientation)
        for e in result.events
    ]
    return result.ok, result.start, result.final, events, result.diagnostics


def run_code(result):
    [diagnostic] = result.diagnostics
    assert diagnostic.phase == "runtime"
    return diagnostic.code


@pytest.mark.parametrize("optimize", [True, False])
def test_v03_integral_example_reaches_final_state(optimize):
    result = run(INTEGRAL, optimize=optimize)
    assert result.ok
    assert position(result) == (3, 1, "ESTE")
    actions = [event.action for event in result.events]
    assert actions.count("move-step") == 5
    assert actions.count("turn") == 1


def test_integral_views_match_the_guide():
    compiled = compile_source(INTEGRAL)
    data = compiled.to_dict()
    assert data["tac_before"][:2] == ["T0 = 2 + 1", "S0 = T0"]
    assert data["tac_after"] == [
        "T0 = 3", "S0 = T0", "S1 = RIGHT", "MOVE S0", "TURN S1", "S2 = 2", "MOVE S2",
    ]
    assert data["assembly"] == [
        "LOADC R0, 3", "STORE T0, R0", "LOAD R0, T0", "STORE S0, R0",
        "LOADC R0, RIGHT", "STORE S1, R0", "LOAD R0, S0", "MOVE R0",
        "LOAD R0, S1", "TURN R0", "LOADC R0, 2", "STORE S2, R0",
        "LOAD R0, S2", "MOVE R0", "HALT",
    ]


def test_without_optimization_tac_after_is_unchanged():
    data = compile_source(INTEGRAL, optimize=False).to_dict()
    assert data["tac_after"] == data["tac_before"]
    assert data["assembly"][:4] == ["LOADC R0, 2", "LOADC R1, 1", "ADD R0, R1", "STORE T0, R0"]


@pytest.mark.parametrize("optimize", [True, False])
def test_v04_out_of_bounds_keeps_four_valid_steps(optimize):
    result = run("mover(20);", optimize=optimize)
    assert not result.ok and run_code(result) == "RUN_OUT_OF_BOUNDS"
    assert [(e.x, e.y) for e in result.events] == [(1, 3), (1, 2), (1, 1), (1, 0)]
    assert position(result) == (1, 0, "NORTE")
    assert (result.diagnostics[0].line, result.diagnostics[0].column) == (1, 1)


def test_v01_simple_move():
    assert position(run("mover(3);")) == (1, 1, "NORTE")


def test_v02_turn_then_move():
    assert position(run("girar(derecha); mover(2);")) == (3, 4, "ESTE")


def test_left_turn_program():
    assert position(run("girar(izquierda); mover(1);")) == (0, 4, "OESTE")


@pytest.mark.parametrize("source", ["mover(-1);", "entero x=1; mover(0-x);", "mover(2-3);"])
def test_v05_negative_move_fails_without_steps(source):
    result = run(source)
    assert run_code(result) == "RUN_NEGATIVE_STEPS" and result.events == []


@pytest.mark.parametrize("source", ["mover(0);", "mover(2-2);", "mover(0*9);", "mover(-0);"])
def test_zero_move_succeeds_without_steps(source):
    result = run(source)
    assert result.ok and result.events == []


@pytest.mark.parametrize("source", ["", "   \n// solo comentario\n", "{ }"])
def test_v06_empty_program_only_halts(source):
    compiled = compile_source(source)
    assert compiled.assembly == ["HALT"]
    result = execute(compiled.instructions)
    assert result.ok and result.events == [] and result.final == result.start


@pytest.mark.parametrize(
    ("source", "phase", "code"),
    [
        ("mover(@);", "lexical", "LEX_UNKNOWN_CHAR"),
        ("mover(3;", "syntax", "SYN_EXPECTED_TOKEN"),
        ("mover(derecha);", "semantic", "SEM_TYPE_MISMATCH"),
        ("mover(x);", "semantic", "SEM_UNDECLARED"),
    ],
)
def test_v07_failed_phase_produces_nothing_to_execute(source, phase, code):
    compiled = compile_source(source)
    assert not compiled.ok
    assert compiled.instructions == [] and compiled.assembly == []
    assert compiled.tac_before == [] and compiled.tac_after == []
    [diagnostic] = compiled.diagnostics
    assert (diagnostic.phase, diagnostic.code) == (phase, code)


def test_reached_phases_are_kept_when_a_later_one_fails():
    lexical = compile_source("mover(@);").to_dict()
    assert lexical["tokens"] == [] and lexical["ast"] is None
    syntax = compile_source("mover(3;").to_dict()
    assert syntax["tokens"] and syntax["ast"] is None
    semantic = compile_source("mover(derecha);").to_dict()
    assert semantic["ast"]["node"] == "Program" and semantic["symbols"] == []


def test_v08_repeated_runs_are_identical():
    assert compile_source(INTEGRAL) == compile_source(INTEGRAL)
    assert run(INTEGRAL) == run(INTEGRAL)


EQUIVALENCE_PROGRAMS = [
    *(path.read_text(encoding="utf-8") for path in sorted(EXAMPLES.glob("0[1-3,7-8]_*.rbl"))),
    "",
    "mover(2+1); girar(izquierda); mover(1*1);",
    "mover((2+3)*4-19);",
    "entero x=2*2-3; { entero x=x+1; mover(x); } mover(x);",
    "mover(-1);",
    "mover(1-2);",
    "mover(1); mover(5*5);",
    "giro g=derecha; { g=izquierda; } girar(g); mover(0*7); mover(9-1);",
    f"mover(1); mover({HUGE}*{HUGE}); mover(1);",
    f"entero x={HUGE}; x=x*x; mover(1);",
]


@pytest.mark.parametrize("source", EQUIVALENCE_PROGRAMS)
def test_i06_optimization_preserves_observable_behavior(source):
    assert observable(run(source, optimize=True)) == observable(run(source, optimize=False))


def test_optimization_actually_changes_the_generated_code():
    folded = compile_source("mover(2+1);", optimize=True)
    plain = compile_source("mover(2+1);", optimize=False)
    assert len(folded.instructions) < len(plain.instructions)


def test_instruction_budget_counts_effective_instructions_in_each_mode():
    folded = compile_source("mover(2+1);", optimize=True).instructions
    plain = compile_source("mover(2+1);", optimize=False).instructions
    config = RobotConfig(max_instructions=len(folded))
    assert execute(folded, config).ok
    assert run_code(execute(plain, config)) == "RUN_LIMIT_EXCEEDED"


@pytest.mark.parametrize("optimize", [True, False])
def test_default_instruction_budget_stops_long_programs(optimize):
    source = "entero a=1;" + "a=-1;" * ((MAX_SOURCE_CHARS - 11) // 5)
    assert len(source) <= MAX_SOURCE_CHARS
    assert run_code(run(source, optimize=optimize)) == "RUN_LIMIT_EXCEEDED"


def test_default_step_budget_keeps_valid_steps():
    round_trip = "mover(3);girar(derecha);girar(derecha);"
    source = round_trip * (MAX_ROBOT_STEPS // 3 + 1)
    result = run(source)
    assert run_code(result) == "RUN_LIMIT_EXCEEDED"
    steps = [event for event in result.events if event.action == "move-step"]
    assert len(steps) == MAX_ROBOT_STEPS


@pytest.mark.parametrize("optimize", [True, False])
def test_integer_budget_reports_the_operator_in_both_modes(optimize):
    source = f"mover(1);\nentero x = {HUGE} * {HUGE};"
    result = run(source, optimize=optimize)
    assert run_code(result) == "RUN_LIMIT_EXCEEDED"
    assert len(result.events) == 1
    diagnostic = result.diagnostics[0]
    assert (diagnostic.line, diagnostic.column) == (2, source.splitlines()[1].index("*") + 1)


def test_source_limit_is_inclusive():
    assert compile_source(" " * MAX_SOURCE_CHARS).ok
    compiled = compile_source(" " * (MAX_SOURCE_CHARS + 1))
    [diagnostic] = compiled.diagnostics
    assert (diagnostic.phase, diagnostic.code) == ("lexical", "LEX_SOURCE_TOO_LONG")
    assert (diagnostic.line, diagnostic.column) == (1, 1)
    assert compiled.tokens == [] and compiled.instructions == []


def test_deepest_accepted_expression_compiles_serializes_and_runs():
    source = f"mover({'-' * MAX_SYNTAX_DEPTH}1);"
    compiled = compile_source(source)
    assert compiled.ok
    json.dumps(compiled.to_dict())
    assert execute(compiled.instructions).ok != (MAX_SYNTAX_DEPTH % 2 == 1)


def test_expression_beyond_the_shared_depth_is_a_diagnostic():
    compiled = compile_source(f"mover({'-' * (MAX_SYNTAX_DEPTH + 1)}1);")
    assert compiled.diagnostics[0].code == "SYN_TOO_COMPLEX"


@pytest.mark.parametrize(("source", "optimize"), [(1, True), ("", 1), ("", None)])
def test_invalid_argument_types_are_rejected(source, optimize):
    with pytest.raises(TypeError):
        compile_source(source, optimize=optimize)


def test_shown_assembly_is_the_code_the_vm_consumed():
    compiled = compile_source(INTEGRAL)
    result = execute(compiled.instructions)
    expected = {"move-step": "MOVE R0", "turn": "TURN R0"}
    assert [compiled.assembly[event.pc] for event in result.events] == [
        expected[event.action] for event in result.events
    ]


def test_robot_follows_generated_instructions_not_the_source():
    compiled = compile_source("mover(3);")
    load, *rest = compiled.instructions
    patched = [replace(load, args=(load.args[0], ImmInt(1))), *rest]
    assert position(execute(patched)) == (1, 3, "NORTE")


def test_compilation_serializes_with_the_agreed_shape():
    data = json.loads(json.dumps(compile_source(INTEGRAL).to_dict()))
    assert list(data) == [
        "ok", "tokens", "ast", "symbols", "tac_before", "tac_after", "assembly", "diagnostics",
    ]
    assert "instructions" not in data
    assert data["tokens"][0] == {"type": "KW_ENTERO", "lexeme": "entero", "line": 1, "column": 1}
    assert data["symbols"][2] == {
        "name": "pasos", "type": "entero", "scope_id": "bloque_1", "slot": "S2",
        "decl_line": 6, "decl_col": 12,
    }
    declaration = data["ast"]["statements"][0]
    assert declaration["node"] == "VarDeclaration"
    assert declaration["resolved_slot"] == "S0"
    assert declaration["expression"]["node"] == "BinaryOperation"
    assert declaration["location"] == {"line": 1, "column": 1}


def demo(*arguments):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "demo_cli.py"), *arguments],
        capture_output=True, encoding="utf-8", check=False,
    )


def test_cli_runs_the_integral_example_by_default():
    completed = demo()
    assert completed.returncode == 0, completed.stderr
    assert "Estado final: (3,1) ESTE" in completed.stdout
    assert "LOADC R0, 3" in completed.stdout


def test_cli_without_optimization_shows_the_operation():
    completed = demo("--no-optimize")
    assert completed.returncode == 0
    assert "ADD R0, R1" in completed.stdout


@pytest.mark.parametrize(
    ("example", "code"),
    [
        ("04_error_lexico.rbl", "LEX_UNKNOWN_CHAR"),
        ("05_error_sintaxis.rbl", "SYN_EXPECTED_TOKEN"),
        ("06_error_semantico.rbl", "SEM_TYPE_MISMATCH"),
        ("07_error_runtime.rbl", "RUN_OUT_OF_BOUNDS"),
    ],
)
def test_cli_reports_each_failure_class(example, code):
    completed = demo(str(EXAMPLES / example))
    assert completed.returncode == 1
    assert code in completed.stdout


def test_cli_reports_unreadable_files():
    completed = demo(str(EXAMPLES / "no_existe.rbl"))
    assert completed.returncode == 2
    assert "No se pudo leer" in completed.stderr


@pytest.mark.parametrize(
    ("sample", "example"),
    [
        ("integral.json", "08_integral.rbl"),
        ("error_semantico.json", "06_error_semantico.rbl"),
        ("error_runtime.json", "07_error_runtime.rbl"),
    ],
)
def test_published_samples_match_real_output(sample, example):
    completed = demo("--json", str(EXAMPLES / example))
    assert json.loads(completed.stdout) == json.loads(
        (SAMPLES / sample).read_text(encoding="utf-8")
    )
