# RoboLang · Arquitectura del backend

Este documento describe la parte que va del AST validado a la ejecución del robot. El lenguaje y el análisis están en [lenguaje.md](lenguaje.md). El contrato entre integrantes está en [Revision_y_plan.md](Revision_y_plan.md).

```text
fuente → tokenize → parse → analyze → generate_tac → optimize → generate_vm_code → execute
         lexer.py  parser.py semantic.py  tac.py    optimizer.py   codegen.py       vm.py
                              └────────────── orquestado por compiler.py ──────┘
```

`compile_source` termina en `generate_vm_code` y no mueve el robot. `execute` es un paso aparte y solo recibe objetos `Instruction`. La VM no ve el texto fuente ni el ensamblador.

| Módulo | Responsabilidad |
|---|---|
| `settings.py` | Límites, tamaño de la cuadrícula y estado inicial. |
| `tac.py` | Operandos `ImmInt`, `ImmTurn`, `Slot`, `Temp`; `Quad`; `generate_tac`; `format_quad`. |
| `optimizer.py` | Plegado de constantes. |
| `codegen.py` | `Register`, `Instruction`, `generate_vm_code`, `format_instruction`. |
| `vm.py` | `RobotConfig`, `RobotState`, `ExecutionEvent`, `ExecutionResult`, `execute`. |
| `compiler.py` | `CompilationResult`, `compile_source`. |
| `scripts/demo_cli.py` | Demostración por consola, sin web. |

## TAC y optimización

Cada cuádrupla es `Quad(op, arg1, arg2, result, location)`, con las operaciones `ADD`, `SUB`, `MUL`, `NEG`, `COPY`, `MOVE` y `TURN`. Las operaciones aritméticas conservan la posición de su operador. `COPY`, `MOVE` y `TURN` conservan el inicio de la sentencia.

El optimizador solo reemplaza operaciones cuyos operandos son inmediatos: `ADD 2 1 -> T0` pasa a `COPY 3 -> T0`. Es una pasada por cuádrupla, así que:

- No propaga constantes por temporales ni variables. `2 + 3 * 4` queda como `T0 = 12` y `T1 = 2 + T0`.
- No elimina temporales ni cambia el orden de ninguna cuádrupla.
- Si el resultado excede el presupuesto de enteros, deja la operación intacta. La VM reporta entonces el mismo error, en la misma posición, con y sin optimizar.

## Código objetivo

Es pseudoensamblador de una CPU virtual propia, no código nativo.

| Instrucción | Efecto |
|---|---|
| `LOADC Rn, inmediato` | Carga un entero o giro en el registro. |
| `LOAD Rn, Sx/Tx` | Lee memoria. |
| `STORE Sx/Tx, R0` | Escribe memoria. |
| `ADD/SUB/MUL R0, R1` | Deja el resultado en `R0`. |
| `NEG R0` | Niega `R0`. |
| `MOVE R0` | Avanza el robot. |
| `TURN R0` | Gira 90° según `RIGHT` o `LEFT`. |
| `HALT` | Termina; lleva la posición del token EOF. |

`R0` y `R1` solo sostienen operandos durante una operación. Variables y temporales viven siempre en memoria, por diseño: no hay asignación dinámica de registros, spill, marcos de pila ni heap.

## Máquina virtual

El robot parte de `(1,4)` mirando al `NORTE` en una cuadrícula 8×8. `x` crece hacia la derecha e `y` hacia abajo. Cada paso elemental se valida antes de aplicarse, de modo que un fallo conserva los eventos válidos anteriores y el robot nunca sale del tablero.

| Código | Causa |
|---|---|
| `RUN_OUT_OF_BOUNDS` | El siguiente paso saldría de la cuadrícula. |
| `RUN_NEGATIVE_STEPS` | `mover` recibió un valor negativo. |
| `RUN_LIMIT_EXCEEDED` | Se agotó el presupuesto de instrucciones, de pasos o de magnitud entera. |
| `RUN_INTERNAL_ERROR` | Código mal formado: opcode desconocido, lectura sin escritura previa, tipo incorrecto o falta de `HALT`. El compilador no debería producirlo. |

| Límite (`settings.py`) | Valor | Dónde se aplica |
|---|---:|---|
| `MAX_SOURCE_CHARS` | 4.000 | `compile_source`, con `LEX_SOURCE_TOO_LONG` en 1:1. |
| `MAX_VM_INSTRUCTIONS` | 2.000 | VM. Cuenta las instrucciones ejecutadas, incluido `HALT`. |
| `MAX_ROBOT_STEPS` | 200 | VM. Cuenta pasos elementales. |
| `MAX_INTEGER_BITS` | 1.024 | VM y optimizador. |

El presupuesto de instrucciones puede distinguir ambos modos, porque el código plegado es más corto. Las comparaciones de equivalencia usan presupuestos holgados y este límite se prueba aparte.

Los límites de José siguen en `frontend_limits.py`: 256 dígitos por literal y profundidad 64. El presupuesto de 1.024 bits admite cualquier literal de 256 dígitos, y una prueba lo verifica. **Estos valores están pendientes de confirmación con José.**

## Interfaz para la API

```python
from robolang.compiler import compile_source
from robolang.vm import execute

compiled = compile_source(source, optimize=True)
payload = compiled.to_dict()
payload["execution"] = execute(compiled.instructions).to_dict() if compiled.ok else None
```

- `compile_source` lanza `TypeError` si `source` no es texto u `optimize` no es booleano. Los errores del programa nunca lanzan excepción: llegan en `diagnostics` con `ok=False`, e `instructions` queda vacío.
- Cualquier otra excepción es un fallo interno y corresponde a la respuesta HTTP 500.
- `to_dict()` de compilación devuelve `ok, tokens, ast, symbols, tac_before, tac_after, assembly, diagnostics`. `instructions` no se serializa.
- `to_dict()` de ejecución devuelve `ok, start, final, events, diagnostics`. Cada evento trae `pc, source_line, source_column, action, x, y, orientation`, y `action` es `move-step` o `turn`.
- El AST incluye literales de hasta 256 dígitos como números JSON. JavaScript los leería con pérdida de precisión, así que conviene no operar con ellos en el navegador.

Muestras reales generadas con `python scripts/demo_cli.py --json <archivo>`, con la misma forma que `/api/run`. Una prueba verifica que siguen coincidiendo con la salida actual:

- [integral.json](muestras/integral.json): ejemplo §15, compilación y ejecución correctas.
- [error_semantico.json](muestras/error_semantico.json): falla la compilación y `execution` es `null`.
- [error_runtime.json](muestras/error_runtime.json): compila, falla en ejecución y conserva cuatro pasos.

## Comprobación

```sh
python -m pytest -q
python scripts/demo_cli.py
python scripts/demo_cli.py --no-optimize
python scripts/demo_cli.py examples/07_error_runtime.rbl
```

| Archivo | Datos de entrada |
|---|---|
| `tests/test_optimizer.py`, `tests/test_codegen_vm.py` | Cuádruplas e instrucciones escritas a mano (fixtures). |
| `tests/test_tac.py` | Lexer, parser y análisis semántico reales. |
| `tests/test_end_to_end.py` | Pipeline real completo, VM y CLI. |
