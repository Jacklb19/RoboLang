# RoboLang 1.0 · Lenguaje

RoboLang admite declaraciones, asignaciones, bloques y órdenes para un robot virtual. Las palabras reservadas distinguen mayúsculas de minúsculas. Los comentarios `//` terminan al final de la línea.

## Gramática

```ebnf
programa    = { sentencia }, EOF ;
sentencia   = declaracion | asignacion | mover | girar | bloque ;
declaracion = tipo, IDENT, "=", expresion, ";" ;
tipo        = "entero" | "giro" ;
asignacion  = IDENT, "=", expresion, ";" ;
mover       = "mover", "(", expresion, ")", ";" ;
girar       = "girar", "(", expresion, ")", ";" ;
bloque      = "{", { sentencia }, "}" ;
expresion   = suma ;
suma        = producto, { ("+" | "-"), producto } ;
producto    = unario, { "*", unario } ;
unario      = "-", unario | primario ;
primario    = INT | "derecha" | "izquierda" | IDENT | "(", expresion, ")" ;
```

`IDENT` sigue `[A-Za-z_][A-Za-z0-9_]*` y `INT` sigue `[0-9]+`. El menos unario tiene mayor precedencia que la multiplicación. Los operadores binarios se asocian a la izquierda, por lo que `8 - 3 - 2` equivale a `(8 - 3) - 2`.

## Tipos y ámbitos

- `entero` admite aritmética y es el tipo de los argumentos de `mover`. `giro` admite los valores `derecha` e `izquierda` y es el tipo de los argumentos de `girar`. Las asignaciones conservan el tipo declarado.
- Un bloque puede sombrear una variable externa. Su inicializador se valida antes de declarar la variable local, por lo que `entero x = 1; { entero x = x + 1; }` lee el `x` externo. Dos declaraciones del mismo nombre en un mismo ámbito producen un error.
- Los diagnósticos incluyen fase, código, mensaje en inglés, línea y columna a partir de 1. CRLF cuenta como un salto de línea y un tabulador cuenta como un carácter.
- Los literales tienen un máximo de 256 dígitos y el parser limita la profundidad a 64 niveles. Ambas constantes viven en `robolang/frontend_limits.py`. El compilador integrado aplicará el presupuesto global de fuente y la VM controlará la ejecución.

## Entrega para el generador de TAC

```python
from pathlib import Path

from robolang.lexer import tokenize
from robolang.parser import parse
from robolang.semantic import analyze

source = Path("examples/08_integral.rbl").read_text(encoding="utf-8")
result = analyze(parse(tokenize(source)))
assert [(symbol.name, symbol.slot) for symbol in result.symbols] == [
    ("pasos", "S0"), ("lado", "S1"), ("pasos", "S2")
]
```

`result.program` contiene el AST validado. Los nodos de declaración, asignación y referencia exponen `resolved_slot`. El análisis devuelve un árbol nuevo, así que el AST sintáctico original sigue disponible para inspección. Cada nodo tiene `location`. Los fallos esperados lanzan `CompileError` y exponen `.diagnostic`.

## Programas de ejemplo

| Ejemplo | Resultado hasta el análisis semántico |
|---|---|
| `01_basico.rbl`, `02_variables.rbl`, `03_scopes.rbl`, `08_integral.rbl` | Aceptados. |
| `04_error_lexico.rbl` | `LEX_UNKNOWN_CHAR` en 1:7. |
| `05_error_sintaxis.rbl` | `SYN_EXPECTED_TOKEN` en 1:8. |
| `06_error_semantico.rbl` | `SEM_TYPE_MISMATCH` en 3:1. |
| `07_error_runtime.rbl` | Aceptado. El fallo de límites del tablero se comprobará con la VM. |
