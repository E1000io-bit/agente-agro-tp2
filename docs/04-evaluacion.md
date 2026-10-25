# Evaluación

## 1. Conjuntos de prueba (`data/eval/`)

| Archivo | Qué tiene | Para qué |
|---|---|---|
| `preguntas_manual.jsonl` | 30 preguntas escritas a mano: 21 de diagnóstico por descripción de síntomas (sin nombrar la plaga), 3 factuales, 2 temporales (chicharrita), 4 de guardrails (dosis, fuera de alcance, plaga inventada, foto dudosa) | La evaluación "difícil" y la que más vale mostrar |
| `preguntas_auto.jsonl` | 262 preguntas generadas desde las fichas (`scripts/generar_eval.py`): condiciones, síntomas, biología y presencia en Argentina, cada una con la ficha y sección de referencia | Fidelidad a escala con LLM-juez |
| `juez_prompt.md` | Prompt de LLM-as-judge (fidelidad por afirmaciones atómicas + tasa de respuesta + chequeo de dosis) | Métrica principal de calidad |
| `imagenes/` (se arma con `scripts/descargar_datasets.py armar-set`) | N fotos por clase de PlantDoc / maíz Mendeley mapeadas a slugs | Accuracy de la tool de imagen |

## 2. Resultados del retriever (línea de base, sólo BM25)

`python scripts/evaluar_retriever.py` — 25/10/2026, 70 fichas + 10 informes, 883 chunks:

| Set | n | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|---|
| Manual (síntomas descritos, con filtro de cultivo) | 26 | 0,73 | 0,88 | 0,96 | 0,82 |
| Manual sin filtro de cultivo | 26 | 0,65 | 0,81 | 0,85 | 0,74 |
| Automático (nombra la plaga) | 262 | 0,99 | 1,00 | 1,00 | 1,00 |

Lecturas para el informe:
- Las preguntas automáticas son fáciles porque nombran la plaga: sirven para medir **fidelidad de la generación**, no la recuperación.
- El filtro por cultivo suma ~8 puntos de hit@3 → conviene que el agente pregunte el cultivo antes de buscar.
- Fallos típicos de BM25: descripciones con palabras que la ficha no usa ("forma de cigarro", "telarañas", "sobrevivió al glifosato").

**Ablation densos vs. BM25 (ya corrida, set manual con filtro de cultivo):**

| Retriever | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| **BM25 + alias + recencia (default)** | **0,73** | **0,88** | **0,96** | **0,82** |
| Híbrido RRF con `multilingual-e5-small` | 0,69 | 0,88 | 0,88 | 0,77 |
| Híbrido RRF con `multilingual-e5-base` | 0,69 | 0,88 | 0,92 | 0,80 |
| Sólo denso `e5-small` | 0,38 | 0,65 | — | 0,54 |
| Sólo denso `e5-base` | 0,46 | 0,69 | — | 0,61 |

Conclusión (buen material para el informe): en un corpus chico, técnico y con encabezados enriquecidos con nombres vulgares, **BM25 le gana a los embeddings multilingües genéricos**; el híbrido no mejora. Por eso el índice entregado usa BM25. Si quieren seguir: probar un modelo más grande (p. ej. `BAAI/bge-m3`), *query rewriting* con el LLM (que reformule la descripción del usuario en términos técnicos antes de buscar) o un *reranker*. Para regenerar densos: `python -m agente.rag.indexar --embeddings --modelo <modelo>`.
- Mejoras que ya se aplicaron y movieron la métrica (sirven como "iteraciones" en el informe): agrupar secciones cortas en un chunk "Identidad"; agregar alias argentinos y el grupo (maleza/insecto/hongo) al encabezado de cada chunk; bonus de recencia para informes. De hit@3 = 0,81 a 0,88 y de hit@1 = 0,65 a 0,73.

## 3. Evaluación del agente completo

**Piso de comparación ya medido** — `agente/baseline_extractivo.py` (sin LLM: devuelve el mejor fragmento con su link), 29 manuales (sin la de foto) + 20 automáticas:
cita fuente 100 % · menciona la plaga esperada 76 % · sin dosis 100 % (`data/eval/resultados_baseline_extractivo.jsonl`).
El agente con LLM tiene que superar ese 76 % y además explicar, integrar clima y fotos, y responder bien las preguntas que no tienen fragmento obvio.

1. `python scripts/evaluar_agente.py --agente <modulo>:responder --auto 40`
   → guarda respuestas y calcula: % que cita fuente, % que menciona la plaga esperada, % sin dosis, % que deriva en preguntas de dosis.
2. Pasar cada respuesta por el juez (`juez_prompt.md`) con el contexto recuperado → **fidelidad** media y **tasa de respuesta**.
3. Validar el juez: puntuar a mano ~20 respuestas y comparar.
4. Reportar tabla: métrica × configuración (sin RAG / RAG BM25 / RAG híbrido).

## 4. Evaluación de la tool de imagen

1. `python scripts/descargar_datasets.py plantdoc` (y opcional el ZIP de maíz de Mendeley).
2. `python scripts/descargar_datasets.py armar-set --n 10`.
3. Correr `diagnosticar_cultivo` sobre cada imagen (≤ 50 imágenes para no gastar los 100 créditos gratis; la caché evita repetir) y comparar el nombre científico sugerido con `slug_esperado` → top-1 / top-3.
4. Comparar con el VLM del LLM usado (mismo set, prompt: "¿qué enfermedad de maíz ves? respondé con nombre científico").
5. No usar PlantVillage para medir: son fotos de laboratorio y sobreestiman el desempeño a campo (motivación del paper de PlantDoc).

## 5. Qué mostrar en la demo

- Una consulta por síntomas sin foto (m04 ojo de rana) con citas.
- Una foto de maíz con roya + localidad → candidatos + validación con ficha + riesgo según pronóstico.
- "¿Cómo viene la chicharrita?" → responde con informe N° 52 y su fecha.
- "¿Qué dosis le pongo?" → no receta y deriva.
