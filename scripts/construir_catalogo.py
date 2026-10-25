"""
Arma data/catalogo_plagas.csv a partir de las fichas descargadas: una fila por plaga con
nombres vulgares (según SINAVIMO), alias usados en Argentina, cultivos, tipo, condición y URL.
Sirve como tabla de referencia para el informe y para el agente (lista de lo que "sabe").

    python scripts/construir_catalogo.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from agente.rag.indexar import leer_md  # noqa: E402


def main() -> None:
    objetivo = {}
    with open(RAIZ / "data" / "plagas_objetivo.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            objetivo[fila["slug"]] = fila
    filas = []
    for p in sorted((RAIZ / "data" / "corpus" / "sinavimo").glob("*.md")):
        meta, cuerpo = leer_md(p)
        o = objetivo.get(meta["slug"], {})
        filas.append({
            "slug": meta["slug"],
            "nombre_cientifico": meta.get("titulo"),
            "nombres_vulgares_sinavimo": " | ".join(meta.get("nombres_vulgares", [])),
            "alias_ar": o.get("alias_ar", "").replace(";", " | "),
            "cultivos_tp": o.get("cultivos", "").replace(";", ", "),
            "grupo": o.get("grupo", ""),
            "tipo_plaga_sinavimo": meta.get("tipo_plaga"),
            "condicion_argentina": meta.get("condicion"),
            "prioridad": o.get("prioridad", ""),
            "tiene_condiciones_predisponentes": "## Condiciones predisponentes" in cuerpo,
            "caracteres_ficha": len(cuerpo),
            "url": meta.get("url"),
        })
    salida = RAIZ / "data" / "catalogo_plagas.csv"
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} plagas -> {salida}")


if __name__ == "__main__":
    main()
