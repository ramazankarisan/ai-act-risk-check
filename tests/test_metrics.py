"""Tests for evals.metrics. The docstrings in that module are the spec."""

from collections.abc import Callable, Sequence

import pytest

from evals.metrics import citation_precision, citation_recall, class_accuracy, flag_recall
from evals.schema import GoldenCase, Prediction, ReviewStatus, RiskClass

STUB = pytest.mark.xfail(
    raises=NotImplementedError, strict=True, reason="stub: not implemented yet"
)

MetricFn = Callable[[Sequence[Prediction], Sequence[GoldenCase]], float]


def gold(
    case_id: str,
    cls: RiskClass = RiskClass.HIGH_RISK,
    articles: Sequence[str] = (),
    flag: bool = False,
) -> GoldenCase:
    """Build a golden case with dummy text."""
    return GoldenCase(
        id=case_id,
        description="dummy description",
        expected_class=cls,
        expected_articles=list(articles),
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
) -> Prediction:
    """Build a prediction."""
    return Prediction(
        case_id=case_id, predicted_class=cls, cited_articles=list(cited), flagged=flagged
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


def test_citation_recall_empty_lists_raise() -> None:
    with pytest.raises(ValueError):
        citation_recall([], [])


# --- flag_recall ------------------------------------------------------------------------


@STUB
def test_flag_recall_docstring_example_three_of_four() -> None:
    golds = [gold(str(i), flag=True) for i in range(4)]
    preds = [pred(str(i), flagged=i < 3) for i in range(4)]

    result = flag_recall(preds, golds)

    assert result == pytest.approx(0.75)


@STUB
def test_flag_recall_flags_on_unflagged_cases_do_not_count() -> None:
    golds = [gold("a", flag=True), gold("b", flag=False)]
    preds = [pred("a", flagged=False), pred("b", flagged=True)]

    result = flag_recall(preds, golds)

    assert result == pytest.approx(0.0)


@STUB
def test_flag_recall_without_should_flag_case_raises() -> None:
    golds = [gold("a", flag=False)]
    preds = [pred("a", flagged=True)]

    with pytest.raises(ValueError):
        flag_recall(preds, golds)


@STUB
def test_flag_recall_all_flagged_is_one() -> None:
    golds = [gold("a", flag=True), gold("b", flag=True)]
    preds = [pred("a", flagged=True), pred("b", flagged=True)]

    result = flag_recall(preds, golds)

    assert result == pytest.approx(1.0)


# --- shared pairing rules ---------------------------------------------------------------

# Metrics that are still stubs carry the STUB mark, so only they are expected to fail.
METRICS = [
    pytest.param(class_accuracy, id="class_accuracy"),
    pytest.param(citation_precision, id="citation_precision"),
    pytest.param(citation_recall, id="citation_recall"),
    pytest.param(flag_recall, id="flag_recall", marks=STUB),
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
        pred("a", RiskClass.HIGH_RISK, ["A"], flagged=True),
        pred("b", RiskClass.MINIMAL, ["B"], flagged=True),
    ]

    result = metric(list(reversed(in_order)), golds)

    assert result == pytest.approx(1.0)


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
