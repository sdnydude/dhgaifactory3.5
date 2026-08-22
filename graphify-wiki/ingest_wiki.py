#!/usr/bin/env python3
"""Ingest graphify wiki articles into the registry doc_pages table.

Usage: python3 ingest_wiki.py [--limit N]   (default: all articles)
Re-runnable: clears the graphify-wiki project first, then bulk-ingests.
"""
import json, os, sys, time, urllib.request
from pathlib import Path

WIKI_DIR = Path.home() / "DHG/portage/graphify-out/wiki"
REGISTRY = "http://127.0.0.1:8011/api/doc-pages"
PROJECT = "graphify-wiki"
BATCH = 25

def _write_token():
    # Same contract as registry/doc_ingest.py and dhg-memreg: env first,
    # then ~/.claude/secrets/registry-write-token. Empty = no header.
    token = os.environ.get("REGISTRY_WRITE_TOKEN", "")
    if not token:
        try:
            token = (Path.home() / ".claude/secrets/registry-write-token").read_text().strip()
        except OSError:
            token = ""
    return token

def req(method, url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    token = _write_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(r, timeout=300) as resp:
        return json.loads(resp.read() or "{}")

def pages():
    for f in sorted(WIKI_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        title = next((l.lstrip("# ").strip() for l in text.splitlines()
                      if l.startswith("#")), f.stem.replace("_", " "))
        yield {"project_name": PROJECT, "source_file": f"wiki/{f.name}",
               "chunk_index": 0, "title": title[:500], "content": text,
               "tags": ["graphify", "wiki"],
               "meta_data": {"generator": "graphify"}}

limit = None
if "--limit" in sys.argv:
    limit = int(sys.argv[sys.argv.index("--limit") + 1])

all_pages = list(pages())
if limit:
    all_pages = all_pages[:limit]

try:
    req("DELETE", f"{REGISTRY}/project/{PROJECT}")
except Exception as e:
    print(f"project clear skipped: {e}")

total = 0
t0 = time.time()
for i in range(0, len(all_pages), BATCH):
    chunk = all_pages[i:i + BATCH]
    out = req("POST", f"{REGISTRY}/bulk",
              {"project_name": PROJECT, "pages": chunk, "sweep_stale": False})
    total += out.get("upserted", 0)
    print(f"{total}/{len(all_pages)} upserted ({time.time()-t0:.0f}s)", flush=True)
print("done")
