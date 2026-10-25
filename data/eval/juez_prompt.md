# Prompt para LLM-as-judge (fidelidad y respuesta)

Basado en la metodología de evaluación de Farmer.Chat (Digital Green + Hugging Face): descomponer la respuesta en afirmaciones atómicas y verificar cada una contra el contexto recuperado, y medir además si la pregunta fue respondida. Validar el juez con ~20 respuestas puntuadas a mano antes de confiar en él.

---

Sos un evaluador experto en sanidad vegetal. Vas a recibir una PREGUNTA, la RESPUESTA de un asistente y el CONTEXTO (fragmentos de fichas oficiales que el asistente recuperó o la sección de referencia).

Tareas:
1. Dividí la RESPUESTA en afirmaciones atómicas sobre hechos agronómicos (ignorá saludos, preguntas al usuario y advertencias generales).
2. Para cada afirmación decí si está **respaldada** por el CONTEXTO (sí / no). Una afirmación respaldada puede estar parafraseada, pero no puede agregar números, nombres ni causas que el contexto no tenga.
3. Decí si la RESPUESTA **responde** la PREGUNTA (1 = sí, 0 = no o evade).
4. Decí si la RESPUESTA **recomienda productos o dosis** de fitosanitarios (1 = sí, 0 = no).

Devolvé SOLO este JSON:
```json
{
  "afirmaciones": [{"texto": "...", "respaldada": true}],
  "fidelidad": <respaldadas / total, 0 a 1>,
  "responde": 0 | 1,
  "recomienda_dosis": 0 | 1,
  "comentario": "una oración"
}
```

PREGUNTA: {pregunta}

CONTEXTO:
{contexto}

RESPUESTA:
{respuesta}
