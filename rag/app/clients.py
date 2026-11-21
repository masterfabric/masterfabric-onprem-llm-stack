"""Clients for the OpenAI-compatible inference servers (llama.cpp today, vLLM with the same API)."""
from __future__ import annotations

import httpx
import numpy as np

from .config import settings

_http = httpx.Client(timeout=settings.request_timeout_s)


def embed(texts: list[str], prefix: str = "") -> list[np.ndarray]:
    r = _http.post(f"{settings.embed_url}/embeddings",
                   json={"model": settings.embed_model, "input": [prefix + t for t in texts]})
    r.raise_for_status()
    data = sorted(r.json()["data"], key=lambda d: d["index"])
    out = []
    for d in data:
        v = np.asarray(d["embedding"], dtype=np.float32)
        out.append(v / (np.linalg.norm(v) or 1.0))
    return out


def chat(messages: list[dict], max_tokens: int) -> dict:
    r = _http.post(f"{settings.llm_url}/chat/completions",
                   json={"model": settings.llm_model, "messages": messages, "max_tokens": max_tokens,
                         "temperature": 0.0, "seed": 7})
    r.raise_for_status()
    return r.json()
