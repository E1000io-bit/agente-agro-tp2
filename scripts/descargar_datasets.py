"""
Descarga/prepara datasets de imágenes para EVALUAR la tool de diagnóstico por foto
(no hace falta entrenar nada: la idea es medir crop.health vs. el VLM del LLM).

    python scripts/descargar_datasets.py plantdoc        # git clone (CC BY 4.0, ~2.600 imágenes de campo)
    python scripts/descargar_datasets.py armar-set --n 10 # arma data/eval/imagenes/ con N fotos por clase relevante
    python scripts/descargar_datasets.py info            # instrucciones para los demás datasets

Las carpetas de clase se mapean a fichas del corpus por palabras clave (no por nombre exacto,
así funciona con PlantDoc y con el dataset de maíz de Mendeley aunque cambien mayúsculas o espacios):
    maíz + rust          -> puccinia-sorghi
    maíz + blight        -> exserohilum-turcicum
    maíz + gray/grey     -> cercospora-zeae-maydis
    maíz + healthy       -> sana
    maíz + insect        -> dano-insectos
    soy* (sin enfermedad)-> sana
"""
from __future__ import annotations

import argparse
import csv
import random
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATASETS = RAIZ / "datasets"
SET_EVAL = RAIZ / "data" / "eval" / "imagenes"

REGLAS = [  # (palabras que deben aparecer en el nombre de la carpeta, slug)
    (("rust",), "puccinia-sorghi"),
    (("blight",), "exserohilum-turcicum"),
    (("gray",), "cercospora-zeae-maydis"),
    (("grey",), "cercospora-zeae-maydis"),
    (("healthy",), "sana"),
    (("insect",), "dano-insectos"),
]


def clasificar_carpeta(nombre: str, es_maiz: bool) -> str | None:
    n = nombre.lower()
    if "soy" in n and not any(w in n for w in ("rust", "spot", "blight", "mildew")):
        return "sana"
    if not (es_maiz or "corn" in n or "maize" in n):
        return None
    for palabras, slug in REGLAS:
        if all(w in n for w in palabras):
            return slug
    return None

INFO = """
Datasets recomendados
---------------------
1) PlantDoc (CC BY 4.0) — fotos reales de campo, 13 especies, 17 clases. IDEAL PARA EVALUAR.
   git clone https://github.com/pratikkayal/PlantDoc-Dataset datasets/PlantDoc-Dataset
   Versión para detección (bounding boxes): https://public.roboflow.com/object-detection/plantdoc

2) Corn Leaf Disease (Mendeley, 2026, CC BY 4.0) — ~17.000 hojas de maíz, 5 clases
   (roya común, tizón, mancha gris, sana, daño por insectos).
   Bajar el ZIP a mano desde https://data.mendeley.com/datasets/hmkd6nbngr y descomprimir en
   datasets/corn-mendeley/ (una carpeta por clase). Después: python scripts/descargar_datasets.py armar-set

3) PlantVillage (TFDS "plant_village") — 54.303 imágenes, 38 clases, ~830 MB.
   OJO: fotos de laboratorio con fondo uniforme; NO sirve para medir desempeño a campo.
   pip install tensorflow-datasets && python -c "import tensorflow_datasets as t; t.load('plant_village')"

4) IP102 — 75.222 imágenes de 102 plagas de insectos (18.976 con bounding boxes).
   https://github.com/xpwu95/IP102  (links de descarga en el README del repo)

5) Digipathos (Embrapa) — patologías de plantas de Brasil, wrapper Python:
   https://digipathos.readthedocs.io
"""


def plantdoc() -> None:
    destino = DATASETS / "PlantDoc-Dataset"
    if destino.exists():
        print(f"Ya existe {destino}")
        return
    DATASETS.mkdir(exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/pratikkayal/PlantDoc-Dataset", str(destino)], check=True)


def armar_set(n: int) -> None:
    """Copia N imágenes por clase mapeada a data/eval/imagenes/<slug>/ y escribe un CSV de etiquetas."""
    random.seed(42)
    fuentes = []
    pd = DATASETS / "PlantDoc-Dataset" / "test"
    if pd.exists():
        for c in sorted(p for p in pd.iterdir() if p.is_dir()):
            if (s := clasificar_carpeta(c.name, es_maiz=False)):
                fuentes.append((c, s, "PlantDoc"))
    mm = DATASETS / "corn-mendeley"
    if mm.exists():
        for c in sorted(p for p in mm.rglob("*") if p.is_dir()):
            if (s := clasificar_carpeta(c.name, es_maiz=True)):
                fuentes.append((c, s, "Corn-Mendeley"))
    if not fuentes:
        print("No hay datasets descargados. Correr primero: python scripts/descargar_datasets.py plantdoc")
        sys.exit(1)
    SET_EVAL.mkdir(parents=True, exist_ok=True)
    filas = []
    for carpeta, slug, origen in fuentes:
        imgs = [p for p in carpeta.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        for p in random.sample(imgs, min(n, len(imgs))):
            dst = SET_EVAL / slug / f"{origen}_{p.name}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            filas.append({"archivo": str(dst.relative_to(RAIZ)), "slug_esperado": slug, "origen": origen, "clase_original": carpeta.name})
    with open(SET_EVAL / "etiquetas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} imágenes -> {SET_EVAL}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["plantdoc", "armar-set", "info"])
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()
    {"plantdoc": plantdoc, "info": lambda: print(INFO), "armar-set": lambda: armar_set(a.n)}[a.accion]()


if __name__ == "__main__":
    main()
