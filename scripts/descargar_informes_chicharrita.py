"""
Descarga los informes de la Red Nacional de Monitoreo de Dalbulus maidis (chicharrita del maíz)
publicados por MAIZAR, guarda el PDF y una versión en texto (Markdown) para el RAG.

Fuentes:
  - Listado MAIZAR: https://www.maizar.org.ar/vertodas_area.php?id=39  (informes recientes, 2024-2026)
  - Listado INTA:   https://www.argentina.gob.ar/inta/achaparramiento-del-maiz/red-nacional-de-monitoreo-informes
                    (informes N° 1 a 21, 2024-2025)

Uso:
    python scripts/descargar_informes_chicharrita.py            # últimos 10 informes de MAIZAR
    python scripts/descargar_informes_chicharrita.py --n 30     # últimos 30
    python scripts/descargar_informes_chicharrita.py --inta     # además, los 21 primeros del sitio del INTA
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "data" / "corpus" / "chicharrita"
PDFS = SALIDA / "pdf"
HEADERS = {"User-Agent": "TP-IA-agente-agro/1.0 (uso academico)"}
MAIZAR_LISTA = "https://www.maizar.org.ar/vertodas_area.php?id=39"
INTA_LISTA = "https://www.argentina.gob.ar/inta/achaparramiento-del-maiz/red-nacional-de-monitoreo-informes"
PAUSA_SEG = 1.5


def nueva_sesion() -> requests.Session:
    """Sesión con reintentos automáticos (los servidores a veces cortan la conexión)."""
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    s = requests.Session()
    s.headers.update(HEADERS)
    reintentos = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                       allowed_methods=("GET",), raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=reintentos))
    s.mount("http://", HTTPAdapter(max_retries=reintentos))
    return s


def listar_maizar(s: requests.Session) -> list[dict]:
    r = s.get(MAIZAR_LISTA, timeout=60)
    r.encoding = r.apparent_encoding or "latin-1"
    h = r.text
    # Cada item: <a href="vertext.php?id=NNNN"> ... NN° Informe ... dd/mm/aaaa
    items = []
    for m in re.finditer(r'href="(vertext\.php\?id=(\d+))"[^>]*>(.*?)</a>', h, re.S):
        texto = html.unescape(re.sub(r"<[^>]+>", " ", m.group(3)))
        texto = re.sub(r"\s+", " ", texto).strip()
        if "Informe" not in texto:
            continue
        num = re.search(r"(\d+)\s*°", texto)
        items.append({"pagina": urljoin(MAIZAR_LISTA, m.group(1)), "titulo": texto,
                      "numero": int(num.group(1)) if num else None})
    # fechas: aparecen después de cada título en el listado
    fechas = re.findall(r"(\d{2}/\d{2}/\d{4})", re.sub(r"<[^>]+>", " ", h))
    for it, f in zip(items, fechas):
        it["fecha"] = dt.datetime.strptime(f, "%d/%m/%Y").date().isoformat()
    # quitar duplicados por página
    vistos, unicos = set(), []
    for it in items:
        if it["pagina"] not in vistos:
            vistos.add(it["pagina"])
            unicos.append(it)
    return unicos


def pdf_de_pagina(s: requests.Session, pagina: str) -> str | None:
    r = s.get(pagina, timeout=60)
    r.encoding = r.apparent_encoding or "latin-1"
    m = re.search(r'href="([^"]+\.pdf)"', r.text, re.I)
    if not m:
        return None
    url = html.unescape(m.group(1))
    url = urljoin(pagina, url)
    return quote(url, safe=":/%?=&")


def listar_inta(s: requests.Session) -> list[dict]:
    h = s.get(INTA_LISTA, timeout=60).text
    urls = sorted(set(re.findall(r'href="(https://www\.argentina\.gob\.ar/sites/default/files/[^"]+informe[^"]+\.pdf)"', h)))
    out = []
    for u in urls:
        num = re.search(r"/(\d+)(?:deg|do|er|to|mo|vo|no|_)", u)
        out.append({"pdf": u, "titulo": f"Informe {num.group(1) if num else ''} Red Nacional de Monitoreo (INTA)",
                    "numero": int(num.group(1)) if num else None, "fecha": "", "pagina": INTA_LISTA})
    return out


def pdf_a_texto(ruta: Path) -> str:
    lector = PdfReader(str(ruta))
    paginas = []
    for i, p in enumerate(lector.pages, 1):
        t = (p.extract_text() or "").strip()
        if t:
            paginas.append(f"<!-- página {i} -->\n{t}")
    return "\n\n".join(paginas)


def guardar(s: requests.Session, it: dict) -> Path | None:
    num = it.get("numero") or 0
    base = f"informe-{num:03d}"
    md = SALIDA / f"{base}.md"
    if md.exists():
        return md
    pdf_url = it.get("pdf") or pdf_de_pagina(s, it["pagina"])
    if not pdf_url:
        print(f"  sin PDF: {it['titulo']}")
        return None
    time.sleep(PAUSA_SEG)
    r = s.get(pdf_url, timeout=120)
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        print(f"  no se pudo bajar {pdf_url} (HTTP {r.status_code})")
        return None
    pdf = PDFS / f"{base}.pdf"
    pdf.write_bytes(r.content)
    texto = pdf_a_texto(pdf)
    fm = "\n".join([
        "---",
        f"slug: chicharrita-{base}",
        f'titulo: "{it["titulo"]}"',
        f"numero: {num}",
        f"fecha: {it.get('fecha', '')}",
        "tema: Red Nacional de Monitoreo de Dalbulus maidis",
        "cultivos_tp: [maiz]",
        "fuente: Red Nacional de Monitoreo (INTA / MAIZAR y otras instituciones)",
        f"url: {pdf_url}",
        f"pagina: {it['pagina']}",
        f"fecha_descarga: {dt.date.today().isoformat()}",
        "---",
        "",
        f"# {it['titulo']}",
        "",
    ])
    md.write_text(fm + "\n" + texto + f"\n\n_Fuente: [{it['titulo']}]({pdf_url})_\n", encoding="utf-8")
    return md


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="cuántos informes recientes de MAIZAR bajar")
    ap.add_argument("--inta", action="store_true", help="bajar también los informes 1-21 del sitio del INTA")
    args = ap.parse_args()
    PDFS.mkdir(parents=True, exist_ok=True)
    s = nueva_sesion()

    items = listar_maizar(s)[: args.n]
    if args.inta:
        items += listar_inta(s)
    ok = 0
    for it in items:
        p = guardar(s, it)
        if p:
            ok += 1
            print(f"ok  {p.name}  ({it.get('fecha', '')})")
        time.sleep(PAUSA_SEG)
    print(f"\nGuardados: {ok}/{len(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
