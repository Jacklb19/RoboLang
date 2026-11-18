"""API tests with fixture results from the compiler and VM.

`fixtures/api/*.json` are real outputs copied from `docs/muestras/` on
Steven's branch (`scripts/demo_cli.py --json`). The lexical and syntax results
below are written by hand following the shared contract. The fake backend lets
these tests check routing, status codes and validation without the compiler.
"""

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from web.app import create_app
from web.backend import Backend

FIXTURES = Path(__file__).parent / "fixtures" / "api"
MAX_SOURCE_CHARS = 4_000

INTEGRAL_SOURCE = (
    "entero pasos = 2 + 1;\ngiro lado = derecha;\nmover(pasos);\ngirar(lado);\n"
    "{\n    entero pasos = 2;\n    mover(pasos);\n}\n"
)
SEMANTIC_SOURCE = "giro lado = derecha;\nmover(lado);"
RUNTIME_SOURCE = "mover(20);"
LEXICAL_SOURCE = "mover(@);"
SYNTAX_SOURCE = "mover(3;"

COMPILE_KEYS = {"ok", "tokens", "ast", "symbols", "tac_before", "tac_after", "assembly", "diagnostics"}


def load_sample(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def compile_failure(tokens: list[dict[str, Any]], diagnostic: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False, "tokens": tokens, "ast": None, "symbols": [],
        "tac_before": [], "tac_after": [], "assembly": [], "diagnostics": [diagnostic],
    }


def token(type_: str, lexeme: str, column: int) -> dict[str, Any]:
    return {"type": type_, "lexeme": lexeme, "line": 1, "column": column}


LEXICAL_RESULT = compile_failure(
    [], {"phase": "lexical", "code": "LEX_UNKNOWN_CHAR", "message": "Unknown character '@'.", "line": 1, "column": 7},
)
SYNTAX_RESULT = compile_failure(
    [token("KW_MOVER", "mover", 1), token("LPAREN", "(", 6), token("INT", "3", 7),
     token("SEMICOLON", ";", 8), token("EOF", "", 9)],
    {"phase": "syntax", "code": "SYN_EXPECTED_TOKEN", "message": "Expected ')'.", "line": 1, "column": 8},
)


@dataclass
class FakeCompiled:
    data: dict[str, Any]
    execution: dict[str, Any] | None
    instructions: list[Any] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.data["ok"]

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.data)


@dataclass
class FakeExecuted:
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self.data)


class FakeBackend:
    """Return fixture results and record how the API calls the backend."""

    def __init__(self) -> None:
        self.programs: dict[str, dict[str, Any]] = {}
        self.compile_calls: list[tuple[str, bool]] = []
        self.executed: list[list[Any]] = []
        for source, name in ((INTEGRAL_SOURCE, "integral"), (SEMANTIC_SOURCE, "error_semantico"),
                             (RUNTIME_SOURCE, "error_runtime")):
            self.programs[source] = load_sample(name)
        self.programs[LEXICAL_SOURCE] = {**LEXICAL_RESULT, "execution": None}
        self.programs[SYNTAX_SOURCE] = {**SYNTAX_RESULT, "execution": None}

    def compile_source(self, source: str, *, optimize: bool = True) -> FakeCompiled:
        self.compile_calls.append((source, optimize))
        sample = copy.deepcopy(self.programs[source])
        execution = sample.pop("execution")
        if not optimize:
            sample["tac_after"] = list(sample["tac_before"])
        instructions = [f"instruction-for:{source}"] if sample["ok"] else []
        return FakeCompiled(sample, execution, instructions)

    def execute(self, instructions: list[Any]) -> FakeExecuted:
        self.executed.append(instructions)
        source = instructions[0].removeprefix("instruction-for:")
        return FakeExecuted(self.programs[source]["execution"])

    def as_backend(self) -> Backend:
        return Backend(self.compile_source, self.execute, MAX_SOURCE_CHARS)


