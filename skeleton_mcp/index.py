from __future__ import annotations

import math
import re
from collections import Counter

from skeleton_mcp.models import DocChunk


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_ALIASES = {
    "modal": ["dialog"],
    "range": ["slider"],
    "range-slider": ["slider"],
    "toaster": ["toast"],
    "paginator": ["pagination"],
    "radio-group": ["segmented", "segmented-control"],
    "progress-ring": ["progress", "circular"],
}


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class LexicalIndex:
    def __init__(self, chunks: list[DocChunk]) -> None:
        self.chunks = chunks
        self._df: Counter[str] = Counter()
        self._chunk_body_tfs: list[Counter[str]] = []
        self._chunk_title_tfs: list[Counter[str]] = []
        self._chunk_section_tfs: list[Counter[str]] = []
        self._fit()

    def _fit(self) -> None:
        for chunk in self.chunks:
            body_tf = Counter(_tokenize(chunk.text))
            title_tf = Counter(_tokenize(chunk.title))
            section_tf = Counter(_tokenize(chunk.section))
            self._chunk_body_tfs.append(body_tf)
            self._chunk_title_tfs.append(title_tf)
            self._chunk_section_tfs.append(section_tf)
            vocab = set(body_tf) | set(title_tf) | set(section_tf)
            for token in vocab:
                self._df[token] += 1

    def _idf(self, token: str) -> float:
        n = len(self.chunks)
        df = self._df.get(token, 0)
        return math.log((1 + n) / (1 + df)) + 1.0

    def _expand_query(self, query: str) -> list[str]:
        tokens = _tokenize(query)
        expanded = list(tokens)
        for token in tokens:
            expanded.extend(_ALIASES.get(token, []))
        return expanded

    def search(
        self,
        query: str,
        top_k: int,
        framework: str | None = None,
        section: str | None = None,
    ) -> list[tuple[DocChunk, float]]:
        query_tokens = self._expand_query(query)
        scored: list[tuple[int, float]] = []
        for idx, chunk in enumerate(self.chunks):
            if framework and chunk.framework != framework and chunk.framework != "all":
                continue
            if section and section.lower() not in chunk.section.lower():
                continue

            score = 0.0
            body_tf = self._chunk_body_tfs[idx]
            title_tf = self._chunk_title_tfs[idx]
            section_tf = self._chunk_section_tfs[idx]

            for token in query_tokens:
                idf = self._idf(token)
                score += body_tf.get(token, 0) * idf * 1.0
                score += title_tf.get(token, 0) * idf * 3.0
                score += section_tf.get(token, 0) * idf * 2.0

            if score > 0:
                scored.append((idx, score))

        scored.sort(key=lambda item: (-item[1], self.chunks[item[0]].chunk_id))
        return [(self.chunks[idx], score) for idx, score in scored[:top_k]]
