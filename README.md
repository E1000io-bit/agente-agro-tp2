# AgroAgente — TP2 Inteligencia Artificial

Agente conversacional de consulta fitosanitaria para maíz, soja, trigo y maní de la región centro de Argentina. Responde por texto o foto, cita fuentes oficiales (SENASA/SINAVIMO, Red Nacional de Monitoreo de chicharrita), cruza las condiciones que favorecen cada plaga con el pronóstico del lote y **no receta productos ni dosis**.

> **Estado (27/10/2026):** agente de **consultas por texto** listo en dos versiones, siguiendo `17_Agentes` de la cátedra: ReAct manual y LangChain `create_agent`, con Hugging Face Router y Qwen2.5-7B. Ver [`docs/07-agente-consultas.md`](docs/07-agente-consultas.md). Las fotos quedan para la etapa 2.

## Qué hay en esta carpeta

```
agente-agro-tp2/
├── README.md                      ← este archivo
├── CONTRIBUTING.md                ← cómo trabajamos: issues, ramas, commits, PRs, datos y resultados
├── CHANGELOG.md                   ← qué cambió en cada versión
├── requirements.txt · .env.example · .gitignore · .gitattributes
├── .github/                       ← CI (tests en cada push/PR) + plantillas de issues y PRs
├── docs/
│   ├── 00-idea-y-plan.md          ← idea, variantes de alcance, fuentes investigadas, plan de acción
│   ├── 01-fuentes-y-corpus.md     ← qué se descargó, de dónde, cómo actualizarlo
│   ├── 02-apis.md                 ← endpoints verificados (Open-Meteo, crop.health, Pl@ntNet, AGROVOC, EPPO, NASA POWER)
│   ├── 03-arquitectura-y-tools.md ← flujo, tools, cómo integrarlas, decisiones del RAG, guardrails, memoria
│   ├── 04-evaluacion.md           ← sets de prueba, resultados del retriever, ablation, baseline, protocolo de imágenes
│   ├── 05-glosario-agronomico.md  ← conceptos mínimos (MIP, umbrales, fenología, nombres que confunden)
│   ├── 06-decisiones.md           ← registro de decisiones de diseño con fecha y evidencia
│   └── 07-agente-consultas.md     ← el agente de consultas: alineación con la cátedra, tools, uso, problemas
├── notebooks/AgroAgente_consultas.ipynb ← demo para Colab en el formato de la cátedra
├── data/
│   ├── plagas_objetivo.csv        ← 70 plagas elegidas: cultivo, grupo, prioridad, alias usados en Argentina
│   ├── catalogo_plagas.csv        ← lo mismo + nombres vulgares y condición según SINAVIMO + URL
│   ├── corpus/
│   │   ├── sinavimo/              ← 70 fichas oficiales en Markdown (síntomas, condiciones predisponentes, biología…)
│   │   └── chicharrita/           ← 10 informes recientes (N° 42–50 y 52, hasta 20/10/2026) en PDF + texto
│   ├── index/chunks.jsonl         ← índice del RAG (937 fragmentos)
│   └── eval/
│       ├── preguntas_manual.jsonl ← 30 preguntas difíciles (síntomas sin nombrar la plaga, guardrails)
│       ├── preguntas_auto.jsonl   ← 262 preguntas generadas desde las fichas
│       ├── juez_prompt.md         ← prompt de LLM-as-judge (fidelidad + tasa de respuesta)
│       └── resultados_baseline_extractivo.jsonl
├── agente/
│   ├── llm.py                     ← conexión HF Router (cliente OpenAI / ChatOpenAI), como la cátedra
│   ├── react_manual.py            ← AGENTE ReAct manual (Tool, prompt, parser, loop, traza, memoria)
│   ├── agente_langchain.py        ← AGENTE LangChain (create_agent + @tool + skill + memoria)
│   ├── consultas.py               ← tools de texto compartidas por los dos agentes
│   ├── guardrails.py              ← filtro de dosis antes y después del LLM
│   ├── chat.py                    ← chat por consola
│   ├── prompts/system_prompt_consultas.md ← prompt del agente de consultas
│   ├── prompts/system_prompt.md   ← prompt completo (con fotos, etapa 2)
│   ├── registro_tools.py          ← TODAS las tools + JSON schemas (OpenAI / Anthropic) + ejecutar()
│   ├── rag/indexar.py · buscar.py ← chunking por sección + BM25 en español (+ densos opcional)
│   ├── tools/clima.py             ← Open-Meteo: geocodificar, pronóstico, histórico
│   ├── tools/imagen.py            ← crop.health (enfermedades/plagas) y Pl@ntNet (malezas), con caché
│   ├── tools/glosario.py          ← AGROVOC (FAO)
│   ├── tools/eppo.py              ← EPPO Global Database (opcional)
│   ├── baseline_extractivo.py     ← "agente" sin LLM para comparar
│   └── probar_tools.py            ← prueba rápida de todo
├── scripts/
│   ├── descargar_sinavimo.py      ← baja/actualiza fichas (lista curada, slugs sueltos o todo el sitemap)
│   ├── descargar_informes_chicharrita.py
│   ├── descargar_datasets.py      ← PlantDoc, maíz Mendeley, PlantVillage, IP102 + arma set de imágenes
│   ├── construir_catalogo.py · generar_eval.py
│   ├── evaluar_retriever.py       ← hit@k / MRR
│   ├── evaluar_agente.py          ← corre el set contra tu agente y calcula chequeos
│   └── crear_issues_iniciales.sh  ← crea etiquetas + issues de próximos pasos (gh CLI, una sola vez)
└── tests/                         ← test_offline.py (sin red) · test_agente.py (agentes con LLM simulado)
```

