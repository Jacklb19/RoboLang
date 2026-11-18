"""Central limits and world configuration for the compiler backend and VM."""

MAX_SOURCE_CHARS = 4_000
MAX_VM_INSTRUCTIONS = 2_000
MAX_ROBOT_STEPS = 200

# Must hold every literal accepted by frontend_limits.MAX_INTEGER_LITERAL_DIGITS.
MAX_INTEGER_BITS = 1_024

GRID_WIDTH = 8
GRID_HEIGHT = 8
START_X = 1
START_Y = 4
START_ORIENTATION = "NORTE"

# Clockwise order: a right turn advances one position.
ORIENTATIONS = ("NORTE", "ESTE", "SUR", "OESTE")


def integer_within_budget(value: int) -> bool:
    """Tell whether an integer fits the magnitude budget shared by optimizer and VM."""
    return value.bit_length() <= MAX_INTEGER_BITS