@pytest.fixture
def fake() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def client(fake: FakeBackend) -> TestClient:
    return TestClient(create_app(fake.as_backend))


# --- /api/compile -------------------------------------------------------------------------------


def test_compile_success_returns_every_phase(client: TestClient, fake: FakeBackend) -> None:
    response = client.post("/api/compile", json={"source": INTEGRAL_SOURCE})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == COMPILE_KEYS
    assert body["ok"] is True
    assert body["diagnostics"] == []
    assert body["ast"]["node"] == "Program"
    assert body["tac_before"] != body["tac_after"]
    assert body["assembly"][-1] == "HALT"
    assert fake.compile_calls == [(INTEGRAL_SOURCE, True)]
    assert fake.executed == []


def test_compile_does_not_send_instructions_to_the_browser(client: TestClient) -> None:
    body = client.post("/api/compile", json={"source": INTEGRAL_SOURCE}).json()

    assert "instructions" not in body
    assert "execution" not in body


def test_compile_without_optimization_keeps_tac(client: TestClient, fake: FakeBackend) -> None:
    body = client.post("/api/compile", json={"source": INTEGRAL_SOURCE, "optimize": False}).json()

    assert fake.compile_calls == [(INTEGRAL_SOURCE, False)]
    assert body["ok"] is True
    assert body["tac_after"] == body["tac_before"]


@pytest.mark.parametrize(
    ("source", "phase", "code"),
    [
        (LEXICAL_SOURCE, "lexical", "LEX_UNKNOWN_CHAR"),
        (SYNTAX_SOURCE, "syntax", "SYN_EXPECTED_TOKEN"),
        (SEMANTIC_SOURCE, "semantic", "SEM_TYPE_MISMATCH"),
    ],
)
def test_compile_errors_are_program_results(client: TestClient, source: str, phase: str, code: str) -> None:
    response = client.post("/api/compile", json={"source": source})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert [(d["phase"], d["code"]) for d in body["diagnostics"]] == [(phase, code)]
    assert body["tac_before"] == body["tac_after"] == body["assembly"] == []


# --- /api/run -----------------------------------------------------------------------------------


def test_run_success_reaches_final_position(client: TestClient, fake: FakeBackend) -> None:
    response = client.post("/api/run", json={"source": INTEGRAL_SOURCE, "optimize": True})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == COMPILE_KEYS | {"execution"}
    assert body["ok"] is True
    execution = body["execution"]
    assert execution["ok"] is True
    assert execution["start"] == {"x": 1, "y": 4, "orientation": "NORTE"}
    assert execution["final"] == {"x": 3, "y": 1, "orientation": "ESTE"}
    assert {event["action"] for event in execution["events"]} == {"move-step", "turn"}
    assert fake.compile_calls == [(INTEGRAL_SOURCE, True)]
    assert fake.executed == [[f"instruction-for:{INTEGRAL_SOURCE}"]]


def test_run_executes_only_server_compiled_instructions(client: TestClient, fake: FakeBackend) -> None:
    response = client.post("/api/run", json={"source": INTEGRAL_SOURCE, "instructions": ["MOVE R0"]})

    assert response.status_code == 422
    assert fake.compile_calls == []
    assert fake.executed == []


def test_run_without_optimization_recompiles_with_same_option(client: TestClient, fake: FakeBackend) -> None:
    body = client.post("/api/run", json={"source": INTEGRAL_SOURCE, "optimize": False}).json()

    assert fake.compile_calls == [(INTEGRAL_SOURCE, False)]
    assert body["tac_after"] == body["tac_before"]
    assert body["execution"]["ok"] is True


def test_run_runtime_error_keeps_partial_trace(client: TestClient) -> None:
    response = client.post("/api/run", json={"source": RUNTIME_SOURCE})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    execution = body["execution"]
    assert execution["ok"] is False
    assert len(execution["events"]) == 4
    assert execution["final"] == {"x": 1, "y": 0, "orientation": "NORTE"}
    assert [(d["phase"], d["code"]) for d in execution["diagnostics"]] == [("runtime", "RUN_OUT_OF_BOUNDS")]


