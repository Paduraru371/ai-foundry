"""Ingest every Markdown document in data/ through the teaching API.

Run from the repository root:

    .venv/Scripts/python scripts/ingest_corpus.py

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

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_MANIFEST = REPO_ROOT / "runtime" / "corpus_ingest_manifest.json"
EXCLUDED_CORPUS_FILES = {"readme.md", "questions.md"}
EXCLUDED_SOURCES = {"questions"}


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


def request_json(
    url: str,
    payload: dict | None,
    timeout: float,
    *,
    method: str = "POST",
) -> dict:
    request = Request(
        url,
        data=(json.dumps(payload).encode("utf-8") if payload is not None else None),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Cannot reach {url}: {error.reason}") from error


def post_json(url: str, payload: dict, timeout: float) -> dict:
    return request_json(url, payload, timeout)


def corpus_files(data_dir: Path) -> list[Path]:
    return sorted(
        path for path in data_dir.glob("*.md")
        if path.name.casefold() not in EXCLUDED_CORPUS_FILES
    )


def load_manifest(path: Path, data_dir: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"managed_sources": [], "documents": {}}
    if value.get("data_dir") != str(data_dir):
        return {"managed_sources": [], "documents": {}}
    return value


def save_manifest(
    path: Path,
    data_dir: Path,
    documents: dict[str, dict],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "version": 1,
        "data_dir": str(data_dir),
        "managed_sources": sorted(documents),
        "documents": documents,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


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
    result.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    result.add_argument("--dry-run", action="store_true")
    result.add_argument(
        "--direct",
        action="store_true",
        help="Ingest through backend Python code without requiring a running API.",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    data_dir = args.data_dir.resolve()
    files = corpus_files(data_dir)
    if not files:
        print(f"No corpus Markdown files found in {data_dir}", file=sys.stderr)
        return 2

    manifest_path = args.manifest.resolve()
    previous_manifest = load_manifest(manifest_path, data_dir)
    current_sources = {path.stem for path in files}
    removed_sources = (
        set(previous_manifest.get("managed_sources", [])) - current_sources
    )
    total_chunks = 0
    indexed_documents = 0
    unchanged_documents = 0
    manifest_documents: dict[str, dict] = {}
    endpoint = f"{args.api_url.rstrip('/')}/ingest"
    direct_ingest = None
    ingest_request = None
    direct_delete_source = None
    if args.direct and not args.dry_run:
        sys.path.insert(0, str(REPO_ROOT))
        from backend.api.routers.rag import ingest as direct_ingest
        from backend.api.dependencies import store
        from backend.schemas import IngestRequest as ingest_request
        direct_delete_source = store.delete_source

    if not args.dry_run:
        for source in sorted(EXCLUDED_SOURCES | removed_sources):
            if direct_delete_source is not None:
                deleted = direct_delete_source(source)
            else:
                cleanup = request_json(
                    f"{args.api_url.rstrip('/')}/collection/sources/{source}",
                    None,
                    args.timeout,
                    method="DELETE",
                )
                deleted = int(cleanup["deleted_points"])
            reason = "removed source" if source in removed_sources else "excluded source"
            print(f"[cleanup] {source}: removed {deleted} chunks ({reason})")

    for path in files:
        text = path.read_text(encoding="utf-8")
        metadata = frontmatter(text)
        title = metadata.get("title") or path.stem.replace("_", " ").title()
        source = path.stem
        if args.dry_run:
            print(f"[dry-run] {source}: {title}")
            continue

        payload = {
            "text": text,
            "strategy": args.strategy,
            "source": source,
            "document_title": title,
            "chunk_size": args.chunk_size,
            "chunk_overlap": args.chunk_overlap,
        }
        if direct_ingest is not None and ingest_request is not None:
            response = direct_ingest(ingest_request(**payload)).model_dump()
        else:
            response = post_json(endpoint, payload, args.timeout)
        count = int(response["count"])
        status = response.get("status", "indexed")
        manifest_documents[source] = {
            "fingerprint": response.get("fingerprint"),
            "chunks": count,
            "strategy": response["strategy"],
        }
        if status == "unchanged":
            unchanged_documents += 1
            print(f"[skip] {source}: unchanged ({count} existing chunks)")
        else:
            indexed_documents += 1
            total_chunks += count
            print(f"[ok] {source}: {count} chunks ({response['strategy']})")

    if args.dry_run:
        print(f"Found {len(files)} documents; no requests sent.")
    else:
        save_manifest(manifest_path, data_dir, manifest_documents)
        print(
            f"Corpus ready: {indexed_documents} indexed, "
            f"{unchanged_documents} unchanged, {total_chunks} new/updated chunks."
        )
        print(f"Incremental manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
