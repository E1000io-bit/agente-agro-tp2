"""
Tool de clima del lote (Open-Meteo, gratis y sin API key para uso no comercial; atribución CC BY 4.0).

- geocodificar("Río Cuarto")                  -> lat/lon de una localidad argentina
- clima_lote(lat, lon, dias=7)                 -> resumen diario de pronóstico + humedad de suelo
- clima_historico(lat, lon, "2026-09-01", "2026-09-30") -> resumen diario de lo que pasó (ERA5)

Las variables elegidas son las que se cruzan con la sección "Condiciones predisponentes"
de las fichas SINAVIMO: temperatura, lluvia, humedad relativa y probabilidad de mojado de hoja.
Docs: https://open-meteo.com/en/docs
"""
from __future__ import annotations

from statistics import mean

from agente.tools._http import sesion

PRONOSTICO = "https://api.open-meteo.com/v1/forecast"
HISTORICO = "https://archive-api.open-meteo.com/v1/archive"
GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"
TZ = "America/Argentina/Cordoba"

DIARIAS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "relative_humidity_2m_mean",
    "et0_fao_evapotranspiration",
]
DIARIAS_PRONOSTICO = DIARIAS + ["leaf_wetness_probability_mean", "vapour_pressure_deficit_max"]
HORARIAS_SUELO = ["soil_moisture_3_to_9cm", "soil_moisture_9_to_27cm", "soil_temperature_6cm"]


def geocodificar(lugar: str, pais: str = "AR") -> dict:
    """Devuelve el mejor resultado para una localidad (nombre, provincia, lat, lon)."""
    r = sesion().get(GEOCODING, params={"name": lugar, "count": 3, "language": "es", "countryCode": pais}, timeout=30)
    r.raise_for_status()
    res = r.json().get("results") or []
    if not res:
        return {"error": f"No encontré la localidad '{lugar}'"}
    m = res[0]
    return {
        "nombre": m["name"],
        "provincia": m.get("admin1"),
        "departamento": m.get("admin2"),
        "lat": m["latitude"],
        "lon": m["longitude"],
        "otras_coincidencias": [f"{x['name']} ({x.get('admin1')})" for x in res[1:]],
    }


def _por_dia(horario: dict, clave: str) -> dict[str, float]:
    """Promedia una variable horaria por día."""
    acumulado: dict[str, list[float]] = {}
    for t, v in zip(horario["time"], horario[clave]):
        if v is not None:
            acumulado.setdefault(t[:10], []).append(v)
    return {d: round(mean(vs), 3) for d, vs in acumulado.items()}


def _resumen(diario: dict, unidades: dict) -> dict:
    dias = diario["time"]
    filas = []
    for i, d in enumerate(dias):
        filas.append({k: diario[k][i] for k in diario if k != "time"} | {"fecha": d})
    lluvia = [f.get("precipitation_sum") or 0 for f in filas]
    hr = [f["relative_humidity_2m_mean"] for f in filas if f.get("relative_humidity_2m_mean") is not None]
    mojado = [f["leaf_wetness_probability_mean"] for f in filas if f.get("leaf_wetness_probability_mean") is not None]
    tmax = [f["temperature_2m_max"] for f in filas if f.get("temperature_2m_max") is not None]
    tmin = [f["temperature_2m_min"] for f in filas if f.get("temperature_2m_min") is not None]
    indicadores = {
        "lluvia_total_mm": round(sum(lluvia), 1),
        "dias_con_lluvia_>=1mm": sum(1 for x in lluvia if x >= 1),
        "hr_media_%": round(mean(hr), 1) if hr else None,
        "dias_hr_media_>=80%": sum(1 for x in hr if x >= 80),
        "tmax_media_C": round(mean(tmax), 1) if tmax else None,
        "tmin_media_C": round(mean(tmin), 1) if tmin else None,
    }
    if mojado:
        indicadores["dias_mojado_hoja_>=60%"] = sum(1 for x in mojado if x >= 60)
    return {"indicadores": indicadores, "dias": filas, "unidades": unidades}


def clima_lote(lat: float, lon: float, dias: int = 7) -> dict:
    """Pronóstico diario (hasta 16 días) + humedad y temperatura de suelo promedio por día."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(DIARIAS_PRONOSTICO),
        "hourly": ",".join(HORARIAS_SUELO),
        "forecast_days": max(1, min(dias, 16)),
        "timezone": TZ,
    }
    r = sesion().get(PRONOSTICO, params=params, timeout=30)
    r.raise_for_status()
    d = r.json()
    out = _resumen(d["daily"], d["daily_units"])
    suelo = {k: _por_dia(d["hourly"], k) for k in HORARIAS_SUELO}
    for fila in out["dias"]:
        for k, serie in suelo.items():
            fila[k] = serie.get(fila["fecha"])
    out["unidades"] |= {k: d["hourly_units"][k] for k in HORARIAS_SUELO}
    out["fuente"] = "Open-Meteo (pronóstico), CC BY 4.0 — https://open-meteo.com"
    out["ubicacion"] = {"lat": d["latitude"], "lon": d["longitude"], "elevacion_m": d.get("elevation")}
    return out


def clima_historico(lat: float, lon: float, desde: str, hasta: str) -> dict:
    """Clima observado/reanálisis entre dos fechas (AAAA-MM-DD). Útil para '¿llovió mucho este mes?'."""
    params = {"latitude": lat, "longitude": lon, "start_date": desde, "end_date": hasta,
              "daily": ",".join(DIARIAS), "timezone": TZ}
    r = sesion().get(HISTORICO, params=params, timeout=60)
    r.raise_for_status()
    d = r.json()
    out = _resumen(d["daily"], d["daily_units"])
    out["fuente"] = "Open-Meteo Historical Weather API (ERA5), CC BY 4.0 — https://open-meteo.com"
    return out


if __name__ == "__main__":
    import json

    lugar = geocodificar("Río Cuarto")
    print(json.dumps(lugar, ensure_ascii=False, indent=2))
    c = clima_lote(lugar["lat"], lugar["lon"], dias=5)
    print(json.dumps(c["indicadores"], ensure_ascii=False, indent=2))
    print(json.dumps(c["dias"][0], ensure_ascii=False, indent=2))
