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


def guard_v2_chart():
    import numpy as np
    d = json.loads((RESULTS / "eval_guard_v2.json").read_text())
    rows = json.loads((RESULTS / "guard_v2_scores.json").read_text())["rows"]
    thr1, thr2 = 0.6, d["chosen"]["threshold"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 5.4), gridspec_kw={"width_ratios": [1.2, 1]})
    h2 = [r for r in rows if r["set"] == "heldout2"]
    h2.sort(key=lambda r: (r["kind"], r["scores"]["override"]))
    for i, r in enumerate(h2):
        a, b = r["scores"]["override"], r["scores"]["override_narrow"]
        col = HEX["RED"] if r["kind"] == "attack" else HEX["ICE"]
        a1.plot([a, b], [i, i], color=HEX["LINE"], lw=1.2, zorder=1)
        a1.scatter([a], [i], s=26, color=HEX["GREY"], zorder=2)
        a1.scatter([b], [i], s=30, color=col, zorder=3)
    nb = sum(r["kind"] == "attack" for r in h2)
    a1.axhline(nb - 0.5, color=HEX["LINE"], lw=1)
    a1.axvline(thr1, color=HEX["GREY"], ls=":", lw=1.4)
    a1.axvline(thr2, color=HEX["YELLOW"], ls="--", lw=1.4)
    a1.text(thr1 + 0.01, len(h2) - 0.3, "v1.1 at 0.6", color=HEX["GREY"], fontsize=9)
    a1.text(thr2 - 0.01, len(h2) - 0.3, f"v1.2 at {thr2}", color=HEX["YELLOW"], fontsize=9, ha="right")
    a1.set_yticks([nb / 2, nb + (len(h2) - nb) / 2], ["24 attacks", "20 hard benign"])
    a1.set_xlim(0, 1)
    a1.set_xlabel("risk score: grey = v1.1 definition, colour = v1.2 definition")
    a1.set_title("Fresh held-out v2: each item under both definitions", loc="left")
    sets = [("dev", "dev\n22 + 39"), ("heldout1", "held-out v1\n16 + 14\n(used to select)"),
            ("heldout2", "held-out v2\n24 + 20\n(fresh)")]
    x = np.arange(len(sets))
    for off, key, col, lab in ((-0.2, "v1_1_same_backend", HEX["GREY"], "v1.1: override at 0.6"),
                               (0.2, "v1_2", HEX["YELLOW"], f"v1.2: override_narrow at {thr2}")):
        caught = [d[key][s]["caught"] / d[key][s]["attacks"] for s, _ in sets]
        fb = [d[key][s]["benign_blocked"] / d[key][s]["benign"] for s, _ in sets]
        a2.bar(x + off, caught, 0.38, color=col, label=lab + " (attacks caught)")
        a2.bar(x + off, [-f for f in fb], 0.38, color=col, alpha=0.45)
        for xi, s, c, f in zip(x + off, sets, caught, fb):
            a2.text(xi, c + 0.03, f"{d[key][s[0]]['caught']}/{d[key][s[0]]['attacks']}", ha="center", fontsize=9)
            a2.text(xi, -f - 0.08, f"{d[key][s[0]]['benign_blocked']}/{d[key][s[0]]['benign']}", ha="center", fontsize=9)
    a2.axhline(0, color=HEX["WHITE"], lw=0.8)
    a2.set_xticks(x, [l for _, l in sets])
    a2.set_ylim(-0.45, 1.25)
    a2.set_ylabel("attacks caught (up) · benign blocked (down)")
    a2.legend(fontsize=9, loc="upper center", ncols=1)
    a2.set_title("Rules + classifier, deployed CPU guard pod", loc="left")
    fig.tight_layout()
    fig.savefig(IMG / "guard_v2.png")
    plt.close(fig)


def rag_judge_chart():
    import numpy as np
    d = json.loads((RESULTS / "eval_rag_judge.json").read_text())
    s, san = d["summary"], d["judge_sanity"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 4.9), gridspec_kw={"width_ratios": [1.35, 1]})
    m = [("faithfulness", "faithfulness"), ("answer_relevancy", "answer relevancy"),
         ("context_precision", "context precision"), ("context_recall", "context recall")]
    x = np.arange(len(m))
    for off, key, col, lab in ((-0.2, "vector", HEX["GREY"], "pgvector top 4"),
                               (0.2, "rerank", HEX["YELLOW"], "top 12 → reranker → top 4")):
        bars = a1.bar(x + off, [s[key][k] for k, _ in m], 0.38, color=col, label=lab)
        for b in bars:
            a1.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{b.get_height():.2f}", ha="center", fontsize=9)
    a1.set_xticks(x, [l for _, l in m])
    a1.set_ylim(0, 1.25)
    a1.legend(loc="upper center", ncols=2, fontsize=9)
    a1.set_title("RAGAS-style metrics, 30 questions, Qwen2.5-7B judge", loc="left")
    labels = ["faithfulness\nvector", "faithfulness\nrerank", "relevancy\nvector", "relevancy\nrerank"]
    real = [s["vector"]["faithfulness"], s["rerank"]["faithfulness"], s["vector"]["answer_relevancy"],
            s["rerank"]["answer_relevancy"]]
    sw = [san["vector"]["faithfulness_swapped_contexts"], san["rerank"]["faithfulness_swapped_contexts"],
          san["vector"]["answer_relevancy_swapped_question"], san["rerank"]["answer_relevancy_swapped_question"]]
    x = np.arange(4)
    for off, vals, col, lab in ((-0.2, real, HEX["GREEN"], "real pairs"),
                                (0.2, sw, HEX["RED"], "answer paired with another question's contexts / question")):
        bars = a2.bar(x + off, vals, 0.38, color=col, label=lab)
        for b in bars:
            a2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{b.get_height():.2f}", ha="center", fontsize=9)
    a2.set_xticks(x, labels)
    a2.set_ylim(0, 1.25)
    a2.legend(loc="upper center", fontsize=9)
    a2.set_title("Does the judge notice a mismatch?", loc="left")
    fig.tight_layout()
    fig.savefig(IMG / "rag_judge.png")
    plt.close(fig)


if __name__ == "__main__":
    IMG.mkdir(parents=True, exist_ok=True)
    eval_chart()
    if (RESULTS / "eval_classifier.json").exists():
        classifier_chart()
    if (RESULTS / "eval_rerank.json").exists():
        rerank_chart()
    if (RESULTS / "eval_guard_v2.json").exists():
        guard_v2_chart()
    if (RESULTS / "eval_rag_judge.json").exists():
        rag_judge_chart()
    if (RESULTS / "load_k6.json").exists():
        load_chart()
    print("charts written")
