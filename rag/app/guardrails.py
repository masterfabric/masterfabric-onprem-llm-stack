"""Guardrails around the model: input screening, PII masking, retrieved-context filtering, output checks.

Deterministic and explainable on purpose: every block or redaction returns a named rule, so an
operator can see why a request was refused. It is a first line of defence, not a replacement for a
model-based classifier (see the README's limitations).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- prompt injection / jailbreak patterns (direct, in the user's question) ----------------------
INJECTION_PATTERNS: dict[str, re.Pattern] = {
    "ignore_instructions": re.compile(r"\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|your|the)\b.{0,30}\b(instructions?|rules|prompt|guidelines|directions)", re.I | re.S),
    "reveal_system_prompt": re.compile(r"\b(reveal|show|print|repeat|output|tell me|what (is|are))\b.{0,40}\b(system|hidden|initial|developer)\s+(prompt|instructions?|message)", re.I | re.S),
    "role_override": re.compile(r"\b(you are now|from now on,? you|act as|pretend (to be|you are)|roleplay as)\b.{0,60}\b(unfiltered|unrestricted|jailbroken|dan|evil|no (rules|restrictions|limits)|developer mode)", re.I | re.S),
    "developer_mode": re.compile(r"\b(developer|god|admin|sudo|debug)\s+mode\b", re.I),
    "delimiter_injection": re.compile(r"(<\|?(system|im_start|im_end)\|?>|\[/?INST\]|###\s*(system|instruction))", re.I),
    "encoded_payload": re.compile(r"\b(base64|rot13|hex)\b.{0,40}\b(decode|decoded|execute|follow|instructions?)", re.I | re.S),
    "exfiltration": re.compile(r"\b(send|post|upload|exfiltrate|leak)\b.{0,40}\b(https?://|webhook|endpoint|url|email)", re.I | re.S),
}

# --- PII (Turkish context: TCKN, +90 mobile numbers, TR IBAN) ---------------------------------------
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_TR = re.compile(r"(?<!\d)(?:\+?90[\s-]?|0)?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)")
TCKN = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
IBAN_TR = re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.I)
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def tckn_valid(s: str) -> bool:
    """Turkish national ID checksum (digits 10 and 11)."""
    d = [int(c) for c in s]
    if len(d) != 11 or d[0] == 0:
        return False
    d10 = ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
    return d10 == d[9] and sum(d[:10]) % 10 == d[10]


def iban_valid(s: str) -> bool:
    s = re.sub(r"\s", "", s).upper()
    r = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in r)) % 97 == 1


def luhn_valid(s: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", s)]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, n in enumerate(reversed(digits)):
        if i % 2 == 1:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Replace PII with typed placeholders. Checksums keep false positives (e.g. measured numbers) out."""
    found: list[str] = []

    def sub(pattern, label, check=None):
        nonlocal text

        def repl(m):
            if check and not check(m.group(0)):
                return m.group(0)
            found.append(label)
            return f"[{label}]"

        text = pattern.sub(repl, text)

    sub(IBAN_TR, "IBAN", iban_valid)
    sub(EMAIL, "EMAIL")
    sub(CARD, "CARD", luhn_valid)
    sub(TCKN, "TCKN", tckn_valid)
    sub(PHONE_TR, "PHONE")
    return text, found


@dataclass
class Verdict:
    allowed: bool
    text: str
    rules: list[str] = field(default_factory=list)


def screen_input(question: str, max_chars: int) -> Verdict:
    q = question.strip()
    if not q:
        return Verdict(False, q, ["empty"])
    if len(q) > max_chars:
        return Verdict(False, q, ["too_long"])
    hits = [name for name, p in INJECTION_PATTERNS.items() if p.search(q)]
    if hits:
        return Verdict(False, q, [f"injection:{h}" for h in hits])
    masked, pii = mask_pii(q)
    return Verdict(True, masked, [f"pii_masked:{p}" for p in pii])


def filter_context(chunks: list[dict]) -> tuple[list[dict], list[str]]:
    """Drop retrieved chunks that carry instructions aimed at the model (indirect prompt injection)."""
    kept, dropped = [], []
    for c in chunks:
        if any(p.search(c["content"]) for p in INJECTION_PATTERNS.values()):
            dropped.append(c["source"])
        else:
            kept.append(c)
    return kept, [f"context_dropped:{s}" for s in dropped]


def screen_output(answer: str, canary: str, n_sources: int) -> Verdict:
    rules = []
    if canary in answer:
        return Verdict(False, "", ["system_prompt_leak"])
    masked, pii = mask_pii(answer)
    rules += [f"pii_redacted:{p}" for p in pii]
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", masked)}
    if n_sources and not cited:
        rules.append("no_citation")
    if any(n < 1 or n > n_sources for n in cited):
        rules.append("bad_citation")
    return Verdict(True, masked, rules)
