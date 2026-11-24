# Agente de ejemplo: flujo de casos (S1-32)

## 1. Propósito

Este módulo implementa un agente de demostración mediante un grafo de ejecución con LangGraph. Su objetivo es mostrar una estructura reutilizable para construir agentes con:

- Responsabilidades separadas por nodo.
- Estado compartido entre pasos.
- Contratos tipados para validar entradas y salidas.
- Manejo explícito de errores.
- Revisión y decisión humana.
- Pruebas unitarias de los distintos escenarios.

El ejemplo utiliza una factura simulada y herramientas deterministas. No realiza operaciones sobre documentos reales ni utiliza un modelo de lenguaje.

## 2. Alcance y limitaciones

Esta implementación demuestra el patrón de orquestación, no una integración productiva.

| Elemento | Implementación |
|---|---|
| Orquestación | LangGraph |
| Estado | `TypedDict` |
| Validación de datos | Pydantic |
| Herramientas | Funciones deterministas simuladas |
| Manejo de importes | `Decimal` |
| Revisión humana | `interrupt()` |
| Persistencia | `InMemorySaver` |
| Modelo LLM | No utilizado |
| MCP | No utilizado |
| Base de datos | No utilizada |

El estado se conserva en memoria y se pierde al cerrar el proceso. Para reanudar un caso debe utilizarse la misma instancia de `FlujoCasos`.

La comparación aritmética es una regla de demostración y no representa la validación integral de una factura.

## 3. Arquitectura del agente

El flujo está compuesto por cuatro nodos:

```text
              START
                |
                v
           EXTRACTOR
                |
                v
           VALIDADOR
                |
                v
            REDACTOR
                |
                v
       REVISION_ANALISTA
                |
           interrupt()
                |
          Pausa del grafo
                |
       Decisión del analista
                |
          Command(resume)
                |
                v
               END
```

### 3.1 Extractor

Función: `extraer_factura_demo()`.

- Genera una factura de demostración.
- Construye el resultado utilizando `FacturaExtraida` y `CampoLeido`.
- Entrega la factura serializada al estado del grafo.

### 3.2 Validador

**Nodo del grafo:** `validador()`.

**Herramienta utilizada:** `validar_factura_demo()`.

- Comprueba que exista la factura en el estado.
- Valida su estructura mediante `FacturaExtraida`.
- Comprueba la presencia de subtotal, impuestos y total.
- Convierte los importes a `Decimal`.
- Compara subtotal + impuestos contra el total.

Resultados posibles:

- `aceptado`: los importes coinciden.
- `humana`: existe una diferencia y se requiere revisión humana.

Los datos incompletos o inválidos generan errores explícitos.

### 3.3 Redactor

Función: `redactar_demo()`.

- Recibe el motivo generado por el validador.
- Comprueba que el texto no esté vacío.
- Construye una explicación para el analista.

### 3.4 Revisión del analista

Función: `revision_analista()`.

- Utiliza `interrupt()` para detener la ejecución.
- Presenta el identificador, el resultado sugerido y la explicación.
- Espera una decisión humana.
- Valida la respuesta mediante `DecisionAnalista`.

La recomendación del agente y la decisión humana se almacenan por separado. El agente no sustituye la responsabilidad del analista.

## 4. Estructura de archivos

```text
backend/
└── grafo_casos/
    ├── flujo.py
    ├── herramientas_demo.py
    ├── README.md
    ├── requirements.txt
    └── tests/
        └── test_flujo.py
```

Responsabilidades:

| Archivo | Responsabilidad |
|---|---|
| `flujo.py` | Estado, nodos y orquestación del grafo |
| `herramientas_demo.py` | Herramientas deterministas y validación de importes |
| `tests/test_flujo.py` | Pruebas unitarias |
| `README.md` | Documentación y guía de reutilización |
| `requirements.txt` | Dependencias del módulo |

## 5. Estado y contratos

### EstadoCaso

`EstadoCaso` es un `TypedDict` que describe los datos compartidos entre nodos.

Sus campos principales son:

- `caso_id`: identificador del caso.
- `factura`: representación serializada de la factura.
- `resultado_sugerido`: recomendación del validador.
- `motivo`: justificación de la validación.
- `explicacion`: texto generado para el analista.
- `decision_analista`: decisión humana registrada.

Un `TypedDict` describe la estructura esperada, pero no valida automáticamente los datos durante la ejecución. Por eso los nodos incorporan validaciones explícitas.

### FacturaExtraida

Se reutiliza el contrato compartido `FacturaExtraida`, junto con `CampoLeido`, desde:

`datos/steward_datos/contratos.py`

No se crean modelos duplicados ni se modifican los contratos compartidos.

### DecisionAnalista

Modelo Pydantic definido en `flujo.py`.

Contiene:

- `resultado`: `aceptado` o `rechazado`.
- `motivo`: texto obligatorio que justifica la decisión.

La configuración rechaza campos adicionales y elimina espacios al inicio y al final de las cadenas.

## 6. Manejo de errores

El agente valida los datos antes de continuar con pasos que dependen de ellos.

