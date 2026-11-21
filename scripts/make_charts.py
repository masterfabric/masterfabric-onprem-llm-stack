"""Charts from docs/results (evaluation and k6 load test)."""
from __future__ import annotations

import json

from mfviz import HEX, IMG, RESULTS, mpl_setup

plt = mpl_setup()


def load_chart():
    r = json.loads((RESULTS / "load_k6.json").read_text())["stages"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5))
    for kind, col, label in (("llm", HEX["ICE"], "LLM direct (64 output tokens)"), ("rag", HEX["GREEN"], "RAG /v1/ask")):
        st = sorted((v for k, v in r.items() if k.startswith(kind)), key=lambda v: v["vus"])
        x = [s["vus"] for s in st]
        a1.plot(x, [s["latency_ms"]["p50"] / 1000 for s in st], "-o", color=col, label=f"{label} p50")
        a1.plot(x, [s["latency_ms"]["p95"] / 1000 for s in st], "--", color=col, alpha=0.7, label=f"{label} p95")
        a2.plot(x, [s["rps"] for s in st], "-o", color=col, label=f"{label} req/s")
        if kind == "llm":
            for s in st:
                a2.annotate(f"{s['output_tokens_per_s']:.0f} tok/s", (s["vus"], s["rps"]), textcoords="offset points",
                            xytext=(0, 8), ha="center", fontsize=9, color=col)
    for a in (a1, a2):
        a.set_xscale("log", base=2)
        a.set_xticks([1, 2, 4, 8], ["1", "2", "4", "8"])
        a.set_xlabel("concurrent users")
        a.legend(fontsize=9)
    a1.set_ylabel("latency (s)")
    a1.set_title("Latency vs concurrency (llama.cpp, 4 slots, CPU)", loc="left")
    a2.set_ylabel("requests per second")
    a2.set_title("Throughput: saturates at the 4 parallel slots", loc="left")
    fig.tight_layout()
    fig.savefig(IMG / "load_test.png")
    plt.close(fig)


def eval_chart():
    v1 = json.loads((RESULTS / "eval_quality_prompt_v1.json").read_text())["summary"]
    v2 = json.loads((RESULTS / "eval_quality.json").read_text())["summary"]
    g = json.loads((RESULTS / "eval_guardrails.json").read_text())["by_category"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw={"width_ratios": [1.1, 1]})
    m = [("answer_accuracy", "answer accuracy"), ("retrieval_hit_at_k", "retrieval hit@4"),
         ("answers_with_citation", "cites a passage"), ("refusal_accuracy", "refuses unanswerable")]
    import numpy as np
    x = np.arange(len(m))
    for off, s, col, lab in ((-0.2, v1, HEX["GREY"], "prompt v1"), (0.2, v2, HEX["GREEN"], "prompt v2 (deployed)")):
        bars = a1.bar(x + off, [s[k] for k, _ in m], 0.38, color=col, label=lab)
        for b in bars:
            a1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{b.get_height():.2f}", ha="center", fontsize=9)
    a1.set_xticks(x, [l for _, l in m])
    a1.set_ylim(0, 1.15)
    a1.legend(loc="upper center", ncols=2)
    a1.set_title("RAG quality: 30 answerable + 5 unanswerable questions", loc="left")
    cats = list(g)
    a2.barh(cats, [g[c]["n"] for c in cats], color=HEX["LINE"])
    a2.barh(cats, [g[c]["passed"] for c in cats], color=[HEX["RED"] if g[c]["passed"] == 0 else HEX["GREEN"] for c in cats])
    for i, c in enumerate(cats):
        a2.text(g[c]["n"] + 0.1, i, f"{g[c]['passed']}/{g[c]['n']}", va="center")
    a2.invert_yaxis()
    a2.set_title("Guardrails: blocked or masked per category", loc="left")
    fig.tight_layout()
    fig.savefig(IMG / "evaluation.png")
    plt.close(fig)


