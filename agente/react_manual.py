"""
AgroAgente — versión ReAct MANUAL (misma estructura que 17_Agentes/Agente_ReAct.ipynb de la cátedra):

    Tool (dataclass) → descripción de tools → prompt ReAct → parser con regex → bucle
    Thought → Action → Observation → FINAL, con traza de cada paso.

Uso:
    from agente.react_manual import AgroAgenteReAct
    ag = AgroAgenteReAct()
    respuesta, traza = ag.preguntar("¿Qué condiciones favorecen la roya común del maíz?")

    python -m agente.react_manual "pregunta"        # una consulta, imprime la traza
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from agente import consultas
from agente.guardrails import NOTA_PARA_EL_LLM, pide_dosis, revisar_respuesta


# ---------------------------------------------------------------- tools
@dataclass
class Tool:
    name: str
    description: str
    func: Callable[[str], str]


def parse_tool_input(text: str) -> Tuple[str, Dict[str, str]]:
    """'roya común | cultivo=maiz | k=3' -> ('roya común', {'cultivo': 'maiz', 'k': '3'})  (igual que la cátedra)."""
    partes = [p.strip() for p in text.split("|")]
    params = {}
    for p in partes[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().lower()] = v.strip()
    return partes[0], params


def _int(v: Optional[str], defecto: int) -> int:
    try:
        return int(v) if v else defecto
    except ValueError:
        return defecto


def t_buscar_fichas(inp: str) -> str:
    q, p = parse_tool_input(inp)
    return consultas.consultar_fichas(q, cultivo=p.get("cultivo"), k=_int(p.get("k"), 4))


def t_chicharrita(inp: str) -> str:
    q, p = parse_tool_input(inp)
    return consultas.situacion_chicharrita(q or "situación actual", k=_int(p.get("k"), 3))


def t_clima(inp: str) -> str:
    q, p = parse_tool_input(inp)
    return consultas.clima_localidad(q, dias=_int(p.get("dias"), 7))


def t_riesgo(inp: str) -> str:
    q, p = parse_tool_input(inp)
    if not p.get("localidad"):
        return "Error: falta localidad. Formato: Action: evaluar_riesgo | plaga | localidad=Río Cuarto | cultivo=maiz"
    return consultas.evaluar_riesgo(q, p["localidad"], cultivo=p.get("cultivo"), dias=_int(p.get("dias"), 7))


def t_glosario(inp: str) -> str:
    q, _ = parse_tool_input(inp)
    return consultas.definir_termino(q)


TOOLS: Dict[str, Tool] = {
    "buscar_fichas": Tool(
        "buscar_fichas",
        "Busca en las fichas oficiales de plagas, enfermedades y malezas (SINAVIMO-SENASA): síntomas, biología, "
        "condiciones predisponentes, cultivos afectados y si está presente en Argentina.\n"
        "Usar SIEMPRE antes de dar información sobre una plaga o de diagnosticar por síntomas.\n"
        "Formato: Action: buscar_fichas | consulta | cultivo=maiz|soja|trigo|mani (opcional) | k=4\n"
        "Ejemplo: Action: buscar_fichas | manchas circulares con borde rojizo en hojas | cultivo=soja",
        t_buscar_fichas,
    ),
    "situacion_chicharrita": Tool(
        "situacion_chicharrita",
        "Busca en los informes más recientes de la Red Nacional de Monitoreo de la chicharrita del maíz "
        "(capturas por región y % de portación de Spiroplasma). Usar para '¿cómo viene la chicharrita?'.\n"
        "Formato: Action: situacion_chicharrita | región o tema\n"
        "Ejemplo: Action: situacion_chicharrita | capturas región Centro Norte",
        t_chicharrita,
    ),
    "clima_lote": Tool(
        "clima_lote",
        "Pronóstico de los próximos días (temperatura, lluvia, humedad, mojado de hoja) para una localidad argentina.\n"
        "Formato: Action: clima_lote | localidad | dias=7\n"
        "Ejemplo: Action: clima_lote | Marcos Juárez | dias=5",
        t_clima,
    ),
    "evaluar_riesgo": Tool(
        "evaluar_riesgo",
        "Skill: trae juntas las condiciones que favorecen una plaga (ficha oficial) y el pronóstico de una localidad, "
        "para estimar el riesgo. Usar cuando pregunten si hay riesgo de una plaga/enfermedad en un lugar.\n"
        "Formato: Action: evaluar_riesgo | plaga | localidad=... | cultivo=... (opcional)\n"
        "Ejemplo: Action: evaluar_riesgo | mancha amarilla del trigo | localidad=Pergamino | cultivo=trigo",
        t_riesgo,
    ),
    "glosario": Tool(
        "glosario",
        "Define o traduce un término agronómico con el tesauro AGROVOC (FAO).\n"
        "Formato: Action: glosario | término\nEjemplo: Action: glosario | umbral económico",
        t_glosario,
    ),
    "fecha_actual": Tool(
        "fecha_actual",
        "Devuelve la fecha y hora actual. Usar sólo si hace falta la fecha.\nFormato: Action: fecha_actual |",
        consultas.fecha_actual,
    ),
}


def build_tools_description(tools: Dict[str, Tool]) -> str:
    return "\n\n".join(f"- {t.name}: {t.description}" for t in tools.values())


# ---------------------------------------------------------------- prompt
SYSTEM_PROMPT = f"""
Sos AgroAgente, un agente ReAct que responde consultas fitosanitarias sobre maíz, soja, trigo y maní en Argentina.

