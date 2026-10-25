"""
Tools de diagnóstico por imagen.

1) diagnosticar_cultivo(ruta_imagen)  -> crop.health (Kindwise): cultivo + enfermedad/plaga probable.
   - 23 cultivos (incluye maíz, soja, trigo, cebada, papa; NO girasol ni maní), ~288 problemas.
   - 100 créditos gratis al registrarse (1 identificación = 1 crédito): https://admin.kindwise.com
   - Endpoint: POST https://crop.kindwise.com/api/v1/identification  (header "Api-Key")
     body JSON: {"images": [<base64>], "similar_images": true, "latitude": .., "longitude": ..}
     query: ?details=common_names,description,symptoms,treatment,severity,spreading,eppo_code&language=es
   - Las respuestas se cachean en .cache/ por hash de la imagen para NO gastar créditos repitiendo.

2) identificar_maleza(ruta_imagen)  -> Pl@ntNet (identificación de especies, sirve para malezas).
   - Endpoint: POST https://my-api.plantnet.org/v2/identify/all?api-key=...&lang=es  (multipart)
   - Cuota diaria gratuita por usuario: https://my.plantnet.org

Variables de entorno (.env): CROP_HEALTH_API_KEY, PLANTNET_API_KEY
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

from agente.tools._http import sesion

RAIZ = Path(__file__).resolve().parents[2]
CACHE = RAIZ / ".cache" / "imagen"
CROP_URL = "https://crop.kindwise.com/api/v1/identification"
PLANTNET_URL = "https://my-api.plantnet.org/v2/identify/all"
DETALLES = "common_names,type,description,symptoms,treatment,severity,spreading,eppo_code,taxonomy"


def _hash(datos: bytes, extra: str = "") -> str:
    return hashlib.sha256(datos + extra.encode()).hexdigest()[:20]


def _cache_get(clave: str) -> dict | None:
    p = CACHE / f"{clave}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _cache_put(clave: str, data: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{clave}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _resumir_sugerencias(clasif: dict | None, k: int = 3) -> list[dict]:
    if not clasif:
        return []
    out = []
    for s in clasif.get("suggestions", [])[:k]:
        det = s.get("details") or {}
        out.append({
            "nombre": s.get("name"),
            "nombre_cientifico": s.get("scientific_name"),
            "probabilidad": round(s.get("probability", 0), 3),
            "nombres_comunes": det.get("common_names"),
            "tipo": det.get("type"),
            "sintomas": det.get("symptoms"),
            "severidad": det.get("severity"),
            "propagacion": det.get("spreading"),
            "tratamiento_segun_proveedor": det.get("treatment"),
            "eppo_code": det.get("eppo_code"),
        })
    return out


def diagnosticar_cultivo(ruta_imagen: str, lat: float | None = None, lon: float | None = None,
                         idioma: str = "es", usar_cache: bool = True) -> dict:
    """Identifica cultivo y problema sanitario probable a partir de una foto (crop.health)."""
    api_key = os.getenv("CROP_HEALTH_API_KEY")
    datos = Path(ruta_imagen).read_bytes()
    clave = "crop_" + _hash(datos, f"{lat},{lon},{idioma}")
    if usar_cache and (c := _cache_get(clave)):
        return c | {"cache": True}
    if not api_key:
        return {"error": "Falta CROP_HEALTH_API_KEY en .env",
                "sugerencia": "Registrarse en https://admin.kindwise.com (100 créditos gratis) o usar el VLM del LLM como fallback."}

    payload = {"images": [base64.b64encode(datos).decode("ascii")], "similar_images": False}
    if lat is not None and lon is not None:
        payload |= {"latitude": lat, "longitude": lon}
    r = sesion().post(CROP_URL, params={"details": DETALLES, "language": idioma},
                      headers={"Api-Key": api_key, "Content-Type": "application/json"},
                      json=payload, timeout=90)
    if r.status_code >= 400:
        return {"error": f"crop.health respondió HTTP {r.status_code}", "detalle": r.text[:500]}
    crudo = r.json()
    res = crudo.get("result", {})
    out = {
        "es_planta": res.get("is_plant", {}).get("probability"),
        "cultivo": _resumir_sugerencias(res.get("crop"), k=2),
        "problemas_probables": _resumir_sugerencias(res.get("disease"), k=3),
        "creditos_restantes": crudo.get("remaining_credits"),
        "fuente": "crop.health (Kindwise) — https://www.kindwise.com/crop-health",
        "advertencia": "Diagnóstico orientativo por imagen; confirmar a campo y con un ingeniero agrónomo.",
    }
    _cache_put(clave, out)
    return out


def identificar_maleza(ruta_imagen: str, organo: str = "auto", usar_cache: bool = True) -> dict:
    """Identifica la especie vegetal de una foto (útil para malezas) con Pl@ntNet."""
    api_key = os.getenv("PLANTNET_API_KEY")
    datos = Path(ruta_imagen).read_bytes()
    clave = "plantnet_" + _hash(datos, organo)
    if usar_cache and (c := _cache_get(clave)):
        return c | {"cache": True}
    if not api_key:
        return {"error": "Falta PLANTNET_API_KEY en .env", "sugerencia": "Crear cuenta gratis en https://my.plantnet.org"}
    files = [("images", (Path(ruta_imagen).name, datos))]
    r = sesion().post(PLANTNET_URL, params={"api-key": api_key, "lang": "es", "nb-results": 5},
                      files=files, data={"organs": [organo]}, timeout=90)
    if r.status_code >= 400:
        return {"error": f"Pl@ntNet respondió HTTP {r.status_code}", "detalle": r.text[:500]}
    crudo = r.json()
    out = {
        "mejor_coincidencia": crudo.get("bestMatch"),
        "candidatos": [
            {
                "nombre_cientifico": c["species"].get("scientificNameWithoutAuthor"),
                "nombres_comunes": c["species"].get("commonNames", [])[:5],
                "familia": c["species"].get("family", {}).get("scientificNameWithoutAuthor"),
                "score": round(c.get("score", 0), 3),
            }
            for c in crudo.get("results", [])[:5]
        ],
        "fuente": "Pl@ntNet API — https://my.plantnet.org",
    }
    _cache_put(clave, out)
    return out


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("uso: python -m agente.tools.imagen <foto.jpg> [maleza]")
        raise SystemExit(1)
    f = identificar_maleza if len(sys.argv) > 2 and sys.argv[2] == "maleza" else diagnosticar_cultivo
    print(json.dumps(f(sys.argv[1]), ensure_ascii=False, indent=2))
