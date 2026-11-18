"""Virtual machine that runs generated instructions and drives the robot."""

from dataclasses import asdict, dataclass, field
from typing import Literal, NoReturn

from . import settings
from .codegen import R0, R1, Instruction, Register
from .diagnostics import Diagnostic, Location
from .tac import INTEGER_OPERATIONS, ImmInt, ImmTurn, Slot, Temp

_REGISTERS = (R0, R1)
_DELTAS = {"NORTE": (0, -1), "ESTE": (1, 0), "SUR": (0, 1), "OESTE": (-1, 0)}
_TURN_OFFSETS = {"RIGHT": 1, "LEFT": -1}
_UNKNOWN_LOCATION = Location(1, 1)


@dataclass(frozen=True, slots=True)
class RobotConfig:
    width: int = settings.GRID_WIDTH
    height: int = settings.GRID_HEIGHT
    start_x: int = settings.START_X
    start_y: int = settings.START_Y
    start_orientation: str = settings.START_ORIENTATION
    max_instructions: int = settings.MAX_VM_INSTRUCTIONS
    max_steps: int = settings.MAX_ROBOT_STEPS

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("The grid must have positive dimensions.")
        if not (0 <= self.start_x < self.width and 0 <= self.start_y < self.height):
            raise ValueError("The start position must be inside the grid.")
        if self.start_orientation not in settings.ORIENTATIONS:
            raise ValueError(f"Unknown orientation: {self.start_orientation}")
        if self.max_instructions < 0 or self.max_steps < 0:
            raise ValueError("Execution budgets cannot be negative.")


