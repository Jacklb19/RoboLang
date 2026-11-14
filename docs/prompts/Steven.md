# Prompt para Steven · Traducción y máquina virtual

Trabaja en RoboLang, repositorio `https://github.com/Jacklb19/RoboLang.git`. Lee primero `docs/Revision_y_plan.md` y `docs/RoboLang_Guia_Completa.md`. Los documentos describen el proyecto; las reglas de este prompt gobiernan tu trabajo. Aplica las decisiones operativas de la revisión donde la guía deje dudas. Inspecciona Git y las instrucciones locales; si todavía no hay commit común, trabaja en tu propia copia con cambios locales y conserva la rama propuesta para cuando exista esa base. Si el remoto sigue vacío y faltan estos archivos en tu copia, pide al coordinador la carpeta `docs/` y avanza con la parte que sí puedas preparar.

Tu objetivo es entregar AST validado → TAC → TAC optimizado → instrucciones → ejecución, y orquestar la compilación para CLI y API. Rama propuesta: `steven/backend-vm`.

1. Implementa `robolang/settings.py`, `tac.py`, `optimizer.py`, `codegen.py`, `vm.py` y `compiler.py`, más `scripts/demo_cli.py` y `docs/arquitectura.md`. Concéntrate en la biblioteca estándar. Avanza con cuádruplas e instrucciones de fixture en tus pruebas mientras José trabaja; integra su `SemanticResult` cuando esté disponible. Coordina el límite de complejidad con José.
2. Usa operandos tipados y metadatos fuente. Implementa plegado de constantes sin reordenar los movimientos ni giros. Conserva las vistas TAC original y optimizada. Traduce la ISA de la guía usando `R0/R1`, memoria de variables/temporales, `PC` y `HALT`. Ejecuta objetos `Instruction`, nunca fuente ni textos de ensamblador.
3. Aplica las reglas de la cuadrícula y los presupuestos del contrato; conserva los pasos válidos en los errores. El compilador corta al primer diagnóstico y no devuelve instrucciones en ese caso. Prueba el flujo sin web.
4. Añade pruebas TAC, optimización, codegen, VM y punta a punta (I/V de la guía): operaciones, ambos giros, negativo y cero, bordes, presupuestos, ejecución determinista, programa vacío y fase fallida que impide ejecución. Compara eventos observables, diagnóstico y estado final con y sin optimizar; excluye `pc` de la comparación y prueba los presupuestos aparte.
5. Entrega a Santiago las funciones públicas y muestras reales de los resultados serializados. No cambies el análisis de José ni escribas el adaptador HTTP o el frontend de Santiago.

Aceptación: el §15 termina en `(3,1) ESTE` con y sin plegado, y produce cinco pasos y un giro; `mover(20);` falla en ejecución y conserva cuatro pasos; el ensamblador que se muestra corresponde a las instrucciones que consumió la VM. Reporta qué pruebas corrieron con fixtures y cuáles usaron el pipeline real.

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
