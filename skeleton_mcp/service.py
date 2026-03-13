from __future__ import annotations

import threading
from datetime import datetime, timezone

from skeleton_mcp.cache import load_snapshot, save_snapshot
from skeleton_mcp.config import get_cache_path, settings
from skeleton_mcp.fetch import extract_llm_file_urls, fetch_text
from skeleton_mcp.index import LexicalIndex
from skeleton_mcp.models import DocRecord, IndexSnapshot, utc_now_iso
from skeleton_mcp.parse import chunk_documents, parse_documents


def _parse_iso(dt: str) -> datetime:
    return datetime.fromisoformat(dt)


class SkeletonDocsService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._refresh_lock = threading.Lock()
        self._refresh_thread: threading.Thread | None = None
        self._snapshot: IndexSnapshot | None = None
        self._index: LexicalIndex | None = None

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._snapshot is None:
                self._load_or_refresh_locked()
                return

        if self._is_stale() and (self._refresh_thread is None or not self._refresh_thread.is_alive()):
            self._refresh_thread = threading.Thread(target=self._safe_refresh, daemon=True)
            self._refresh_thread.start()

    def _load_or_refresh_locked(self) -> None:
        cache_path = get_cache_path()
        snapshot = load_snapshot(cache_path)
        if snapshot:
            self._snapshot = snapshot
            self._index = LexicalIndex(snapshot.chunks)
            if self._is_stale_unlocked():
                self._safe_refresh()
            return
        self._refresh_locked(force=True)

    def _is_stale_unlocked(self) -> bool:
        if self._snapshot is None:
            return True
        age = datetime.now(timezone.utc) - _parse_iso(self._snapshot.created_at)
        return age.total_seconds() > settings.index_ttl_seconds

    def _is_stale(self) -> bool:
        with self._lock:
            return self._is_stale_unlocked()

    def _safe_refresh(self) -> None:
        with self._refresh_lock:
            try:
                self.refresh_index(force=True)
            except Exception:
                return

    def refresh_index(self, force: bool = False) -> dict[str, object]:
        with self._lock:
            snapshot = self._snapshot
            if snapshot and not force and not self._is_stale_unlocked():
                return {
                    "status": "skipped",
                    "reason": "cache-fresh",
                    "created_at": snapshot.created_at,
                    "docs": len(snapshot.docs),
                    "chunks": len(snapshot.chunks),
                }
            self._refresh_locked(force=True)
            assert self._snapshot is not None
            return {
                "status": "ok",
                "created_at": self._snapshot.created_at,
                "docs": len(self._snapshot.docs),
                "chunks": len(self._snapshot.chunks),
                "sources": self._snapshot.source_urls,
            }

    def _refresh_locked(self, force: bool) -> None:
        if not force and self._snapshot and not self._is_stale_unlocked():
            return

        llms_index = fetch_text(settings.docs_index_url, settings.refresh_timeout_seconds)
        urls = extract_llm_file_urls(llms_index)
        target_urls = [u for u in urls if not u.endswith("/llms.txt")]
        if not target_urls:
            target_urls = ["https://www.skeleton.dev/llms-full.txt"]

        docs: list[DocRecord] = []
        seen: set[tuple[str, str]] = set()
        for url in target_urls:
            text = fetch_text(url, settings.refresh_timeout_seconds)
            for doc in parse_documents(url, text):
                key = (doc.framework, doc.title.lower().strip())
                if key in seen:
                    continue
                seen.add(key)
                docs.append(doc)

        chunks = chunk_documents(docs)
        snapshot = IndexSnapshot(
            created_at=utc_now_iso(),
            source_urls=target_urls,
            docs=docs,
            chunks=chunks,
        )
        self._snapshot = snapshot
        self._index = LexicalIndex(chunks)
        save_snapshot(get_cache_path(), snapshot)

    def list_docs(self, framework: str | None = None) -> dict[str, object]:
        self.ensure_loaded()
        assert self._snapshot is not None
        docs = self._snapshot.docs
        if framework:
            docs = [d for d in docs if d.framework == framework or d.framework == "all"]
        docs_sorted = sorted(docs, key=lambda d: (d.framework, d.title))
        return {
            "count": len(docs_sorted),
            "docs": [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "framework": d.framework,
                    "source_url": d.source_url,
                }
                for d in docs_sorted
            ],
            "created_at": self._snapshot.created_at,
        }

    def get_doc(self, path_or_slug: str) -> dict[str, object]:
        self.ensure_loaded()
        assert self._snapshot is not None
        needle = path_or_slug.strip().lower()

        for doc in self._snapshot.docs:
            if doc.doc_id.lower() == needle or doc.title.lower() == needle:
                return {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "framework": doc.framework,
                    "source_url": doc.source_url,
                    "content": doc.body,
                    "created_at": self._snapshot.created_at,
                }

        return {
            "error": "not_found",
            "message": f"no doc match for '{path_or_slug}'",
            "created_at": self._snapshot.created_at,
        }

    def search_docs(
        self,
        query: str,
        framework: str | None,
        section: str | None,
        top_k: int,
    ) -> dict[str, object]:
        self.ensure_loaded()
        assert self._index is not None
        assert self._snapshot is not None

        top_k = max(1, min(top_k, 20))
        hits = self._index.search(query=query, top_k=top_k, framework=framework, section=section)
        return {
            "query": query,
            "count": len(hits),
            "results": [
                {
                    "score": round(score, 4),
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "framework": chunk.framework,
                    "section": chunk.section,
                    "source_url": chunk.source_url,
                    "snippet": chunk.text,
                }
                for chunk, score in hits
            ],
            "created_at": self._snapshot.created_at,
        }

    def get_excerpt(self, query: str, top_k: int, max_chars: int) -> dict[str, object]:
        result = self.search_docs(query=query, framework=None, section=None, top_k=top_k)
        excerpts: list[dict[str, object]] = []
        chars_used = 0
        max_chars = max(200, min(max_chars, settings.max_excerpt_chars))

        for item in result["results"]:
            snippet = str(item["snippet"]).strip()
            if not snippet:
                continue
            room = max_chars - chars_used
            if room <= 0:
                break
            clipped = snippet[:room]
            chars_used += len(clipped)
            excerpts.append(
                {
                    "chunk_id": item["chunk_id"],
                    "title": item["title"],
                    "section": item["section"],
                    "framework": item["framework"],
                    "source_url": item["source_url"],
                    "excerpt": clipped,
                }
            )

        return {
            "query": query,
            "count": len(excerpts),
            "max_chars": max_chars,
            "used_chars": chars_used,
            "results": excerpts,
            "created_at": result["created_at"],
        }
