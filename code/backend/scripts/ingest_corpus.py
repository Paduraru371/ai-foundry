"""Ingest every Markdown document in data/ through the teaching API.

Run from code/backend:

    uv run python scripts/ingest_corpus.py

Use ``--dry-run`` to inspect discovered documents without making HTTP calls.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data"


def frontmatter(text: str) -> dict[str, str]:
    """Parse the corpus' deliberately simple scalar YAML header."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if separator:
            result[key.strip()] = value.strip().strip("\"'")
    return result


def post_json(url: str, payload: dict, timeout: float) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Cannot reach {url}: {error.reason}") from error


def corpus_files(data_dir: Path) -> list[Path]:
    return sorted(
        path for path in data_dir.glob("*.md")
        if path.name.casefold() != "readme.md"
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    result.add_argument(
        "--api-url",
        default=os.getenv("RAG_API_URL", "http://localhost:7799"),
        help="Backend base URL (default: %(default)s or RAG_API_URL)",
    )
    result.add_argument("--strategy", default="heading", choices=[
        "static", "dynamic", "heading", "sentence", "semantic",
    ])
    result.add_argument("--chunk-size", type=int, default=500)
    result.add_argument("--chunk-overlap", type=int, default=80)
    result.add_argument("--timeout", type=float, default=60)
    result.add_argument("--dry-run", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    data_dir = args.data_dir.resolve()
    files = corpus_files(data_dir)
    if not files:
        print(f"No corpus Markdown files found in {data_dir}", file=sys.stderr)
        return 2

    total_chunks = 0
    endpoint = f"{args.api_url.rstrip('/')}/ingest"
    for path in files:
        text = path.read_text(encoding="utf-8")
        metadata = frontmatter(text)
        title = metadata.get("title") or path.stem.replace("_", " ").title()
        source = path.stem
        if args.dry_run:
            print(f"[dry-run] {source}: {title}")
            continue

        response = post_json(endpoint, {
            "text": text,
            "strategy": args.strategy,
            "source": source,
            "document_title": title,
            "chunk_size": args.chunk_size,
            "chunk_overlap": args.chunk_overlap,
        }, args.timeout)
        count = int(response["count"])
        total_chunks += count
        print(f"[ok] {source}: {count} chunks ({response['strategy']})")

    if args.dry_run:
        print(f"Found {len(files)} documents; no requests sent.")
    else:
        print(f"Ingested {len(files)} documents as {total_chunks} chunks.")
        print("Re-running this command uses the same point IDs and replaces each chunk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
