"""Tests for the corpus parser: chunk ids, structure and text helpers."""

import json
import re
from pathlib import Path

import pytest

from ai_act_check.corpus import (
    RAW_HTML_PATH,
    SOURCE_URL,
    Chunk,
    clean_text,
    label_key,
    parse_regulation,
    write_jsonl,
)

SOURCE_VERSION = "OJ L, 2024/1689, 12.7.2024"


@pytest.fixture(scope="module")
def chunks() -> list[Chunk]:
    """Parse the committed raw regulation once per module."""
    return parse_regulation(RAW_HTML_PATH.read_bytes())


@pytest.fixture(scope="module")
def by_id(chunks: list[Chunk]) -> dict[str, Chunk]:
    """Index chunks by chunk_id."""
    return {chunk.chunk_id: chunk for chunk in chunks}


# --- Counts and uniqueness ----------------------------------------------------------------


def test_recital_count_is_180(chunks: list[Chunk]) -> None:
    recitals = {c.recital for c in chunks if c.kind == "recital"}

    assert len(recitals) == 180


def test_article_count_is_113(chunks: list[Chunk]) -> None:
    articles = {c.article for c in chunks if c.kind == "article"}

    assert len(articles) == 113


def test_annex_count_is_13(chunks: list[Chunk]) -> None:
    annexes = {c.annex for c in chunks if c.kind == "annex"}

    assert annexes == {
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI",
        "VII",
        "VIII",
        "IX",
        "X",
        "XI",
        "XII",
        "XIII",
    }


def test_chunk_ids_are_unique(chunks: list[Chunk]) -> None:
    ids = [c.chunk_id for c in chunks]

    assert len(ids) == len(set(ids))


def test_no_chunk_has_empty_text(chunks: list[Chunk]) -> None:
    empty = [c.chunk_id for c in chunks if not c.text.strip()]

    assert empty == []


def test_article_50_is_present(chunks: list[Chunk]) -> None:
    assert any(c.article == 50 for c in chunks)


# --- Metadata -----------------------------------------------------------------------------


def test_source_version_is_oj_reference(chunks: list[Chunk]) -> None:
    versions = {c.source_version for c in chunks}

    assert versions == {SOURCE_VERSION}


def test_source_url_has_celex_base_and_anchor(chunks: list[Chunk]) -> None:
    pattern = re.compile(r"#(rct|art|anx)_")

    bad = [
        c.chunk_id
        for c in chunks
        if not c.source_url.startswith(SOURCE_URL) or not pattern.search(c.source_url)
    ]

    assert bad == []


def test_article_chunks_have_chapter(chunks: list[Chunk]) -> None:
    missing = [c.chunk_id for c in chunks if c.kind == "article" and not c.chapter]

    assert missing == []


def test_article_5_has_chapter_ii_and_title(chunks: list[Chunk]) -> None:
    art5 = [c for c in chunks if c.article == 5]

    assert {c.chapter for c in art5} == {"II"}
    assert {c.title for c in art5} == {"Prohibited AI practices"}


# --- Article splitting --------------------------------------------------------------------


def test_art_5_1_points_are_a_to_h(chunks: list[Chunk]) -> None:
    points = {c.point for c in chunks if c.article == 5 and c.paragraph == 1 and c.point}

    assert points == set("abcdefgh")


def test_art_5_1_has_rest_chunk_without_point(by_id: dict[str, Chunk]) -> None:
    rest = by_id["art-5-1-rest"]

    assert rest.point is None


def test_art_5_1_rest_starts_with_point_h_reference(by_id: dict[str, Chunk]) -> None:
    assert by_id["art-5-1-rest"].text.startswith("Point (h) of the first subparagraph")


def test_art_5_1_f_keeps_lead_in(by_id: dict[str, Chunk]) -> None:
    text = by_id["art-5-1-f"].text

    assert text.startswith("1. The following AI practices shall be prohibited:")
    assert "(f)" in text
    assert "emotions" in text


