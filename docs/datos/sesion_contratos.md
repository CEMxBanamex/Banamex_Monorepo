# Sesión de contratos (0.7.4): lo que el frente de Datos necesita cerrar

Duración sugerida: 1 hora. Cada punto dice con quién se cierra y qué proponemos. Los contratos viven en `datos/steward_datos/contratos.py`; su resumen, en [`contratos_tools.md`](contratos_tools.md).

| # | Tema | Con quién | Propuesta de Datos |
|---|---|---|---|
| 1 | Forma de `FacturaExtraida` | Carlos Delgado | La de `contratos_tools.md`: `valor` como texto impreso, `confianza` 0–100 por campo, `bbox` opcional y `texto_completo` para R-030. |
| 2 | Confianza por campo del modelo de visión | Carlos Delgado | Pedirla al modelo (logprobs o autoevaluación). Mientras no exista, R-003 avisa con un hallazgo informativo. Decidir si esos casos van a revisión humana (`sin_confianza: revision`). |
| 3 | Validador: nodo de código o agente con LLM | Carlos Delgado, Iris | Nodo de código con `preparar_para_redactor`: mismo resultado siempre, sin GPU. 39/39 casos de evaluación con su cita exacta. |
| 4 | Filtro de `buscar_politicas` en el validador | Carlos Delgado / Ramos | Buscar por `reglas` e `historia`, no por `tipo`: con `tipo=facturas`, R-002 recibe P-001 en lugar de P-011 y las 6 reglas de la Historia 2 no reciben política. |
| 5 | Umbral de `buscar_politicas` con filtro por regla | Carlos Delgado / Ramos | No aplicar el umbral cuando viene `reglas`; la sección exacta no debe perderse por similitud baja. |
| 6 | `RAG_UMBRAL_SIMILITUD` | Carlos Delgado | Correr `scripts/evaluar_rag.py --calibrar` con `embeddinggemma:300m` y fijar el valor. |
| 7 | Guardar hallazgos | Carlos Delgado, Yael | El grafo guarda todo al final con `persistencia.guardar_resultado`, en una transacción, para que un caso no quede a medias. |
| 8 | Salida del agente de gobernanza | Carlos Ramos | Texto con la línea final `Fuentes: …` (ver `datos/agentes/gobernanza.md`); para evaluar, el grafo escribe JSONL con `id`, `tools` y `respuesta`. |
| 9 | Seguridad del SQL libre | Juan Pablo | Lista blanca de funciones en `sqlglot` (rechazar `set_config`, `current_setting`, `pg_*`, `dblink`); conexión como `steward_consultas`; contexto con `fijar_en_bd`. Crear `steward_backend`, `steward_mcp` y `steward_consultas` antes de migrar. |
| 10 | `consultar_catalogo` y `listar_vistas_consultables` | Juan Pablo | Leer `catalogo_tablas` y `catalogo_columnas` (`consultable = true`). El agente de gobernanza cita `Catálogo: <tabla>`. |
| 11 | Contexto del usuario en el MCP | Juan Pablo, Carlos Ramos | `usuario_actual.set(ContextoUsuario(...))` desde el JWT en cada petición. Roles válidos: `analista`, `administrador`. |
