"""Runtime configuration, from environment variables (set by the Helm chart)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    llm_url: str = field(default_factory=lambda: _env("LLM_URL", "http://llm:8080/v1"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "qwen2.5-1.5b-instruct"))
    embed_url: str = field(default_factory=lambda: _env("EMBED_URL", "http://embed:8080/v1"))
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL", "bge-small-en-v1.5"))
    embed_dim: int = field(default_factory=lambda: int(_env("EMBED_DIM", "384")))
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", "postgresql://rag:rag@pgvector:5432/rag"))
    top_k: int = field(default_factory=lambda: int(_env("TOP_K", "4")))
    min_score: float = field(default_factory=lambda: float(_env("MIN_SCORE", "0.55")))
    max_tokens: int = field(default_factory=lambda: int(_env("MAX_TOKENS", "200")))
    max_question_chars: int = field(default_factory=lambda: int(_env("MAX_QUESTION_CHARS", "1000")))
    request_timeout_s: float = field(default_factory=lambda: float(_env("REQUEST_TIMEOUT_S", "120")))
    # second guardrail layer (LLM classifier) and reranker; both optional
    guard_enabled: bool = field(default_factory=lambda: _env("GUARD_ENABLED", "false").lower() == "true")
    guard_url: str = field(default_factory=lambda: _env("GUARD_URL", "http://guard:8080"))
    guard_threshold: float = field(default_factory=lambda: float(_env("GUARD_THRESHOLD", "0.6")))
    guard_fail_mode: str = field(default_factory=lambda: _env("GUARD_FAIL_MODE", "closed"))   # closed | open
    guard_timeout_s: float = field(default_factory=lambda: float(_env("GUARD_TIMEOUT_S", "10")))
    guard_debug: bool = field(default_factory=lambda: _env("GUARD_DEBUG", "false").lower() == "true")
    rerank_enabled: bool = field(default_factory=lambda: _env("RERANK_ENABLED", "false").lower() == "true")
    rerank_url: str = field(default_factory=lambda: _env("RERANK_URL", "http://rerank:8080/v1"))
    rerank_model: str = field(default_factory=lambda: _env("RERANK_MODEL", "bge-reranker-v2-m3"))
    rerank_candidates: int = field(default_factory=lambda: int(_env("RERANK_CANDIDATES", "12")))
    corpus_dir: str = field(default_factory=lambda: _env("CORPUS_DIR", "/app/corpus"))


settings = Settings()
