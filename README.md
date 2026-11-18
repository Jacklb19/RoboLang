# RoboLang

RoboLang is an educational programming language for moving a virtual robot on an 8×8 grid. The project demonstrates how source code becomes tokens, an abstract syntax tree, validated symbols, three-address code, and instructions for a virtual machine.

The compiler targets Python 3.11 or later. The project guide and the team's integration contract are available in Spanish.

- [Project guide](docs/RoboLang_Guia_Completa.md)
- [Technical review and integration contract](docs/Revision_y_plan.md)
- [Language reference](docs/lenguaje.md)
- [Backend and VM architecture](docs/arquitectura.md)
- [Presentation script](docs/sustentacion.md)

Use `main` as the shared starting point for the compiler frontend, VM, and web work.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` pins the versions checked with Python 3.14 on Windows.

## Run the web interface

```powershell
uvicorn web.app:app --reload
```

Open `http://127.0.0.1:8000/`. The API loads the compiler and VM on the first request; if they cannot be imported it answers HTTP 500 with a generic message and logs the cause.

## Deploy to Vercel

Import this GitHub repository into Vercel and select the `main` branch. Keep the root directory at the repository root and select the FastAPI framework preset. Use its default build settings.

`app.py` exposes the existing application as `app` at the repository root. `.python-version` selects Python 3.14. Vercel installs `requirements.txt` and loads the application through its Python runtime. The `.vercelignore` file excludes local environments, test files, and documentation while retaining `examples/` and `web/static/`.

After deploying, open the site and check that `/api/config` and `/api/examples` return JSON. Compile and execute the integral example, which should end at `(3,1) ESTE`.

See the [Vercel FastAPI guide](https://vercel.com/docs/frameworks/backend/fastapi) for the framework preset and the [Python runtime guide](https://vercel.com/docs/functions/runtimes/python) for supported versions.

## Tests

```powershell
python -m pytest -q
```

Run the browser state regression tests with Node.js 18 or later, using its built-in test runner.

```sh
node --test tests/web_ui.test.cjs
```

`tests/test_api.py` checks the API with fixture results, so it runs without the compiler. Most fixtures are real outputs from `scripts/demo_cli.py --json`. The compiler tests alone only need `requirements-dev.txt`.

## Console demo

```powershell
python scripts/demo_cli.py                      # §15 example, optimized
python scripts/demo_cli.py --no-optimize
python scripts/demo_cli.py examples/07_error_runtime.rbl
```

## API

| Endpoint | Body | Response |
|---|---|---|
| `POST /api/compile` | `{"source": str, "optimize": bool = true}` | `ok, tokens, ast, symbols, tac_before, tac_after, assembly, diagnostics` |
| `POST /api/run` | same | the compile result plus `execution` (`ok, start, final, events, diagnostics`), or `null` when compilation fails |
| `GET /api/config` | — | `max_source_chars`, `grid`, `start` (read from `robolang/settings.py`) |
| `GET /api/examples` | — | programs from `examples/*.rbl` |

- **200**: the program was processed. The top-level `ok` describes compilation, and `execution.ok` describes execution.
- **422**: invalid request (missing `source`, non-strict types, unknown fields, or source over the limit).
- **500**: internal failure, with a generic message only.

`/api/run` always recompiles the source on the server. Clients never send VM instructions.

## Web layout

| Path | Role |
|---|---|
| `web/app.py` | FastAPI app, validation and error handling. |
| `web/backend.py` | Lazy connection to `robolang.compiler` and `robolang.vm`. |
| `web/config.py` | Web-only settings: paths, example titles, messages. |
| `web/static/` | `index.html`, `styles.css`, `app.js` (no framework). |

The interface only displays API results. It does not tokenize, type-check, optimize or move the robot itself. When the code or the optimize option changes, it discards results, cancels playback and ignores responses to older requests.

Execute becomes available after a successful compilation of the current source and optimization option. A failed request displays its error even when a previous execution completed successfully.
