"""FastAPI application exposing the RoboLang compiler and VM.

Status codes:
- 200: the program was processed, even if it has compile or runtime errors.
- 422: the request itself is invalid (types, missing fields, source too long).
- 500: unexpected failure; the client receives a generic message only.
"""

import logging
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr

from . import config
from .backend import Backend, load_backend

logger = logging.getLogger(__name__)


class ProgramRequest(BaseModel):
    """Body of both endpoints. Clients never send VM instructions."""

    model_config = ConfigDict(extra="forbid")

    source: StrictStr
    optimize: StrictBool = config.DEFAULT_OPTIMIZE


class SourceTooLong(Exception):
    def __init__(self, limit: int) -> None:
        super().__init__(limit)
        self.limit = limit


class BackendUnavailable(Exception):
    pass


def create_app(
    backend_factory: Callable[[], Backend] = load_backend,
    *,
    examples_dir: Path = config.EXAMPLES_DIR,
    static_dir: Path = config.STATIC_DIR,
) -> FastAPI:
    app = FastAPI(title=config.APP_TITLE)

    @cache
    def cached_backend() -> Backend:
        return backend_factory()

    def get_backend() -> Backend:
        try:
            return cached_backend()
        except Exception as error:
            raise BackendUnavailable from error

    def compile_request(body: ProgramRequest, backend: Backend) -> Any:
        limit = backend.world.max_source_chars
        if len(body.source) > limit:
            raise SourceTooLong(limit)
        return backend.compile_source(body.source, optimize=body.optimize)

    @app.get(f"{config.API_PREFIX}/config")
    def config_endpoint(backend: Backend = Depends(get_backend)) -> dict[str, Any]:
        return backend.world.to_dict()

    @app.get(f"{config.API_PREFIX}/examples")
    def examples_endpoint() -> dict[str, Any]:
        return {"default": config.DEFAULT_EXAMPLE, "examples": _load_examples(examples_dir)}

    @app.post(f"{config.API_PREFIX}/compile")
    def compile_endpoint(body: ProgramRequest, backend: Backend = Depends(get_backend)) -> dict[str, Any]:
        return compile_request(body, backend).to_dict()

    @app.post(f"{config.API_PREFIX}/run")
    def run_endpoint(body: ProgramRequest, backend: Backend = Depends(get_backend)) -> dict[str, Any]:
        # The program is always recompiled here: the VM only runs server-generated code.
        compiled = compile_request(body, backend)
        payload = compiled.to_dict()
        payload["execution"] = backend.execute(compiled.instructions).to_dict() if compiled.ok else None
        return payload

    @app.exception_handler(RequestValidationError)
    async def on_invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        errors = [_describe_error(item) for item in error.errors()]
        return _invalid_request(errors)

    @app.exception_handler(SourceTooLong)
    async def on_source_too_long(_: Request, error: SourceTooLong) -> JSONResponse:
        message = config.VALIDATION_MESSAGES["source_too_long"].format(limit=error.limit)
        return _invalid_request([{"field": "source", "type": "source_too_long", "message": message}])

    @app.exception_handler(BackendUnavailable)
    async def on_backend_unavailable(_: Request, error: BackendUnavailable) -> JSONResponse:
        logger.error("Could not load the compiler backend", exc_info=error.__cause__)
        return _internal_error()

    @app.exception_handler(Exception)
    async def on_unexpected_error(_: Request, error: Exception) -> JSONResponse:
        logger.error("Unexpected error while handling a request", exc_info=error)
        return _internal_error()

    # Mounted last so the API routes above take precedence over static files.
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


def _load_examples(directory: Path) -> list[dict[str, str]]:
    if not directory.is_dir():
        return []
    files = {path.name: path for path in directory.glob(config.EXAMPLE_PATTERN) if path.is_file()}
    ordered = [name for name in config.EXAMPLE_TITLES if name in files]
    ordered += sorted(name for name in files if name not in config.EXAMPLE_TITLES)
    return [
        {
            "id": name,
            "title": config.EXAMPLE_TITLES.get(name, name),
            "source": files[name].read_text(encoding="utf-8"),
        }
        for name in ordered
    ]


def _describe_error(item: dict[str, Any]) -> dict[str, str]:
    location = [str(part) for part in item.get("loc", ()) if part != "body"]
    error_type = item.get("type", "")
    message = config.VALIDATION_MESSAGES.get(error_type, config.DEFAULT_VALIDATION_MESSAGE)
    return {"field": ".".join(location), "type": error_type, "message": message}


def _invalid_request(errors: list[dict[str, str]]) -> JSONResponse:
    return JSONResponse(status_code=422, content={"message": config.INVALID_REQUEST_MESSAGE, "errors": errors})


def _internal_error() -> JSONResponse:
    return JSONResponse(status_code=500, content={"message": config.INTERNAL_ERROR_MESSAGE})


app = create_app()
