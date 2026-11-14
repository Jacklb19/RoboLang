# RoboLang

RoboLang is an educational programming language for moving a virtual robot on an 8×8 grid. The project demonstrates how source code becomes tokens, an abstract syntax tree, validated symbols, three-address code, and instructions for a virtual machine.

The compiler targets Python 3.11 or later. The project guide and the team's integration contract are available in Spanish.

- [Project guide](docs/RoboLang_Guia_Completa.md)
- [Technical review and integration contract](docs/Revision_y_plan.md)

Use `main` as the shared starting point for the compiler frontend, VM, and web work.

## Compiler frontend

On the compiler frontend branch, install the development dependencies and run the test suite from the repository root.

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The [language reference](docs/lenguaje.md) shows how to tokenize, parse, and analyze a sample source file and read its resolved variable slots.
