from __future__ import annotations

import re
from collections.abc import Iterable

from skeleton_mcp.config import settings
from skeleton_mcp.models import DocChunk, DocRecord


_TITLE_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
_SECTION_RE = re.compile(r"^##\s+(?P<section>.+?)\s*$")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    text = _NON_WORD_RE.sub("-", text.lower()).strip("-")
    return text or "untitled"


def _detect_framework(url: str) -> str:
    lower = url.lower()
    if "svelte" in lower:
        return "svelte"
    if "react" in lower:
        return "react"
    return "all"


def _split_docs(raw_text: str) -> list[tuple[str, str]]:
    lines = raw_text.splitlines()
    docs: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = _TITLE_RE.match(line)
        if match:
            next_title = match.group("title").strip()
            if current_title and current_lines:
                docs.append((current_title, "\n".join(current_lines).strip()))
            current_title = next_title
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)

    if current_title and current_lines:
        docs.append((current_title, "\n".join(current_lines).strip()))

    ignore = {
        "skeleton documentation",
        "get started",
        "guides",
        "design system",
        "tailwind components",
        "framework components",
        "integrations",
        "resources",
    }
    return [(title, body) for (title, body) in docs if title.strip().lower() not in ignore and body]


def parse_documents(url: str, raw_text: str) -> list[DocRecord]:
    framework = _detect_framework(url)
    docs: list[DocRecord] = []
    seen_ids: set[str] = set()

    for title, body in _split_docs(raw_text):
        base = f"{framework}/{_slugify(title)}"
        doc_id = base
        i = 2
        while doc_id in seen_ids:
            doc_id = f"{base}-{i}"
            i += 1
        seen_ids.add(doc_id)
        docs.append(
            DocRecord(
                doc_id=doc_id,
                title=title.strip(),
                framework=framework,
                source_url=url,
                body=body.strip(),
            )
        )
    return docs


def chunk_documents(docs: Iterable[DocRecord]) -> list[DocChunk]:
    chunks: list[DocChunk] = []
    for doc in docs:
        section = "overview"
        buf: list[str] = []
        chunk_num = 1

        for line in doc.body.splitlines():
            section_match = _SECTION_RE.match(line)
            if section_match:
                if buf:
                    chunks.append(_make_chunk(doc, section, chunk_num, "\n".join(buf).strip()))
                    chunk_num += 1
                    buf = []
                section = section_match.group("section").strip()
                continue

            buf.append(line)
            if sum(len(x) for x in buf) >= settings.max_chunk_chars:
                chunks.append(_make_chunk(doc, section, chunk_num, "\n".join(buf).strip()))
                chunk_num += 1
                buf = []

        if buf:
            chunks.append(_make_chunk(doc, section, chunk_num, "\n".join(buf).strip()))

    return [c for c in chunks if c.text]


def _make_chunk(doc: DocRecord, section: str, chunk_num: int, text: str) -> DocChunk:
    return DocChunk(
        chunk_id=f"{doc.doc_id}:{chunk_num}",
        doc_id=doc.doc_id,
        title=doc.title,
        framework=doc.framework,
        source_url=doc.source_url,
        section=section,
        text=text,
    )