def classifier_chart():
    d = json.loads((RESULTS / "eval_classifier.json").read_text())
    rows, thr = d["rows"], d["summary"]["threshold"]
    groups = [
        ("dev · rule attacks", lambda r: r["set"] == "dev" and r["kind"] == "attack" and r["category"] != "evasion", HEX["GREY"]),
        ("dev · 4 evasions", lambda r: r["category"] == "evasion", HEX["ORANGE"]),
        ("dev · benign questions", lambda r: r["set"] == "dev" and r["category"] == "question", HEX["GREEN"]),
        ("dev · PII questions", lambda r: r["category"] == "pii", HEX["PURPLE"]),
        ("held-out · attacks", lambda r: r["set"] == "heldout" and r["kind"] == "attack", HEX["RED"]),
        ("held-out · hard benign", lambda r: r["set"] == "heldout" and r["kind"] == "benign", HEX["ICE"]),
    ]
    import numpy as np
    rng = np.random.default_rng(7)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1.25, 1]})
    for i, (name, f, col) in enumerate(groups):
        sc = [r["score"] for r in rows if f(r)]
        a1.scatter(sc, i + rng.uniform(-0.18, 0.18, len(sc)), s=34, color=col, alpha=0.9, edgecolor="none")
        above = sum(s >= thr for s in sc)
        a1.text(1.02, i, f"{above}/{len(sc)} ≥ {thr}", va="center", fontsize=10, color=col)
    a1.axvline(thr, color=HEX["YELLOW"], ls="--", lw=1.5)
    a1.set_yticks(range(len(groups)), [g[0] for g in groups])
    a1.invert_yaxis()
    a1.set_xlim(0, 1.0)
    a1.set_xlabel("Granite Guardian risk score  P(Yes)")
    a1.set_title("Classifier score per item (threshold 0.6 fixed on dev)", loc="left")
    ts = [float(t) for t in d["summary"]["sweep"]]
    sw = d["summary"]["sweep"]
    h = sw[str(thr)]["heldout"]
    a2.plot(ts, [sw[str(t)]["heldout"]["caught"] / h["attacks"] for t in ts], "-o", color=HEX["RED"], label="held-out attacks caught")
    a2.plot(ts, [sw[str(t)]["heldout"]["benign_blocked"] / h["benign"] for t in ts], "-o", color=HEX["ICE"], label="held-out hard benign blocked")
    a2.plot(ts, [sw[str(t)]["dev"]["benign_blocked"] / sw[str(t)]["dev"]["benign"] for t in ts], "--o", color=HEX["GREEN"],
            label="dev benign + PII blocked")
    a2.axvline(thr, color=HEX["YELLOW"], ls="--", lw=1.5)
    a2.set_xlabel("threshold (rules + classifier)")
    a2.set_ylabel("share")
    a2.set_ylim(-0.03, 1.05)
    a2.legend(fontsize=9)
    a2.set_title("Threshold sweep", loc="left")
    fig.tight_layout()
    fig.savefig(IMG / "classifier_eval.png")
    plt.close(fig)


def rerank_chart():
    d = json.loads((RESULTS / "eval_rerank.json").read_text())
    v, r = d["vector_only"]["summary"], d["reranked"]["summary"]
    import numpy as np
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw={"width_ratios": [1.3, 1]})
    m = [("hit_at_1", "hit@1"), ("hit_at_4", "hit@4"), ("mrr", "MRR"), ("answer_accuracy", "answer accuracy")]
    x = np.arange(len(m))
    for off, s, col, lab in ((-0.2, v, HEX["GREY"], "pgvector top 4"), (0.2, r, HEX["YELLOW"], "top 12 → reranker → top 4")):
        bars = a1.bar(x + off, [s[k] for k, _ in m], 0.38, color=col, label=lab)
        for b in bars:
            a1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{b.get_height():.2f}", ha="center", fontsize=9)
    a1.set_xticks(x, [l for _, l in m])
    a1.set_ylim(0, 1.32)
    a1.legend(loc="upper center", ncols=2)
    a1.set_title("Retrieval improves, answers do not (30 answerable questions)", loc="left")

    def med(rows, k):
        vals = [x["timings_ms"].get(k, 0) for x in rows if x["timings_ms"]]
        return float(np.median(vals)) / 1000 if vals else 0
    stages = [("guard", HEX["RED"]), ("embed", HEX["PURPLE"]), ("retrieve", HEX["ORANGE"]), ("rerank", HEX["YELLOW"]),
              ("generate", HEX["ICE"])]
    for i, (key, name) in enumerate((("vector_only", "pgvector"), ("reranked", "reranked"))):
        left = 0.0
        for st, col in stages:
            w = med(d[key]["rows"], st)
            a2.barh(i, w, left=left, color=col, label=st if i == 1 else None)
            if w > 0.5:
                a2.text(left + w / 2, i, f"{w:.1f}", ha="center", va="center", fontsize=9, color=HEX["BG"])
            left += w
    a2.set_yticks([0, 1], ["pgvector", "reranked"])
    a2.set_xlabel("median seconds per stage (CPU, k3d)")
    a2.legend(fontsize=9, ncols=5, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    a2.set_title("Where the time goes", loc="left")
    fig.tight_layout()
    fig.savefig(IMG / "rerank_ab.png")
    plt.close(fig)


if __name__ == "__main__":
    IMG.mkdir(parents=True, exist_ok=True)
    eval_chart()
    if (RESULTS / "eval_classifier.json").exists():
        classifier_chart()
    if (RESULTS / "eval_rerank.json").exists():
        rerank_chart()
    if (RESULTS / "load_k6.json").exists():
        load_chart()
    print("charts written")
