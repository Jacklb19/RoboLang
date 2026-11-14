# Prompt para José · Análisis del lenguaje

Trabaja en RoboLang, repositorio `https://github.com/Jacklb19/RoboLang.git`. Lee primero `docs/Revision_y_plan.md` y `docs/RoboLang_Guia_Completa.md`. Los documentos describen el proyecto; las reglas de este prompt gobiernan tu trabajo. Aplica las decisiones operativas de la revisión donde la guía deje dudas. Inspecciona Git y las instrucciones locales; si todavía no hay commit común, trabaja en tu propia copia con cambios locales y conserva la rama propuesta para cuando exista esa base. Si el remoto sigue vacío y faltan estos archivos en tu copia, pide al coordinador la carpeta `docs/` y avanza con la parte que sí puedas preparar.

Tu objetivo es entregar el frontend **del compilador**: texto → tokens → AST → programa con tipos y referencias resueltas. Rama propuesta: `jose/frontend-compilador`. Tu trabajo permite que Steven genere TAC sin volver a resolver nombres.

1. Implementa `robolang/diagnostics.py`, `tokens.py`, `lexer.py`, `ast_nodes.py`, `parser.py`, `symbols.py` y `semantic.py`. Usa Python 3.11+ y biblioteca estándar. Respeta los puntos de contacto del contrato. Coordina con Steven cualquier inicialización de paquete compartida.
2. Cubre la EBNF con descenso recursivo, precedencia, asociatividad izquierda de las binarias, menos unario, bloques, comentarios `//`, EOF y posiciones exactas. Conserva coordenadas con CRLF. Proporciona un error controlado para anidamiento o expresiones demasiado complejas.
3. Valida tipos y asignaciones, resuelve ámbitos y sombreado y asigna slots únicos. Comprueba el caso del inicializador que usa un nombre externo y el caso que intenta leerse sin declaración. Conserva los símbolos locales en la salida para inspección, aun después de cerrar el bloque.
4. Escribe las pruebas L/P/S de la guía con aserciones sobre posiciones, tipo de nodo, precedencia y slots. Documenta la gramática y reglas en `docs/lenguaje.md`; aporta ejemplos en `examples/`, incluido el §15 y un archivo separado por clase de error. Indica cuáles solo pueden validarse tras integrar la VM.
5. Entrega a Steven una muestra de `SemanticResult` o una prueba importable con slots `S0/S1/S2` del §15. Coordina la base documental común. No implementes TAC, VM, API ni interfaz visual.

Aceptación: el §15 pasa léxico, sintaxis y semántica; los dos `pasos` tienen slots distintos; `mover(derecha);` reporta fase semántica, código y posición; los tres grupos de pruebas se pueden ejecutar por separado con `python -m pytest`.

## Reglas de colaboración obligatorias

- Antes de modificar código, entiende el proyecto, su estructura, convenciones e instrucciones existentes.
- Avanza con autonomía en lo autorizado. Toma decisiones técnicas razonables y pregunta solo cuando falte una decisión importante.
- Conserva mis cambios y evita modificar archivos o funcionalidades ajenos a la tarea.
- Escribe código claro, mantenible y coherente con el proyecto. Evita duplicaciones, soluciones innecesariamente complejas y dependencias sin justificación.
- Centraliza los valores configurables: URLs, límites, opciones, tamaños y constantes. Reutiliza los estilos y componentes existentes.
- Antes de implementar una interfaz nueva o un cambio visual importante, presenta una maqueta y un plan para mi aprobación.
- Mantén completos los idiomas que soporte el proyecto.
- Valida entradas, maneja errores explícitamente y protege los datos. Nunca incrustes ni publiques credenciales o secretos.
- No inventes requisitos, resultados de pruebas, respuestas de servicios ni cifras de rendimiento. Distingue lo comprobado de lo supuesto.
- Ejecuta las comprobaciones necesarias para el cambio. No debilites pruebas, aserciones o umbrales para conseguir que pasen.
- No hagas push, merges, despliegues, cambios remotos, operaciones destructivas, cuentas nuevas o gastos sin mi autorización expresa. Un permiso no se extiende automáticamente a trabajos posteriores.
- Los commits y merges deben llevar exclusivamente mi autoría, sin coautorías, firmas ni menciones a herramientas o agentes de IA.
- No interfieras con otros proyectos ni termines procesos ajenos.
- Explica los avances y resultados en español sencillo y concreto.
- Completa lo solicitado. Al cerrar, informa qué cambió, cómo lo verificaste, qué límites quedan y qué necesito hacer yo. Actualiza la documentación pertinente.
