"""
Genera preguntas de evaluación automáticas a partir de las fichas descargadas
(complementan las 30 preguntas escritas a mano en data/eval/preguntas_manual.jsonl).

    python scripts/generar_eval.py   ->  data/eval/preguntas_auto.jsonl

Cada pregunta apunta a la ficha y sección que contiene la respuesta (referencia), así un
LLM-juez puede verificar fidelidad leyendo esa sección (estilo RAGAS / Farmer.Chat).
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from agente.rag.indexar import leer_md  # noqa: E402

NOMBRE_CULTIVO = {"maiz": "maíz", "soja": "soja", "trigo": "trigo", "mani": "maní", "varios": "cultivos extensivos"}


def main() -> None:
    random.seed(7)
    alias = {}
    with open(RAIZ / "data" / "plagas_objetivo.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            alias[fila["slug"]] = [a for a in fila["alias_ar"].split(";") if a]
    preguntas = []
    for p in sorted((RAIZ / "data" / "corpus" / "sinavimo").glob("*.md")):
        meta, cuerpo = leer_md(p)
        slug = meta["slug"]
        cientifico = meta.get("titulo", slug)
        comun = (alias.get(slug) or meta.get("nombres_vulgares") or [cientifico])[0]
        cultivo = (meta.get("cultivos_tp") or ["varios"])[0]
        cult_txt = NOMBRE_CULTIVO.get(cultivo, cultivo)
        secciones = cuerpo
        plantillas = []
        if "## Condiciones predisponentes" in secciones:
            plantillas.append(("condiciones", "Condiciones predisponentes",
                               f"¿Qué condiciones ambientales favorecen {comun.lower()} ({cientifico})?"))
        if "## Signos y síntomas" in secciones:
            plantillas.append(("sintomas", "Signos y síntomas / Daños",
                               f"¿Cómo reconozco {comun.lower()} en {cult_txt}? ¿Qué síntomas o daños produce?"))
        if "## Descripción biológica" in secciones:
            plantillas.append(("biologia", "Descripción biológica",
                               f"Contame cómo es y cómo se disemina {cientifico}."))
        plantillas.append(("condicion_pais", "Condición",
                           f"¿{cientifico} está presente en Argentina?"))
        for tipo, seccion, preg in plantillas:
            preguntas.append({
                "id": f"a-{slug}-{tipo}",
                "tipo": f"auto_{tipo}",
                "cultivo": cultivo if cultivo != "varios" else "",
                "pregunta": preg,
                "slugs_esperados": [slug],
                "referencia": {"archivo": f"data/corpus/sinavimo/{slug}.md", "seccion": seccion,
                               "condicion_esperada": meta.get("condicion", "") if tipo == "condicion_pais" else None},
                "comportamiento": "Responder sólo con lo que dice la sección de referencia y citar la URL de la ficha.",
            })
    salida = RAIZ / "data" / "eval" / "preguntas_auto.jsonl"
    with open(salida, "w", encoding="utf-8") as f:
        for q in preguntas:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"{len(preguntas)} preguntas -> {salida}")


if __name__ == "__main__":
    main()
