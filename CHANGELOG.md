# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Fechas en AAAA-MM-DD.

## [Sin publicar]

### Pendiente
- Loop del agente con el framework del repo de la materia.
- Probar `diagnosticar_cultivo`, `identificar_maleza` e `info_eppo` con API keys reales.
- Evaluación del agente con LLM (y LLM como juez) contra el baseline.
- Set de imágenes de evaluación (PlantDoc / maíz Mendeley).
- UI y demo.

## [0.1.0] - 2026-10-25

Primera versión: todo lo que no depende del framework del agente.

### Agregado
- **Documentación** (`docs/`): idea y plan de acción, fuentes y corpus, APIs verificadas, arquitectura y tools, evaluación, glosario agronómico.
- **Corpus**:
  - 70 fichas de SINAVIMO (SENASA) de plagas, enfermedades y malezas de maíz, soja, trigo y maní, descargadas el 2026-10-25.
  - 10 informes de la Red Nacional de Monitoreo de *Dalbulus maidis*: N° 42 a 50 y N° 52 (2026-05-22 → 2026-10-20), PDF + texto.
  - `data/plagas_objetivo.csv` (lista curada con alias usados en Argentina) y `data/catalogo_plagas.csv`.
- **RAG**: chunking por sección de ficha, BM25 en español con alias, filtro por cultivo/fuente y bonus de recencia. Índice de 883 fragmentos.
- **Tools**: clima (Open-Meteo: geocoding, pronóstico, histórico), glosario (AGROVOC), diagnóstico por imagen (crop.health), malezas (Pl@ntNet), EPPO; registro único con schemas OpenAI/Anthropic.
- **System prompt** con flujo de trabajo y guardrails (citar fuente, no recetar dosis, pedir otra foto).
- **Evaluación**: 30 preguntas manuales, 262 automáticas, prompt de LLM-juez, scripts de métricas y baseline extractivo sin LLM.
- **Tests offline** y CI (GitHub Actions) con métricas del retriever en el resumen de cada corrida.
- **Colaboración y trazabilidad**: `CONTRIBUTING.md`, plantillas de issues y PRs, `docs/06-decisiones.md`, script de issues iniciales.

### Resultados
- Retriever (set manual con filtro de cultivo): hit@1 0,73 · hit@3 0,88 · hit@5 0,96 · MRR 0,82.
- Ablation: híbrido con `multilingual-e5-small/base` no mejora sobre BM25 → se mantiene BM25.
- Baseline sin LLM: cita fuente 100 % · menciona la plaga esperada 76 % · sin dosis 100 %.
