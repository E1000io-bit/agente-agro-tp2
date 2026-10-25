# Registro de decisiones

Cada decisión que cambia cómo funciona el agente, con fecha, alternativas y motivo. Las nuevas van **arriba**. Si una decisión se revierte, no se borra: se agrega una nueva que la reemplace y se marca la vieja como "Reemplazada por D-xx".

Plantilla:
```
## D-XX · Título — AAAA-MM-DD · Estado: vigente | reemplazada por D-YY
**Contexto:** qué problema había.
**Alternativas:** A, B, C.
**Decisión:** qué se eligió.
**Motivo / evidencia:** por qué (números si hay).
**Consecuencias:** qué implica o qué queda pendiente.
```

---

## D-07 · BM25 como retriever por defecto (sin embeddings densos) — 2026-10-25 · Estado: vigente
**Contexto:** había que elegir entre recuperación léxica, densa o híbrida.
**Alternativas:** BM25 · denso `multilingual-e5-small` · denso `multilingual-e5-base` · híbridos RRF.
**Decisión:** BM25 con normalización en español, alias argentinos en el encabezado de cada chunk y filtro por cultivo.
**Motivo / evidencia:** en el set manual BM25 logró hit@1 0,73 / MRR 0,82; los híbridos 0,69 / 0,77–0,80 y los densos solos 0,38–0,46 de hit@1 (`docs/04-evaluacion.md`).
**Consecuencias:** el código soporta densos (`--embeddings`) para volver a probar con otros modelos o con *query rewriting*.

## D-06 · Chunking por sección de ficha + chunk "Identidad" — 2026-10-25 · Estado: vigente
**Contexto:** las fichas de SINAVIMO tienen secciones que responden preguntas distintas; las secciones cortas sueltas metían ruido.
**Alternativas:** ventanas de tamaño fijo · una ficha = un chunk · una sección = un chunk.
**Decisión:** una sección = un chunk, con encabezado `nombre científico (nombres vulgares + alias) [tipo · grupo]`; secciones cortas agrupadas en "Identidad"; bibliografía fuera del índice.
**Motivo / evidencia:** hit@3 pasó de 0,81 a 0,88 y hit@1 de 0,65 a 0,73 con estos cambios.

## D-05 · El agente no recomienda productos ni dosis — 2026-10-24 · Estado: vigente
**Contexto:** un error de dosis tiene consecuencias reales y la aplicación requiere receta de un profesional matriculado (en Córdoba, Ley 9164 y receta fitosanitaria digital).
**Decisión:** guardrail en el system prompt; ante pedidos de dosis, manejo integrado + derivación a Ing. Agrónomo, etiqueta registrada (Guía CASAFE) y receta. El campo `treatment` de crop.health no se transmite como receta.
**Evidencia a generar:** pregunta `g01` y chequeos `sin_dosis` / `deriva` en `scripts/evaluar_agente.py`.

## D-04 · crop.health como tool de imagen principal; VLM como alternativa — 2026-10-24 · Estado: vigente
**Contexto:** entrenar un modelo propio no entra en los tiempos del TP, y los modelos entrenados en PlantVillage generalizan mal a campo.
**Alternativas:** modelo propio · crop.health (Kindwise) · VLM del LLM · Pl@ntNet (sólo especies).
**Decisión:** crop.health para enfermedades y plagas (cubre maíz, soja y trigo; 100 créditos gratis) con caché; Pl@ntNet para malezas; comparar contra el VLM en la evaluación.
**Consecuencias:** no cubre girasol ni maní; cuidar los créditos.

## D-03 · Open-Meteo para el clima del lote — 2026-10-24 · Estado: vigente
**Alternativas:** Open-Meteo · NASA POWER · SMN.
**Decisión:** Open-Meteo (sin key, pronóstico + histórico + geocoding, incluye probabilidad de mojado de hoja y humedad de suelo). NASA POWER queda como respaldo.

## D-02 · SINAVIMO + informes de chicharrita como corpus base — 2026-10-24 · Estado: vigente
**Contexto:** hacían falta fuentes oficiales, en español, citables y de Argentina.
**Decisión:** fichas de SINAVIMO (estructura homogénea, incluye "condiciones predisponentes") y los informes de la Red Nacional de Monitoreo para preguntas de coyuntura. CASAFE y el mapa de malezas de Aapresid se usan sólo para derivar.

## D-01 · Alcance: maíz, soja, trigo y maní de la región centro; 70 plagas — 2026-10-24 · Estado: vigente
**Contexto:** un alcance abierto hace imposible evaluar bien.
**Decisión:** 4 cultivos y 70 plagas/enfermedades/malezas (`data/plagas_objetivo.csv`). Variante del TP: agente RAG + diagnóstico por foto, con cruce climático como extra (ver `docs/00-idea-y-plan.md`).
