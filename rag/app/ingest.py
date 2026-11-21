"""Chunk the markdown corpus by heading and load it into pgvector.

    python -m app.ingest                 # corpus/ only (idempotent: replaces all rows)
    python -m app.ingest --attack        # also load corpus/attack/ (guardrail tests)
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

from . import clients, store
from .config import settings

MAX_CHARS = 1200
OVERLAP = 150


def clean(md: str) -> str:
    md = re.sub(r"<p[^>]*>.*?</p>", "", md, flags=re.S)          # image/caption blocks
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)                  # markdown images
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)              # keep link text only
    md = re.sub(r"```mermaid.*?```", "", md, flags=re.S)          # diagrams carry no prose
    return re.sub(r"\n{3,}", "\n\n", md)


def chunks_of(path: Path, root: Path) -> list[dict]:
    text = clean(path.read_text())
    source = str(path.relative_to(root))
    title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("# ")), path.stem)
    out, heads, buf = [], [title], []

    def flush():
        body = "\n".join(buf).strip()
        if len(body) < 40:
            return
        section = " > ".join(heads)
        for i in range(0, len(body), MAX_CHARS - OVERLAP):
            piece = body[i:i + MAX_CHARS]
            out.append(dict(source=source, section=section, content=f"{section}\n\n{piece}"))
            if i + MAX_CHARS >= len(body):
                break

    for ln in text.splitlines():
        m = re.match(r"^(#{2,4})\s+(.*)", ln)
        if m:
            flush()
            buf = []
            level = len(m.group(1))
            heads = heads[: level - 1] + [m.group(2).strip()]
        else:
            buf.append(ln)
    flush()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--attack", action="store_true")
    args = ap.parse_args()
    root = Path(settings.corpus_dir)
    files = sorted(p for p in root.rglob("*.md") if "attack" not in p.parts and p.name != "CORPUS.md")
    items = [c | {"trust": "internal"} for f in files for c in chunks_of(f, root)]
    if args.attack:
        items += [c | {"trust": "untrusted"} for f in sorted((root / "attack").glob("*.md")) for c in chunks_of(f, root)]
    t = time.perf_counter()
    conn = store.connect()
    store.init(conn)
    conn.execute("TRUNCATE chunks")
    for i in range(0, len(items), 16):
        batch = items[i:i + 16]
        vecs = clients.embed([b["content"] for b in batch])
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO chunks (source, section, content, trust, embedding) VALUES (%s,%s,%s,%s,%s)",
                            [(b["source"], b["section"], b["content"], b["trust"], v) for b, v in zip(batch, vecs)])
    print(f"ingested {len(items)} chunks from {len(files)} files in {time.perf_counter() - t:.1f}s")


if __name__ == "__main__":
    main()