==================================================
HERRAMIENTAS DISPONIBLES
==================================================

{build_tools_description(TOOLS)}

==================================================
FORMATO OBLIGATORIO
==================================================

Si necesitás una herramienta respondé EXACTAMENTE así y nada más:

Thought: razonamiento breve
Action: nombre_tool | input

Cuando tengas suficiente información respondé EXACTAMENTE:

FINAL: respuesta final para el usuario

==================================================
REGLAS
==================================================

1. SOLO podés usar: {", ".join(TOOLS)}. NO inventes herramientas.
2. NUNCA escribas Observation: la agrega Python.
3. Una sola Action por respuesta. La Action SIEMPRE lleva "|".
4. Antes de afirmar síntomas, condiciones o datos de una plaga, usá buscar_fichas. No respondas de memoria.
5. Basá la respuesta FINAL sólo en las Observations. Si no alcanzan, decí que no encontraste la información.
6. En la respuesta FINAL citá las fuentes con su URL, así: (Fuente: URL).
7. NUNCA indiques productos, principios activos ni dosis. Recomendá manejo integrado (monitoreo, umbrales,
   rotación, prácticas culturales) y derivá a un Ingeniero Agrónomo y a la etiqueta del producto registrado.
8. Si la consulta no es agronómica (precios, mercados, otros temas), respondé FINAL diciendo que está fuera de tu alcance.
9. Si falta un dato clave (por ejemplo el cultivo), podés preguntarlo en la respuesta FINAL.
10. Para diagnósticos por síntomas, aclarales que es orientativo y que conviene confirmarlo a campo.
11. Respondé en español rioplatense, claro y breve.

==================================================
EJEMPLO
==================================================

Thought: Necesito los síntomas de la roya común en las fichas.
Action: buscar_fichas | pústulas color óxido en hojas | cultivo=maiz

Observation: [1] Puccinia sorghi — Signos y síntomas / Daños
URL: https://www.sinavimo.gob.ar/plaga/puccinia-sorghi
...

