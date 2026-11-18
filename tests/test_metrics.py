"""Tests for evals.metrics. The docstrings in that module are the spec."""

from collections.abc import Callable, Sequence

import pytest

from evals.metrics import (
    citation_precision,
    citation_recall,
    class_accuracy,
    flag_recall,
    retrieval_recall,
    review_rate,
    silent_miss_rate,
)
from evals.schema import GoldenCase, Prediction, ReviewStatus, RiskClass

MetricFn = Callable[[Sequence[Prediction], Sequence[GoldenCase]], float]


def gold(
    case_id: str,
    cls: RiskClass = RiskClass.HIGH_RISK,
    articles: Sequence[str] = (),
    flag: bool = False,
    acceptable: Sequence[str] = (),
) -> GoldenCase:
    """Build a golden case with dummy text."""
    return GoldenCase(
        id=case_id,
        description="dummy description",
        expected_class=cls,
        expected_articles=list(articles),
        acceptable_articles=list(acceptable),
        should_flag=flag,
        source="dummy source",
        review_status=ReviewStatus.DRAFT,
        notes="dummy notes",
    )


def pred(
    case_id: str,
    cls: RiskClass = RiskClass.HIGH_RISK,
    cited: Sequence[str] = (),
    flagged: bool = False,
    retrieved: Sequence[str] = (),
) -> Prediction:
    """Build a prediction."""
    return Prediction(
        case_id=case_id,
        predicted_class=cls,
        cited_articles=list(cited),
        flagged=flagged,
        retrieved_articles=list(retrieved),
    )


# --- class_accuracy ---------------------------------------------------------------------


def test_class_accuracy_all_correct_is_one() -> None:
    golds = [gold("a", RiskClass.HIGH_RISK), gold("b", RiskClass.MINIMAL)]
    preds = [pred("a", RiskClass.HIGH_RISK), pred("b", RiskClass.MINIMAL)]

    result = class_accuracy(preds, golds)

    assert result == pytest.approx(1.0)


def test_class_accuracy_docstring_example_excluding_unclear() -> None:
    golds = [
        gold("a", RiskClass.HIGH_RISK),
        gold("b", RiskClass.MINIMAL),
        gold("c", RiskClass.UNCLEAR),
    ]
    preds = [
        pred("a", RiskClass.HIGH_RISK),
        pred("b", RiskClass.UNCLEAR),
        pred("c", RiskClass.UNCLEAR),
    ]

    result = class_accuracy(preds, golds, exclude_unclear=True)

    assert result == pytest.approx(0.5)


def test_class_accuracy_docstring_example_including_unclear() -> None:
    golds = [
        gold("a", RiskClass.HIGH_RISK),
        gold("b", RiskClass.MINIMAL),
        gold("c", RiskClass.UNCLEAR),
    ]
    preds = [
        pred("a", RiskClass.HIGH_RISK),
        pred("b", RiskClass.UNCLEAR),
        pred("c", RiskClass.UNCLEAR),
    ]

    result = class_accuracy(preds, golds, exclude_unclear=False)

    assert result == pytest.approx(2 / 3)


def test_class_accuracy_unclear_prediction_on_definite_case_is_wrong() -> None:
    golds = [gold("a", RiskClass.PROHIBITED)]
    preds = [pred("a", RiskClass.UNCLEAR)]

    result = class_accuracy(preds, golds)

    assert result == pytest.approx(0.0)


def test_class_accuracy_all_unclear_gold_excluded_raises() -> None:
    golds = [gold("a", RiskClass.UNCLEAR), gold("b", RiskClass.UNCLEAR)]
    preds = [pred("a", RiskClass.UNCLEAR), pred("b", RiskClass.MINIMAL)]

    with pytest.raises(ValueError):
        class_accuracy(preds, golds, exclude_unclear=True)


def test_class_accuracy_all_unclear_gold_included_is_scored() -> None:
    golds = [gold("a", RiskClass.UNCLEAR), gold("b", RiskClass.UNCLEAR)]
    preds = [pred("a", RiskClass.UNCLEAR), pred("b", RiskClass.MINIMAL)]

    result = class_accuracy(preds, golds, exclude_unclear=False)

    assert result == pytest.approx(0.5)


