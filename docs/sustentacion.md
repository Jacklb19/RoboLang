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
| 1.5 min | Ejemplos **Error léxico**, **Error sintáctico** y **Error semántico** → Ejecutar. | Error localizado por fase; `execution` es `null` y el robot no se mueve. |
| 0.5 min | Ejemplo **Error de ejecución** → Ejecutar. | Compila (`ok: true`), falla la VM (`execution.ok: false`) y se conserva la traza parcial hasta (1,0). |
| 0.5 min | — | Conclusiones y límites. |

Demostraciones imprescindibles (§21): **A**, el §15 hasta (3,1) ESTE; **B**, `mover(lado)` con `lado: giro`, con error en la línea 3 y el robot sin moverse.

## Evidencias

### Comprobadas el 2026-11-18, antes de integrar en `main`

La interfaz y la API de `santiago/web-api` se ejecutaron con el compilador y la VM de la rama `steven/backend-vm` (commit `19f17d5`), cargados desde una copia temporal sin fusionar:

| Caso | Resultado observado en el navegador |
|---|---|
| §15 con optimización | `Ejecución completada · (3,1) ESTE`, 6 eventos; TAC `T0 = 2 + 1` → `T0 = 3`. |
| §15 sin optimización | Mismo final (3,1) ESTE y 6 eventos; TAC sin cambios. |
| `04_error_lexico.rbl` | `LEX_UNKNOWN_CHAR`, línea 1, columna 7; robot en (1,4) NORTE. |
| `05_error_sintaxis.rbl` | `SYN_EXPECTED_TOKEN`, línea 1, columna 8; robot en (1,4) NORTE. |
| `06_error_semantico.rbl` | `SEM_TYPE_MISMATCH`, línea 3, columna 1; robot en (1,4) NORTE. |
| `07_error_runtime.rbl` | `RUN_OUT_OF_BOUNDS`, línea 1, columna 1; 4 eventos válidos, robot en (1,0) NORTE. |
| Editar durante la reproducción | Se detiene, el robot vuelve a (1,4) y las pestañas se vacían. |
| Respuesta tardía tras editar o cambiar «Optimizar» | Se descarta; queda «El código cambió: vuelve a compilar». |
| Móvil (390 px) | Columnas apiladas, sin desplazamiento horizontal de la página. |

### Pendientes tras integrar en `main`

- Salida de `python -m pytest -q` con todo el código integrado.
- Capturas de la demo A y B, y de los errores léxico, sintáctico y runtime.
- Repetir la tabla anterior con `uvicorn web.app:app` desde `main`.

## Límites que conviene mencionar

- Los mensajes de diagnóstico del compilador están en inglés y se muestran tal cual.
- Los literales enteros de muchos dígitos se muestran con sus dígitos exactos solo en navegadores que exponen el texto original del JSON (Chrome 114+); en otros pueden verse redondeados. La ejecución no se ve afectada porque ocurre en el servidor.
- La reproducción es visual: Pausar, Paso y Reiniciar no vuelven a ejecutar la VM.
