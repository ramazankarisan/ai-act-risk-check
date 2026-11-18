"""Tests for the BM25 retriever."""

import pytest

from ai_act_check.adapters.bm25_retriever import BM25Retriever, tokenize
from ai_act_check.corpus import Chunk


def make_chunk(chunk_id: str, text: str, title: str | None = None) -> Chunk:
    """Build a small hand-made chunk."""
    return Chunk(
        chunk_id=chunk_id,
        kind="article",
        title=title,
        text=text,
        source_url="https://example.test",
        source_version="test",
    )


CHUNKS = [
    make_chunk("a", "Providers must keep technical documentation for ten years."),
    make_chunk("b", "Emotion recognition systems in the workplace are prohibited."),
    make_chunk("c", "Penalties apply to infringements of this regulation."),
    make_chunk("d", "Fish swim in the sea and birds fly in the sky."),
]


def test_tokenize_lowercases_and_splits_on_non_alphanumerics() -> None:
    assert tokenize("Art. 5(1)(f) -- Hello, World!") == ["art", "5", "1", "f", "hello", "world"]


def test_tokenize_empty_string_gives_no_tokens() -> None:
    assert tokenize("") == []


def test_search_returns_best_match_first() -> None:
    retriever = BM25Retriever(CHUNKS)

    results = retriever.search("emotion recognition workplace", top_k=4)

    assert results[0].chunk_id == "b"


def test_search_top_k_limits_results() -> None:
    retriever = BM25Retriever(CHUNKS)

    results = retriever.search("regulation", top_k=2)

    assert len(results) == 2


def test_search_top_k_larger_than_corpus_returns_all_chunks() -> None:
    retriever = BM25Retriever(CHUNKS)

    results = retriever.search("regulation", top_k=50)

    assert len(results) == len(CHUNKS)


def test_search_matches_on_title() -> None:
    chunks = [*CHUNKS, make_chunk("e", "Plain body text.", title="Zebra crossing rules")]
    retriever = BM25Retriever(chunks)

    results = retriever.search("zebra", top_k=1)

    assert results[0].chunk_id == "e"


def test_empty_chunk_list_raises_value_error() -> None:
    with pytest.raises(ValueError):
        BM25Retriever([])


def test_from_corpus_finds_emotion_inference_prohibition() -> None:
    """Art. 5(1)(f) prohibits inferring emotions in the workplace; uses the committed HTML."""
    retriever = BM25Retriever.from_corpus()

    results = retriever.search("inferring the emotions of employees in the workplace", top_k=8)

    assert "art-5-1-f" in [chunk.chunk_id for chunk in results]
