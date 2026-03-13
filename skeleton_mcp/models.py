from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DocChunk:
    chunk_id: str
    doc_id: str
    title: str
    framework: str
    source_url: str
    section: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocRecord:
    doc_id: str
    title: str
    framework: str
    source_url: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IndexSnapshot:
    created_at: str
    source_urls: list[str]
    docs: list[DocRecord]
    chunks: list[DocChunk]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "source_urls": self.source_urls,
            "docs": [d.to_dict() for d in self.docs],
            "chunks": [c.to_dict() for c in self.chunks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndexSnapshot":
        docs = [DocRecord(**item) for item in data.get("docs", [])]
        chunks = [DocChunk(**item) for item in data.get("chunks", [])]
        return cls(
            created_at=data.get("created_at", utc_now_iso()),
            source_urls=list(data.get("source_urls", [])),
            docs=docs,
            chunks=chunks,
        )
