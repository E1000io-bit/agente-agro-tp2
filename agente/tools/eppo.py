"""
Tool EPPO Global Database (opcional): código EPPO, hospederos y distribución de una plaga.

Requiere registro gratuito en https://data.eppo.int (Open Data Licence) para obtener el token.
API REST v1.0 (rutas confirmadas: responden 403 sin token válido):
    GET  https://data.eppo.int/api/rest/1.0/taxon/{EPPOCODE}?authtoken=...
    GET  https://data.eppo.int/api/rest/1.0/taxon/{EPPOCODE}/hosts?authtoken=...
    GET  https://data.eppo.int/api/rest/1.0/taxon/{EPPOCODE}/distribution?authtoken=...
    POST https://data.eppo.int/api/rest/1.0/tools/names2codes   (form: intext=<nombres separados por |>, authtoken=...)

Nota: el formato exacto de las respuestas no se pudo verificar sin token; las funciones devuelven
el JSON crudo y el agente lo resume. Probar con `python -m agente.tools.eppo "Dalbulus maidis"`.
Variable de entorno: EPPO_TOKEN
"""
from __future__ import annotations

import os

from agente.tools._http import sesion

BASE = "https://data.eppo.int/api/rest/1.0"


def _token() -> str | None:
    return os.getenv("EPPO_TOKEN")


def nombre_a_codigo(nombre_cientifico: str) -> dict:
    tok = _token()
    if not tok:
        return {"error": "Falta EPPO_TOKEN en .env (registro gratis en https://data.eppo.int)"}
    r = sesion().post(f"{BASE}/tools/names2codes", data={"intext": nombre_cientifico, "authtoken": tok}, timeout=30)
    return r.json() if r.ok else {"error": f"HTTP {r.status_code}", "detalle": r.text[:300]}


def hospederos(codigo_eppo: str) -> dict:
    tok = _token()
    if not tok:
        return {"error": "Falta EPPO_TOKEN en .env"}
    r = sesion().get(f"{BASE}/taxon/{codigo_eppo}/hosts", params={"authtoken": tok}, timeout=30)
    return r.json() if r.ok else {"error": f"HTTP {r.status_code}", "detalle": r.text[:300]}


def distribucion(codigo_eppo: str) -> dict:
    tok = _token()
    if not tok:
        return {"error": "Falta EPPO_TOKEN en .env"}
    r = sesion().get(f"{BASE}/taxon/{codigo_eppo}/distribution", params={"authtoken": tok}, timeout=30)
    return r.json() if r.ok else {"error": f"HTTP {r.status_code}", "detalle": r.text[:300]}


def info_eppo(nombre_cientifico: str) -> dict:
    """Atajo para el agente: nombre científico -> código -> hospederos."""
    cod = nombre_a_codigo(nombre_cientifico)
    if "error" in cod:
        return cod
    # La respuesta de names2codes trae el código asociado al nombre; se toma el primero que aparezca
    texto = str(cod)
    import re

    m = re.search(r"\b([A-Z0-9]{5,6})\b", texto)
    if not m:
        return {"error": "No se encontró código EPPO", "respuesta": cod}
    return {"codigo": m.group(1), "hospederos": hospederos(m.group(1)), "fuente": "EPPO Global Database"}


if __name__ == "__main__":
    import json
    import sys

    print(json.dumps(info_eppo(sys.argv[1] if len(sys.argv) > 1 else "Dalbulus maidis"), ensure_ascii=False, indent=2))
