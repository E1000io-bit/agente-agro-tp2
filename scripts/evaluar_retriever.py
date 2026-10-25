"""
Evalúa el retriever con las preguntas que tienen slugs esperados.

    python scripts/evaluar_retriever.py                              # preguntas_manual.jsonl
    python scripts/evaluar_retriever.py --archivo data/eval/preguntas_auto.jsonl

Métricas: hit@1, hit@3, hit@5 y MRR sobre la ficha/informe esperado (a nivel slug, no chunk).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from agente.rag.buscar import buscar_fichas  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", default=str(RAIZ / "data" / "eval" / "preguntas_manual.jsonl"))
    ap.add_argument("--sin-filtro-cultivo", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    filas = [json.loads(l) for l in Path(args.archivo).read_text(encoding="utf-8").splitlines() if l.strip()]
    filas = [f for f in filas if f.get("slugs_esperados")]
    hits = {1: 0, 3: 0, 5: 0}
    mrr = 0.0
    for f in filas:
        cultivo = None if args.sin_filtro_cultivo else (f.get("cultivo") or None)
        res = buscar_fichas(f["pregunta"], cultivo=cultivo, k=10)
        slugs = list(dict.fromkeys(r["slug"] for r in res))
        pos = next((i for i, s in enumerate(slugs) if s in f["slugs_esperados"]), None)
        for k in hits:
            hits[k] += int(pos is not None and pos < k)
        mrr += 1 / (pos + 1) if pos is not None else 0
        if args.verbose or pos is None or pos > 2:
            print(f"{'OK ' if pos == 0 else ('~' + str(pos + 1) + ' ' if pos is not None else 'XX ')} {f['id']}: "
                  f"{f['pregunta'][:70]}…  -> {slugs[:3]}  (esperado {f['slugs_esperados'][:2]})")
    n = len(filas)
    print(f"\nn={n}  hit@1={hits[1]/n:.2f}  hit@3={hits[3]/n:.2f}  hit@5={hits[5]/n:.2f}  MRR={mrr/n:.2f}")


if __name__ == "__main__":
    main()