def test_class_accuracy_empty_lists_raise() -> None:
    with pytest.raises(ValueError):
        class_accuracy([], [])


# --- citation_precision -----------------------------------------------------------------


def test_citation_precision_docstring_example() -> None:
    golds = [gold("a", articles=["A", "B"])]
    preds = [pred("a", cited=["A", "C"])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(0.5)


def test_citation_precision_both_empty_is_one() -> None:
    golds = [gold("a", articles=[])]
    preds = [pred("a", cited=[])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(1.0)


def test_citation_precision_nothing_cited_but_expected_is_zero() -> None:
    golds = [gold("a", articles=["A"])]
    preds = [pred("a", cited=[])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(0.0)


def test_citation_precision_cited_but_nothing_expected_is_zero() -> None:
    golds = [gold("a", articles=[])]
    preds = [pred("a", cited=["A"])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(0.0)


def test_citation_precision_duplicates_count_once() -> None:
    golds = [gold("a", articles=["A"])]
    preds = [pred("a", cited=["A", "A"])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(1.0)


def test_citation_precision_is_mean_over_cases() -> None:
    golds = [gold("a", articles=["A"]), gold("b", articles=["B"])]
    preds = [pred("a", cited=["A"]), pred("b", cited=["X"])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(0.5)


def test_citation_precision_docstring_example_with_acceptable() -> None:
    golds = [gold("a", articles=["A", "B"], acceptable=["C"])]
    preds = [pred("a", cited=["A", "C", "D"])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(2 / 3)


def test_citation_precision_only_acceptable_cited_is_one() -> None:
    golds = [gold("a", articles=["A"], acceptable=["B", "C"])]
    preds = [pred("a", cited=["B", "C"])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(1.0)


def test_citation_precision_nothing_cited_nothing_expected_with_acceptable_is_one() -> None:
    golds = [gold("a", articles=[], acceptable=["B"])]
    preds = [pred("a", cited=[])]

    result = citation_precision(preds, golds)

    assert result == pytest.approx(1.0)


def test_citation_precision_empty_lists_raise() -> None:
    with pytest.raises(ValueError):
        citation_precision([], [])


# --- citation_recall --------------------------------------------------------------------


def test_citation_recall_docstring_example() -> None:
    golds = [gold("a", articles=["A", "B"])]
    preds = [pred("a", cited=["A", "C"])]

    result = citation_recall(preds, golds)

    assert result == pytest.approx(0.5)


def test_citation_recall_nothing_expected_is_one() -> None:
    golds = [gold("a", articles=[])]
    preds = [pred("a", cited=[])]

    result = citation_recall(preds, golds)

    assert result == pytest.approx(1.0)


def test_citation_recall_nothing_expected_is_one_even_if_cited() -> None:
    golds = [gold("a", articles=[])]
    preds = [pred("a", cited=["A"])]

    result = citation_recall(preds, golds)

    assert result == pytest.approx(1.0)


def test_citation_recall_nothing_cited_but_expected_is_zero() -> None:
    golds = [gold("a", articles=["A"])]
    preds = [pred("a", cited=[])]

    result = citation_recall(preds, golds)

    assert result == pytest.approx(0.0)


def test_citation_recall_duplicates_count_once() -> None:
    golds = [gold("a", articles=["A", "B"])]
    preds = [pred("a", cited=["A", "A"])]

    result = citation_recall(preds, golds)

    assert result == pytest.approx(0.5)


def test_citation_recall_is_mean_over_cases() -> None:
    golds = [gold("a", articles=["A"]), gold("b", articles=["B"])]
    preds = [pred("a", cited=["A"]), pred("b", cited=[])]

    result = citation_recall(preds, golds)

    assert result == pytest.approx(0.5)


def test_citation_recall_ignores_acceptable_articles() -> None:
    golds = [gold("a", articles=["A"], acceptable=["B"])]

    only_acceptable = citation_recall([pred("a", cited=["B"])], golds)
    expected_cited = citation_recall([pred("a", cited=["A"])], golds)

    assert only_acceptable == pytest.approx(0.0)
    assert expected_cited == pytest.approx(1.0)


def test_citation_recall_empty_lists_raise() -> None:
    with pytest.raises(ValueError):
        citation_recall([], [])


# --- flag_recall ------------------------------------------------------------------------


def test_flag_recall_docstring_example_three_of_four() -> None:
    golds = [gold(str(i), flag=True) for i in range(4)]
    preds = [pred(str(i), flagged=i < 3) for i in range(4)]

    result = flag_recall(preds, golds)

    assert result == pytest.approx(0.75)


def test_flag_recall_flags_on_unflagged_cases_do_not_count() -> None:
    golds = [gold("a", flag=True), gold("b", flag=False)]
    preds = [pred("a", flagged=False), pred("b", flagged=True)]

    result = flag_recall(preds, golds)

    assert result == pytest.approx(0.0)


def test_flag_recall_without_should_flag_case_raises() -> None:
    golds = [gold("a", flag=False)]
    preds = [pred("a", flagged=True)]

    with pytest.raises(ValueError):
        flag_recall(preds, golds)


def test_flag_recall_all_flagged_is_one() -> None:
    golds = [gold("a", flag=True), gold("b", flag=True)]
    preds = [pred("a", flagged=True), pred("b", flagged=True)]

    result = flag_recall(preds, golds)

    assert result == pytest.approx(1.0)


# --- review_rate ------------------------------------------------------------------------


def test_review_rate_docstring_example_three_of_ten() -> None:
    golds = [gold(str(i)) for i in range(10)]
    preds = [pred(str(i), flagged=i < 3) for i in range(10)]

    result = review_rate(preds, golds)

    assert result == pytest.approx(0.3)


def test_review_rate_nothing_flagged_is_zero() -> None:
    golds = [gold("a"), gold("b")]
    preds = [pred("a", flagged=False), pred("b", flagged=False)]

    result = review_rate(preds, golds)

    assert result == pytest.approx(0.0)


def test_review_rate_flagging_everything_is_visible() -> None:
    golds = [gold("a", flag=True), gold("b", flag=False), gold("c", flag=False)]
    preds = [pred(case_id, flagged=True) for case_id in ("a", "b", "c")]

    recall = flag_recall(preds, golds)
    rate = review_rate(preds, golds)

    assert recall == pytest.approx(1.0)
    assert rate == pytest.approx(1.0)


def test_review_rate_ignores_should_flag() -> None:
    preds = [pred("a", flagged=True), pred("b", flagged=False)]

    with_flags = review_rate(preds, [gold("a", flag=True), gold("b", flag=True)])
    without_flags = review_rate(preds, [gold("a", flag=False), gold("b", flag=False)])

    assert with_flags == pytest.approx(0.5)
    assert without_flags == pytest.approx(0.5)


def test_review_rate_empty_lists_raise() -> None:
    with pytest.raises(ValueError):
        review_rate([], [])


# --- silent_miss_rate -------------------------------------------------------------------


def test_silent_miss_rate_docstring_example() -> None:
    golds = [gold(str(i), RiskClass.HIGH_RISK) for i in range(10)]
    preds = [pred(str(i), RiskClass.HIGH_RISK) for i in range(7)]
    preds.append(pred("7", RiskClass.MINIMAL, flagged=True))
    preds.append(pred("8", RiskClass.MINIMAL))
    preds.append(pred("9", RiskClass.MINIMAL))

    result = silent_miss_rate(preds, golds)

    assert result == pytest.approx(0.2)


def test_silent_miss_rate_all_correct_is_zero() -> None:
    golds = [gold("a", RiskClass.HIGH_RISK), gold("b", RiskClass.MINIMAL)]
    preds = [pred("a", RiskClass.HIGH_RISK), pred("b", RiskClass.MINIMAL)]

    result = silent_miss_rate(preds, golds)

    assert result == pytest.approx(0.0)


def test_silent_miss_rate_wrong_but_flagged_is_not_a_miss() -> None:
    golds = [gold("a", RiskClass.HIGH_RISK)]
    preds = [pred("a", RiskClass.MINIMAL, flagged=True)]

    result = silent_miss_rate(preds, golds)

    assert result == pytest.approx(0.0)


def test_silent_miss_rate_correct_and_flagged_is_not_a_miss() -> None:
    golds = [gold("a", RiskClass.HIGH_RISK)]
    preds = [pred("a", RiskClass.HIGH_RISK, flagged=True)]

    result = silent_miss_rate(preds, golds)

    assert result == pytest.approx(0.0)


def test_silent_miss_rate_gold_unclear_predicted_definite_unflagged_is_a_miss() -> None:
    golds = [gold("a", RiskClass.UNCLEAR)]
    preds = [pred("a", RiskClass.HIGH_RISK, flagged=False)]

    result = silent_miss_rate(preds, golds)

    assert result == pytest.approx(1.0)


def test_silent_miss_rate_empty_lists_raise() -> None:
    with pytest.raises(ValueError):
        silent_miss_rate([], [])


# --- retrieval_recall -------------------------------------------------------------------


def test_retrieval_recall_docstring_example() -> None:
    golds = [gold("a", articles=["A", "B"])]
    preds = [pred("a", retrieved=["A", "C", "D"])]

    result = retrieval_recall(preds, golds)

    assert result == pytest.approx(0.5)


def test_retrieval_recall_nothing_expected_is_one() -> None:
    golds = [gold("a", articles=[])]
    preds = [pred("a", retrieved=[])]

    result = retrieval_recall(preds, golds)

    assert result == pytest.approx(1.0)


def test_retrieval_recall_duplicates_count_once() -> None:
    golds = [gold("a", articles=["A", "B"])]
    preds = [pred("a", retrieved=["A", "A"])]

    result = retrieval_recall(preds, golds)

    assert result == pytest.approx(0.5)


def test_retrieval_recall_is_mean_over_cases() -> None:
    golds = [gold("a", articles=["A"]), gold("b", articles=["B"])]
    preds = [pred("a", retrieved=["A"]), pred("b", retrieved=[])]

    result = retrieval_recall(preds, golds)

    assert result == pytest.approx(0.5)


def test_retrieval_recall_ignores_cited_articles() -> None:
    golds = [gold("a", articles=["A"])]
    preds = [pred("a", cited=["A"], retrieved=[])]

    result = retrieval_recall(preds, golds)

    assert result == pytest.approx(0.0)


def test_retrieval_recall_empty_lists_raise() -> None:
    with pytest.raises(ValueError):
        retrieval_recall([], [])


# --- shared pairing rules ---------------------------------------------------------------

METRICS: list[MetricFn] = [
    class_accuracy,
    citation_precision,
    citation_recall,
    flag_recall,
    review_rate,
    silent_miss_rate,
    retrieval_recall,
]


def _golds() -> list[GoldenCase]:
    """Two cases that every metric can score (definite class, should_flag set)."""
    return [gold("a", articles=["A"], flag=True), gold("b", articles=["B"], flag=True)]


@pytest.mark.parametrize("metric", METRICS)
def test_predictions_in_different_order_match_by_id(metric: MetricFn) -> None:
    golds = [
        gold("a", RiskClass.HIGH_RISK, ["A"], flag=True),
        gold("b", RiskClass.MINIMAL, ["B"], flag=True),
    ]
    in_order = [
        pred("a", RiskClass.HIGH_RISK, ["A"], flagged=True, retrieved=["A"]),
        pred("b", RiskClass.MINIMAL, ["B"], flagged=True, retrieved=["B"]),
    ]

    result = metric(list(reversed(in_order)), golds)

    # Every prediction is right, so each metric has its best score: 1.0, except
    # silent_miss_rate, where lower is better and the best score is 0.0.
    best = 0.0 if metric is silent_miss_rate else 1.0
    assert result == pytest.approx(best)


@pytest.mark.parametrize("metric", METRICS)
def test_missing_prediction_raises(metric: MetricFn) -> None:
    preds = [pred("a")]

    with pytest.raises(ValueError):
        metric(preds, _golds())


@pytest.mark.parametrize("metric", METRICS)
def test_prediction_for_unknown_case_raises(metric: MetricFn) -> None:
    preds = [pred("a"), pred("b"), pred("zzz")]

    with pytest.raises(ValueError):
        metric(preds, _golds())


@pytest.mark.parametrize("metric", METRICS)
def test_duplicate_prediction_raises(metric: MetricFn) -> None:
    preds = [pred("a"), pred("a"), pred("b")]

    with pytest.raises(ValueError):
        metric(preds, _golds())
