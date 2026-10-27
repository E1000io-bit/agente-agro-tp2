"""
Capacidades del agente de CONSULTAS (sin fotos), como funciones que devuelven TEXTO listo para
pasarle al LLM como Observation. Las usan los dos agentes:
  - agente/react_manual.py   (ReAct escrito a mano, como Agente_ReAct.ipynb)
  - agente/agente_langchain.py (create_agent de LangChain, como Agente_LangChain.ipynb)

Devolver texto corto y con la URL de la fuente ayuda a que un modelo chico (7B) cite bien.
"""
from __future__ import annotations

from datetime import datetime

from agente.rag.buscar import buscar_fichas
from agente.tools.clima import clima_lote, geocodificar
from agente.tools.glosario import glosario

CULTIVOS = {"maiz", "maíz", "soja", "trigo", "mani", "maní"}
MAX_CHARS_FRAGMENTO = 700


def _norm_cultivo(c: str | None) -> str | None:
    if not c:
        return None
    c = c.strip().lower().replace("í", "i")
    return c if c in {"maiz", "soja", "trigo", "mani"} else None


def _formatear(resultados: list[dict]) -> str:
    if not resultados:
        return "Sin resultados en las fuentes oficiales disponibles."
    bloques = []
    for i, r in enumerate(resultados, 1):
        texto = r["texto"]
        if len(texto) > MAX_CHARS_FRAGMENTO:
            texto = texto[:MAX_CHARS_FRAGMENTO].rsplit(" ", 1)[0] + " […]"
        fecha = f" · fecha {r['fecha']}" if r["fuente"] != "sinavimo" else ""
        bloques.append(f"[{i}] {r['titulo']} — {r['seccion']}{fecha}\nURL: {r['url']}\n{texto}")
    return "\n\n".join(bloques)


def consultar_fichas(consulta: str, cultivo: str | None = None, k: int = 4) -> str:
    """Busca en las 70 fichas oficiales de SINAVIMO (síntomas, biología, condiciones predisponentes)."""
    res = buscar_fichas(consulta, cultivo=_norm_cultivo(cultivo), k=k, fuente="sinavimo")
    return _formatear(res)


def situacion_chicharrita(consulta: str = "situación actual de la chicharrita", k: int = 3) -> str:
    """Busca en los informes más recientes de la Red Nacional de Monitoreo de Dalbulus maidis."""
    res = buscar_fichas(consulta, fuente="chicharrita", mas_reciente=True, k=k)
    return _formatear(res)


def clima_localidad(localidad: str, dias: int = 7) -> str:
    """Pronóstico resumido para una localidad argentina (Open-Meteo)."""
    lugar = geocodificar(localidad)
    if "error" in lugar:
        return lugar["error"]
    c = clima_lote(lugar["lat"], lugar["lon"], dias=dias)
    ind = c["indicadores"]
    filas = [
        f"{d['fecha']}: Tmax {d['temperature_2m_max']}°C / Tmin {d['temperature_2m_min']}°C, "
        f"lluvia {d['precipitation_sum']} mm, HR {d['relative_humidity_2m_mean']}%, "
        f"prob. mojado de hoja {d.get('leaf_wetness_probability_mean')}%"
        for d in c["dias"]
    ]
    return (
        f"Localidad: {lugar['nombre']} ({lugar.get('provincia')}) lat {lugar['lat']:.2f}, lon {lugar['lon']:.2f}\n"
        f"Próximos {len(filas)} días — lluvia total {ind['lluvia_total_mm']} mm, "
        f"días con lluvia {ind['dias_con_lluvia_>=1mm']}, HR media {ind['hr_media_%']}%, "
        f"días con HR≥80% {ind['dias_hr_media_>=80%']}, días con mojado de hoja ≥60% {ind.get('dias_mojado_hoja_>=60%')}, "
        f"Tmax media {ind['tmax_media_C']}°C, Tmin media {ind['tmin_media_C']}°C\n"
        + "\n".join(filas)
        + "\nFuente: Open-Meteo (https://open-meteo.com), pronóstico."
    )


def definir_termino(termino: str) -> str:
    """Término agronómico en AGROVOC (FAO): etiqueta es/en y términos relacionados."""
    g = glosario(termino)
    if "error" in g:
        return g["error"]
    partes = [f"Término: {', '.join(g.get('es') or [])} (en inglés: {', '.join(g.get('en') or [])})"]
    if g.get("mas_amplio"):
        partes.append("Concepto más amplio: " + ", ".join(map(str, g["mas_amplio"])))
    if g.get("mas_especifico"):
        partes.append("Conceptos más específicos: " + ", ".join(map(str, g["mas_especifico"][:8])))
    partes.append(f"Fuente: AGROVOC (FAO) {g['uri']}")
    return "\n".join(partes)


def evaluar_riesgo(plaga: str, localidad: str, cultivo: str | None = None, dias: int = 7) -> str:
    """SKILL: junta las condiciones predisponentes de la plaga (ficha) con el pronóstico de la localidad.
    No decide sola: le deja al LLM los dos textos lado a lado para comparar."""
    cond = buscar_fichas(f"{plaga} condiciones predisponentes temperatura humedad", cultivo=_norm_cultivo(cultivo),
                         k=3, fuente="sinavimo")
    cond = [r for r in cond if r["seccion"].lower().startswith("condiciones")] or cond[:1]
    return (
        "=== CONDICIONES QUE FAVORECEN LA PLAGA (ficha oficial) ===\n"
        + _formatear(cond[:2])
        + "\n\n=== PRONÓSTICO DEL LUGAR ===\n"
        + clima_localidad(localidad, dias)
        + "\n\nCompará los rangos de la ficha con el pronóstico y decí si el riesgo es bajo, medio o alto, "
        "explicando con números. Es una estimación orientativa."
    )


def fecha_actual(_: str = "") -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
