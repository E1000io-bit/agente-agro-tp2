"""
Tool de glosario / sinónimos con AGROVOC (tesauro agrícola multilingüe de la FAO). Sin API key.

- buscar_termino("roya")          -> conceptos AGROVOC en español con su URI
- detalle_concepto(uri)           -> etiqueta en es/en, sinónimos, términos más amplios y más específicos

Sirve para: (a) explicar términos técnicos, (b) expandir la consulta del RAG con sinónimos
(ej. "cigarrita" -> "chicharrita"), (c) traducir nombres al inglés para APIs internacionales.
Docs: https://www.fao.org/agrovoc/machine-use  ·  REST Skosmos: https://agrovoc.fao.org/browse/rest/v1/
"""
from __future__ import annotations

from agente.tools._http import sesion

BASE = "https://agrovoc.fao.org/browse/rest/v1"


def buscar_termino(texto: str, idioma: str = "es", max_resultados: int = 5) -> list[dict]:
    consulta = texto if texto.endswith("*") else f"{texto}*"
    r = sesion().get(f"{BASE}/search/", params={"query": consulta, "lang": idioma, "maxhits": max_resultados}, timeout=30)
    r.raise_for_status()
    return [
        {"etiqueta": x.get("prefLabel"), "alternativa": x.get("altLabel"), "uri": x.get("uri")}
        for x in r.json().get("results", [])
    ]


def _etiquetas(valor, idiomas=("es", "en")) -> dict[str, list[str]]:
    if not valor:
        return {}
    if isinstance(valor, dict):
        valor = [valor]
    out: dict[str, list[str]] = {}
    for v in valor:
        if isinstance(v, dict) and v.get("lang") in idiomas:
            out.setdefault(v["lang"], []).append(v["value"])
    return out


def _uris(valor) -> list[str]:
    if not valor:
        return []
    if isinstance(valor, dict):
        valor = [valor]
    return [v["uri"] for v in valor if isinstance(v, dict) and "uri" in v]


def detalle_concepto(uri: str) -> dict:
    r = sesion().get(f"{BASE}/agrovoc/data", params={"uri": uri, "format": "application/ld+json"}, timeout=30)
    r.raise_for_status()
    grafo = r.json().get("graph", [])
    nodos = {n.get("uri"): n for n in grafo}
    c = nodos.get(uri, {})

    def nombre(u: str) -> str | None:
        et = _etiquetas(nodos.get(u, {}).get("prefLabel"), ("es",))
        return (et.get("es") or [None])[0]

    pref = _etiquetas(c.get("prefLabel"))
    return {
        "uri": uri,
        "es": pref.get("es"),
        "en": pref.get("en"),
        "sinonimos": _etiquetas(c.get("altLabel")),
        "mas_amplio": [nombre(u) or u for u in _uris(c.get("broader"))],
        "mas_especifico": [nombre(u) or u for u in _uris(c.get("narrower"))][:15],
        "definicion": c.get("skos:definition") or c.get("definition"),
        "fuente": "AGROVOC (FAO) — https://agrovoc.fao.org",
    }


def glosario(termino: str) -> dict:
    """Atajo para el agente: busca el término y devuelve el detalle del mejor resultado."""
    hits = buscar_termino(termino)
    if not hits:
        return {"error": f"'{termino}' no está en AGROVOC"}
    return detalle_concepto(hits[0]["uri"]) | {"otros_resultados": [h["etiqueta"] for h in hits[1:]]}


if __name__ == "__main__":
    import json

    print(json.dumps(glosario("roya"), ensure_ascii=False, indent=2))
