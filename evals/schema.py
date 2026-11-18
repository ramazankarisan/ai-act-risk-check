"""Golden-set schema: the expected answer for each eval case, the system's prediction, and a loader.

A golden case is one use-case description with its correct risk class, the chunk ids it
should cite, and whether a human should review it. The loader checks every cited chunk id
against the corpus, so a typo in the golden file fails fast instead of skewing a metric.
"""

import re
from collections.abc import Set
from enum import StrEnum
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ai_act_check.corpus import RAW_HTML_PATH, parse_regulation
from ai_act_check.risk import RiskClass

__all__ = ["GoldenCase", "Prediction", "ReviewStatus", "RiskClass", "load_golden"]

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
GOLDEN_V0_PATH = GOLDEN_DIR / "v0.yaml"

# Chunk ids written inside free text, e.g. "anx-III-4-a" in "anx-III-4-a; rec-53".
# Ids start with a number (rec-18, art-5-1-f) or a Roman numeral (anx-III-4-a), so words
# such as "art-based" are not mistaken for chunk ids.
_CHUNK_ID_IN_TEXT = re.compile(r"\b(?:rec-\d+|art-\d+|anx-[IVXL]+)(?:-[A-Za-z0-9]+)*\b")


class ReviewStatus(StrEnum):
    """Review state of a golden case: drafted, or reviewed by the maintainer."""

    DRAFT = "draft"  # not reviewed yet
    ACCEPTED = "accepted"  # reviewed, kept as drafted
    CHANGED = "changed"  # reviewed and edited


class GoldenCase(BaseModel):
    """One eval case with its expected outcome and the source that justifies it.

    Citations: `expected_articles` must be cited (citation recall counts them).
    `acceptable_articles` may be cited without penalty (citation precision allows
    expected plus acceptable). The two lists must not overlap.

    Flags: `should_flag` means the case is uncertain and needs a human decision. It does not
    mean severe: a clearly prohibited practice has `should_flag: False`.
    """

    model_config = ConfigDict(extra="forbid")  # a misspelled field name is an error

    id: str
    description: str
    expected_class: RiskClass
    expected_articles: list[str]  # corpus chunk ids that must be cited, e.g. "anx-III-4-a"
    # corpus chunk ids that may also be cited (correct, but not required)
    acceptable_articles: list[str] = Field(default_factory=list)
    should_flag: bool  # True if a human should review this case
    source: str  # chunk ids or a named Commission guideline that justify the label
    review_status: ReviewStatus
    notes: str


class Prediction(BaseModel):
    """What the system answered for one golden case; matched to it by `case_id`."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    predicted_class: RiskClass
    cited_articles: list[str] = Field(default_factory=list)  # corpus chunk ids
    # chunk ids the retriever returned for this case (what the LLM got to read)
    retrieved_articles: list[str] = Field(default_factory=list)
    flagged: bool


@cache  # parse the corpus once per process; later calls return the stored result
def corpus_chunk_ids(html_path: Path = RAW_HTML_PATH) -> frozenset[str]:
    """Return every chunk id in the corpus, parsed from the committed raw HTML."""
    return frozenset(chunk.chunk_id for chunk in parse_regulation(html_path.read_bytes()))


def load_golden(path: Path = GOLDEN_V0_PATH, chunk_ids: Set[str] | None = None) -> list[GoldenCase]:
    """Load and validate a golden-set YAML file.

    The file has a top-level `cases:` list. Raises `ValueError` if the file has no case list,
    if two cases share an id, if a case has an empty source, if a chunk id is both expected
    and acceptable, or if a case names a chunk id (in `expected_articles`,
    `acceptable_articles` or `source`) that is not in the corpus.
    Pass `chunk_ids` to check against a known set instead of parsing the corpus.
    """
    cases = read_cases(path)
    check_unique_ids(cases)
    check_sources(cases)
    check_no_overlap(cases)
    check_chunk_ids(cases, corpus_chunk_ids() if chunk_ids is None else chunk_ids)
    return cases


def read_cases(path: Path) -> list[GoldenCase]:
    """Parse the YAML file and validate each entry of its `cases:` list as a GoldenCase."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError(f"{path}: expected a top-level 'cases:' list")
    return [GoldenCase.model_validate(raw) for raw in data["cases"]]


def check_unique_ids(cases: list[GoldenCase]) -> None:
    """Raise `ValueError` if two cases share an id."""
    ids = [case.id for case in cases]
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate case ids: {duplicates}")


def check_sources(cases: list[GoldenCase]) -> None:
    """Raise `ValueError` if a case has an empty source: no label without a source."""
    no_source = [case.id for case in cases if not case.source.strip()]
    if no_source:
        raise ValueError(f"cases without a source: {no_source}")


def check_no_overlap(cases: list[GoldenCase]) -> None:
    """Raise `ValueError` if a chunk id is listed as both expected and acceptable."""
    overlap: dict[str, list[str]] = {}
    for case in cases:
        both = sorted(set(case.expected_articles) & set(case.acceptable_articles))
        if both:
            overlap[case.id] = both
    if overlap:
        raise ValueError(f"chunk ids both expected and acceptable per case: {overlap}")


def check_chunk_ids(cases: list[GoldenCase], known: Set[str]) -> None:
    """Raise `ValueError` if a case names a chunk id that is not in `known`."""
    unknown: dict[str, list[str]] = {}
    for case in cases:
        named = (
            set(case.expected_articles)
            | set(case.acceptable_articles)
            | set(_CHUNK_ID_IN_TEXT.findall(case.source))
        )
        missing = sorted(named - known)
        if missing:
            unknown[case.id] = missing
    if unknown:
        raise ValueError(f"unknown chunk ids per case: {unknown}")
