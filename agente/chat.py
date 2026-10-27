"""
Chat por consola con AgroAgente (consultas por texto).

    python -m agente.chat                     # versión LangChain (por defecto)
    python -m agente.chat --modo react        # versión ReAct manual
    python -m agente.chat --modo react --traza  # muestra Thought / Action / Observation

Comandos dentro del chat:  /nuevo (borra la memoria)   /salir
"""
from __future__ import annotations

import argparse
import uuid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["langchain", "react"], default="langchain")
    ap.add_argument("--traza", action="store_true", help="mostrar los pasos del agente")
    a = ap.parse_args()

    if a.modo == "react":
        from agente.react_manual import AgroAgenteReAct, print_trace

        agente = AgroAgenteReAct()
    else:
        from agente.agente_langchain import crear_agente, mostrar_pasos, preguntar

        agente = crear_agente()
        hilo = str(uuid.uuid4())

    print(f"AgroAgente ({a.modo}) — consultas fitosanitarias de maíz, soja, trigo y maní. /nuevo · /salir\n")
    while True:
        try:
            q = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q == "/salir":
            break
        if q == "/nuevo":
            if a.modo == "react":
                agente.reiniciar()
            else:
                hilo = str(uuid.uuid4())
            print("(memoria borrada)\n")
            continue
        try:
            if a.modo == "react":
                r, traza = agente.preguntar(q)
                if a.traza:
                    print_trace(traza)
            else:
                r, msgs = preguntar(agente, q, thread_id=hilo, devolver_mensajes=True)
                if a.traza:
                    mostrar_pasos(msgs)
        except Exception as e:  # noqa: BLE001
            r = f"[error] {type(e).__name__}: {e}"
        print(f"\nAgroAgente: {r}\n")


if __name__ == "__main__":
    main()
