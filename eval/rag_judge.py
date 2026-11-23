"""RAG quality with a local judge: RAGAS-style faithfulness, answer relevancy, context precision and recall.

Input: docs/results/rag_collect.jsonl (eval/collect_rag.py: question, the contexts the generator saw, answer;
vector-only and reranked retrieval). Judge: Qwen2.5-7B-Instruct Q4_K_M under llama.cpp on the host
(JUDGE_URL), temperature 0, JSON-schema-constrained output. Embeddings for answer relevancy: the stack's
own bge-small-en-v1.5 (EMBED_URL, a port-forward to llm-embed).

The metric definitions follow the RAGAS paper (Es et al., 2023), re-implemented here with short prompts of
our own; the `ragas` package is not used, so the numbers are "RAGAS-style", not RAGAS.
  faithfulness       answer split into statements; share of statements the contexts support
  answer relevancy   judge writes 3 questions the answer would answer; mean cosine to the real question;
                     0 when the judge marks the answer non-committal
  context precision  each context judged useful or not for the reference answer; average precision over ranks
  context recall     reference answer (the expected key fact) attributable to the contexts: yes / no
Checks on the judge itself: answers paired with another question's contexts (faithfulness should collapse)
and with another question (relevancy should drop); agreement with the string-match correctness of run_eval.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "docs" / "results"
JUDGE = os.environ.get("JUDGE_URL", "http://127.0.0.1:58090")
EMBED = os.environ.get("EMBED_URL", "http://127.0.0.1:58093")
http = httpx.Client(timeout=300)
CALLS = {"n": 0, "s": 0.0}


def norm(s: str) -> str:  # same as run_eval.py
    return s.lower().replace("\u2011", "-").replace("`", "")


def judge(system: str, user: str, schema: dict) -> dict:
    t = time.perf_counter()
    r = http.post(f"{JUDGE}/v1/chat/completions", json={
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0, "max_tokens": 600, "seed": 7,
        "response_format": {"type": "json_object", "schema": schema}})
    r.raise_for_status()
    CALLS["n"] += 1
    CALLS["s"] += time.perf_counter() - t
    return json.loads(r.json()["choices"][0]["message"]["content"])


def embed(texts: list[str]) -> np.ndarray:
    r = http.post(f"{EMBED}/v1/embeddings", json={"model": "bge-small-en-v1.5", "input": texts})
    r.raise_for_status()
    v = np.array([d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])], dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def ctx_block(contexts: list[dict]) -> str:
    return "\n\n".join(f"[{c['n']}] {c['text']}" for c in contexts)


def statements(question: str, answer: str) -> list[str]:
    out = judge("You split answers into short, self-contained factual statements. A refusal or 'I don't know' "
                "has no statements. Citation markers like [2] are not statements.",
                f"Question: {question}\nAnswer: {answer}\n\nList the factual statements the answer makes.",
                {"type": "object", "properties": {"statements": {"type": "array", "items": {"type": "string"}}},
                 "required": ["statements"]})
    return [s for s in out["statements"] if s.strip()][:8]


def supported(stmts: list[str], contexts: list[dict]) -> list[bool]:
    if not stmts:
        return []
    out = judge("You check statements against a context. A statement is supported only if the context states it "
                "or it follows directly from the context. Background knowledge does not count.",
                f"Context:\n{ctx_block(contexts)}\n\nStatements:\n" + "\n".join(f"{i}. {s}" for i, s in
                                                                             enumerate(stmts, 1)) +
                "\n\nFor each statement, in order, say whether the context supports it.",
                {"type": "object", "properties": {"verdicts": {"type": "array", "items": {"type": "boolean"},
                                                               "minItems": len(stmts), "maxItems": len(stmts)}},
                 "required": ["verdicts"]})
    return list(out["verdicts"])[:len(stmts)]


def gen_questions(answer: str) -> tuple[list[str], bool]:
    out = judge("You write the questions an answer responds to, and say whether the answer is non-committal "
                "(evasive, vague or a refusal).",
                f"Answer: {answer}\n\nWrite 3 different questions this answer would be a direct answer to.",
                {"type": "object", "properties": {
                    "questions": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3},
                    "noncommittal": {"type": "boolean"}}, "required": ["questions", "noncommittal"]})
    return out["questions"], bool(out["noncommittal"])


def useful(question: str, reference: str, contexts: list[dict]) -> list[bool]:
    out = judge("You judge retrieved passages. A passage is useful if it contains information needed to arrive at "
                "the reference answer to the question.",
                f"Question: {question}\nReference answer: {reference}\n\nPassages:\n{ctx_block(contexts)}\n\n"
                "For each passage, in order, say whether it is useful.",
                {"type": "object", "properties": {"verdicts": {"type": "array", "items": {"type": "boolean"},
                                                               "minItems": len(contexts),
                                                               "maxItems": len(contexts)}},
                 "required": ["verdicts"]})
    return list(out["verdicts"])[:len(contexts)]


def attributable(question: str, reference: str, contexts: list[dict]) -> bool:
    out = judge("You decide whether a reference answer can be attributed to (is stated in) given passages.",
                f"Question: {question}\nReference answer: {reference}\n\nPassages:\n{ctx_block(contexts)}\n\n"
                "Is the reference answer stated in the passages?",
                {"type": "object", "properties": {"attributable": {"type": "boolean"}}, "required": ["attributable"]})
    return bool(out["attributable"])


def avg_precision(v: list[bool]) -> float:
    hits, s = 0, 0.0
    for k, x in enumerate(v, 1):
        if x:
            hits += 1
            s += hits / k
    return s / hits if hits else 0.0


def main() -> None:
    items = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "eval" / "questions.jsonl").read_text().splitlines()}
    rows_in = [json.loads(l) for l in (RES / "rag_collect.jsonl").read_text().splitlines()]
    rows = []
    for r in rows_in:
        it = items[r["id"]]
        if it.get("expect_refusal"):
            continue
        ref = f"{', '.join(it['expect_any'])} (source: {it['source']})"
        st = statements(r["question"], r["answer"])
        sup = supported(st, r["contexts"])
        qs, nonc = gen_questions(r["answer"])
        e = embed([r["question"]] + qs)
        rel = 0.0 if nonc else float(np.mean(e[1:] @ e[0]))
        use = useful(r["question"], ref, r["contexts"]) if r["contexts"] else []
        row = {"id": r["id"], "mode": r["mode"], "answer": r["answer"],
               "correct": any(norm(x) in norm(r["answer"]) for x in it["expect_any"]),
               "statements": st, "supported": sup,
               "faithfulness": (sum(sup) / len(sup)) if sup else None,
               "gen_questions": qs, "noncommittal": nonc, "answer_relevancy": round(rel, 4),
               "useful": use, "context_precision": round(avg_precision(use), 4),
               "context_recall": attributable(r["question"], ref, r["contexts"]) if r["contexts"] else False,
               "context_recall_string": any(norm(x) in norm(c["text"]) for x in it["expect_any"]
                                            for c in r["contexts"]),
               "_qvecs": e[1:]}
        rows.append(row)
        print(f"{row['id']} {row['mode']:6s} F={row['faithfulness']} AR={row['answer_relevancy']:.2f} "
              f"CP={row['context_precision']:.2f} CR={row['context_recall']} ok={row['correct']}", flush=True)

    # judge sanity: answer i against contexts / question of the next question (same mode)
    sanity = {}
    for mode in ("vector", "rerank"):
        m = [r for r in rows if r["mode"] == mode]
        src = {r["id"]: r for r in rows_in if r["mode"] == mode}
        f_sw, ar_sw = [], []
        for i, r in enumerate(m):
            other = src[m[(i + 1) % len(m)]["id"]]
            if r["statements"]:
                s = supported(r["statements"], other["contexts"])
                f_sw.append(sum(s) / len(s))
            q = embed([other["question"]])[0]
            ar_sw.append(0.0 if r["noncommittal"] else float(np.mean(r["_qvecs"] @ q)))
        sanity[mode] = {"faithfulness_swapped_contexts": round(statistics.mean(f_sw), 3),
                        "answer_relevancy_swapped_question": round(statistics.mean(ar_sw), 3)}

    def summ(m):
        f = [r["faithfulness"] for r in m if r["faithfulness"] is not None]
        ok, bad = [r for r in m if r["correct"]], [r for r in m if not r["correct"]]
        return {"n": len(m), "answered_with_statements": len(f),
                "faithfulness": round(statistics.mean(f), 3),
                "answer_relevancy": round(statistics.mean(r["answer_relevancy"] for r in m), 3),
                "context_precision": round(statistics.mean(r["context_precision"] for r in m), 3),
                "context_recall": round(sum(r["context_recall"] for r in m) / len(m), 3),
                "context_recall_string_match": round(sum(r["context_recall_string"] for r in m) / len(m), 3),
                "recall_judge_vs_string_agreement": round(sum(r["context_recall"] == r["context_recall_string"]
                                                              for r in m) / len(m), 3),
                "string_match_correct": len(ok),
                "answer_relevancy_correct_vs_incorrect": [
                    round(statistics.mean(r["answer_relevancy"] for r in ok), 3) if ok else None,
                    round(statistics.mean(r["answer_relevancy"] for r in bad), 3) if bad else None],
                "context_recall_correct_vs_incorrect": [
                    round(sum(r["context_recall"] for r in ok) / len(ok), 3) if ok else None,
                    round(sum(r["context_recall"] for r in bad) / len(bad), 3) if bad else None],
                "unfaithful_answers": [r["id"] for r in m if r["faithfulness"] is not None and r["faithfulness"] < 1]}

    out = {"judge": "qwen2.5-7b-instruct Q4_K_M, llama.cpp Metal, temperature 0, JSON-schema output",
           "generator": "qwen2.5-1.5b-instruct (the deployed llm pod)", "questions": "eval/questions.jsonl q01-q30",
           "summary": {m: summ([r for r in rows if r["mode"] == m]) for m in ("vector", "rerank")},
           "judge_sanity": sanity,
           "judge_calls": CALLS["n"], "judge_seconds": round(CALLS["s"], 1),
           "rows": [{k: v for k, v in r.items() if k != "_qvecs"} for r in rows]}
    (RES / "eval_rag_judge.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("summary", "judge_sanity", "judge_calls", "judge_seconds")}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
