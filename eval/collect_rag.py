"""Collect question, retrieved contexts and answer for the RAG judge eval (eval/rag_judge.py).

Runs inside the API pod (`kubectl exec -i deploy/llm-rag -- python - < eval/collect_rag.py`), so it goes
through the deployed code path (rules, guard, embedding, pgvector, optional rerank, generation, output
guardrails) unchanged. The one addition is a wrapper around the chat call that records the context the
generator actually saw. The questions (eval/questions.jsonl) arrive as a JSON list in the env var QUESTIONS.
Prints one JSON object per question and mode.
"""
import json
import os
import re
import sys

sys.path.insert(0, "/app")
from app import main as m  # noqa: E402

seen = {}
_chat = m.clients.chat


def chat(messages, max_tokens):
    seen["messages"] = messages
    return _chat(messages, max_tokens)


m.clients.chat = chat
m._open()
CTX = re.compile(r"^\[(\d+)\] \(([^)]*)\)\n", re.M)

for mode in ("vector", "rerank"):
    for item in json.loads(os.environ["QUESTIONS"]):
        seen.clear()
        res = m.ask(m.Ask(question=item["question"], rerank=(mode == "rerank")))
        contexts = []
        if "messages" in seen:
            user = seen["messages"][1]["content"]
            body = user.split("Context:\n", 1)[1].rsplit("\n\nQuestion: ", 1)[0]
            parts = CTX.split(body)[1:]
            contexts = [{"n": int(parts[i]), "source": parts[i + 1], "text": parts[i + 2].strip()}
                        for i in range(0, len(parts), 3)]
        print(json.dumps({"id": item["id"], "mode": mode, "question": item["question"], "answer": res["answer"],
                          "blocked": res["blocked"], "contexts": contexts,
                          "generate_ms": res.get("timings_ms", {}).get("generate")}), flush=True)