@pytest.mark.parametrize("source", [LEXICAL_SOURCE, SYNTAX_SOURCE, SEMANTIC_SOURCE])
def test_run_does_not_execute_after_compile_error(client: TestClient, fake: FakeBackend, source: str) -> None:
    response = client.post("/api/run", json={"source": source})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["execution"] is None
    assert fake.executed == []


# --- Request validation -------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ["/api/compile", "/api/run"])
@pytest.mark.parametrize(
    ("payload", "field", "error_type"),
    [
        ({}, "source", "missing"),
        ({"source": 42}, "source", "string_type"),
        ({"source": None}, "source", "string_type"),
        ({"source": "mover(1);", "optimize": "true"}, "optimize", "bool_type"),
        ({"source": "mover(1);", "optimize": 1}, "optimize", "bool_type"),
        ({"source": "mover(1);", "extra": True}, "extra", "extra_forbidden"),
    ],
)
def test_invalid_payload_returns_422(
    client: TestClient, fake: FakeBackend, endpoint: str, payload: dict[str, Any], field: str, error_type: str,
) -> None:
    response = client.post(endpoint, json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["message"] == "Solicitud inválida."
    assert {"field": field, "type": error_type} in [
        {"field": error["field"], "type": error["type"]} for error in body["errors"]
    ]
    assert fake.compile_calls == []


@pytest.mark.parametrize("endpoint", ["/api/compile", "/api/run"])
@pytest.mark.parametrize("content", ["[1, 2]", "no es json"])
def test_non_object_body_returns_422(client: TestClient, fake: FakeBackend, endpoint: str, content: str) -> None:
    response = client.post(endpoint, content=content, headers={"Content-Type": "application/json"})

    assert response.status_code == 422
    assert fake.compile_calls == []


@pytest.mark.parametrize("endpoint", ["/api/compile", "/api/run"])
def test_source_over_limit_returns_422(client: TestClient, fake: FakeBackend, endpoint: str) -> None:
    response = client.post(endpoint, json={"source": "x" * (MAX_SOURCE_CHARS + 1)})

    assert response.status_code == 422
    assert response.json()["errors"] == [{
        "field": "source", "type": "source_too_long",
        "message": f"El código fuente admite como máximo {MAX_SOURCE_CHARS} caracteres.",
    }]
    assert fake.compile_calls == []


def test_source_at_limit_is_accepted(fake: FakeBackend) -> None:
    source = "x" * MAX_SOURCE_CHARS
    fake.programs[source] = {**LEXICAL_RESULT, "execution": None}
    client = TestClient(create_app(fake.as_backend))

    assert client.post("/api/compile", json={"source": source}).status_code == 200


# --- Internal failures --------------------------------------------------------------------------


def broken(*_: Any, **__: Any) -> Any:
    raise RuntimeError("secret internal detail")


@pytest.mark.parametrize(
    ("endpoint", "backend"),
    [
        ("/api/compile", Backend(broken, broken, MAX_SOURCE_CHARS)),
        ("/api/run", Backend(FakeBackend().compile_source, broken, MAX_SOURCE_CHARS)),
    ],
)
def test_internal_failure_returns_generic_500(endpoint: str, backend: Backend) -> None:
    client = TestClient(create_app(lambda: backend), raise_server_exceptions=False)

    response = client.post(endpoint, json={"source": INTEGRAL_SOURCE})

    assert response.status_code == 500
    assert response.json() == {"message": "Error interno del servidor. Inténtalo de nuevo."}
    assert "secret" not in response.text


def test_missing_backend_returns_generic_500() -> None:
    def unavailable() -> Backend:
        raise ImportError("No module named 'robolang.compiler'")

    client = TestClient(create_app(unavailable), raise_server_exceptions=False)

    response = client.post("/api/compile", json={"source": INTEGRAL_SOURCE})

    assert response.status_code == 500
    assert "robolang" not in response.text
