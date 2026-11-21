# 0003. Deterministic guardrails first, measured against evasions

- Status: Accepted
- Date: 2026-11-21

## Decision

Rules in `rag/app/guardrails.py`, applied at three points:

1. **Input**: block injection, extraction, jailbreak, delimiter, encoded-payload and exfiltration
   patterns. Mask Turkish PII: TCKN and IBAN (with checksums), +90 mobile numbers, email, and
   Luhn-valid cards.
2. **Context**: drop retrieved chunks that contain instructions aimed at the model.
3. **Output**: withhold answers that contain a per-process canary from the system prompt, redact PII,
   and flag missing or out-of-range citations.

Every event has a rule name, and each one is returned to the caller and counted in Prometheus.

## Why not only a classifier model

Rules are explainable, need no GPU and add microseconds. They also miss paraphrases, and the
evaluation includes 4 deliberate evasions to show that (0/4 caught). The canary and the "answer only
from context" prompt are the second layer. A model-based classifier (for example Llama Guard or a
fine-tuned small encoder) is the next layer, listed in the roadmap.
