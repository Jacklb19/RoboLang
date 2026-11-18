"""Codegen and VM tests built from hand-written quadruples and instructions (fixtures)."""

import pytest

from robolang.codegen import (
    R0,
    R1,
    Instruction,
    Register,
    format_instruction,
    generate_vm_code,
)
from robolang.diagnostics import Location
from robolang.settings import MAX_INTEGER_BITS
from robolang.tac import ImmInt, ImmTurn, Quad, Slot, Temp
from robolang.vm import RobotConfig, RobotState, execute

HERE = Location(2, 5)
EOF = Location(9, 1)
S0 = Slot("S0")
T0 = Temp("T0")
TOO_LARGE = 1 << MAX_INTEGER_BITS


def assembly(tac):
    return [format_instruction(i) for i in generate_vm_code(tac, eof_location=EOF)]


def ins(opcode, *args):
    return Instruction(opcode, args, HERE)


def program(*instructions):
    return [*instructions, Instruction("HALT", (), EOF)]


def move(steps):
    return [ins("LOADC", R0, ImmInt(steps)), ins("MOVE", R0)]


def turn(direction):
    return [ins("LOADC", R0, ImmTurn(direction)), ins("TURN", R0)]


def position(result):
    state = result.final
    return state.x, state.y, state.orientation


def failure(result):
    assert not result.ok
    [diagnostic] = result.diagnostics
    assert diagnostic.phase == "runtime"
    return diagnostic


@pytest.mark.parametrize("op", ["ADD", "SUB", "MUL"])
def test_i04_binary_operation_uses_both_registers_and_temporary(op):
    tac = [Quad(op, S0, ImmInt(2), T0, HERE)]
    assert assembly(tac) == ["LOAD R0, S0", "LOADC R1, 2", f"{op} R0, R1", "STORE T0, R0", "HALT"]


def test_negation_translation():
    assert assembly([Quad("NEG", S0, None, T0, HERE)]) == [
        "LOAD R0, S0", "NEG R0", "STORE T0, R0", "HALT",
    ]


def test_copy_accepts_slot_and_temporary_destinations():
    tac = [Quad("COPY", ImmInt(3), None, T0, HERE), Quad("COPY", T0, None, S0, HERE)]
    assert assembly(tac) == ["LOADC R0, 3", "STORE T0, R0", "LOAD R0, T0", "STORE S0, R0", "HALT"]


def test_i05_move_loads_the_slot():
    assert assembly([Quad("MOVE", S0, None, None, HERE)]) == ["LOAD R0, S0", "MOVE R0", "HALT"]


def test_turn_loads_a_typed_direction():
    assert assembly([Quad("TURN", ImmTurn("LEFT"), None, None, HERE)]) == [
        "LOADC R0, LEFT", "TURN R0", "HALT",
    ]


def test_instructions_keep_quad_location_and_halt_uses_eof():
    code = generate_vm_code([Quad("MOVE", ImmInt(1), None, None, HERE)], eof_location=EOF)
    assert [instruction.location for instruction in code] == [HERE, HERE, EOF]
    assert code[0] == Instruction("LOADC", (R0, ImmInt(1)), HERE)


@pytest.mark.parametrize(
    "quad",
    [
        Quad("JUMP", None, None, None, HERE),
        Quad("MOVE", None, None, None, HERE),
        Quad("COPY", ImmInt(1), None, None, HERE),
    ],
)
def test_malformed_tac_is_rejected(quad):
    with pytest.raises(ValueError):
        generate_vm_code([quad], eof_location=EOF)


@pytest.mark.parametrize(
    ("opcode", "left", "right"), [("ADD", 1, 2), ("SUB", 5, 2), ("MUL", 3, 1)],
)
def test_arithmetic_leaves_its_result_in_r0(opcode, left, right):
    code = program(
        ins("LOADC", R0, ImmInt(left)),
        ins("LOADC", R1, ImmInt(right)),
        ins(opcode, R0, R1),
        ins("MOVE", R0),
    )
    assert position(execute(code)) == (1, 1, "NORTE")


