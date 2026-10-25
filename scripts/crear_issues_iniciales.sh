#!/usr/bin/env bash
# Crea las etiquetas y los issues iniciales del TP en el repo de GitHub actual.
# Requiere la CLI de GitHub (https://cli.github.com) y haber hecho `gh auth login`.
# Correr UNA sola vez desde la carpeta del repo:   bash scripts/crear_issues_iniciales.sh
set -euo pipefail

gh label create tarea   --color 1D76DB --description "Algo a implementar o investigar" --force
gh label create agente  --color 5319E7 --description "Loop, prompt, memoria"          --force
gh label create tools   --color 0E8A16 --description "Tools externas"                  --force
gh label create eval    --color FBCA04 --description "Evaluación y resultados"         --force
gh label create corpus  --color C2E0C6 --description "Fuentes y datos"                 --force
gh label create ui      --color D4C5F9 --description "Interfaz y demo"                 --force

nuevo() {  # titulo, etiquetas, cuerpo
  gh issue create --title "$1" --label "$2" --body "$3"
}

nuevo "Revisar el repo de la materia y elegir framework/LLM" "tarea,agente" \
"## Objetivo
Definir con qué framework y LLM se arma el loop del agente, según los contenidos del repo de la materia.

## Criterio de terminado
- [ ] Lista de temas del repo mapeados a piezas del agente (completar \`docs/00-idea-y-plan.md\` §5)
- [ ] Decisión registrada en \`docs/06-decisiones.md\` (D-08)"

nuevo "Implementar el loop del agente con las tools" "tarea,agente" \
"## Objetivo
Loop ReAct/function calling usando \`agente/registro_tools.py\` y \`agente/prompts/system_prompt.md\`.

## Criterio de terminado
- [ ] Función \`responder(pregunta) -> str\` en \`agente/\`
- [ ] Memoria del lote (cultivo, localidad, fenología)
- [ ] Funciona con las 4 preguntas de demo de \`docs/04-evaluacion.md\` §5

Ver \`docs/03-arquitectura-y-tools.md\` §2."

nuevo "Probar tools de imagen y EPPO con API keys" "tarea,tools" \
"## Objetivo
Registrarse en crop.health (100 créditos gratis), Pl@ntNet y EPPO; probar las tools.

## Criterio de terminado
- [ ] \`python -m agente.probar_tools --foto <hoja.jpg>\` devuelve candidatos
- [ ] \`identificar_maleza\` probado con una foto de maleza
- [ ] \`info_eppo\` ajustado al formato real de respuesta
- [ ] Keys sólo en \`.env\`, nunca en el repo"

nuevo "Evaluar el agente vs. baseline y con LLM-juez" "tarea,eval" \
"## Objetivo
Medir el agente completo y compararlo con \`agente/baseline_extractivo.py\`.

## Criterio de terminado
- [ ] \`scripts/evaluar_agente.py --agente <modulo>:responder --auto 40\` corrido y \`.jsonl\` guardado en \`data/eval/\`
- [ ] Fidelidad y tasa de respuesta con \`data/eval/juez_prompt.md\` (juez validado con ~20 respuestas a mano)
- [ ] Tabla en \`docs/04-evaluacion.md\` §3"

nuevo "Armar set de imágenes y medir la tool de diagnóstico" "tarea,eval" \
"## Objetivo
Accuracy top-1/top-3 de crop.health vs. el VLM del LLM en fotos de campo.

## Criterio de terminado
- [ ] \`python scripts/descargar_datasets.py plantdoc\` + \`armar-set --n 10\`
- [ ] ≤ 50 imágenes evaluadas (cuidar créditos)
- [ ] Resultados en \`docs/04-evaluacion.md\` §4"

nuevo "Mejorar recuperación con reescritura de consulta" "tarea,agente" \
"## Objetivo
Que el LLM reformule la descripción del usuario en vocabulario técnico antes de \`buscar_fichas\` (ataca los fallos de BM25: m02, m13, m17, m19).

## Criterio de terminado
- [ ] hit@3 del set manual antes → después en el PR
- [ ] Decisión en \`docs/06-decisiones.md\`"

nuevo "UI y demo" "tarea,ui" \
"## Objetivo
Interfaz simple (Streamlit/Gradio o la de la cátedra) con chat + subida de foto + localidad.

## Criterio de terminado
- [ ] Se puede correr con un comando documentado en el README
- [ ] Guion de demo (\`docs/04-evaluacion.md\` §5) grabado o probado"

nuevo "Actualizar informes de chicharrita antes de la entrega" "tarea,corpus" \
"## Objetivo
Bajar los informes nuevos de la Red Nacional de Monitoreo y reindexar.

## Criterio de terminado
- [ ] \`python scripts/descargar_informes_chicharrita.py --n 3\`
- [ ] \`python -m agente.rag.indexar\` y tests en verde
- [ ] Anotado en \`CHANGELOG.md\`"

echo "Listo: etiquetas e issues creados."
