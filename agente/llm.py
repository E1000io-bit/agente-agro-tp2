"""
Conexión con el LLM, igual que en las notebooks de la cátedra (17_Agentes):
Hugging Face Router expone una API compatible con OpenAI, así que usamos el cliente de OpenAI
cambiando sólo la `base_url`.

Variables de entorno (.env):
    HF_TOKEN       token de Hugging Face (obligatorio)
    LLM_MODEL      modelo (por defecto Qwen/Qwen2.5-7B-Instruct, el de la cátedra)
    LLM_BASE_URL   por defecto https://router.huggingface.co/v1
                   (sirve cualquier endpoint compatible: Groq, Ollama, LM Studio…)
"""
from __future__ import annotations

import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL", "https://router.huggingface.co/v1")
MODEL_ID = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")


def _api_key() -> str:
    key = os.getenv("HF_TOKEN") or os.getenv("LLM_API_KEY")
    if not key:
        raise RuntimeError("Falta HF_TOKEN en .env (https://huggingface.co/settings/tokens)")
    return key


_cliente = None


def cliente():
    """Cliente OpenAI apuntando a Hugging Face Router (se crea una sola vez)."""
    global _cliente
    if _cliente is None:
        from openai import OpenAI

        _cliente = OpenAI(base_url=BASE_URL, api_key=_api_key())
    return _cliente


def call_llm(messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
    """Mismo helper que la notebook Agente_ReAct: manda mensajes y devuelve el texto."""
    r = cliente().chat.completions.create(model=MODEL_ID, messages=messages, temperature=temperature)
    return r.choices[0].message.content or ""


def chat_langchain(temperature: float = 0.1):
    """Modelo de chat para LangChain, como en la notebook Agente_LangChain."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(api_key=_api_key(), base_url=BASE_URL, model=MODEL_ID, temperature=temperature)
