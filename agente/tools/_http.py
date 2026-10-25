"""Sesión HTTP compartida por las tools, con reintentos (las APIs públicas a veces cortan o tardan)."""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_SESION: requests.Session | None = None


def sesion() -> requests.Session:
    global _SESION
    if _SESION is None:
        s = requests.Session()
        s.headers.update({"User-Agent": "TP-IA-agente-agro/1.0 (uso academico)"})
        reintentos = Retry(
            total=3,
            connect=3,
            read=2,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        s.mount("https://", HTTPAdapter(max_retries=reintentos))
        s.mount("http://", HTTPAdapter(max_retries=reintentos))
        _SESION = s
    return _SESION
