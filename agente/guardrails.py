"""
Guardrails deterministas que complementan al system prompt (un modelo de 7B no siempre obedece).

- pide_dosis(pregunta): detecta pedidos de producto/dosis ANTES de llamar al LLM.
- revisar_respuesta(respuesta): si igual se cuela una dosis, la reemplaza por la derivación.
"""
from __future__ import annotations

import re

PEDIDO_DOSIS = re.compile(
    r"\b(dosis|cu[aá]nto (le )?(aplico|pongo|echo|tiro)|qu[eé] (producto|insecticida|fungicida|herbicida|le aplico|le pongo|le tiro)"
    r"|con qu[eé] (lo )?(curo|controlo|fumigo|mato)|cu[aá]ntos? (litros|cc|gramos))\b",
    re.I,
)
DOSIS_EN_RESPUESTA = re.compile(r"\b\d+[.,]?\d*\s*(l|lt|litros?|cc|ml|g|gr|kg|cm3)\s*/\s*(ha|hect[aá]rea)\b", re.I)

DERIVACION = (
    "No puedo indicar productos, principios activos ni dosis: una aplicación de fitosanitarios requiere "
    "la receta de un Ingeniero Agrónomo matriculado y respetar la etiqueta del producto registrado en SENASA "
    "(podés consultar la Guía de Productos Fitosanitarios de CASAFE: https://www.casafe.org/publicaciones/guia-de-productos-fitosanitarios/). "
    "Lo que sí puedo hacer es ayudarte con el manejo integrado: cómo monitorear, qué umbrales se usan, "
    "qué condiciones favorecen la plaga y medidas culturales."
)

NOTA_PARA_EL_LLM = (
    "[Nota del sistema: el usuario pide productos o dosis. NO los indiques. Explicá manejo integrado "
    "(monitoreo, umbrales, prácticas culturales) usando las fichas y terminá derivando a un Ingeniero "
    "Agrónomo, la etiqueta registrada y la receta fitosanitaria.]"
)


def pide_dosis(pregunta: str) -> bool:
    return bool(PEDIDO_DOSIS.search(pregunta))


def revisar_respuesta(respuesta: str) -> str:
    if DOSIS_EN_RESPUESTA.search(respuesta):
        return DERIVACION
    return respuesta
