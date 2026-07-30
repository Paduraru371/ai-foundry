"""Heading-aware Markdown parsing and hierarchical chunk context."""
from __future__ import annotations

import re

from .core import chunk_dynamic

MARKDOWN_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
FRONTMATTER = re.compile(
    r"\A---[ \t]*\n(?P<header>.*?)\n---[ \t]*(?:\n|\Z)",
    re.DOTALL,
)


def frontmatter_title(text: str) -> tuple[str | None, str]:
    """Return a scalar YAML title and the Markdown body."""
    match = FRONTMATTER.match(text)
    if not match:
        return None, text
    title = None
    for line in match.group("header").splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() == "title":
            title = value.strip().strip("\"'")
            break
    return title or None, text[match.end():].lstrip()


def markdown_sections(text: str) -> list[tuple[str, str, str]]:
    """Split Markdown into section path, heading line, and body tuples."""
    sections: list[tuple[str, str, str]] = []
    heading_stack: list[str] = []
    current_path = "Overview"
    current_heading = ""
    body: list[str] = []
    in_fence = False

    def flush() -> None:
        content = "\n".join(body).strip()
        if content or current_heading:
            sections.append((current_path, current_heading, content))

    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
        match = None if in_fence else MARKDOWN_HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = match.group(2).strip()
            del heading_stack[level - 1:]
            while len(heading_stack) < level - 1:
                heading_stack.append("")
            heading_stack.append(heading)
            current_path = " > ".join(part for part in heading_stack if part)
            current_heading = line.strip()
            body = []
        else:
            body.append(line)
    flush()
    return sections


def chunk_heading(
    text: str,
    size: int,
    overlap: int,
    document_title: str | None = None,
    min_size: int = 0,
) -> list[str]:
    """Split Markdown by heading and add document, hierarchy, and order."""
    metadata_title, body = frontmatter_title(text)
    title = document_title or metadata_title or "Untitled document"
    sections = markdown_sections(body)
    if not sections and body.strip():
        sections = [("Overview", "", body.strip())]

    chunks: list[str] = []
    section_count = len(sections)
    for section_index, (section_path, heading_line, section_body) in enumerate(
        sections,
        start=1,
    ):
        base_context = f"Document: {title}\nSection: {section_path}"
        fixed_length = len(base_context) + len(heading_line) + 45
        content_budget = max(50, size - fixed_length)
        pieces = (
            chunk_dynamic(
                section_body,
                content_budget,
                min(overlap, content_budget - 1),
                min(min_size, content_budget),
            )
            if section_body
            else [""]
        )
        part_count = len(pieces)
        for part_index, piece in enumerate(pieces, start=1):
            context = (
                f"{base_context}\n"
                f"Order: section {section_index}/{section_count}, "
                f"part {part_index}/{part_count}"
            )
            content = "\n\n".join(
                part for part in (heading_line, piece) if part
            )
            chunks.append(f"{context}\n\n{content}".rstrip())
    return chunks
