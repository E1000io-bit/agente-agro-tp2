"""
AgroAgente — versión LangChain (misma estructura que 17_Agentes/Agente_LangChain.ipynb de la cátedra):

    ChatOpenAI → Hugging Face Router  ·  tools con @tool  ·  una skill expuesta como tool  ·  create_agent

LangChain se encarga del loop modelo → tool → observación → modelo (usa function calling nativo,
sin parser con regex). Se agrega memoria por conversación con un checkpointer (thread_id).

Uso:
    from agente.agente_langchain import crear_agente, preguntar
    agente = crear_agente()
    print(preguntar(agente, "¿Qué es la chicharrita del maíz?", thread_id="demo"))

    python -m agente.agente_langchain "pregunta"
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from agente import consultas
from agente.guardrails import NOTA_PARA_EL_LLM, pide_dosis, revisar_respuesta

PROMPT = (Path(__file__).parent / "prompts" / "system_prompt_consultas.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- tools (@tool)
# La docstring es lo que lee el modelo para decidir cuándo usar cada tool.

@tool
def buscar_fichas(consulta: str, cultivo: Optional[str] = None) -> str:
    """
    Busca en las fichas oficiales de plagas, enfermedades y malezas de SINAVIMO (SENASA):
    síntomas, biología, condiciones predisponentes, cultivos afectados y presencia en Argentina.
    Usar SIEMPRE antes de dar información sobre una plaga o de diagnosticar por síntomas.
    cultivo (opcional): maiz, soja, trigo o mani.
    """
    return consultas.consultar_fichas(consulta, cultivo=cultivo)


@tool
def situacion_chicharrita(consulta: str = "situación actual") -> str:
    """
    Busca en los informes más recientes de la Red Nacional de Monitoreo de la chicharrita del maíz
    (Dalbulus maidis): capturas por región y porcentaje de portación de Spiroplasma.
    Usar para preguntas sobre cómo viene la chicharrita o el achaparramiento ahora.
    """
    return consultas.situacion_chicharrita(consulta)


@tool
def clima_lote(localidad: str, dias: int = 7) -> str:
    """
    Pronóstico de los próximos días (temperatura, lluvia, humedad relativa, probabilidad de mojado de hoja)
    para una localidad de Argentina. dias entre 1 y 16.
    """
    return consultas.clima_localidad(localidad, dias=dias)


@tool
def glosario(termino: str) -> str:
    """Define o traduce un término agronómico usando el tesauro AGROVOC de la FAO."""
    return consultas.definir_termino(termino)


# ---------------------------------------------------------------- skill expuesta como tool
@tool
def evaluar_riesgo(plaga: str, localidad: str, cultivo: Optional[str] = None) -> str:
    """
    Skill de riesgo climático: trae juntas las condiciones que favorecen una plaga o enfermedad
    (ficha oficial) y el pronóstico de la localidad para estimar si el riesgo es bajo, medio o alto.
    Usar cuando pregunten si hay riesgo de una plaga o enfermedad en un lugar en los próximos días.
    """
    return consultas.evaluar_riesgo(plaga, localidad, cultivo=cultivo)


TOOLS = [buscar_fichas, situacion_chicharrita, clima_lote, evaluar_riesgo, glosario]


def crear_agente(llm=None, memoria: bool = True):
    """Arma el agente con create_agent. Con memoria=True recuerda la conversación por thread_id."""
    from langchain.agents import create_agent

    if llm is None:
        from agente.llm import chat_langchain

        llm = chat_langchain()
    kwargs = {}
    if memoria:
        from langgraph.checkpoint.memory import InMemorySaver

        kwargs["checkpointer"] = InMemorySaver()
    return create_agent(model=llm, tools=TOOLS, system_prompt=PROMPT, **kwargs)


def preguntar(agente, pregunta: str, thread_id: str = "default", devolver_mensajes: bool = False):
    contenido = pregunta + (f"\n\n{NOTA_PARA_EL_LLM}" if pide_dosis(pregunta) else "")
    res = agente.invoke({"messages": [{"role": "user", "content": contenido}]},
                        config={"configurable": {"thread_id": thread_id}})
    respuesta = revisar_respuesta(res["messages"][-1].content or "")
    return (respuesta, res["messages"]) if devolver_mensajes else respuesta


def mostrar_pasos(mensajes) -> None:
    """Imprime las tools que usó el agente (equivalente a print_trace de la versión manual)."""
    for m in mensajes:
        for tc in getattr(m, "tool_calls", None) or []:
            print(f"[Tool] {tc['name']}({tc['args']})")
        if m.type == "tool":
            print(f"   ↳ {str(m.content)[:300]}…")


_AGENTE = None


def responder(pregunta: str) -> str:
    """Interfaz para scripts/evaluar_agente.py (un thread nuevo por pregunta)."""
    global _AGENTE
    import uuid

    if _AGENTE is None:
        _AGENTE = crear_agente()
    return preguntar(_AGENTE, pregunta, thread_id=str(uuid.uuid4()))


if __name__ == "__main__":
    import sys

    ag = crear_agente()
    r, msgs = preguntar(ag, " ".join(sys.argv[1:]) or "¿Qué es la chicharrita del maíz?", devolver_mensajes=True)
    mostrar_pasos(msgs)
    print("\nRESPUESTA:\n", r)