| Situación | Comportamiento |
|---|---|
| Identificador vacío o inválido | Se genera `ValueError` |
| Caso ya iniciado | Se rechaza el inicio duplicado |
| Factura inexistente | Se genera `ValueError` |
| Estructura de factura inválida | Se genera `ValueError` conservando la causa original |
| Campo monetario faltante | Se genera `ValueError` |
| Importe vacío o no numérico | Se genera `ValueError` |
| Importe no finito | Se genera `ValueError` |
| Motivo de redacción vacío | Se genera `ValueError` |
| Decisión humana inválida | Pydantic genera `ValidationError` |
| Caso sin pausa pendiente | Se genera `ValueError` |

Los errores no se convierten silenciosamente en resultados exitosos.

Una diferencia aritmética entre el total capturado y el esperado no se considera un error de ejecución: se representa mediante el resultado `humana`.

## 7. Convención para incorporar prompts

Este ejemplo utiliza funciones deterministas, por lo que no requiere un prompt ejecutado por un LLM.

La convención permite mantener nodos deterministas cuando la tarea puede resolverse mediante reglas de código.

Si posteriormente se incorpora un nodo basado en un modelo de lenguaje, su prompt debe estar versionado y documentar:

1. Objetivo y alcance del nodo.
2. Información de entrada.
3. Herramientas disponibles y sus permisos.
4. Evidencia y fuentes que puede utilizar.
5. Formato esperado de salida.
6. Errores y condiciones de derivación a revisión humana.
7. Restricciones y acciones que el modelo no puede ejecutar.

Los documentos y resultados de herramientas deben tratarse como datos no confiables, no como instrucciones que puedan modificar las reglas del sistema.

El modelo puede generar recomendaciones, pero no debe sustituir las decisiones que corresponden a una persona.

## 8. Ejecución del agente

Desde la raíz del monorepo, con el entorno virtual configurado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\backend\grafo_casos\requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .\datos
```

Ejemplo de inicio:

```python
from backend.grafo_casos.flujo import FlujoCasos

flujo = FlujoCasos()

estado = flujo.procesar_caso("caso-001")

print(estado["resultado_sugerido"])
print(estado["explicacion"])
```

Al finalizar `procesar_caso()`, el grafo queda pausado esperando la decisión del analista.

Ejemplo de reanudación:

```python
decision = {
    "resultado": "rechazado",
    "motivo": "El total de la factura no coincide."
}

estado_final = flujo.reanudar_caso(
    "caso-001",
    decision
)

print(estado_final["decision_analista"])
```

La decisión debe cumplir el contrato `DecisionAnalista`.

Es necesario conservar la misma instancia de `FlujoCasos` durante el proceso, ya que el checkpoint utilizado es `InMemorySaver`.

## 9. Pruebas unitarias

Ejecutar desde la raíz del monorepo:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s backend/grafo_casos/tests -v
```

La suite contiene 13 pruebas.

### Pruebas del flujo

- Recorrido completo hasta la pausa humana.
- Rechazo de decisiones inválidas sin consumir la pausa.
- Aislamiento entre casos.
- Rechazo de identificadores inválidos.
- Rechazo de facturas con estructura inválida.
- Rechazo de motivos inválidos en el redactor.

### Pruebas de herramientas

- Factura consistente.
- Factura con diferencias.
- Campo obligatorio faltante.
- Importes vacíos o inválidos.
- Importes no finitos.
- Motivo de redacción vacío.
- Redacción con motivo válido.

Resultado esperado:

```text
Ran 13 tests

OK
```

Las herramientas simuladas permiten comprobar la orquestación y el comportamiento esperado, pero no demuestran la precisión de un modelo de lenguaje ni el funcionamiento de servicios externos.

## 10. Guía para reutilizar el patrón

Para construir otro agente siguiendo esta convención:

1. **Definir el objetivo:** delimitar qué responsabilidad tendrá el agente.
2. **Definir los contratos:** reutilizar modelos existentes y establecer entradas y salidas.
3. **Separar responsabilidades:** implementar cada paso como un nodo independiente.
4. **Definir las herramientas:** utilizar funciones con entradas y salidas explícitas.
5. **Validar los datos:** comprobar las entradas antes de ejecutar operaciones dependientes.
6. **Controlar los errores:** distinguir entre errores de ejecución, resultados de negocio y situaciones que requieren intervención humana.
7. **Incorporar revisión humana:** separar las recomendaciones de las decisiones autorizadas.
8. **Agregar pruebas:** cubrir recorridos exitosos, entradas inválidas, errores de herramientas y pausas humanas.
9. **Documentar:** explicar la arquitectura, los contratos, las dependencias, las limitaciones y cómo ejecutar el agente.

### Principios de diseño

- Cada nodo debe tener una responsabilidad definida.
- Las entradas y salidas deben ser observables.
- Los permisos deben controlarse en el código, no delegarse al modelo.
- Los errores no deben ocultarse.
- Las decisiones humanas deben mantenerse separadas de las recomendaciones automáticas.
- Las pruebas deben verificar tanto el funcionamiento esperado como los escenarios de error.

---

**Alcance de esta implementación:** ejemplo determinista de agente con LangGraph, validación de datos, manejo de errores, revisión humana y pruebas. No incluye integración con LLM, MCP, servicios externos, persistencia productiva ni el grafo del chat.
