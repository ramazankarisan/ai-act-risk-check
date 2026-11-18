"""Retriever that ranks corpus chunks by BM25 keyword relevance."""

import re
from collections.abc import Sequence
from pathlib import Path

from rank_bm25 import BM25Okapi

from ai_act_check.corpus import RAW_HTML_PATH, Chunk, parse_regulation

DEFAULT_TOP_K = 8

_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-case the text and split it into words of letters and digits."""
    return _WORD.findall(text.lower())


class BM25Retriever:
    """Keyword search over chunks. Implements the `Retriever` port."""

    def __init__(self, chunks: Sequence[Chunk]) -> None:
        """Build the BM25 index once from the chunk titles and texts."""
        if not chunks:
            raise ValueError("cannot build a BM25 index without chunks")
        self._chunks = list(chunks)
        self._index = BM25Okapi([tokenize(f"{c.title or ''} {c.text}") for c in self._chunks])

    @classmethod
    def from_corpus(cls, html_path: Path = RAW_HTML_PATH) -> "BM25Retriever":
        """Build a retriever from the committed AI Act HTML."""
        return cls(parse_regulation(html_path.read_bytes()))

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[Chunk]:
        """Return up to `top_k` chunks with the highest BM25 score, best first."""
        scores = self._index.get_scores(tokenize(query))
        # Sort chunk positions by score, highest first; ties keep corpus order.
        ranked = sorted(range(len(self._chunks)), key=lambda i: scores[i], reverse=True)
        return [self._chunks[i] for i in ranked[:top_k]]
