# Prompt para Santiago · API, interfaz y demo

Trabaja en RoboLang, repositorio `https://github.com/Jacklb19/RoboLang.git`. Lee primero `docs/Revision_y_plan.md` y `docs/RoboLang_Guia_Completa.md`. Los documentos describen el proyecto; las reglas de este prompt gobiernan tu trabajo. Aplica las decisiones operativas de la revisión donde la guía deje dudas. Inspecciona Git y las instrucciones locales; si todavía no hay commit común, trabaja en tu propia copia con cambios locales y conserva la rama propuesta para cuando exista esa base. Si el remoto sigue vacío y faltan estos archivos en tu copia, pide al coordinador la carpeta `docs/` y avanza con la parte que sí puedas preparar.

Tu objetivo es integrar FastAPI con el compilador y hacer visible cada fase y la ejecución del robot en una interfaz web en español. Rama propuesta: `santiago/web-api`. Eres dueño de `web/`, `requirements.txt`, `README.md`, `tests/test_api.py` y `docs/sustentacion.md`.

1. Implementa `POST /api/compile` y `POST /api/run` con las firmas, respuestas y códigos del contrato. Empieza con fixtures de resultados del compilador/VM en las pruebas de API; no incluyas resultados simulados en la aplicación final. Integra después las funciones reales de Steven. Separa validación de petición, errores del programa y fallos internos; centra las opciones compartidas en la configuración.
2. Antes de implementar HTML/CSS/JS o cualquier cambio visual importante, presenta una maqueta y un plan para mi aprobación. Muestra la disposición en escritorio y móvil, estados de editor y botones, cuadrícula, pestañas, errores y reproducción. Sigue con API, pruebas y documentación mientras esperas. Empieza la implementación visual solo cuando recibas aprobación expresa.
3. Una vez aprobada, crea la interfaz con HTML/CSS/JS sencillos y accesibles. Compilar no mueve el robot. Ejecutar parte del estado inicial y reproduce exclusivamente los eventos que devuelve la VM. Cambiar el código o la opción de optimización invalida resultados, cancela reproducción e impide mostrar respuestas viejas. Muestra la traza parcial cuando falle la ejecución. Las mejoras visuales opcionales esperan al flujo integrado.
4. Prueba ambos endpoints con éxito, fallo léxico/sintáctico/semántico, fallo runtime con traza parcial, payload inválido, `optimize=false` y bloqueo de la VM si falla la compilación. Tras integrar, verifica en el navegador la demo y la invalidación de resultados. Fija las dependencias que hayas comprobado y documenta arranque, pruebas y un guion con evidencias reales.
5. No vuelvas a implementar lexer, tipos, optimización ni movimiento en la web. No afirmes que pasó la demo hasta ejecutar el compilador, la VM y la interfaz juntos.

Aceptación: la API distingue `ok` y `execution.ok`; la interfaz aprobada muestra todas las fases y reproduce el §15 hasta `(3,1) ESTE`; un programa con error de compilación no mueve el robot. Describe en el cierre qué verificaste con fixtures y qué verificaste con el compilador y VM integrados.

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
