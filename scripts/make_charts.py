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


if __name__ == "__main__":
    IMG.mkdir(parents=True, exist_ok=True)
    eval_chart()
    if (RESULTS / "load_k6.json").exists():
        load_chart()
    print("charts written")
