#!/usr/bin/env python3
"""Ingest markdown documentation into the DHG Registry doc_pages table.

Reads all .md files from a project directory, chunks at heading boundaries
(max 1500 chars with 200 char overlap), and posts to the registry API.
Supports mark-and-sweep to remove stale chunks.

Usage:
  python doc_ingest.py --project portage --docs-dir /path/to/docs [--sweep]
  python doc_ingest.py --project portage --docs-dir /path/to/docs --registry-url http://localhost:8011
"""
import argparse
import logging
import os
import re
import sys
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REGISTRY_URL = os.getenv("REGISTRY_URL", "http://localhost:8011")
MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 200


def extract_heading_path(lines: list[str], end_idx: int) -> str:
    """Walk backwards from end_idx to build the heading hierarchy."""
    headings: dict[int, str] = {}
    for i in range(end_idx, -1, -1):
        line = lines[i].strip()
        match = re.match(r'^(#{1,6})\s+(.+)', line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            if level not in headings:
                headings[level] = text
    parts = [headings[k] for k in sorted(headings)]
    return " > ".join(parts) if parts else ""


def chunk_markdown(content: str) -> list[dict]:
    """Split markdown into chunks at heading boundaries."""
    lines = content.split('\n')
    chunks: list[dict] = []
    current_lines: list[str] = []
    current_title: str | None = None
    current_heading_start = 0

    def flush(heading_idx: int):
        nonlocal current_lines, current_title
        if not current_lines:
            return
        text = '\n'.join(current_lines).strip()
        if not text:
            current_lines = []
            return

        heading_path = extract_heading_path(lines, heading_idx)

        if len(text) <= MAX_CHUNK_CHARS:
            chunks.append({
                "title": current_title,
                "content": text,
                "heading_path": heading_path,
            })
        else:
            paragraphs = re.split(r'\n\n+', text)
            sub_chunk = ""
            for para in paragraphs:
                if len(sub_chunk) + len(para) + 2 > MAX_CHUNK_CHARS and sub_chunk:
                    chunks.append({
                        "title": current_title,
                        "content": sub_chunk.strip(),
                        "heading_path": heading_path,
                    })
                    overlap = sub_chunk[-OVERLAP_CHARS:] if len(sub_chunk) > OVERLAP_CHARS else sub_chunk
                    sub_chunk = overlap + "\n\n" + para
                else:
                    sub_chunk = (sub_chunk + "\n\n" + para).strip()
            if sub_chunk.strip():
                chunks.append({
                    "title": current_title,
                    "content": sub_chunk.strip(),
                    "heading_path": heading_path,
                })
        current_lines = []

    for i, line in enumerate(lines):
        heading_match = re.match(r'^(#{1,3})\s+(.+)', line)
        if heading_match:
            flush(current_heading_start)
            current_title = heading_match.group(2).strip()
            current_heading_start = i
            current_lines = [line]
        else:
            current_lines.append(line)

    flush(current_heading_start)
    return chunks


def find_markdown_files(docs_dir: Path) -> list[Path]:
    """Find all .md files, excluding node_modules and hidden dirs."""
    files = []
    for p in sorted(docs_dir.rglob("*.md")):
        parts = p.parts
        if any(part.startswith('.') or part == 'node_modules' for part in parts):
            continue
        files.append(p)
    return files


def ingest_project(project_name: str, docs_dir: Path, registry_url: str, sweep: bool):
    """Ingest all markdown files for a project."""
    md_files = find_markdown_files(docs_dir)
    if not md_files:
        logger.warning("No .md files found in %s", docs_dir)
        return

    logger.info("Found %d markdown files in %s", len(md_files), docs_dir)

    pages: list[dict] = []
    for md_file in md_files:
        rel_path = str(md_file.relative_to(docs_dir))
        content = md_file.read_text(encoding="utf-8", errors="replace")

        if not content.strip():
            continue

        chunks = chunk_markdown(content)
        for idx, chunk in enumerate(chunks):
            pages.append({
                "project_name": project_name,
                "source_file": rel_path,
                "chunk_index": idx,
                "title": chunk["title"],
                "content": chunk["content"],
                "heading_path": chunk["heading_path"],
                "tags": [project_name],
            })

    logger.info("Generated %d chunks from %d files", len(pages), len(md_files))

    payload = {
        "project_name": project_name,
        "pages": pages,
        "sweep_stale": sweep,
    }

    url = f"{registry_url}/api/doc-pages/bulk"
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                "Ingested: %d upserted, %d swept for project '%s'",
                result.get("upserted", 0),
                result.get("swept", 0),
                project_name,
            )
    except httpx.HTTPStatusError as e:
        logger.error("Registry API error: %s — %s", e.response.status_code, e.response.text[:500])
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to reach registry at %s: %s", url, e)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Ingest markdown docs into DHG Registry")
    parser.add_argument("--project", required=True, help="Project name (e.g., portage)")
    parser.add_argument("--docs-dir", required=True, help="Path to docs directory")
    parser.add_argument("--registry-url", default=REGISTRY_URL, help="Registry API URL")
    parser.add_argument("--sweep", action="store_true", help="Remove stale chunks not in this ingest")
    args = parser.parse_args()

    docs_path = Path(args.docs_dir).resolve()
    if not docs_path.is_dir():
        logger.error("Docs directory not found: %s", docs_path)
        sys.exit(1)

    ingest_project(args.project, docs_path, args.registry_url, args.sweep)


if __name__ == "__main__":
    main()
