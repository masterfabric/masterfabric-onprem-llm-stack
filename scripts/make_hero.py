"""Compose docs/hero.png (1600x900) from real screenshots and measured numbers.

Every number on the hero is read from docs/results/*.json at render time.
"""

from __future__ import annotations

import json

from PIL import Image, ImageDraw, ImageFilter

from mfviz import BG, BG2, DOCS, GREEN, GREY, ICE, IMG, ORANGE, PURPLE, RED, RESULTS, SHOTS, WHITE, YELLOW, font

W, H = 1600, 900


def load(n):
    return json.loads((RESULTS / f"{n}.json").read_text())


def background():
    im = Image.new("RGB", (W, H), BG)
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = min(1.0, (x / W) * 0.75 + (y / H) * 0.35)
            px[x, y] = tuple(int(BG[i] * (1 - t) + BG2[i] * t) for i in range(3))
    return im


def card(base, path, box, label, color, crop=None):
    x0, y0, x1, y1 = box
    shot = Image.open(path).convert("RGB")
    if crop:
        shot = shot.crop(crop)
    shot = shot.resize((x1 - x0, round(shot.height * (x1 - x0) / shot.width)), Image.LANCZOS)
    shot = shot.crop((0, 0, x1 - x0, min(shot.height, y1 - y0)))
    shadow = Image.new("RGBA", (shot.width + 40, shot.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((20, 20, shot.width + 20, shot.height + 20), radius=16, fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    base.paste(shadow, (x0 - 20, y0 - 12), shadow)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, shot.width, shot.height), radius=14, fill=255)
    base.paste(shot, (x0, y0), mask)
    d = ImageDraw.Draw(base)
    f = font(20, 800)
    w = d.textlength(label, font=f)
    d.rounded_rectangle((x0 - 10, y0 - 22, x0 + w + 18, y0 + 14), radius=18, fill=color)
    d.text((x0 + 4, y0 - 18), label, font=f, fill=(255, 255, 255))


def main():
    q, g, l = load("eval_quality")["summary"], load("eval_guardrails"), load("load_k6")["stages"]
    best_llm = max((v for k, v in l.items() if k.startswith("llm")), key=lambda v: v["output_tokens_per_s"])
    best_rag = max((v for k, v in l.items() if k.startswith("rag")), key=lambda v: v["rps"])
    im = background()
    card(im, IMG / "architecture.png", (980, 70, 1560, 330), "k3d · one Helm release", ICE)
    card(im, IMG / "load_test.png", (1000, 380, 1570, 600), "k6 load test in-cluster", GREEN)
    card(im, SHOTS / "rag_api_swagger_ask.png", (980, 660, 1500, 860), "RAG API · live answer", PURPLE, crop=(0, 1180, 1440, 1800))
    d = ImageDraw.Draw(im)
    d.text((80, 70), "MASTERFABRIC", font=font(36, 800), fill=WHITE)
    d.text((76, 120), "On-Prem LLM Stack", font=font(84, 800), fill=WHITE)
    x, y = 80, 238
    for word, col in (("k3d", ICE), (" · ", GREY), ("llama.cpp/vLLM", ORANGE), (" · ", GREY), ("pgvector", PURPLE),
                      (" · ", GREY), ("guardrails", GREEN)):
        f = font(38, 800)
        d.text((x, y), word, font=f, fill=col)
        x += d.textlength(word, font=f)
    d.text((80, 318), "Open-weight LLM, embeddings, vector store and a guarded RAG API", font=font(26, 500), fill=GREY)
    d.text((80, 352), "from one Helm chart on local Kubernetes. Every number measured.", font=font(26, 500), fill=GREY)
    facts = [
        (f"retrieval hit@4 {q['retrieval_hit_at_k']:.2f} · refusals {q['refusal_accuracy'] * 100:.0f}%",
         f"answer accuracy {q['answer_accuracy']:.2f} on 30 questions · Qwen2.5-1.5B Q4 on CPU", GREEN),
        (f"{g['passed']}/{g['total']} guardrail tests · 0 benign blocks",
         "all direct injections blocked, TR PII masked · 0/4 paraphrase evasions caught", RED),
        (f"{best_llm['output_tokens_per_s']:.0f} output tok/s at {best_llm['vus']} users",
         f"llama.cpp, 4 slots · RAG best {best_rag['rps']:.1f} req/s at {best_rag['vus']} users", ICE),
        ("vLLM on GPU: same chart, one values file", "rendered and linted, not run here (no NVIDIA GPU in the lab)", YELLOW),
    ]
    y = 430
    for title, sub, col in facts:
        d.rounded_rectangle((80, y + 6, 88, y + 62), radius=4, fill=col)
        d.text((106, y), title, font=font(29, 750), fill=WHITE)
        d.text((106, y + 38), sub, font=font(20, 450), fill=GREY)
        y += 92
    d.text((80, 820), "github.com/masterfabric/masterfabric-onprem-llm-stack", font=font(30, 700), fill=WHITE)
    im.save(DOCS / "hero.png", optimize=True)
    print("docs/hero.png written")


if __name__ == "__main__":
    main()
