"""Answer quality and retrieval with and without the cross-encoder reranker -> docs/results/eval_rerank.json.

    python eval/run_rerank_eval.py --api http://127.0.0.1:48080

The same 35 questions are asked twice through /v1/ask, once with {"rerank": false} (pgvector top 4) and once
with {"rerank": true} (pgvector top 12 -> bge-reranker-v2-m3 -> top 4). Retrieval is scored by the rank
of the first citation from the expected document (hit@1, hit@4, MRR); answers as in run_eval.py.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "results" / "eval_rerank.json"
REFUSAL = re.compile(r"(don't|do not|cannot|can't) know|not (contain|mention|provide|specif)|no information", re.I)


def norm(s: str) -> str:
    return s.lower().replace("\u2011", "-").replace("`", "")


def run(c: httpx.Client, api: str, rerank: bool) -> dict:
    rows = []
    for line in (ROOT / "eval" / "questions.jsonl").read_text().splitlines():
        it = json.loads(line)
        t = time.perf_counter()
        r = c.post(f"{api}/v1/ask", json={"question": it["question"], "rerank": rerank})
        r.raise_for_status()
        res, secs = r.json(), time.perf_counter() - t
        ans = norm(res["answer"])
        row = {"id": it["id"], "answer": res["answer"], "seconds": round(secs, 2), "blocked": res["blocked"],
               "citations": [x["source"] for x in res["citations"]], "timings_ms": res.get("timings_ms", {})}
        if it.get("expect_refusal"):
            row |= {"kind": "unanswerable", "correct": bool(REFUSAL.search(ans))}
        else:
            ranks = [i for i, s in enumerate(row["citations"], 1) if it["source"] in s]
            row |= {"kind": "answerable", "correct": any(norm(e) in ans for e in it["expect_any"]),
                    "rank": ranks[0] if ranks else None}
        rows.append(row)
        print(f"rerank={rerank!s:5s} {it['id']} {'OK ' if row['correct'] else 'BAD'} rank={row.get('rank')} {secs:5.1f}s")
    a = [r for r in rows if r["kind"] == "answerable"]
    u = [r for r in rows if r["kind"] == "unanswerable"]
    stage = lambda k: [r["timings_ms"][k] for r in rows if k in r["timings_ms"]]  # noqa: E731
    return {"summary": {
        "answer_accuracy": round(sum(r["correct"] for r in a) / len(a), 3),
        "refusal_accuracy": round(sum(r["correct"] for r in u) / len(u), 3),
        "hit_at_1": round(sum(r["rank"] == 1 for r in a) / len(a), 3),
        "hit_at_4": round(sum(r["rank"] is not None for r in a) / len(a), 3),
        "mrr": round(sum(1 / r["rank"] for r in a if r["rank"]) / len(a), 3),
        "blocked": sum(r["blocked"] for r in rows),
        "latency_s_p50": round(statistics.median(r["seconds"] for r in rows), 2),
        "rerank_ms_p50": round(statistics.median(stage("rerank")), 1) if stage("rerank") else None,
        "rerank_ms_p95": round(sorted(stage("rerank"))[int(0.95 * (len(stage("rerank")) - 1))], 1) if stage("rerank") else None,
        "guard_ms_p50": round(statistics.median(stage("guard")), 1) if stage("guard") else None,
    }, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:48080")
    args = ap.parse_args()
    with httpx.Client(timeout=300) as c:
        out = {"vector_only": run(c, args.api, False), "reranked": run(c, args.api, True)}
    changed = [x["id"] for x, y in zip(out["vector_only"]["rows"], out["reranked"]["rows"]) if x["correct"] != y["correct"]]
    out["changed_correctness"] = changed
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v["summary"] for k, v in out.items() if k != "changed_correctness"}, indent=1), changed)


if __name__ == "__main__":
    main()
