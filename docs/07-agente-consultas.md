# Agente de consultas (texto, sin fotos)

Primera versión del agente: responde consultas por texto. El diagnóstico por foto queda para una etapa posterior (las tools `diagnosticar_cultivo` / `identificar_maleza` ya existen pero no están conectadas).

## 1. Cómo se alinea con la materia

El repo de la cátedra ([`17_Agentes`](https://github.com/lauraceciliadiazdavila/IA-LIDeSIA-Dpto-Computacion/tree/main/17_Agentes)) arma un agente en dos pasos, y nosotros seguimos el mismo recorrido:

| Notebook de la cátedra | Lo que vemos ahí | Nuestro equivalente |
|---|---|---|
| `Agente_ReAct.ipynb` | Hugging Face Router con cliente OpenAI y `Qwen/Qwen2.5-7B-Instruct`; `Tool` (dataclass); prompt ReAct; parser con regex; loop `Thought → Action → Observation → FINAL`; `print_trace` | `agente/llm.py` + `agente/react_manual.py` |
| `Agente_LangChain.ipynb` | `ChatOpenAI` apuntando al router; `@tool`; `create_agent`; *skill* que combina tools y se expone como tool | `agente/agente_langchain.py` (skill: `evaluar_riesgo`) |
| "Próximos pasos: RAG Agents" | agentes conectados a bases de conocimiento | `buscar_fichas` sobre 70 fichas SINAVIMO + informes de chicharrita |

Diferencias que agregamos (y conviene contar en el informe): **RAG propio** como herramienta principal, **memoria** de conversación, **guardrails deterministas** (filtro de dosis antes y después del LLM) y **evaluación** contra un baseline.

Detalle de la notebook de la cátedra: el prompt pide terminar con `FINAL:` pero el parser busca `Final Answer:`. Nuestro parser acepta los dos.

## 2. Herramientas del agente de consultas

| Tool | Para qué | Formato ReAct manual |
|---|---|---|
| `buscar_fichas` | Síntomas, biología, condiciones predisponentes, presencia en Argentina | `Action: buscar_fichas \| consulta \| cultivo=soja \| k=4` |
| `situacion_chicharrita` | Último informe de la Red Nacional de Monitoreo | `Action: situacion_chicharrita \| región Centro Norte` |
| `clima_lote` | Pronóstico de una localidad (Open-Meteo) | `Action: clima_lote \| Marcos Juárez \| dias=5` |
| `evaluar_riesgo` (**skill**) | Junta condiciones de la ficha + pronóstico para estimar riesgo | `Action: evaluar_riesgo \| mancha amarilla \| localidad=Pergamino \| cultivo=trigo` |
| `glosario` | Término técnico (AGROVOC) | `Action: glosario \| umbral económico` |
| `fecha_actual` | Fecha (sólo ReAct manual, como `now` en la cátedra) | `Action: fecha_actual \|` |

Las funciones reales están en `agente/consultas.py`, y las dos versiones del agente las comparten. Devuelven texto corto (máximo 700 caracteres por fragmento) con la URL de la fuente, para que un modelo de 7B cite bien.

## 3. Cómo usarlo

```bash
cp .env.example .env            # completar HF_TOKEN
python -m agente.chat                         # LangChain
python -m agente.chat --modo react --traza    # ReAct manual mostrando Thought/Action/Observation
python -m agente.react_manual "¿Qué condiciones favorecen la roya común del maíz?"
```
O en Colab: `notebooks/AgroAgente_consultas.ipynb` (mismo formato que las notebooks de la cátedra).

En código:
```python
from agente.react_manual import AgroAgenteReAct
r, traza = AgroAgenteReAct().preguntar("¿Qué es la chicharrita?")

from agente.agente_langchain import crear_agente, preguntar
ag = crear_agente()
preguntar(ag, "¿Qué es la chicharrita?", thread_id="charla-1")
preguntar(ag, "¿Y qué la favorece?", thread_id="charla-1")   # recuerda la anterior
```

## 4. Guardrails

1. **Prompt:** reglas de citar fuente, no recetar, no inventar y quedarse dentro del alcance.
2. **Antes del LLM:** si la pregunta pide producto o dosis (`guardrails.pide_dosis`), se le agrega una nota al mensaje recordando que no debe recetar.
3. **Después del LLM:** si la respuesta igual trae una dosis (`l/ha`, `cc/ha`, `g/ha`…), se reemplaza por la derivación a un Ingeniero Agrónomo, la etiqueta y CASAFE.

## 5. Probarlo y evaluarlo

```bash
python tests/test_agente.py        # loops con LLM simulado (no necesitan token)
python scripts/evaluar_agente.py --agente agente.react_manual:responder
python scripts/evaluar_agente.py --agente agente.agente_langchain:responder
python scripts/evaluar_agente.py --agente agente.baseline_extractivo:responder   # piso: 76 % menciona la plaga esperada
```
Guardar cada `.jsonl` de resultados con un nombre que diga la configuración y el modelo, y copiar la tabla en `docs/04-evaluacion.md`.

## 6. Problemas esperables y qué probar

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| ReAct manual: el modelo escribe `Observation:` inventada o no respeta el formato | Modelo chico | Bajar `temperature`, probar un modelo más grande de `client.models.list()`, reforzar ejemplos en el prompt |
| LangChain: error de tools o el modelo no llama ninguna | El proveedor del router no soporta *function calling* para ese modelo | Cambiar `LLM_MODEL` por otro modelo con tool calling, o usar la versión ReAct manual (que no depende de eso) |
| Respuestas sin URL | Observations largas | Ya se recortan a 700 caracteres por fragmento; bajar `k` |
| "No llegué a una respuesta final" | Loop de tools | Subir `max_steps` o revisar la traza |
| Recupera la ficha equivocada con descripciones coloquiales | Limitación de BM25 (ver `04-evaluacion.md`) | Issue "reescritura de consulta": que el LLM reformule en términos técnicos antes de buscar |
