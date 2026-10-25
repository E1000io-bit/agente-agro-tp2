"""
Tests sin red (corren en segundos):  python -m pytest tests -q   ·   o   python tests/test_offline.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))


def test_parser_sinavimo():
    from descargar_sinavimo import a_markdown, parsear_ficha

    html = (RAIZ / "tests/fixtures/sinavimo_bipolaris.html").read_text(encoding="utf-8")
    f = parsear_ficha(html, "https://www.sinavimo.gob.ar/plaga/bipolaris-sorokiniana")
    assert f["titulo"] == "Bipolaris sorokiniana"
    for s in ("Nombre vulgar", "Condición", "Condiciones predisponentes", "Signos y síntomas / Daños"):
        assert s in f["secciones"], s
    assert "24 y 28" in f["secciones"]["Condiciones predisponentes"]
    md = a_markdown("bipolaris-sorokiniana", "u", f, {"cultivos": ["trigo"]})
    assert md.startswith("---\nslug: bipolaris-sorokiniana")


def test_tokens_es():
    from agente.rag.buscar import tokens

    assert tokens("Pústulas en las HOJAS de maíz") == tokens("pustula maiz")


def test_indice_y_busqueda():
    from agente.rag.indexar import construir

    chunks = construir()
    assert len(chunks) > 500
    assert all(c["url"] for c in chunks)
    assert not any(c["seccion"].lower().startswith("bibliograf") for c in chunks)

    from agente.rag.buscar import buscar_fichas

    r = buscar_fichas("pústulas color óxido en hojas de maíz", cultivo="maiz", k=3)
    assert any(x["slug"].startswith("puccinia") for x in r)
    r = buscar_fichas("cómo viene la chicharrita", fuente="chicharrita", mas_reciente=True, k=1)
    assert r[0]["slug"] == "chicharrita-informe-052"


def test_schemas_tools():
    from agente.registro_tools import TOOLS, ejecutar, schemas_anthropic, schemas_openai

    assert len(schemas_openai()) == len(TOOLS) == len(schemas_anthropic())
    salida = json.loads(ejecutar("buscar_fichas", {"consulta": "roya asiática soja", "k": 1}))
    assert salida[0]["slug"] == "phakopsora-pachyrhizi"
    assert "error" in json.loads(ejecutar("no_existe", {}))


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
            print(f"ok  {nombre}")
