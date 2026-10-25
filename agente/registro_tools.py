"""
Registro único de tools del agente: nombre -> (función Python, JSON Schema de parámetros).

Está pensado para enchufarse en cualquier framework:
- Function calling "crudo" (OpenAI / Anthropic / Gemini): usar `schemas_openai()` o `schemas_anthropic()`.
- LangChain / LangGraph: `StructuredTool.from_function(func, name=..., description=...)` por cada entrada.
- MCP: exponer cada entrada como tool de un servidor MCP.
- Loop propio: `ejecutar(nombre, argumentos_dict)`.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from agente.rag.buscar import buscar_fichas
from agente.tools.clima import clima_historico, clima_lote, geocodificar
from agente.tools.eppo import info_eppo
from agente.tools.glosario import glosario
from agente.tools.imagen import diagnosticar_cultivo, identificar_maleza

TOOLS: dict[str, dict[str, Any]] = {
    "buscar_fichas": {
        "func": buscar_fichas,
        "description": (
            "Busca en la base de conocimiento oficial (fichas de plagas SINAVIMO-SENASA e informes de la "
            "Red Nacional de Monitoreo de chicharrita). Usar SIEMPRE antes de afirmar síntomas, condiciones "
            "predisponentes, biología o situación de una plaga, enfermedad o maleza. Devuelve fragmentos con URL para citar."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Pregunta o descripción de síntomas en español"},
                "cultivo": {"type": "string", "enum": ["maiz", "soja", "trigo", "mani"], "description": "Filtrar por cultivo (opcional)"},
                "k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
                "fuente": {"type": "string", "enum": ["sinavimo", "chicharrita"], "description": "Limitar a fichas o a informes de chicharrita"},
                "mas_reciente": {"type": "boolean", "description": "Priorizar el informe más reciente (preguntas sobre la situación actual)"},
            },
            "required": ["consulta"],
        },
    },
    "diagnosticar_cultivo": {
        "func": diagnosticar_cultivo,
        "description": (
            "Diagnóstico orientativo por FOTO de una planta de cultivo (crop.health). Devuelve cultivo y hasta 3 "
            "problemas probables con probabilidad. Después de usarla, validar cada candidato con buscar_fichas. "
            "Si la probabilidad máxima es < 0.5, pedir otra foto."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ruta_imagen": {"type": "string"},
                "lat": {"type": "number"},
                "lon": {"type": "number"},
            },
            "required": ["ruta_imagen"],
        },
    },
    "identificar_maleza": {
        "func": identificar_maleza,
        "description": "Identifica la especie de una planta por FOTO (Pl@ntNet). Usar para malezas, no para enfermedades.",
        "parameters": {
            "type": "object",
            "properties": {
                "ruta_imagen": {"type": "string"},
                "organo": {"type": "string", "enum": ["auto", "leaf", "flower", "fruit", "bark", "habit"], "default": "auto"},
            },
            "required": ["ruta_imagen"],
        },
    },
    "geocodificar": {
        "func": geocodificar,
        "description": "Convierte el nombre de una localidad argentina en latitud/longitud (para usar con clima_lote).",
        "parameters": {"type": "object", "properties": {"lugar": {"type": "string"}}, "required": ["lugar"]},
    },
    "clima_lote": {
        "func": clima_lote,
        "description": (
            "Pronóstico diario (hasta 16 días) de temperatura, lluvia, humedad relativa, probabilidad de mojado de hoja, "
            "ET0 y humedad de suelo para un punto. Usar para evaluar si el clima coincide con las 'Condiciones predisponentes' de una ficha."
        ),
        "parameters": {
            "type": "object",
            "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}, "dias": {"type": "integer", "default": 7, "maximum": 16}},
            "required": ["lat", "lon"],
        },
    },
    "clima_historico": {
        "func": clima_historico,
        "description": "Clima diario observado (reanálisis ERA5) entre dos fechas AAAA-MM-DD para un punto.",
        "parameters": {
            "type": "object",
            "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}, "desde": {"type": "string"}, "hasta": {"type": "string"}},
            "required": ["lat", "lon", "desde", "hasta"],
        },
    },
    "glosario": {
        "func": glosario,
        "description": "Define o traduce un término agronómico con el tesauro AGROVOC (FAO): etiqueta es/en, sinónimos, términos relacionados.",
        "parameters": {"type": "object", "properties": {"termino": {"type": "string"}}, "required": ["termino"]},
    },
    "info_eppo": {
        "func": info_eppo,
        "description": "Opcional. Código EPPO y plantas hospederas de una plaga según la EPPO Global Database (requiere token).",
        "parameters": {"type": "object", "properties": {"nombre_cientifico": {"type": "string"}}, "required": ["nombre_cientifico"]},
    },
}


def schemas_openai() -> list[dict]:
    return [{"type": "function", "function": {"name": n, "description": t["description"], "parameters": t["parameters"]}}
            for n, t in TOOLS.items()]


def schemas_anthropic() -> list[dict]:
    return [{"name": n, "description": t["description"], "input_schema": t["parameters"]} for n, t in TOOLS.items()]


def ejecutar(nombre: str, argumentos: dict | str) -> str:
    """Ejecuta una tool y devuelve el resultado como texto JSON (lo que se le pasa de vuelta al LLM)."""
    if isinstance(argumentos, str):
        argumentos = json.loads(argumentos or "{}")
    if nombre not in TOOLS:
        return json.dumps({"error": f"tool desconocida: {nombre}"})
    func: Callable = TOOLS[nombre]["func"]
    try:
        res = func(**argumentos)
    except Exception as e:  # noqa: BLE001 — el agente tiene que poder ver el error y reintentar
        res = {"error": f"{type(e).__name__}: {e}"}
    return json.dumps(res, ensure_ascii=False, default=str)


if __name__ == "__main__":
    print(json.dumps(schemas_openai(), ensure_ascii=False, indent=2))
