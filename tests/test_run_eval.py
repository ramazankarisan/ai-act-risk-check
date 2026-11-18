"""Tests for the eval runner: prediction mapping, statistics, pricing and the report."""

from datetime import UTC, datetime
from typing import cast

import pytest
from pydantic import BaseModel

from ai_act_check.baseline import BaselineAnswer
from ai_act_check.corpus import Chunk
from ai_act_check.ports import Usage
from ai_act_check.risk import RiskClass
from evals import run_eval
from evals.schema import GoldenCase, ReviewStatus


def make_chunk(chunk_id: str) -> Chunk:
    """Build a small hand-made chunk."""
    return Chunk(
        chunk_id=chunk_id,
        kind="article",
        text=f"text of {chunk_id}",
        source_url="https://example.test",
        source_version="test",
    )


class FakeRetriever:
    """Returns the same two chunks for every query."""

    def search(self, query: str, top_k: int = 8) -> list[Chunk]:
        return [make_chunk("art-5-1-f"), make_chunk("art-6-2")][:top_k]


class FakeLLM:
    """Answers depend on the use case text inside the user prompt."""

    def __init__(self, model: str = "gpt-test-2025") -> None:
        self.model = model

    def complete_json[T: BaseModel](
        self, system: str, user: str, schema: type[T]
    ) -> tuple[T, Usage]:
        if "emotion" in user:
            answer = BaselineAnswer(
                risk_class=RiskClass.PROHIBITED,
                cited_chunk_ids=["art-5-1-f"],
                needs_review=False,
                reasoning="Banned.",
            )
        else:
            answer = BaselineAnswer(
                risk_class=RiskClass.UNCLEAR,
                cited_chunk_ids=[],
                needs_review=True,
                reasoning="Not sure.",
            )
        usage = Usage(model=self.model, input_tokens=1000, output_tokens=200, latency_ms=50.0)
        return cast(T, answer), usage


def make_case(
    case_id: str,
    description: str,
    expected: RiskClass,
    articles: list[str],
    should_flag: bool,
) -> GoldenCase:
    """Build a golden case directly."""
    return GoldenCase(
        id=case_id,
        description=description,
        expected_class=expected,
        expected_articles=articles,
        should_flag=should_flag,
        source="synthetic",
        review_status=ReviewStatus.DRAFT,
        notes="",
    )


CASES = [
    make_case("c1", "Infer employee emotion at work", RiskClass.PROHIBITED, ["art-5-1-f"], False),
    make_case("c2", "Tool with vague purpose", RiskClass.HIGH_RISK, ["art-6-2"], True),
    make_case("c3", "Another emotion tool at school", RiskClass.PROHIBITED, ["art-5-1-f"], False),
]


def test_run_returns_one_run_per_case_in_order() -> None:
    runs = run_eval.run(CASES, FakeLLM(), FakeRetriever())

    assert [r.gold.id for r in runs] == ["c1", "c2", "c3"]


def test_run_maps_answer_to_prediction() -> None:
    runs = run_eval.run(CASES, FakeLLM(), FakeRetriever())

    first, second = runs[0].prediction, runs[1].prediction
    assert first.case_id == "c1"
    assert first.predicted_class == RiskClass.PROHIBITED
    assert first.cited_articles == ["art-5-1-f"]
    assert first.flagged is False
    assert second.predicted_class == RiskClass.UNCLEAR
    assert second.cited_articles == []
    assert second.flagged is True


def test_run_stores_retrieved_ids_in_result() -> None:
    runs = run_eval.run(CASES[:1], FakeLLM(), FakeRetriever(), top_k=1)

    assert runs[0].result.retrieved_ids == ["art-5-1-f"]


@pytest.mark.parametrize(
    ("p", "expected"),
    [(50, 20.0), (95, 40.0), (100, 40.0), (1, 10.0), (0, 10.0)],
)
def test_percentile_uses_nearest_rank(p: float, expected: float) -> None:
    assert run_eval.percentile([40, 10, 30, 20], p) == expected


def test_percentile_of_single_value_is_that_value() -> None:
    assert run_eval.percentile([7.5], 95) == 7.5


def test_percentile_of_empty_list_raises_value_error() -> None:
    with pytest.raises(ValueError):
        run_eval.percentile([], 50)


def test_price_for_longest_prefix_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(run_eval.PRICES_USD_PER_1M, "gpt-4", (1.0, 2.0))
    monkeypatch.setitem(run_eval.PRICES_USD_PER_1M, "gpt-4o-mini", (0.1, 0.2))

    assert run_eval.price_for("gpt-4o-mini-2024") == (0.1, 0.2)
    assert run_eval.price_for("gpt-4o") == (1.0, 2.0)


def test_price_for_unknown_model_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(run_eval.PRICES_USD_PER_1M, "gpt-4", (1.0, 2.0))

    assert run_eval.price_for("claude-x") is None


def test_estimate_cost_uses_input_and_output_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(run_eval.PRICES_USD_PER_1M, "gpt-test", (2.0, 8.0))

    cost = run_eval.estimate_cost("gpt-test-2025", 1_000_000, 500_000)

    assert cost == pytest.approx(6.0)


def test_estimate_cost_unknown_model_is_none() -> None:
    assert run_eval.estimate_cost("no-such-model-zzz", 100, 100) is None


def test_build_report_contains_metrics_model_and_case_rows() -> None:
    runs = run_eval.run(CASES, FakeLLM(), FakeRetriever())

    report = run_eval.build_report(
        runs, "foundry", "my-deployment", datetime(2026, 1, 2, tzinfo=UTC)
    )

    for name in run_eval.compute_metrics(runs):
        assert name in report
    assert "`gpt-test-2025`" in report
    assert "`my-deployment`" in report
    for case in CASES:
        assert f"| {case.id} |" in report


def test_build_report_shows_na_cost_when_no_price(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_eval, "PRICES_USD_PER_1M", {})
    runs = run_eval.run(CASES, FakeLLM(), FakeRetriever())

    report = run_eval.build_report(runs, "foundry", "d", datetime(2026, 1, 2, tzinfo=UTC))

    assert "n/a (no price configured)" in report


def test_build_report_shows_cost_when_price_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(run_eval.PRICES_USD_PER_1M, "gpt-test", (1.0, 1.0))
    runs = run_eval.run(CASES, FakeLLM(), FakeRetriever())

    report = run_eval.build_report(runs, "foundry", "d", datetime(2026, 1, 2, tzinfo=UTC))

    # 3 cases x (1000 + 200) tokens at $1 per 1M tokens
    assert "$0.0036" in report


def test_make_llm_unknown_provider_raises_value_error() -> None:
    with pytest.raises(ValueError):
        run_eval.make_llm("x")