def test_negation_replaces_the_register():
    code = program(ins("LOADC", R0, ImmInt(-2)), ins("NEG", R0), ins("MOVE", R0))
    assert position(execute(code)) == (1, 2, "NORTE")


def test_memory_round_trip_feeds_the_robot():
    code = program(
        ins("LOADC", R0, ImmInt(2)),
        ins("STORE", S0, R0),
        ins("LOADC", R0, ImmInt(0)),
        ins("LOAD", R1, S0),
        ins("MOVE", R1),
    )
    assert position(execute(code)) == (1, 2, "NORTE")


@pytest.mark.parametrize(
    ("direction", "orientations"),
    [
        ("RIGHT", ["ESTE", "SUR", "OESTE", "NORTE"]),
        ("LEFT", ["OESTE", "SUR", "ESTE", "NORTE"]),
    ],
)
def test_turns_rotate_ninety_degrees_in_both_directions(direction, orientations):
    result = execute(program(*(turn(direction) * 4)))
    assert [event.orientation for event in result.events] == orientations
    assert {event.action for event in result.events} == {"turn"}
    assert (result.final.x, result.final.y) == (1, 4)


@pytest.mark.parametrize(
    ("turns", "expected"),
    [
        ([], (1, 3)),
        (["RIGHT"], (2, 4)),
        (["RIGHT", "RIGHT"], (1, 5)),
        (["LEFT"], (0, 4)),
    ],
)
def test_each_orientation_moves_along_its_axis(turns, expected):
    code = [instruction for direction in turns for instruction in turn(direction)]
    result = execute(program(*code, *move(1)))
    assert (result.final.x, result.final.y) == expected


def test_events_report_pc_source_and_state():
    result = execute(program(*move(1), *turn("RIGHT")))
    move_event, turn_event = result.events
    assert (move_event.pc, move_event.action, move_event.x, move_event.y) == (1, "move-step", 1, 3)
    assert (move_event.source_line, move_event.source_column) == (2, 5)
    assert (turn_event.pc, turn_event.action, turn_event.orientation) == (3, "turn", "ESTE")


def test_move_zero_is_valid_and_emits_no_event():
    result = execute(program(*move(0)))
    assert result.ok and result.events == []
    assert result.final == result.start


def test_negative_move_fails_without_steps():
    result = execute(program(*move(-1)))
    diagnostic = failure(result)
    assert diagnostic.code == "RUN_NEGATIVE_STEPS"
    assert (diagnostic.line, diagnostic.column) == (2, 5)
    assert result.events == [] and result.final == result.start


@pytest.mark.parametrize(
    ("turns", "valid_steps", "final"),
    [
        ([], 4, (1, 0)),
        (["RIGHT"], 6, (7, 4)),
        (["RIGHT", "RIGHT"], 3, (1, 7)),
        (["LEFT"], 1, (0, 4)),
    ],
)
def test_every_edge_stops_at_the_last_valid_cell(turns, valid_steps, final):
    code = [instruction for direction in turns for instruction in turn(direction)]
    result = execute(program(*code, *move(20)))
    assert failure(result).code == "RUN_OUT_OF_BOUNDS"
    steps = [event for event in result.events if event.action == "move-step"]
    assert len(steps) == valid_steps
    assert (result.final.x, result.final.y) == final


def test_huge_move_stops_at_the_edge_immediately():
    result = execute(program(*move(10**300)))
    assert failure(result).code == "RUN_OUT_OF_BOUNDS"
    assert len(result.events) == 4


def test_step_budget_keeps_valid_steps():
    result = execute(program(*move(3)), RobotConfig(max_steps=2))
    assert failure(result).code == "RUN_LIMIT_EXCEEDED"
    assert len(result.events) == 2
    assert (result.final.x, result.final.y) == (1, 2)