Thought: Ya tengo la información de la ficha.
FINAL: Lo más probable es roya común del maíz (Puccinia sorghi)... (Fuente: https://www.sinavimo.gob.ar/plaga/puccinia-sorghi)
""".strip()

# ---------------------------------------------------------------- parser
ACTION_RE = re.compile(r"^\s*Action:\s*([\w\-]+)\s*\|\s*(.*?)\s*$", re.MULTILINE)
FINAL_RE = re.compile(r"(?:^|\n)\s*(?:FINAL|Final Answer)\s*:\s*(.*)", re.DOTALL | re.IGNORECASE)


def parse_action(llm_output: str) -> Optional[Tuple[str, str]]:
    m = ACTION_RE.search(llm_output)
    return (m.group(1).strip(), m.group(2).strip()) if m else None


def parse_final_answer(llm_output: str) -> Optional[str]:
    m = FINAL_RE.search(llm_output)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------- agente
class AgroAgenteReAct:
    """Agente ReAct con memoria de la conversación (los turnos anteriores quedan en `historial`)."""

    def __init__(self, call_llm: Callable[[List[Dict[str, str]]], str] | None = None, max_steps: int = 6,
                 max_chars_observacion: int = 3500):
        if call_llm is None:
            from agente.llm import call_llm as _call

            call_llm = _call
        self.call_llm = call_llm
        self.max_steps = max_steps
        self.max_chars_observacion = max_chars_observacion
        self.historial: List[Dict[str, str]] = []  # sólo preguntas y respuestas finales

    def reiniciar(self) -> None:
        self.historial = []

    def preguntar(self, user_query: str) -> Tuple[str, List[dict]]:
        contenido = user_query + (f"\n\n{NOTA_PARA_EL_LLM}" if pide_dosis(user_query) else "")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *self.historial,
                    {"role": "user", "content": contenido}]
        trace: List[dict] = []

        for step in range(1, self.max_steps + 1):
            llm_output = self.call_llm(messages)
            messages.append({"role": "assistant", "content": llm_output})
            action = parse_action(llm_output)
            final = parse_final_answer(llm_output)

            if action and not (final and llm_output.find("FINAL") < llm_output.find("Action")):
                nombre, entrada = action
                if nombre not in TOOLS:
                    obs = f"Error: la herramienta '{nombre}' no existe. Herramientas disponibles: {list(TOOLS)}"
                else:
                    try:
                        obs = TOOLS[nombre].func(entrada)
                    except Exception as e:  # noqa: BLE001 — el modelo ve el error y puede reintentar
                        obs = f"Error al ejecutar {nombre}: {type(e).__name__}: {e}"
                obs = obs[: self.max_chars_observacion]
                trace.append({"step": step, "llm_output": llm_output, "action": nombre, "input": entrada, "observation": obs})
                messages.append({"role": "user",
                                 "content": f"Observation: {obs}\n\nContinuá. Si ya podés responder, usá FINAL:"})
                continue

            respuesta = final if final else llm_output.strip()
            trace.append({"step": step, "llm_output": llm_output, "action": None, "observation": None})
            respuesta = revisar_respuesta(respuesta)
            self._recordar(user_query, respuesta)
            return respuesta, trace

        respuesta = "No llegué a una respuesta final dentro del máximo de pasos. ¿Podés reformular la consulta?"
        self._recordar(user_query, respuesta)
        return respuesta, trace

    def _recordar(self, pregunta: str, respuesta: str) -> None:
        self.historial += [{"role": "user", "content": pregunta}, {"role": "assistant", "content": f"FINAL: {respuesta}"}]
        self.historial = self.historial[-8:]  # últimos 4 turnos


def print_trace(trace: List[dict]) -> None:
    for row in trace:
        print(f"\n--- Paso {row['step']} ---")
        print(row["llm_output"])
        if row.get("action"):
            print(f"\n[Tool ejecutada] {row['action']} | {row['input']}")
            print("Observation:", row["observation"][:600], "…" if len(row["observation"]) > 600 else "")


def responder(pregunta: str) -> str:
    """Interfaz para scripts/evaluar_agente.py (agente nuevo por pregunta, sin memoria)."""
    return AgroAgenteReAct().preguntar(pregunta)[0]


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "¿Qué condiciones favorecen la roya común del maíz?"
    r, t = AgroAgenteReAct().preguntar(q)
    print_trace(t)
    print("\nFINAL:\n", r)
