"""
Baseline SIN LLM: devuelve el fragmento más relevante tal cual, con su fuente.
Sirve para (1) probar que scripts/evaluar_agente.py funciona y (2) tener un piso de comparación
en el informe ("¿cuánto agrega el LLM sobre sólo recuperar?").

    python scripts/evaluar_agente.py --agente agente.baseline_extractivo:responder
"""
from __future__ import annotations

import re

from agente.rag.buscar import buscar_fichas

DOSIS = re.compile(r"\b(dosis|cu[aá]nto (le )?aplico|qu[eé] (producto|le aplico))\b", re.I)


def responder(pregunta: str) -> str:
    if DOSIS.search(pregunta):
        return ("No indico productos ni dosis. Consultá a un Ingeniero Agrónomo matriculado, la etiqueta del "
                "producto registrado (Guía CASAFE) y la receta fitosanitaria.")
    res = buscar_fichas(pregunta, k=1)
    if not res:
        return "No encontré información sobre eso en las fuentes disponibles."
    r = res[0]
    return f"{r['texto'][:900]}\n\nFuente: {r['url']}"


if __name__ == "__main__":
    print(responder("Veo pústulas color óxido en hojas de maíz"))