def test_step_budget_can_be_used_exactly():
    assert execute(program(*move(2)), RobotConfig(max_steps=2)).ok


def test_instruction_budget_counts_halt_and_can_be_used_exactly():
    code = program(*move(1))
    assert execute(code, RobotConfig(max_instructions=3)).ok
    result = execute(code, RobotConfig(max_instructions=2))
    diagnostic = failure(result)
    assert diagnostic.code == "RUN_LIMIT_EXCEEDED"
    assert (diagnostic.line, diagnostic.column) == (9, 1)
    assert len(result.events) == 1


@pytest.mark.parametrize(
    ("opcode", "left", "right"),
    [("MUL", TOO_LARGE - 1, TOO_LARGE - 1), ("ADD", TOO_LARGE - 1, 1), ("SUB", 1 - TOO_LARGE, 1)],
)
def test_integer_budget_stops_arithmetic(opcode, left, right):
    result = execute(
        program(ins("LOADC", R0, ImmInt(left)), ins("LOADC", R1, ImmInt(right)), ins(opcode, R0, R1))
    )
    assert failure(result).code == "RUN_LIMIT_EXCEEDED"


def test_integer_budget_applies_to_constants():
    assert failure(execute(program(ins("LOADC", R0, ImmInt(TOO_LARGE))))).code == "RUN_LIMIT_EXCEEDED"


def test_empty_program_only_halts():
    result = execute(program())
    assert result.ok and result.events == [] and result.diagnostics == []
    assert result.final == RobotState(1, 4, "NORTE")


def test_execution_is_deterministic():
    code = program(*move(2), *turn("LEFT"), *move(9))
    assert execute(code) == execute(code)


def test_custom_start_is_respected():
    config = RobotConfig(width=3, height=3, start_x=0, start_y=2, start_orientation="ESTE")
    result = execute(program(*move(2)), config)
    assert position(result) == (2, 2, "ESTE")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width": 0},
        {"start_x": 8},
        {"start_y": -1},
        {"start_orientation": "ARRIBA"},
        {"max_steps": -1},
        {"max_instructions": -1},
    ],
)
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        RobotConfig(**kwargs)


@pytest.mark.parametrize(
    "code",
    [
        [],
        ["MOVE R0"],
        ["LOADC R0, 1", "MOVE R0", "HALT"],
        move(1),
        program(ins("JUMP", R0)),
        program(ins("MOVE", R0)),
        program(ins("LOAD", R0, S0)),
        program(ins("LOADC", R0, S0)),
        program(ins("LOADC", Register("R9"), ImmInt(1))),
        program(Instruction("HALT", [], HERE), ins("ADD", R0)),
        program(ins("ADD", R0)),
        program(ins("LOADC", R0, ImmTurn("RIGHT")), ins("MOVE", R0)),
        program(ins("LOADC", R0, ImmInt(1)), ins("TURN", R0)),
        program(ins("LOADC", R0, ImmTurn("UP"))),
        program(ins("LOADC", R0, ImmTurn(["RIGHT"]))),
        program(ins("LOADC", R0, ImmInt(True))),
    ],
)
def test_malformed_code_gives_controlled_internal_error(code):
    assert failure(execute(code)).code == "RUN_INTERNAL_ERROR"


def test_results_serialize_with_the_agreed_shape():
    data = execute(program(*move(20))).to_dict()
    assert list(data) == ["ok", "start", "final", "events", "diagnostics"]
    assert data["ok"] is False
    assert data["start"] == {"x": 1, "y": 4, "orientation": "NORTE"}
    assert data["final"] == {"x": 1, "y": 0, "orientation": "NORTE"}
    assert data["events"][0] == {
        "pc": 1, "source_line": 2, "source_column": 5, "action": "move-step",
        "x": 1, "y": 3, "orientation": "NORTE",
    }
    assert set(data["diagnostics"][0]) == {"phase", "code", "message", "line", "column"}