## Arranque rápido

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # completar HF_TOKEN (las otras keys son para la etapa de fotos)

python tests/test_offline.py && python tests/test_agente.py   # tests sin red ni token
python -m agente.chat                                   # chatear con el agente (LangChain)
python -m agente.chat --modo react --traza              # versión ReAct manual mostrando los pasos
python -m agente.probar_tools                           # prueba todas las tools (usa internet)
python -m agente.rag.buscar "manchas circulares con borde rojizo en soja"
python scripts/evaluar_retriever.py                     # hit@3 = 0,88 en el set manual
```

El corpus y el índice ya vienen armados. Para actualizarlos:
```bash
python scripts/descargar_informes_chicharrita.py --n 3  # informes nuevos
python scripts/descargar_sinavimo.py --slugs <slug>     # más fichas
python -m agente.rag.indexar && python scripts/construir_catalogo.py && python scripts/generar_eval.py
```

## Estado

| Pieza | Estado |
|---|---|
| Corpus SINAVIMO (70 fichas) + chicharrita (10 informes) | ✅ descargado 25/10/2026 |
| RAG (chunking, BM25, filtros, alias, recencia) | ✅ hit@1 0,73 · hit@3 0,88 · hit@5 0,96 (set manual) |
| Tools clima / geocoding / glosario | ✅ probadas contra las APIs reales |
| Tools crop.health / Pl@ntNet / EPPO | 🔑 endpoints verificados, falta probar con API key |
| System prompt + guardrails | ✅ escrito, falta evaluarlo con el LLM |
| Evaluación: sets, juez, scripts, baseline sin LLM | ✅ |
| Agente de consultas: ReAct manual + LangChain, memoria, guardrails, chat, notebook | ✅ probado con LLM simulado; falta correrlo con `HF_TOKEN` y evaluarlo |
| Fotos (etapa 2) + UI | ⏳ |

## Próximos pasos (plan compacto)

1. Cargar `HF_TOKEN`, probar `python -m agente.chat --modo react --traza` y ajustar el prompt según cómo responde Qwen2.5-7B.
2. Evaluar las dos versiones con `scripts/evaluar_agente.py` + LLM-juez → tabla vs. baseline (76 %).
3. Reescritura de consulta para mejorar la recuperación con descripciones coloquiales.
4. Etapa 2, fotos: crop.health / Pl@ntNet + set de imágenes (`descargar_datasets.py`).
5. UI simple, informe y demo (`docs/04-evaluacion.md` §5).

## Cómo colaborar

Cada tarea es un issue, cada issue una rama, y todo entra a `main` por Pull Request revisado con el CI en verde. Las decisiones van a `docs/06-decisiones.md`, los resultados de evaluación a `data/eval/` (sin pisar los anteriores) y los cambios de versión a `CHANGELOG.md`. Detalle en [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Fuentes y licencias

- Fichas: SINAVIMO – SENASA (información oficial de acceso libre). Cada archivo conserva su URL y fecha de descarga; citar siempre la ficha original.
- Informes: Red Nacional de Monitoreo de *Dalbulus maidis* (vía MAIZAR / INTA).
- Clima: Open-Meteo (CC BY 4.0). Glosario: AGROVOC (FAO).
- Uso académico. El agente es orientativo y no reemplaza el diagnóstico de un Ingeniero Agrónomo.
