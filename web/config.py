"""Settings owned by the web layer.

Compiler and VM limits (source length, instruction budget, grid) live in
`robolang/settings.py`; the API reads them through the backend instead of
repeating them here.
"""

from pathlib import Path

APP_TITLE = "RoboLang"
API_PREFIX = "/api"
STATIC_DIR = Path(__file__).resolve().parent / "static"

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
