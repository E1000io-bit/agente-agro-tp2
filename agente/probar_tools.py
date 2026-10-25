"""
Prueba rápida de todas las tools sin LLM (sirve para verificar instalación y API keys).

    python -m agente.probar_tools
    python -m agente.probar_tools --foto ruta/a/hoja.jpg
"""
from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from agente.registro_tools import ejecutar


def mostrar(titulo: str, salida: str, largo: int = 700) -> None:
    print(f"\n=== {titulo} ===")
    print(salida[:largo] + ("…" if len(salida) > largo else ""))


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto")
    args = ap.parse_args()

    r = json.loads(ejecutar("buscar_fichas", {"consulta": "pústulas color óxido en hojas de maíz", "cultivo": "maiz", "k": 3}))
    mostrar("buscar_fichas", "\n".join(f"{x['titulo']} [{x['seccion']}] {x['url']}" for x in r))

    r = json.loads(ejecutar("buscar_fichas", {"consulta": "cómo viene la chicharrita", "fuente": "chicharrita", "mas_reciente": True, "k": 2}))
    mostrar("buscar_fichas (chicharrita reciente)", "\n".join(f"{x['titulo']} ({x['fecha']})" for x in r))

    g = json.loads(ejecutar("geocodificar", {"lugar": "Marcos Juárez"}))
    mostrar("geocodificar", json.dumps(g, ensure_ascii=False))
    if "lat" in g:
        c = json.loads(ejecutar("clima_lote", {"lat": g["lat"], "lon": g["lon"], "dias": 5}))
        mostrar("clima_lote (indicadores)", json.dumps(c.get("indicadores", c), ensure_ascii=False, indent=1))

    mostrar("glosario", ejecutar("glosario", {"termino": "umbral económico"}))
    mostrar("info_eppo", ejecutar("info_eppo", {"nombre_cientifico": "Dalbulus maidis"}))
    if args.foto:
        mostrar("diagnosticar_cultivo", ejecutar("diagnosticar_cultivo", {"ruta_imagen": args.foto}), 2000)


if __name__ == "__main__":
    main()
