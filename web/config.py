"""Settings owned by the web layer.

Compiler and VM limits (source length, instruction budget, grid) live in
`robolang/settings.py`; the API reads them through the backend instead of
repeating them here.
"""

from pathlib import Path

APP_TITLE = "RoboLang"
API_PREFIX = "/api"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Example programs offered by the interface. Files are read from `examples/`;
# a file without a title here is listed by its name.
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE_PATTERN = "*.rbl"
EXAMPLE_TITLES = {
    "08_integral.rbl": "§15 · Ejemplo integral",
    "01_basico.rbl": "Básico",
    "02_variables.rbl": "Variables",
    "03_scopes.rbl": "Ámbitos y sombreado",
    "04_error_lexico.rbl": "Error léxico",
    "05_error_sintaxis.rbl": "Error sintáctico",
    "06_error_semantico.rbl": "Error semántico",
    "07_error_runtime.rbl": "Error de ejecución",
}
DEFAULT_EXAMPLE = "08_integral.rbl"

DEFAULT_OPTIMIZE = True

INVALID_REQUEST_MESSAGE = "Solicitud inválida."
SOURCE_TOO_LONG_MESSAGE = "El código fuente admite como máximo {limit} caracteres."
INTERNAL_ERROR_MESSAGE = "Error interno del servidor. Inténtalo de nuevo."

# Spanish messages for request validation errors, keyed by Pydantic error type.
VALIDATION_MESSAGES = {
    "missing": "Campo obligatorio.",
    "string_type": "Debe ser texto.",
    "bool_type": "Debe ser booleano (true o false).",
    "extra_forbidden": "Campo no permitido.",
    "model_attributes_type": "El cuerpo debe ser un objeto JSON.",
    "json_invalid": "El cuerpo no es JSON válido.",
    "source_too_long": SOURCE_TOO_LONG_MESSAGE,
}
DEFAULT_VALIDATION_MESSAGE = "Valor inválido."