def test_art_43_1_repeated_runs_get_subparagraph_ids(by_id: dict[str, Chunk]) -> None:
    assert by_id["art-43-1-sub1-a"].subparagraph == 1
    assert by_id["art-43-1-sub2-a"].subparagraph == 2


def test_art_3_split_by_point_uses_pt(by_id: dict[str, Chunk]) -> None:
    assert "‘AI system’" in by_id["art-3-pt-1"].text


def test_short_unnumbered_article_is_one_chunk(by_id: dict[str, Chunk]) -> None:
    assert "art-4" in by_id


def test_exponent_survives_in_art_51_2(by_id: dict[str, Chunk]) -> None:
    assert "10^25" in by_id["art-51-2"].text


# --- Recitals -----------------------------------------------------------------------------


def test_recital_text_has_no_printed_label(chunks: list[Chunk]) -> None:
    labelled = [c.chunk_id for c in chunks if c.kind == "recital" and re.match(r"\(\d+\)", c.text)]

    assert labelled == []


def test_footnote_marker_is_removed(by_id: dict[str, Chunk]) -> None:
    # Art. 78(1)(a) carries footnote marker "(57)" after "of the Council" in the OJ HTML.
    text = by_id["art-78-1"].text

    assert "2016/943 of the European Parliament and of the Council;" in text
    assert "(57)" not in text


# --- Annexes ------------------------------------------------------------------------------


def test_annex_iii_points_are_1_to_8(chunks: list[Chunk]) -> None:
    points = {c.point for c in chunks if c.annex == "III"}

    assert points == set("12345678")


def test_annex_iii_4_a_keeps_heading_lead_in(by_id: dict[str, Chunk]) -> None:
    text = by_id["anx-III-4-a"].text

    assert "4. Employment" in text
    assert "recruitment" in text


@pytest.mark.parametrize("chunk_id", ["anx-VIII-A-1", "anx-X-1-a", "anx-X-3"])
def test_annex_section_and_heading_ids_exist(by_id: dict[str, Chunk], chunk_id: str) -> None:
    assert chunk_id in by_id


def test_annex_ii_labels_are_synthetic(chunks: list[Chunk]) -> None:
    annex_ii = [c for c in chunks if c.annex == "II"]

    assert annex_ii
    assert all(c.synthetic_label for c in annex_ii)


def test_annex_iii_labels_are_not_synthetic(chunks: list[Chunk]) -> None:
    annex_iii = [c for c in chunks if c.annex == "III"]

    assert annex_iii
    assert not any(c.synthetic_label for c in annex_iii)


# --- Pure helpers -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "expected"),
    [("(a)", "a"), ("4.", "4"), ("3.1.", "3-1"), ("—", ""), ("", "")],
)
def test_label_key(label: str, expected: str) -> None:
    assert label_key(label) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10 ^25 .", "10^25."),
        ("( OJ L 157 )", "(OJ L 157)"),
        ("a\xa0b", "a b"),
    ],
)
def test_clean_text(raw: str, expected: str) -> None:
    assert clean_text(raw) == expected


# --- JSONL --------------------------------------------------------------------------------


def test_write_jsonl_round_trip(tmp_path: Path) -> None:
    source = [
        Chunk(
            chunk_id="rec-1",
            kind="recital",
            recital=1,
            text="Äpfel and pears.",
            source_url=f"{SOURCE_URL}#rct_1",
            source_version=SOURCE_VERSION,
        ),
        Chunk(
            chunk_id="art-4",
            kind="article",
            article=4,
            text="AI literacy.",
            source_url=f"{SOURCE_URL}#art_4",
            source_version=SOURCE_VERSION,
        ),
    ]
    target = tmp_path / "out" / "chunks.jsonl"

    count = write_jsonl(source, target)

    lines = target.read_text(encoding="utf-8").splitlines()
    assert count == len(lines) == 2
    assert [Chunk.model_validate(json.loads(line)) for line in lines] == source
