"""Eval metrics: compare predictions with the golden set.

Shared rules for every metric:
- Predictions and golden cases are matched by `Prediction.case_id == GoldenCase.id`.
- Every golden case needs exactly one prediction, and every prediction must belong to a
  golden case. Otherwise the metric raises `ValueError`.
- Each metric returns a float between 0.0 and 1.0.
- If there is nothing to score, the metric raises `ValueError` instead of returning a
  number, because any number would be misleading.
"""

from collections.abc import Sequence

from evals.schema import GoldenCase, Prediction, RiskClass


def _pair_up(
    preds: Sequence[Prediction], golds: Sequence[GoldenCase]
) -> list[tuple[GoldenCase, Prediction]]:
    """Match each golden case with its prediction by case id, in golden-set order.

    Raises `ValueError` if two predictions share a case id, if a golden case has no
    prediction, or if a prediction belongs to no golden case.
    """
    by_id: dict[str, Prediction] = {}
    for pred in preds:
        if pred.case_id in by_id:
            raise ValueError(f"duplicate prediction for case {pred.case_id!r}")
        by_id[pred.case_id] = pred

    gold_ids = {gold.id for gold in golds}
    missing = sorted(gold_ids - by_id.keys())
    if missing:
        raise ValueError(f"golden cases without a prediction: {missing}")
    unknown = sorted(by_id.keys() - gold_ids)
    if unknown:
        raise ValueError(f"predictions for unknown cases: {unknown}")

    return [(gold, by_id[gold.id]) for gold in golds]


def class_accuracy(
    preds: Sequence[Prediction], golds: Sequence[GoldenCase], exclude_unclear: bool = True
) -> float:
    """Share of cases whose predicted risk class equals the expected class.

    With `exclude_unclear=True`, cases whose expected class is `unclear` are skipped.
    A prediction of `unclear` for a case with a definite expected class counts as wrong.
    Raises `ValueError` if no case is left to score.

    Example: expected [high_risk, minimal, unclear], predicted [high_risk, unclear, unclear]
    -> 1/2 = 0.5 with exclude_unclear=True, 2/3 with exclude_unclear=False.
    """
    pairs = _pair_up(preds, golds)
    if exclude_unclear:
        pairs = [(gold, pred) for gold, pred in pairs if gold.expected_class != RiskClass.UNCLEAR]
    if not pairs:
        raise ValueError("no case left to score")

    correct = 0
    for gold, pred in pairs:
        if pred.predicted_class == gold.expected_class:
            correct += 1
    return correct / len(pairs)


def citation_precision(preds: Sequence[Prediction], golds: Sequence[GoldenCase]) -> float:
    """Mean per-case share of cited chunk ids that are expected: "no wrong citations".

    Per case, cited and expected ids are compared as sets (duplicates count once):
    - cited empty, expected empty     -> 1.0
    - cited empty, expected not empty -> 0.0
    - otherwise                       -> |cited & expected| / |cited|
    The result is the average over all cases. Raises `ValueError` for an empty case list.

    Example: expected {A, B}, cited {A, C} -> 1/2 = 0.5.
    """
    # TODO(ramazan): implement
    raise NotImplementedError


def citation_recall(preds: Sequence[Prediction], golds: Sequence[GoldenCase]) -> float:
    """Mean per-case share of expected chunk ids that were cited: "nothing missed".

    Per case, cited and expected ids are compared as sets (duplicates count once):
    - expected empty -> 1.0 (nothing to find)
    - otherwise      -> |cited & expected| / |expected|
    The result is the average over all cases. Raises `ValueError` for an empty case list.

    Example: expected {A, B}, cited {A, C} -> 1/2 = 0.5.
    """
    pairs = _pair_up(preds, golds)
    if not pairs:
        raise ValueError("no case to score")

    total = 0.0
    for gold, pred in pairs:
        expected = set(gold.expected_articles)
        cited = set(pred.cited_articles)
        if not expected:
            total += 1.0  # nothing to find, so nothing was missed
        else:
            total += len(cited & expected) / len(expected)
    return total / len(pairs)


def flag_recall(preds: Sequence[Prediction], golds: Sequence[GoldenCase]) -> float:
    """Share of cases that should be flagged for human review and were flagged.

    Only cases with `should_flag=True` count; flags on other cases do not change the score.
    Raises `ValueError` if no case has `should_flag=True`.

    Example: 4 cases should be flagged, the system flagged 3 of them -> 0.75.
    """
    # TODO(ramazan): implement
    raise NotImplementedError
