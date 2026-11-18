"""Tests for the baseline classifier, using in-test fakes for the LLM and the retriever."""

from typing import cast

from pydantic import BaseModel

from ai_act_check.baseline import (
    SYSTEM_PROMPT,
    BaselineAnswer,
    build_user_prompt,
    classify,
    format_chunk,
)
from ai_act_check.corpus import Chunk
from ai_act_check.ports import Usage
from ai_act_check.risk import RiskClass


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


class FakeRetriever:
    """Records the query and top_k, returns fixed chunks."""

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.queries: list[str] = []
        self.top_ks: list[int] = []

    def search(self, query: str, top_k: int = 8) -> list[Chunk]:
        self.queries.append(query)
        self.top_ks.append(top_k)
        return self.chunks


class FakeLLM:
    """Records system, user and schema, returns a fixed answer and usage."""

    def __init__(self, answer: BaselineAnswer, usage: Usage) -> None:
        self.answer = answer
        self.usage = usage
        self.systems: list[str] = []
        self.users: list[str] = []
        self.schemas: list[type[BaseModel]] = []

    def complete_json[T: BaseModel](
        self, system: str, user: str, schema: type[T]
    ) -> tuple[T, Usage]:
        self.systems.append(system)
        self.users.append(user)
        self.schemas.append(schema)
        return cast(T, self.answer), self.usage


CHUNKS = [
    make_chunk("art-5-1-f", "Emotion inference at work is banned.", title="Prohibited practices"),
    make_chunk("art-6-2", "High-risk systems are listed in Annex III."),
    make_chunk("rec-44", "Emotion recognition raises concerns."),
]
ANSWER = BaselineAnswer(
    risk_class=RiskClass.PROHIBITED,
    cited_chunk_ids=["art-5-1-f"],
    needs_review=False,
    reasoning="Art. 5(1)(f) bans it.",
)
USAGE = Usage(model="fake-model", input_tokens=10, output_tokens=5, latency_ms=12.5)


def make_fakes() -> tuple[FakeLLM, FakeRetriever]:
    """Fresh fakes for one test."""
    return FakeLLM(ANSWER, USAGE), FakeRetriever(CHUNKS)


def test_classify_passes_description_and_top_k_to_retriever() -> None:
    llm, retriever = make_fakes()

    classify("infer emotions of staff", llm, retriever, top_k=3)

    assert retriever.queries == ["infer emotions of staff"]
    assert retriever.top_ks == [3]


def test_classify_uses_default_top_k_of_eight() -> None:
    llm, retriever = make_fakes()

    classify("anything", llm, retriever)

    assert retriever.top_ks == [8]


def test_classify_user_prompt_contains_description_and_every_chunk_id() -> None:
    llm, retriever = make_fakes()

    classify("infer emotions of staff", llm, retriever)

    user = llm.users[0]
    assert "infer emotions of staff" in user
    for chunk in CHUNKS:
        assert f"[{chunk.chunk_id}]" in user


def test_classify_passes_baseline_answer_schema_and_system_prompt() -> None:
    llm, retriever = make_fakes()

    classify("x", llm, retriever)

    assert llm.schemas == [BaselineAnswer]
    assert llm.systems == [SYSTEM_PROMPT]


def test_classify_result_carries_answer_usage_and_ordered_ids() -> None:
    llm, retriever = make_fakes()

    result = classify("x", llm, retriever)

    assert result.answer == ANSWER
    assert result.usage == USAGE
    assert result.retrieved_ids == ["art-5-1-f", "art-6-2", "rec-44"]


def test_format_chunk_with_title() -> None:
    chunk = make_chunk("art-5-1-f", "Some text.", title="Prohibited practices")

    assert format_chunk(chunk) == "[art-5-1-f] Prohibited practices: Some text."


def test_format_chunk_without_title() -> None:
    chunk = make_chunk("rec-44", "Some text.")

    assert format_chunk(chunk) == "[rec-44] Some text."


def test_build_user_prompt_keeps_chunk_order() -> None:
    prompt = build_user_prompt("desc", CHUNKS)

    positions = [prompt.index(f"[{c.chunk_id}]") for c in CHUNKS]
    assert positions == sorted(positions)
