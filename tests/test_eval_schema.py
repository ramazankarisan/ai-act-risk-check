"""Tests for evals.schema: golden-set loading and validation."""

from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.schema import GoldenCase, Prediction, ReviewStatus, RiskClass, load_golden

CHUNK_IDS = {"art-5-1-c", "anx-III-4-a", "art-4"}

VALID_YAML = """\
cases:
  - id: case-1
    description: A social scoring system.
    expected_class: prohibited
    expected_articles: [art-5-1-c]
    should_flag: false
    source: art-5-1-c
    review_status: draft
    notes: dummy
  - id: case-2
    description: A CV screening tool.
    expected_class: high_risk
    expected_articles: [anx-III-4-a]
    should_flag: true
    source: anx-III-4-a
    review_status: accepted
    notes: dummy
"""


def _case_yaml(
    case_id: str = "case-1",
    expected_class: str = "minimal",
    articles: str = "[]",
    acceptable: str | None = None,
    extra: str = "",
    source: str = "Commission guidelines",
    review_status: str = "draft",
) -> str:
    acceptable_line = "" if acceptable is None else f"    acceptable_articles: {acceptable}\n"
    return (
        "cases:\n"
        f"  - id: {case_id}\n"
        "    description: d\n"
        f"    expected_class: {expected_class}\n"
        f"    expected_articles: {articles}\n"
        f"{acceptable_line}"
        "    should_flag: false\n"
        f"    source: {source}\n"
        f"    review_status: {review_status}\n"
        "    notes: n\n"
        f"{extra}"
    )


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "golden.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_golden_loads_committed_v0_file() -> None:
    cases = load_golden()

    assert len(cases) >= 1
    assert len({case.id for case in cases}) == len(cases)


def test_load_golden_valid_file_returns_cases(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID_YAML)

    cases = load_golden(path, chunk_ids=CHUNK_IDS)

    assert [case.id for case in cases] == ["case-1", "case-2"]
    assert all(isinstance(case, GoldenCase) for case in cases)


def test_load_golden_parses_risk_class_values(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID_YAML)

    cases = load_golden(path, chunk_ids=CHUNK_IDS)

    assert cases[0].expected_class is RiskClass.PROHIBITED
    assert cases[1].expected_class is RiskClass.HIGH_RISK


def test_load_golden_unknown_chunk_id_raises_with_case_and_chunk(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(case_id="case-bad", articles="[art-nope]"))

    with pytest.raises(ValueError) as excinfo:
        load_golden(path, chunk_ids=CHUNK_IDS)

    assert "case-bad" in str(excinfo.value)
    assert "art-nope" in str(excinfo.value)


def test_load_golden_duplicate_case_ids_raise(tmp_path: Path) -> None:
    text = _case_yaml(case_id="dup") + _case_yaml(case_id="dup").removeprefix("cases:\n")
    path = _write(tmp_path, text)

    with pytest.raises(ValueError, match="dup"):
        load_golden(path, chunk_ids=CHUNK_IDS)


def test_load_golden_missing_cases_key_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, "other: []\n")

    with pytest.raises(ValueError, match="cases"):
        load_golden(path, chunk_ids=CHUNK_IDS)


def test_load_golden_invalid_expected_class_raises_validation_error(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(expected_class="high"))

    with pytest.raises(ValidationError):
        load_golden(path, chunk_ids=CHUNK_IDS)


def test_load_golden_extra_field_raises_validation_error(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(extra="    surprise: 1\n"))

    with pytest.raises(ValidationError):
        load_golden(path, chunk_ids=CHUNK_IDS)


@pytest.mark.parametrize("source", ['""', '"   "'])
def test_load_golden_empty_source_raises_with_case_id(tmp_path: Path, source: str) -> None:
    path = _write(tmp_path, _case_yaml(case_id="case-nosrc", source=source))

    with pytest.raises(ValueError, match="case-nosrc"):
        load_golden(path, chunk_ids=CHUNK_IDS)


