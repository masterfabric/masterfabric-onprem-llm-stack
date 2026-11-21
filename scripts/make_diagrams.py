"""Architecture diagram (Pillow)."""
from mfviz import GREEN, GREY, ICE, IMG, ORANGE, PURPLE, RED, WHITE, YELLOW, arrow, box, canvas, font


def architecture():
    im, d = canvas(1600, 900)
    d.text((60, 40), "MasterFabric On-Prem LLM Stack · architecture", font=font(36, 800), fill=WHITE)
    d.text((60, 90), "k3d (k3s in Docker), namespace llm, one Helm release. Only the API is exposed (127.0.0.1:48080).",
           font=font(20, 450), fill=GREY)
    box(d, (50, 330, 300, 560), "Client", ["curl / apps", "eval/run_eval.py", "POST /v1/ask"], GREY, line_size=18)
    box(d, (380, 330, 620, 560), "Traefik ingress", ["k3s default", "path /", "→ rag:8000"], YELLOW, line_size=18)
    box(d, (700, 250, 1080, 650), "RAG API (FastAPI)", ["1 input guardrails", "   injection · PII mask", "2 embed question",
                                                         "3 pgvector top-4", "4 context filter", "5 generate (T=0)",
                                                         "6 output guardrails", "   canary · PII · citations",
                                                         "/readyz · /metrics"], GREEN, line_size=18)
    box(d, (1160, 130, 1560, 330), "llm (llama.cpp)", ["Qwen2.5-1.5B-Instruct Q4_K_M", "4 slots · 8k ctx · 4 threads",
                                                       "OpenAI /v1/chat/completions"], ICE, line_size=17)
    box(d, (1160, 370, 1560, 540), "embed (llama.cpp)", ["bge-small-en-v1.5 f16", "384-d · /v1/embeddings"], PURPLE, line_size=17)
    box(d, (1160, 580, 1560, 760), "pgvector (StatefulSet)", ["PostgreSQL 16 · HNSW cosine", "207 chunks · 23 docs"], ORANGE,
        line_size=17)
    box(d, (380, 660, 620, 860), "ingest Job", ["helm post-install", "corpus/ → chunks", "→ embed → pgvector"], RED, line_size=17)
    box(d, (700, 700, 1080, 860), "NetworkPolicy", ["models + DB accept only", "onprem-llm/model-client=true"], RED, line_size=17)
    d.text((1160, 790), "values-vllm-gpu.yaml: same llm Service,", font=font(17, 500), fill=GREY)
    d.text((1160, 815), "vllm/vllm-openai on NVIDIA nodes", font=font(17, 500), fill=GREY)
    arrow(d, (300, 445), (380, 445), GREY)
    arrow(d, (620, 445), (700, 445), YELLOW)
    arrow(d, (1080, 300), (1160, 230), ICE, "generate")
    arrow(d, (1080, 450), (1160, 455), PURPLE, "embed")
    arrow(d, (1080, 600), (1160, 660), ORANGE, "search")
    im.save(IMG / "architecture.png", optimize=True)


if __name__ == "__main__":
    architecture()
    print("diagram written")
