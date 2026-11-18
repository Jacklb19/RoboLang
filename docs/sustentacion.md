# RoboLang · Guion de sustentación

Guion de 10–12 minutos basado en el §21 de la [guía](RoboLang_Guia_Completa.md). Todo se muestra desde la interfaz web (`uvicorn web.app:app`, `http://127.0.0.1:8000/`), salvo las pruebas y el código.

## Preparación

1. `python -m pytest -q`: guardar la salida.
2. Arrancar la interfaz y elegir **§15 · Ejemplo integral** en «Ejemplos».
3. Velocidad «Normal». «Optimizar» activado.

## Guion

| Tiempo | Qué hacer en la interfaz | Qué explicar |
|---|---|---|
| 1 min | Pantalla inicial. | Problema: cómo un compilador convierte texto en acciones del robot. |
| 1 min | Pestaña **Ayuda** y el código del §15. | Gramática y palabras reservadas (`entero`, `giro`, `mover`, `girar`, `derecha`, `izquierda`). |
| 1 min | **Compilar** → pestaña **Tokens**. | Tipo, lexema, línea y columna. Compilar **no** mueve el robot: sigue en (1,4) NORTE. |
| 1.5 min | Pestaña **AST**. | `2 + 1` queda como `BinaryOperation`; precedencia del parser. |
| 1.5 min | Pestaña **Símbolos**. | `pasos` global (S0) y `pasos` del bloque (S2): sombreado con slots distintos. |
| 1.5 min | Pestaña **TAC**. Desactivar «Optimizar» y volver a compilar. | `T0 = 2 + 1` → `T0 = 3`. Sin optimizar, ambas columnas son iguales. Cambiar la opción invalida los resultados. |
| 1.5 min | Pestaña **Ensamblador**. | `LOADC`, `LOAD`, `STORE`, `MOVE`, `TURN`, `HALT`; registros R0/R1 y memoria S/T. |
| 1 min | **Ejecutar** → pestaña **Traza**. | La VM devuelve eventos; la web solo los reproduce. Final: (3,1) ESTE en 6 eventos. Se resalta la línea, el PC y la celda. |
| 1.5 min | Ejemplos **Error léxico**, **Error sintáctico** y **Error semántico** → Compilar. | Error localizado por fase. Ejecutar queda deshabilitado y el robot sigue en su posición inicial. |
| 0.5 min | Ejemplo **Error de ejecución** → Compilar → Ejecutar. | Compila (`ok: true`), falla la VM (`execution.ok: false`) y se conserva la traza parcial hasta (1,0). |
| 0.5 min | — | Conclusiones y límites. |

Demostraciones imprescindibles (§21): **A**, el §15 hasta (3,1) ESTE; **B**, `mover(lado)` con `lado: giro`, con error en la línea 3 y el robot sin moverse.

## Evidencias

Comprobadas el 2026-11-18 en `santiago/web-api` después de fusionar `steven/backend-vm` (commit `19f17d5`), con `uvicorn web.app:app` en `http://127.0.0.1:8000/`.

**Pruebas:** `python -m pytest -q` → `254 passed`. Incluye 206 pruebas de lexer, parser, semántica, TAC, optimizador, VM y extremo a extremo, y 48 de la API: 40 con fixtures y 8 con el compilador y la VM reales.

**Interfaz en el navegador:**

| Caso | Resultado observado |
|---|---|
| §15 · Compilar | `Compilación exitosa · con optimización`; el robot sigue en (1,4) NORTE. |
| §15 · Ejecutar con optimización | `Ejecución completada · (3,1) ESTE`, 6 eventos; TAC `T0 = 2 + 1` → `T0 = 3`. |
| §15 · Ejecutar sin optimización | Mismo final (3,1) ESTE y 6 eventos; TAC sin cambios. |
| `04_error_lexico.rbl` | `LEX_UNKNOWN_CHAR`, línea 1, columna 7; robot en (1,4) NORTE. |
| `05_error_sintaxis.rbl` | `SYN_EXPECTED_TOKEN`, línea 1, columna 8; robot en (1,4) NORTE. |
| `06_error_semantico.rbl` | `SEM_TYPE_MISMATCH`, línea 3, columna 1; robot en (1,4) NORTE. |
| `07_error_runtime.rbl` | `RUN_OUT_OF_BOUNDS`, línea 1, columna 1; 4 eventos válidos, robot en (1,0) NORTE. |
| Cambiar «Optimizar» o editar durante la reproducción | Se detiene, el robot vuelve a (1,4) y las pestañas se vacían. |
| Respuesta tardía tras editar o cambiar «Optimizar»* | Se descarta; queda «El código cambió: vuelve a compilar». |
| Móvil (390 px)* | Columnas apiladas, sin desplazamiento horizontal de la página. |

\* Comprobado antes de la fusión, con el mismo código de Steven cargado desde una copia temporal; la interfaz no cambió después.

**Capturas** (`docs/evidencias/`):

- [Demostración A: §15 hasta (3,1) ESTE](evidencias/demo_a_integral.png)
- [Demostración B: error semántico, robot sin moverse](evidencias/demo_b_error_semantico.png)
- [Error de ejecución con traza parcial](evidencias/error_runtime.png)

Pendiente si el docente lo pide: capturas de cada pestaña (tokens, AST, símbolos, TAC, ensamblador) y de los errores léxico y sintáctico.

## Verificación de las correcciones en main

El 2026-11-18 se comprobaron las correcciones con 254 pruebas Python y 5 pruebas de estado de la interfaz mediante `node --test tests/web_ui.test.cjs`.

En el navegador se verificó que Ejecutar se habilita tras compilar correctamente y se bloquea al editar, cambiar la optimización o fallar la compilación. El ejemplo integral llegó a (3,1) ESTE. Después de una ejecución correcta, se detuvo el servidor temporal y se intentó ejecutar otra vez. La interfaz mantuvo visible el mensaje de conexión fallida.

## Límites que conviene mencionar

- Los mensajes de diagnóstico del compilador están en inglés y se muestran tal cual.
- Los literales enteros de muchos dígitos se muestran con sus dígitos exactos solo en navegadores que exponen el texto original del JSON (Chrome 114+); en otros pueden verse redondeados. La ejecución no se ve afectada porque ocurre en el servidor.
- La reproducción es visual: Pausar, Paso y Reiniciar no vuelven a ejecutar la VM.
