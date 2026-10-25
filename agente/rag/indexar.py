"""
Arma el índice del RAG a partir de data/corpus/**.md

    python -m agente.rag.indexar                 # chunks + BM25 (sin dependencias pesadas)
    python -m agente.rag.indexar --embeddings    # además embeddings densos (sentence-transformers)

Salida: data/index/chunks.jsonl  (+ data/index/embeddings.npy si se pide)

Estrategia de chunking:
- Fichas SINAVIMO: un chunk por sección (Síntomas, Condiciones predisponentes, Descripción, Cultivos...).
  Cada chunk lleva como encabezado el nombre científico + nombres vulgares, así el retriever
  encuentra "roya común" aunque la sección no lo repita. La bibliografía NO se indexa (ruido).
- Informes de chicharrita: por página y ventanas de ~1.200 caracteres con 200 de solapamiento.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CORPUS = RAIZ / "data" / "corpus"
INDICE = RAIZ / "data" / "index"
NO_INDEXAR = re.compile(r"^bibliograf", re.I)
# Secciones cortas que se agrupan en un único chunk "Identidad" (si van solas meten ruido)
A_IDENTIDAD = re.compile(r"^(tipo de plaga|taxonom|condici|sinonimia|otros nombres|acr[oó]nimo|nombre)", re.I)
CSV_OBJETIVO = RAIZ / "data" / "plagas_objetivo.csv"


def aliases_tp() -> dict[str, list[str]]:
    """Nombres comunes usados en Argentina (columna 'alias_ar' del CSV) para sumar al encabezado de cada ficha."""
    if not CSV_OBJETIVO.exists():
        return {}
    out = {}
    with open(CSV_OBJETIVO, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            out[fila["slug"]] = [p.strip() for p in fila.get("alias_ar", "").split(";") if p.strip()]
    return out
VENTANA, SOLAPE = 1200, 200


def leer_md(p: Path) -> tuple[dict, str]:
    txt = p.read_text(encoding="utf-8")
    meta: dict = {}
    if txt.startswith("---"):
        _, fm, cuerpo = txt.split("---", 2)
        for linea in fm.strip().splitlines():
            if ":" not in linea:
                continue
            k, v = linea.split(":", 1)
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                meta[k.strip()] = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
            else:
                meta[k.strip()] = v.strip('"')
        return meta, cuerpo
    return meta, txt


def chunks_ficha(meta: dict, cuerpo: str) -> list[dict]:
    titulo = meta.get("titulo", "")
    nombres = list(dict.fromkeys(meta.get("nombres_vulgares", []) + meta.get("alias_tp", [])))
    encabezado = f"{titulo}" + (f" ({', '.join(nombres)})" if nombres else "")
    etiquetas = [x for x in (meta.get("tipo_plaga"), meta.get("grupo")) if x]
    if etiquetas:
        encabezado += f" [{' · '.join(etiquetas)}]"
    out, identidad = [], []
    for bloque in re.split(r"\n(?=## )", cuerpo):
        if not bloque.startswith("## "):
            continue
        seccion, _, texto = bloque[3:].partition("\n")
        texto = re.sub(r"_Fuente: .*_$", "", texto.strip(), flags=re.M).strip()
        if not texto or NO_INDEXAR.match(seccion):
            continue
        if A_IDENTIDAD.match(seccion):
            identidad.append(f"{seccion}: {' · '.join(l.lstrip('- ') for l in texto.splitlines() if l.strip())}")
            continue
        out.append({"texto": f"{encabezado} — {seccion}\n{texto}", "seccion": seccion})
    out.append({"texto": f"{encabezado} — Identidad\n" + "\n".join(identidad), "seccion": "Identidad"})
    return out


def chunks_informe(meta: dict, cuerpo: str) -> list[dict]:
    titulo = meta.get("titulo", "")
    fecha = meta.get("fecha", "")
    out = []
    for pag in re.split(r"<!-- página (\d+) -->", cuerpo)[2::2] or [cuerpo]:
        pag = re.sub(r"[ \t]+", " ", pag).strip()
        for i in range(0, max(len(pag), 1), VENTANA - SOLAPE):
            trozo = pag[i:i + VENTANA].strip()
            if len(trozo) > 80:
                out.append({"texto": f"{titulo} ({fecha})\n{trozo}", "seccion": "informe"})
    return out


def construir() -> list[dict]:
    chunks = []
    alias = aliases_tp()
    for p in sorted(CORPUS.rglob("*.md")):
        meta, cuerpo = leer_md(p)
        meta["alias_tp"] = alias.get(meta.get("slug", p.stem), [])
        fuente = p.parent.name
        piezas = chunks_ficha(meta, cuerpo) if fuente == "sinavimo" else chunks_informe(meta, cuerpo)
        for j, c in enumerate(piezas):
            chunks.append({
                "id": f"{meta.get('slug', p.stem)}#{j}",
                "slug": meta.get("slug", p.stem),
                "fuente": fuente,
                "titulo": meta.get("titulo", p.stem),
                "nombres_vulgares": meta.get("nombres_vulgares", []) + meta.get("alias_tp", []),
                "cultivos": meta.get("cultivos_tp", []),
                "fecha": meta.get("fecha") or meta.get("fecha_descarga", ""),
                "url": meta.get("url", ""),
                **c,
            })
    return chunks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embeddings", action="store_true")
    ap.add_argument("--modelo", default="intfloat/multilingual-e5-small")
    args = ap.parse_args()

    INDICE.mkdir(parents=True, exist_ok=True)
    chunks = construir()
    with open(INDICE / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(chunks)} chunks -> {INDICE / 'chunks.jsonl'}")

    if args.embeddings:
        import numpy as np
        from sentence_transformers import SentenceTransformer

        modelo = SentenceTransformer(args.modelo)
        prefijo = "passage: " if "e5" in args.modelo else ""
        emb = modelo.encode([prefijo + c["texto"] for c in chunks], batch_size=32,
                            normalize_embeddings=True, show_progress_bar=True)
        np.save(INDICE / "embeddings.npy", emb.astype("float32"))
        (INDICE / "embeddings_modelo.txt").write_text(args.modelo, encoding="utf-8")
        print(f"embeddings {emb.shape} -> {INDICE / 'embeddings.npy'}")


if __name__ == "__main__":
    main()
