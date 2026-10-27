"""
Tests de los agentes con un LLM SIMULADO (no necesitan HF_TOKEN ni red, salvo las tools de clima que no se usan acá).
    python tests/test_agente.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_parser_react():
    from agente.react_manual import parse_action, parse_final_answer, parse_tool_input

    assert parse_action("Thought: x\nAction: buscar_fichas | roya | cultivo=maiz") == ("buscar_fichas", "roya | cultivo=maiz")
    assert parse_action("Action: fecha_actual |") == ("fecha_actual", "")
    assert parse_final_answer("Thought: listo\nFINAL: Es roya.") == "Es roya."
    assert parse_final_answer("Final Answer: ok") == "ok"          # formato alternativo de la notebook
    assert parse_tool_input("roya | cultivo=maiz | k=3") == ("roya", {"cultivo": "maiz", "k": "3"})


def test_loop_react_con_llm_simulado():
    from agente.react_manual import AgroAgenteReAct

    guion = iter([
        "Thought: busco\nAction: buscar_fichas | manchas circulares borde rojizo | cultivo=soja | k=2",
        "Thought: tool inventada\nAction: google | algo",
        "FINAL: Mancha ojo de rana (Fuente: https://www.sinavimo.gob.ar/plaga/cercospora-sojina)",
    ])
    ag = AgroAgenteReAct(call_llm=lambda m: next(guion))
    resp, traza = ag.preguntar("manchas con borde rojizo en soja")
    assert "cercospora-sojina" in traza[0]["observation"]
    assert "no existe" in traza[1]["observation"]
    assert resp.startswith("Mancha ojo de rana")
    assert len(ag.historial) == 2                                  # memoria del turno


def test_guardrail_dosis():
    from agente.guardrails import pide_dosis, revisar_respuesta
    from agente.react_manual import AgroAgenteReAct

    assert pide_dosis("¿Qué dosis de glifosato le pongo?")
    assert pide_dosis("con qué lo curo")
    assert not pide_dosis("¿Qué condiciones favorecen la roya?")
    vistos = []
    ag = AgroAgenteReAct(call_llm=lambda m: vistos.append(m) or "FINAL: Aplicá 1,5 l/ha de X")
    resp, _ = ag.preguntar("¿Qué dosis le aplico a la chinche?")
    assert "Nota del sistema" in vistos[0][1]["content"]            # aviso antes del LLM (mensaje del usuario)
    assert "Ingeniero Agrónomo" in resp and "l/ha" not in resp       # filtro después del LLM
    assert revisar_respuesta("Monitoreá el lote") == "Monitoreá el lote"


def test_agente_langchain_con_llm_simulado():
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage

    from agente.agente_langchain import crear_agente, preguntar

    class Falso(GenericFakeChatModel):
        def bind_tools(self, tools, **kw):
            return self

    guion = iter([
        AIMessage(content="", tool_calls=[{"name": "buscar_fichas", "args": {"consulta": "roya asiática", "cultivo": "soja"}, "id": "1"}]),
        AIMessage(content="Roya asiática (Fuente: https://www.sinavimo.gob.ar/plaga/phakopsora-pachyrhizi)"),
        AIMessage(content="segundo turno"),
    ])
    ag = crear_agente(llm=Falso(messages=guion))
    r, msgs = preguntar(ag, "¿Qué es la roya asiática?", thread_id="t", devolver_mensajes=True)
    assert any(m.type == "tool" and "phakopsora-pachyrhizi" in str(m.content) for m in msgs)
    assert "Roya asiática" in r
    _, msgs2 = preguntar(ag, "¿y qué la favorece?", thread_id="t", devolver_mensajes=True)
    assert len(msgs2) > len(msgs)                                  # memoria por thread_id


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
            print(f"ok  {nombre}")
