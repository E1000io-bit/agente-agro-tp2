"""
Descarga fichas de plagas de SINAVIMO (SENASA) y las guarda como Markdown con frontmatter YAML,
listas para indexar en el RAG.

Fuente: https://www.sinavimo.gob.ar  (portal oficial, acceso libre y gratuito; mantenido por la DIEF - SENASA)
Las URLs de fichas se obtienen del sitemap público (https://www.sinavimo.gob.ar/sitemap.xml).
robots.txt permite /plaga/*. El script espera entre pedidos para no cargar el servidor.

Uso:
    # Lista curada del TP (data/plagas_objetivo.csv)
    python scripts/descargar_sinavimo.py

    # Slugs sueltos
    python scripts/descargar_sinavimo.py --slugs dalbulus-maidis puccinia-sorghi

    # Todo el sitemap (≈4.700 fichas, tarda >1 h) filtrando por cultivo afectado
    python scripts/descargar_sinavimo.py --todo --filtro-cultivo "Zea mays" "Glycine max" "Triticum aestivum"
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.sinavimo.gob.ar"
RAIZ = Path(__file__).resolve().parents[1]
CSV_OBJETIVO = RAIZ / "data" / "plagas_objetivo.csv"
SALIDA = RAIZ / "data" / "corpus" / "sinavimo"
HEADERS = {"User-Agent": "TP-IA-agente-agro/1.0 (uso academico)"}
PAUSA_SEG = 1.5

# Secciones que conviene mantener separadas para el chunking del RAG
SECCIONES_PROSA = {"descripción biológica", "signos y síntomas / daños", "condiciones predisponentes"}


def limpiar(texto: str) -> str:
    texto = texto.replace("\xa0", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = "\n".join(l.strip() for l in texto.splitlines())
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def urls_del_sitemap(sesion: requests.Session) -> list[str]:
    urls: list[str] = []
    indice = sesion.get(f"{BASE}/sitemap.xml", timeout=60).text
    paginas = re.findall(r"<loc>([^<]+)</loc>", indice)
    for pag in paginas:
        xml = sesion.get(pag.replace("&amp;", "&"), timeout=120).text
        urls += [u for u in re.findall(r"<loc>([^<]+)</loc>", xml) if "/plaga/" in u]
        time.sleep(PAUSA_SEG)
    return urls


def parsear_ficha(html: str, url: str) -> dict:
    """Convierte el HTML de una ficha en un dict {titulo, secciones: {label: texto}}."""
    soup = BeautifulSoup(html, "html.parser")
    articulo = soup.find("article") or soup
    titulo_el = soup.find("h1") or soup.find(class_=re.compile("field--name-title"))
    titulo = limpiar(titulo_el.get_text(" ")) if titulo_el else url.rsplit("/", 1)[-1]

    secciones: dict[str, str] = {}
    for label in articulo.select(".field__label"):
        nombre = limpiar(label.get_text(" ")).rstrip(":").strip()
        if not nombre or nombre in secciones:
            continue
        contenedor = label.parent
        # Ítems de lista (nombres vulgares, sinonimia, cultivos, condición, bibliografía)
        items = [limpiar(li.get_text(" ")) for li in contenedor.select(".field__item, li")]
        items = [i for i in items if i]
        if items and nombre.lower() not in SECCIONES_PROSA:
            # quitar duplicados manteniendo orden
            vistos, unicos = set(), []
            for i in items:
                if i not in vistos:
                    vistos.add(i)
                    unicos.append(i)
            secciones[nombre] = "\n".join(f"- {i}" for i in unicos)
        else:
            copia = BeautifulSoup(str(contenedor), "html.parser")
            for l in copia.select(".field__label"):
                l.decompose()
            for br in copia.find_all(["br", "p", "li"]):
                br.append("\n")
            secciones[nombre] = limpiar(copia.get_text(" "))
    return {"titulo": titulo, "secciones": secciones}


def a_lista(texto: str | None) -> list[str]:
    if not texto:
        return []
    return [l.lstrip("- ").strip() for l in texto.splitlines() if l.strip()]


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def a_markdown(slug: str, url: str, ficha: dict, meta: dict) -> str:
    sec = ficha["secciones"]
    nombres = a_lista(sec.get("Nombre vulgar"))
    fm = [
        "---",
        f"slug: {slug}",
        f"titulo: {yaml_str(ficha['titulo'])}",
        f"nombre_cientifico: {yaml_str(meta.get('nombre_cientifico') or ficha['titulo'])}",
        "nombres_vulgares: [" + ", ".join(yaml_str(n) for n in nombres) + "]",
        f"tipo_plaga: {yaml_str(' / '.join(a_lista(sec.get('Tipo de plaga'))))}",
        f"condicion: {yaml_str(' / '.join(a_lista(sec.get('Condición'))))}",
        f"cultivos_tp: [{', '.join(meta.get('cultivos', []))}]",
        f"grupo: {meta.get('grupo', '')}",
        f"prioridad: {meta.get('prioridad', '')}",
        f"fuente: SINAVIMO - SENASA",
        f"url: {url}",
        f"fecha_descarga: {dt.date.today().isoformat()}",
        "---",
        "",
        f"# {ficha['titulo']}",
        "",
        "",
    ]
    cuerpo = []
    for nombre, texto in sec.items():
        if not texto:
            continue
        cuerpo.append(f"## {nombre}\n\n{texto}\n")
    cuerpo.append(f"_Fuente: [SINAVIMO – {ficha['titulo']}]({url})_\n")
    return "\n".join(fm) + "\n".join(cuerpo)


def leer_objetivo() -> dict[str, dict]:
    metas = {}
    with open(CSV_OBJETIVO, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            metas[fila["slug"]] = {
                "nombre_cientifico": fila["nombre_cientifico"],
                "cultivos": [c for c in fila["cultivos"].split(";") if c],
                "grupo": fila["grupo"],
                "prioridad": fila["prioridad"],
            }
    return metas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slugs", nargs="*", help="slugs de /plaga/<slug>")
    ap.add_argument("--todo", action="store_true", help="recorrer todo el sitemap")
    ap.add_argument("--filtro-cultivo", nargs="*", default=[], help="con --todo: guardar sólo si 'Cultivos / Órgano afectado' contiene alguno")
    ap.add_argument("--forzar", action="store_true", help="volver a descargar aunque exista el .md")
    args = ap.parse_args()

    SALIDA.mkdir(parents=True, exist_ok=True)
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    reintentos = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                       allowed_methods=("GET",), raise_on_status=False)
    sesion.mount("https://", HTTPAdapter(max_retries=reintentos))
    metas = leer_objetivo()

    if args.todo:
        urls = urls_del_sitemap(sesion)
    else:
        slugs = args.slugs or list(metas)
        urls = [f"{BASE}/plaga/{s}" for s in slugs]

    ok, fallas = 0, []
    for i, url in enumerate(urls, 1):
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        destino = SALIDA / f"{slug}.md"
        if destino.exists() and not args.forzar:
            continue
        try:
            r = sesion.get(url, timeout=60)
            if r.status_code != 200:
                fallas.append((slug, f"HTTP {r.status_code}"))
                continue
            ficha = parsear_ficha(r.text, url)
            if args.filtro_cultivo:
                cult = ficha["secciones"].get("Cultivos / Órgano afectado", "")
                if not any(c.lower() in cult.lower() for c in args.filtro_cultivo):
                    continue
            destino.write_text(a_markdown(slug, url, ficha, metas.get(slug, {})), encoding="utf-8")
            ok += 1
            print(f"[{i}/{len(urls)}] ok  {slug}")
        except Exception as e:  # noqa: BLE001
            fallas.append((slug, repr(e)))
        time.sleep(PAUSA_SEG)

    print(f"\nGuardadas: {ok}  ·  Fallas: {len(fallas)}")
    for s, e in fallas:
        print(f"  - {s}: {e}")
    return 0 if not fallas else 1


if __name__ == "__main__":
    sys.exit(main())
