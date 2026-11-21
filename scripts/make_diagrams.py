"""Architecture diagram (Pillow)."""
from mfviz import GREEN, GREY, ICE, IMG, ORANGE, PURPLE, RED, WHITE, YELLOW, arrow, box, canvas, font


def architecture():
    im, d = canvas(1600, 1000)
    d.text((60, 40), "MasterFabric On-Prem LLM Stack · architecture", font=font(36, 800), fill=WHITE)
    d.text((60, 90), "k3d (k3s in Docker), namespace llm, one Helm release. Only the API is exposed (127.0.0.1:48080).",
           font=font(20, 450), fill=GREY)
    box(d, (50, 330, 300, 540), "Client", ["curl / apps", "eval/*.py", "POST /v1/ask"], GREY, line_size=18)
    box(d, (380, 330, 620, 540), "Traefik ingress", ["k3s default", "path /", "→ rag:8000"], YELLOW, line_size=18)
    box(d, (700, 170, 1080, 720), "RAG API (FastAPI)", ["1 input rules", "   injection · PII mask", "2 risk classifier",
                                                         "   score ≥ 0.6 → block", "3 embed question",
                                                         "4 pgvector top-4", "   (top-12 if rerank)", "5 context filter",
                                                         "6 rerank → top-4 (on request)", "7 generate (T=0)",
                                                         "8 output guardrails", "   canary · PII · citations",
                                                         "/readyz · /metrics"], GREEN, line_size=18)
    right = [((1160, 140, 1560, 260), "llm (llama.cpp)", ["Qwen2.5-1.5B-Instruct Q4_K_M", "4 slots · 8k ctx"], ICE, "generate", 200),
             ((1160, 280, 1560, 400), "embed (llama.cpp)", ["bge-small-en-v1.5 f16 · 384-d"], PURPLE, "embed", 340),
             ((1160, 420, 1560, 540), "guard (llama.cpp)", ["Granite Guardian 3.2 3B-A800M", "Q4_K_M · P(Yes) score"], RED, "classify", 480),
             ((1160, 560, 1560, 680), "rerank (llama.cpp)", ["bge-reranker-v2-m3 Q8_0", "/v1/rerank cross-encoder"], YELLOW, "rerank", 620),
             ((1160, 700, 1560, 820), "pgvector (StatefulSet)", ["PostgreSQL 16 · HNSW cosine", "207 chunks · 23 docs"], ORANGE, "search", 760)]
    for xy, title, lines, col, label, y in right:
        box(d, xy, title, lines, col, title_size=22, line_size=17)
        arrow(d, (1080, min(max(y, 190), 700)), (1160, y), col, label)
    box(d, (50, 620, 300, 900), "Prometheus", ["scrapes /metrics of", "rag + 4 llama.cpp", "servers every 10 s", "",
                                               "Grafana dashboard", "port-forward only"], ORANGE, line_size=17)
    box(d, (380, 760, 620, 940), "ingest Job", ["helm post-install", "corpus/ → chunks", "→ embed → pgvector"], PURPLE, line_size=17)
    box(d, (700, 760, 1080, 940), "NetworkPolicy", ["models + DB accept only", "onprem-llm/model-client=true;",
                                                    "port 8080 also from", "onprem-llm/metrics-scraper"], RED, line_size=17)
    d.text((1160, 860), "values-vllm-gpu.yaml: same llm Service,", font=font(17, 500), fill=GREY)
    d.text((1160, 885), "vllm/vllm-openai on NVIDIA nodes", font=font(17, 500), fill=GREY)
    arrow(d, (300, 435), (380, 435), GREY)
    arrow(d, (620, 435), (700, 435), YELLOW)
    arrow(d, (300, 680), (700, 680), ORANGE, "scrape", at=0.45)
    im.save(IMG / "architecture.png", optimize=True)


if __name__ == "__main__":
    architecture()
    print("diagram written")
