# Arquitectura del agente y cómo enchufar las tools

> El loop del agente se arma con el framework que use la materia (pendiente de ver el repo).
> Todo lo demás (corpus, retriever, tools, prompt, evaluación) ya está listo y es independiente del framework.

## 1. Flujo

```mermaid
flowchart TD
    U[Usuario: texto / foto / localidad] --> L{LLM + system prompt}
    L -->|consulta| B[buscar_fichas<br/>RAG BM25 + densos opcional]
    L -->|foto de cultivo| D[diagnosticar_cultivo<br/>crop.health]
    L -->|foto de maleza| M[identificar_maleza<br/>Pl@ntNet]
    L -->|localidad| G[geocodificar] --> C[clima_lote / clima_historico<br/>Open-Meteo]
    L -->|término| A[glosario<br/>AGROVOC]
    L -.->|opcional| E[info_eppo]
    B & D & M & C & A & E --> L
    L --> R[Respuesta con citas<br/>+ guardrails]
```

Caso típico (foto + lugar): `diagnosticar_cultivo` → por cada candidato `buscar_fichas(... síntomas)` → `buscar_fichas(... condiciones predisponentes)` → `geocodificar` + `clima_lote` → respuesta: *lo más probable · cómo confirmarlo · riesgo con el clima · qué hacer · fuentes*.

## 2. Tools (`agente/registro_tools.py`)

| Tool | Entrada | Salida | Estado |
|---|---|---|---|
| `buscar_fichas` | consulta, cultivo?, k?, fuente?, mas_reciente? | fragmentos con título, sección, fecha y URL | ✅ |
| `diagnosticar_cultivo` | ruta_imagen, lat?, lon? | cultivo + 3 problemas probables con probabilidad | 🔑 falta key |
| `identificar_maleza` | ruta_imagen, organo? | 5 especies candidatas con score | 🔑 falta key |
| `geocodificar` | lugar | lat, lon, provincia, departamento | ✅ |
| `clima_lote` | lat, lon, dias≤16 | indicadores + tabla diaria (T, lluvia, HR, mojado de hoja, ET0, humedad de suelo) | ✅ |
| `clima_historico` | lat, lon, desde, hasta | indicadores + tabla diaria | ✅ |
| `glosario` | termino | etiqueta es/en, sinónimos, más amplio/específico | ✅ |
| `info_eppo` | nombre_cientifico | código EPPO + hospederos | 🔑 falta token |

`registro_tools.py` expone:
- `schemas_openai()` → lista para `tools=` de OpenAI / compatibles (Groq, Ollama, LM Studio, vLLM).
- `schemas_anthropic()` → lista para `tools=` de la API de Claude.
- `ejecutar(nombre, args)` → corre la tool y devuelve JSON en texto (lo que se le devuelve al LLM).

### Loop mínimo (pseudocódigo, cualquier proveedor con function calling)
```python
mensajes = [{"role": "system", "content": open("agente/prompts/system_prompt.md").read()},
            {"role": "user", "content": pregunta}]
while True:
    resp = llm(mensajes, tools=schemas_openai())
    if not resp.tool_calls:
        break                        # respuesta final
    mensajes.append(resp.message)
    for call in resp.tool_calls:
        mensajes.append({"role": "tool", "tool_call_id": call.id,
                         "content": ejecutar(call.function.name, call.function.arguments)})
```

### LangChain / LangGraph
```python
from langchain_core.tools import StructuredTool
from agente.registro_tools import TOOLS
tools = [StructuredTool.from_function(t["func"], name=n, description=t["description"]) for n, t in TOOLS.items()]
# luego: create_react_agent(modelo, tools, prompt=system_prompt)  (langgraph.prebuilt)
```

### MCP
Cada entrada de `TOOLS` se puede registrar en un servidor MCP (p. ej. con el SDK `mcp` de Python, `@server.tool()`), así el agente sirve también desde Claude Desktop u otro cliente MCP.

## 3. RAG — decisiones de diseño (para el informe)

- **Chunking por sección de ficha** (no por tamaño fijo): cada sección de SINAVIMO responde a un tipo de pregunta distinto (síntomas vs. condiciones vs. biología). Las secciones cortas (tipo, taxonomía, condición, sinonimia) se agrupan en un chunk "Identidad" porque sueltas metían ruido.
- **Encabezado enriquecido**: cada chunk empieza con `Nombre científico (nombres vulgares SINAVIMO + alias usados en Argentina) [tipo · grupo]`. Así "roya común" o "cogollero" encuentran la ficha aunque la sección no repita el nombre.
- **Bibliografía fuera del índice** (queda en el archivo para citar).
- **Informes de chicharrita**: ventanas de 1.200 caracteres con 200 de solapamiento, por página, y **bonus de recencia** cuando la pregunta dice "último", "este mes", "cómo viene"…
- **Retriever**: BM25 con normalización en español (sin tildes, stopwords, stemming liviano); filtro por cultivo y por fuente. Soporta embeddings densos opcionales fusionados por Reciprocal Rank Fusion, pero en la ablation **no mejoraron** (ver `04-evaluacion.md`), así que el índice entregado es BM25 puro.
- **Idea de mejora con LLM**: antes de `buscar_fichas`, pedirle al LLM que reescriba la descripción del usuario en vocabulario técnico ("orugas que caminan arqueadas" → "isoca medidora, defoliación en soja"). Es barato y ataca justo los fallos de BM25.
- **Diccionario de nombres vulgares** armado desde el corpus: si la consulta menciona un nombre vulgar, la ficha correspondiente recibe un bonus.

Resultados del retriever en `04-evaluacion.md`.

## 4. Guardrails (implementados en el prompt; verificarlos en la evaluación)

| Situación | Comportamiento esperado | Pregunta de prueba |
|---|---|---|
| Piden producto/dosis | No recetar; manejo integrado + derivar a Ing. Agrónomo, etiqueta registrada (CASAFE) y receta fitosanitaria | `g01` |
| Fuera de alcance | Decirlo en una oración y ofrecer lo que sí puede hacer | `g02` |
| Plaga inexistente / sin datos | "No encontré información en las fuentes"; no inventar | `g03` |
| Foto dudosa | Si prob. < 0,5 o no es planta → pedir otra foto | `g04` |
| Plaga ausente en Argentina | Decir que SINAVIMO la registra como ausente | auto `a-spissistilus-festinus-condicion_pais` |
| Siempre | Citar URL de ficha/informe; diagnóstico "orientativo" | todas |

¿Por qué el agente no receta? Porque las aplicaciones de fitosanitarios requieren receta de un profesional matriculado (en Córdoba, Ley 9164 y receta fitosanitaria digital) y porque un error de dosis tiene consecuencias reales. Es un buen punto para la sección de ética/limitaciones del informe.

## 5. Memoria de la conversación

Guardar en el estado del agente (o en el historial) los datos del lote apenas aparecen, para no volver a preguntarlos: `cultivo`, `localidad` (+ lat/lon), `estado_fenologico`, `fecha_siembra`, `sintomas_observados`. En LangGraph, un `TypedDict` de estado; en un loop propio, un dict que se agrega al system prompt como "Contexto del lote".