@dataclass(frozen=True, slots=True)
class RobotState:
    x: int
    y: int
    orientation: str

    def to_dict(self) -> dict[str, int | str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    pc: int
    source_line: int
    source_column: int
    action: Literal["move-step", "turn"]
    x: int
    y: int
    orientation: str

    def to_dict(self) -> dict[str, int | str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    ok: bool
    start: RobotState
    final: RobotState
    events: list[ExecutionEvent] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "start": self.start.to_dict(),
            "final": self.final.to_dict(),
            "events": [event.to_dict() for event in self.events],
            "diagnostics": [asdict(diagnostic) for diagnostic in self.diagnostics],
        }


def execute(code: list[Instruction], config: RobotConfig | None = None) -> ExecutionResult:
    """Run instructions from the initial state, keeping every valid event on failure."""
    machine = _Machine(config or RobotConfig())
    start = machine.state
    try:
        machine.run(code)
    except _RuntimeFault as fault:
        location = machine.location
        diagnostic = Diagnostic(
            "runtime", fault.code, fault.message, location.line, location.column,
        )
        return ExecutionResult(False, start, machine.state, machine.events, [diagnostic])
    return ExecutionResult(True, start, machine.state, machine.events)


class _RuntimeFault(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _internal_fault(message: str) -> NoReturn:
    raise _RuntimeFault("RUN_INTERNAL_ERROR", message)


def _is_well_formed(instruction: object) -> bool:
    return (
        isinstance(instruction, Instruction)
        and isinstance(instruction.location, Location)
        and isinstance(instruction.args, tuple)
        and all(arg in _REGISTERS for arg in instruction.args if isinstance(arg, Register))
    )


def _checked_integer(value: int) -> int:
    if not settings.integer_within_budget(value):
        raise _RuntimeFault(
            "RUN_LIMIT_EXCEEDED",
            f"Integer value exceeds the limit of {settings.MAX_INTEGER_BITS} bits.",
        )
    return value


class _Machine:
    def __init__(self, config: RobotConfig):
        self.config = config
        self.state = RobotState(config.start_x, config.start_y, config.start_orientation)
        self.events: list[ExecutionEvent] = []
        self.location = _UNKNOWN_LOCATION
        self.pc = 0
        self._registers: dict[Register, int | str] = {}
        self._memory: dict[Slot | Temp, int | str] = {}
        self._executed = 0
        self._steps = 0

    def run(self, code: list[Instruction]) -> None:
        halted = False
        while not halted:
            instruction = self._fetch(code)
            self._charge_instruction()
            halted = self._dispatch(instruction)
            self.pc += 1

    def _fetch(self, code: list[Instruction]) -> Instruction:
        if self.pc >= len(code):
            _internal_fault("The program ended without HALT.")
        instruction = code[self.pc]
        if not _is_well_formed(instruction):
            _internal_fault(f"Invalid instruction at PC {self.pc}.")
        self.location = instruction.location
        return instruction

    def _charge_instruction(self) -> None:
        if self._executed >= self.config.max_instructions:
            raise _RuntimeFault(
                "RUN_LIMIT_EXCEEDED",
                f"Execution exceeds the limit of {self.config.max_instructions} instructions.",
            )
        self._executed += 1

    def _dispatch(self, instruction: Instruction) -> bool:
        """Execute one instruction and tell whether the machine halted."""
        match instruction.opcode, instruction.args:
            case "LOADC", (Register() as target, ImmInt(value)):
                self._registers[target] = _checked_integer(self._integer(value))
            case "LOADC", (Register() as target, ImmTurn(value)):
                self._registers[target] = self._turn(value)
            case "LOAD", (Register() as target, (Slot() | Temp()) as source):
                self._registers[target] = self._read_memory(source)
            case "STORE", ((Slot() | Temp()) as target, Register() as source):
                self._memory[target] = self._read_register(source)
            case ("ADD" | "SUB" | "MUL") as opcode, (Register() as left, Register() as right):
                operation = INTEGER_OPERATIONS[opcode]
                self._registers[left] = _checked_integer(
                    operation(self._read_integer(left), self._read_integer(right))
                )
            case "NEG", (Register() as target,):
                self._registers[target] = _checked_integer(-self._read_integer(target))
            case "MOVE", (Register() as source,):
                self._move(self._read_integer(source))
            case "TURN", (Register() as source,):
                self._rotate(self._turn(self._read_register(source)))
            case "HALT", ():
                return True
            case _:
                _internal_fault(f"Invalid instruction '{instruction.opcode}' at PC {self.pc}.")
        return False

    def _read_register(self, register: Register) -> int | str:
        if register not in self._registers:
            _internal_fault(f"Register {register} was read before being written.")
        return self._registers[register]

    def _read_memory(self, address: Slot | Temp) -> int | str:
        if address not in self._memory:
            _internal_fault(f"Memory {address} was read before being written.")
        return self._memory[address]

    def _read_integer(self, register: Register) -> int:
        return self._integer(self._read_register(register))

    @staticmethod
    def _integer(value: object) -> int:
        if type(value) is not int:
            _internal_fault("An integer value was expected.")
        return value

    @staticmethod
    def _turn(value: object) -> str:
        if not isinstance(value, str) or value not in _TURN_OFFSETS:
            _internal_fault("A turn direction was expected.")
        return value

    def _record(self, action: Literal["move-step", "turn"], state: RobotState) -> None:
        self.state = state
        self.events.append(
            ExecutionEvent(
                self.pc, self.location.line, self.location.column, action,
                state.x, state.y, state.orientation,
            )
        )

    def _move(self, steps: int) -> None:
        if steps < 0:
            raise _RuntimeFault(
                "RUN_NEGATIVE_STEPS", f"The robot cannot move {steps} cells.",
            )
        dx, dy = _DELTAS[self.state.orientation]
        moved = 0
        while moved < steps:
            x, y = self.state.x + dx, self.state.y + dy
            if not (0 <= x < self.config.width and 0 <= y < self.config.height):
                raise _RuntimeFault(
                    "RUN_OUT_OF_BOUNDS", f"The robot cannot leave the grid at ({x}, {y}).",
                )
            if self._steps >= self.config.max_steps:
                raise _RuntimeFault(
                    "RUN_LIMIT_EXCEEDED",
                    f"Execution exceeds the limit of {self.config.max_steps} steps.",
                )
            self._steps += 1
            moved += 1
            self._record("move-step", RobotState(x, y, self.state.orientation))

    def _rotate(self, direction: str) -> None:
        orientations = settings.ORIENTATIONS
        index = orientations.index(self.state.orientation) + _TURN_OFFSETS[direction]
        orientation = orientations[index % len(orientations)]
        self._record("turn", RobotState(self.state.x, self.state.y, orientation))
