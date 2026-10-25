"""
Retriever del RAG: BM25 (siempre) + embeddings densos (si se generaron) fusionados por RRF.

    from agente.rag.buscar import buscar_fichas
    buscar_fichas("pústulas color óxido en hojas de maíz", cultivo="maiz", k=5)

Detalles útiles para el informe:
- Normalización en español (minúsculas, sin tildes, stopwords) y stemming liviano por sufijos.
- Expansión por nombres vulgares: si la consulta menciona "chicharrita" o "roya común",
  se suma un bonus a la ficha que tiene ese nombre vulgar (diccionario armado desde el corpus).
- Filtro opcional por cultivo y por fuente ("sinavimo" | "chicharrita").
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
INDICE = RAIZ / "data" / "index"

STOP = set("""
a al algo algun alguna algunas alguno algunos ante antes como con contra cual cuales cuando de del desde donde dos
el ella ellas ellos en entre era es esa esas ese eso esos esta estan estas este esto estos fue fueron ha hay la las le
les lo los mas me mi mis mucho muy no nos o otra otro para pero poco por porque que quien se sea segun ser si sin
sobre son su sus tambien tan te tengo tiene tienen todo todos tu un una unas uno unos y ya puede pueden hace mi mis
veo tengo hoja hojas planta plantas lote cultivo
""".split())


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def raiz(p: str) -> str:
    for suf in ("aciones", "acion", "amientos", "amiento", "mente", "idades", "idad", "osos", "osas", "oso", "osa",
                "ales", "ares", "eres", "iones", "ion", "es", "as", "os", "a", "o", "s"):
        if len(p) > len(suf) + 3 and p.endswith(suf):
            return p[: -len(suf)]
    return p


def tokens(t: str) -> list[str]:
    return [raiz(w) for w in re.findall(r"[a-z0-9]+", normalizar(t)) if w not in STOP and len(w) > 1]


class Buscador:
    def __init__(self, k1: float = 1.4, b: float = 0.75):
        ruta = INDICE / "chunks.jsonl"
        if not ruta.exists():
            raise FileNotFoundError("No hay índice. Correr: python -m agente.rag.indexar")
        self.chunks = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines()]
        self.docs = [tokens(c["texto"]) for c in self.chunks]
        self.N = len(self.docs)
        self.avgdl = sum(map(len, self.docs)) / max(self.N, 1)
        df = Counter(t for d in self.docs for t in set(d))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.tf = [Counter(d) for d in self.docs]
        self.k1, self.b = k1, b
        # diccionario nombre vulgar -> slug
        self.vulgares: dict[str, str] = {}
        for c in self.chunks:
            for n in c.get("nombres_vulgares", []):
                n_norm = normalizar(n).strip()
                if len(n_norm) > 4:
                    self.vulgares[n_norm] = c["slug"]
            self.vulgares[normalizar(c["titulo"]).strip()] = c["slug"]
        self.emb = None
        if (INDICE / "embeddings.npy").exists():
            import numpy as np

            self.emb = np.load(INDICE / "embeddings.npy")
            self.modelo_nombre = (INDICE / "embeddings_modelo.txt").read_text(encoding="utf-8").strip()
            self._modelo = None

    def _bm25(self, q: list[str]) -> list[float]:
        out = []
        for tf, d in zip(self.tf, self.docs):
            s = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    s += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avgdl))
            out.append(s)
        return out

    def _denso(self, consulta: str) -> list[float] | None:
        if self.emb is None:
            return None
        if self._modelo is None:
            from sentence_transformers import SentenceTransformer

            self._modelo = SentenceTransformer(self.modelo_nombre)
        pre = "query: " if "e5" in self.modelo_nombre else ""
        v = self._modelo.encode([pre + consulta], normalize_embeddings=True)[0]
        return (self.emb @ v).tolist()

    def slugs_mencionados(self, consulta: str) -> set[str]:
        q = normalizar(consulta)
        return {slug for nombre, slug in self.vulgares.items() if nombre in q}

    RECIENTE = re.compile(r"\b(ultim[oa]s?|reciente|recientes|este mes|esta semana|hoy|actual|actualmente|ahora|como viene|como esta)\b")

    def buscar(self, consulta: str, k: int = 5, cultivo: str | None = None, fuente: str | None = None,
               mas_reciente: bool | None = None) -> list[dict]:
        """mas_reciente=None lo detecta solo ("último informe", "este mes", "cómo viene"...)."""
        q = tokens(consulta)
        if mas_reciente is None:
            mas_reciente = bool(self.RECIENTE.search(normalizar(consulta)))
        fechas_inf = sorted({c["fecha"] for c in self.chunks if c["fuente"] != "sinavimo" and c["fecha"]})
        rango_fecha = {f: i / max(len(fechas_inf) - 1, 1) for i, f in enumerate(fechas_inf)}
        bm = self._bm25(q)
        dn = self._denso(consulta)
        mencionados = self.slugs_mencionados(consulta)

        def ranking(scores: list[float]) -> dict[int, int]:
            orden = sorted(range(self.N), key=lambda i: scores[i], reverse=True)
            return {i: r for r, i in enumerate(orden)}

        r_bm = ranking(bm)
        r_dn = ranking(dn) if dn else None
        finales = []
        for i, c in enumerate(self.chunks):
            if cultivo and c["cultivos"] and normalizar(cultivo) not in [normalizar(x) for x in c["cultivos"]]:
                continue
            if fuente and c["fuente"] != fuente:
                continue
            s = 1 / (60 + r_bm[i])
            if r_dn:
                s += 1 / (60 + r_dn[i])
            if c["slug"] in mencionados:
                s += 0.02
            if mas_reciente and c["fuente"] != "sinavimo":
                s += 0.012 * rango_fecha.get(c["fecha"], 0)
            if bm[i] == 0 and not r_dn and c["slug"] not in mencionados:
                continue
            finales.append((s, i))
        finales.sort(reverse=True)
        res = []
        for s, i in finales[:k]:
            c = self.chunks[i]
            res.append({
                "score": round(s, 4),
                "slug": c["slug"],
                "titulo": c["titulo"],
                "seccion": c["seccion"],
                "fuente": c["fuente"],
                "fecha": c["fecha"],
                "url": c["url"],
                "texto": c["texto"],
            })
        return res


@lru_cache(maxsize=1)
def _buscador() -> Buscador:
    return Buscador()


def buscar_fichas(consulta: str, cultivo: str | None = None, k: int = 5, fuente: str | None = None,
                  mas_reciente: bool | None = None) -> list[dict]:
    """Tool para el agente. Devuelve los k fragmentos más relevantes con su URL para citar."""
    return _buscador().buscar(consulta, k=k, cultivo=cultivo, fuente=fuente, mas_reciente=mas_reciente)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "pústulas color óxido en hojas de maíz"
    for r in buscar_fichas(q, k=5):
        print(f"{r['score']:.4f}  {r['titulo']:<35} [{r['seccion']}]  {r['url']}")