def test_load_golden_unknown_chunk_id_in_source_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(case_id="case-src", source="art-999-1"))

    with pytest.raises(ValueError) as excinfo:
        load_golden(path, chunk_ids=CHUNK_IDS)

    assert "case-src" in str(excinfo.value)
    assert "art-999-1" in str(excinfo.value)


def test_load_golden_known_chunk_id_with_free_text_in_source_passes(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(source="art-5-1-c; Commission guidelines"))

    cases = load_golden(path, chunk_ids=CHUNK_IDS)

    assert len(cases) == 1


def test_load_golden_free_text_source_without_chunk_ids_passes(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(source="Commission guidelines on prohibited AI practices"))

    cases = load_golden(path, chunk_ids=CHUNK_IDS)

    assert cases[0].source == "Commission guidelines on prohibited AI practices"


def test_load_golden_invalid_review_status_raises_validation_error(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(review_status="approved"))

    with pytest.raises(ValidationError):
        load_golden(path, chunk_ids=CHUNK_IDS)


def test_load_golden_parses_review_status_values(tmp_path: Path) -> None:
    path = _write(tmp_path, VALID_YAML)

    cases = load_golden(path, chunk_ids=CHUNK_IDS)

    assert cases[0].review_status is ReviewStatus.DRAFT
    assert cases[1].review_status is ReviewStatus.ACCEPTED


def test_committed_v0_has_twelve_cases() -> None:
    cases = load_golden()

    assert len(cases) == 12


def test_committed_v0_class_counts() -> None:
    cases = load_golden()

    counts = Counter(case.expected_class for case in cases)

    assert counts == {
        RiskClass.PROHIBITED: 3,
        RiskClass.HIGH_RISK: 3,
        RiskClass.TRANSPARENCY: 2,
        RiskClass.MINIMAL: 2,
        RiskClass.UNCLEAR: 2,
    }


def test_committed_v0_every_case_has_a_source() -> None:
    cases = load_golden()

    assert all(case.source.strip() for case in cases)


def test_committed_v0_unclear_cases_are_flagged() -> None:
    cases = load_golden()

    unclear = [case for case in cases if case.expected_class is RiskClass.UNCLEAR]

    assert unclear
    assert all(case.should_flag for case in unclear)


def test_load_golden_omitted_acceptable_articles_defaults_to_empty_list(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml())

    cases = load_golden(path, chunk_ids=CHUNK_IDS)

    assert cases[0].acceptable_articles == []


def test_load_golden_parses_acceptable_articles(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(articles="[art-5-1-c]", acceptable="[art-4]"))

    cases = load_golden(path, chunk_ids=CHUNK_IDS)

    assert cases[0].acceptable_articles == ["art-4"]


def test_load_golden_id_both_expected_and_acceptable_raises(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        _case_yaml(case_id="case-overlap", articles="[art-4]", acceptable="[art-4]"),
    )

    with pytest.raises(ValueError) as excinfo:
        load_golden(path, chunk_ids=CHUNK_IDS)

    assert "case-overlap" in str(excinfo.value)
    assert "art-4" in str(excinfo.value)


def test_load_golden_unknown_acceptable_chunk_id_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, _case_yaml(case_id="case-acc", acceptable="[art-nope]"))

    with pytest.raises(ValueError) as excinfo:
        load_golden(path, chunk_ids=CHUNK_IDS)

    assert "case-acc" in str(excinfo.value)
    assert "art-nope" in str(excinfo.value)


def test_committed_v0_acceptable_articles() -> None:
    cases = load_golden()

    acceptable = {case.id: case.acceptable_articles for case in cases if case.acceptable_articles}

    assert acceptable == {
        "prohibited-003": ["art-3-pt-39"],
        "unclear-002": ["art-50-3"],
        "minimal-001": ["art-4"],
        "minimal-002": ["art-4"],
    }


def test_prediction_cited_articles_defaults_to_empty_list() -> None:
    prediction = Prediction(case_id="a", predicted_class=RiskClass.MINIMAL, flagged=False)

    assert prediction.cited_articles == []
