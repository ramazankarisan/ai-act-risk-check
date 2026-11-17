"""Parse the EU AI Act (Regulation (EU) 2024/1689) OJ HTML into citable chunks.

Chunking rules:
- Recitals: one chunk each (`rec-27`).
- Articles: one chunk per numbered paragraph (`art-5-2`). A paragraph longer than
  `MAX_PARAGRAPH_CHARS` that contains points is split by point (`art-5-1-f`); each point
  chunk starts with the paragraph's lead-in text so it stays understandable on its own.
  Text after the last point becomes its own chunk (`art-5-1-rest`). Articles without
  numbered paragraphs use `pt` to mark points (`art-3-pt-12`) or are one chunk (`art-4`).
- Annexes: one chunk per point; points with sub-points are split by sub-point
  (`anx-III-4-a`). Annex sections and numbered headings become part of the id
  (`anx-VIII-A-1`, `anx-X-1-a`). Unlabelled items get a position number and
  `synthetic_label=True`, because that number is not a legal label.
"""

import json
import re
import warnings
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning
from pydantic import BaseModel

CELEX_ID = "32024R1689"
SOURCE_URL = f"https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{CELEX_ID}"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_HTML_PATH = PROJECT_ROOT / "data" / "raw" / "ai_act_en.html"
CHUNKS_PATH = PROJECT_ROOT / "data" / "corpus" / "ai_act_chunks.jsonl"
MAX_PARAGRAPH_CHARS = 1500

ChunkKind = Literal["recital", "article", "annex"]

_PARAGRAPH_ID = re.compile(r"^\d{3}\.\d{3}$")
_SECTION_HEADING = re.compile(r"^Section\s+([A-Z0-9]+)\b")
_NUMBERED_HEADING = re.compile(r"^(\d+)\.\s")
_NUMBERED_ITEM = re.compile(r"^(\d+(?:\.\d+)*\.)\s+(.*)$", re.DOTALL)


class Chunk(BaseModel):
    """One citable unit of the regulation, with enough metadata to cite and verify it."""

    chunk_id: str
    kind: ChunkKind
    recital: int | None = None
    article: int | None = None
    annex: str | None = None  # Roman numeral, e.g. "III"
    section: str | None = None  # annex section, e.g. "A" in Annex VIII
    paragraph: int | None = None
    subparagraph: int | None = None  # set only when a paragraph has several runs of points
    point: str | None = None  # e.g. "f" in Art. 5(1)(f), "4" in Annex III point 4
    subpoint: str | None = None  # e.g. "a" in Annex III point 4(a)
    synthetic_label: bool = False  # True if point/subpoint is a position, not a legal label
    title: str | None = None
    chapter: str | None = None  # Roman numeral, e.g. "II"
    text: str
    source_url: str
    source_version: str


# --- Text helpers -------------------------------------------------------------------------


def clean_text(text: str) -> str:
    """Normalise whitespace: no non-breaking spaces, single spaces, none before punctuation.

    Joining inline elements with spaces leaves gaps such as "10 ^25 ." or "( OJ L 157";
    the last two substitutions remove them.
    """
    text = re.sub(r"\s+", " ", text.replace("\xa0", " "))
    text = re.sub(r"\s+([.,;:)\]^])", r"\1", text)  # "10 ^25 ." -> "10^25."
    text = re.sub(r"([(\[])\s+", r"\1", text)  # "( OJ" -> "(OJ"
    return text.strip()


def element_text(element: Tag) -> str:
    """Return the cleaned visible text of an element, words separated by single spaces."""
    return clean_text(element.get_text(" "))


def label_key(label: str) -> str:
    """Turn a printed label into an id part: "(a)" -> "a", "4." -> "4", "3.1." -> "3-1".

    Returns "" for a missing label or a dash, meaning the item has no legal label.
    """
    key = label.strip().strip("()").rstrip(".")
    if key in {"", "—", "-", "–"}:
        return ""
    return key.replace(".", "-")


def point_table(element: Tag) -> tuple[str, Tag] | None:
    """Split a point table into (printed label, content cell); None if it is not one.

    The OJ prints each point as a one-row table: [label, content], or
    [empty indent, label, content] in some annexes.
    """
    if element.name != "table":
        return None
    body = element.find("tbody", recursive=False) or element
    row = body.find("tr", recursive=False) if isinstance(body, Tag) else None
    if not isinstance(row, Tag):
        return None
    cells = row.find_all("td", recursive=False)
    if len(cells) < 2:
        return None
    return element_text(cells[-2]), cells[-1]


def child_tags(element: Tag) -> list[Tag]:
    """Return the direct child elements, skipping text nodes."""
    return [child for child in element.children if isinstance(child, Tag)]


def join_blocks(parts: Iterable[str]) -> str:
    """Join non-empty text blocks with newlines."""
    return "\n".join(part for part in parts if part)


def has_class(element: Tag, css_class: str) -> bool:
    """True if the element carries the given CSS class."""
    return css_class in (element.get("class") or [])


# --- Document loading ---------------------------------------------------------------------


def load_document(html: bytes) -> BeautifulSoup:
    """Parse the OJ XHTML and remove footnotes, keeping exponents such as 10^25 readable."""
    with warnings.catch_warnings():
        # The OJ file is XHTML; the forgiving HTML parser handles it fine.
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "lxml")

    for footnote_ref in soup.select('a[href^="#ntr"]'):
        footnote_ref.decompose()
    for footnote in soup.select("p.oj-note"):
        footnote.decompose()
    for superscript in soup.select("span.oj-super"):
        superscript.replace_with(f"^{superscript.get_text()}")
    soup.smooth()  # merge the adjacent text pieces created by the replacements
    return soup


def source_version(soup: BeautifulSoup) -> str:
    """Read the publication reference from the OJ header, e.g. "OJ L, 2024/1689, 12.7.2024"."""

    def header(css_class: str) -> str:
        element = soup.select_one(f"p.{css_class}")
        if element is None:
            raise ValueError(f"OJ header field {css_class!r} not found")
        return element_text(element)

    series = header("oj-hd-coll").split()[0]  # "L series" -> "L"
    return f"OJ {series}, {header('oj-hd-uniq')}, {header('oj-hd-date')}"


# --- Splitting a block list by point ------------------------------------------------------


@dataclass
class PointPart:
    """One piece of a block list split by point: a labelled point or the trailing text."""

    key: str | None  # label key; "" = unlabelled point; None = text after the last point
    lead_in: str
    text: str
    run: int  # 1 for the first run of consecutive points, 2 for the next run, ...
    subparagraph: int  # number of text blocks (subparagraphs) seen up to this point


def split_by_point(blocks: list[Tag]) -> Iterator[PointPart]:
    """Split blocks into one part per point table, each carrying the lead-in text before it.

    A run of non-table blocks right before point tables is their lead-in. Text after the
    last point is yielded as a part with `key=None`.
    """
    lead_in: list[str] = []
    after_points = False
    run = 0
    text_blocks = 0
    for block in blocks:
        cells = point_table(block)
        if cells is None:
            if after_points:  # text after a run of points starts a new lead-in
                lead_in, after_points = [], False
            lead_in.append(element_text(block))
            text_blocks += 1
            continue
        if not after_points:
            run += 1
        after_points = True
        label, content = cells
        text = f"{label} {element_text(content)}"
        yield PointPart(label_key(label), join_blocks(lead_in), text, run, text_blocks)
    if lead_in and not after_points:
        yield PointPart(None, "", join_blocks(lead_in), run, text_blocks)


def part_id(part: PointPart, position: int) -> tuple[str, bool]:
    """Return (id part, synthetic?) for a split part: its label, its position, or "rest"."""
    if part.key is None:
        return "rest", False
    if part.key == "":
        return str(position), True
    return part.key, False


# --- Recitals -----------------------------------------------------------------------------


def parse_recitals(soup: BeautifulSoup, version: str) -> list[Chunk]:
    """Create one chunk per recital (`rec-N`), without the printed "(N)" label."""
    chunks = []
    for recital in soup.find_all("div", id=re.compile(r"^rct_\d+$")):
        number = int(str(recital["id"]).removeprefix("rct_"))
        table = recital.find("table")
        cells = point_table(table) if isinstance(table, Tag) else None
        text = element_text(cells[1]) if cells else element_text(recital)
        chunks.append(
            Chunk(
                chunk_id=f"rec-{number}",
                kind="recital",
                recital=number,
                text=text,
                source_url=f"{SOURCE_URL}#rct_{number}",
                source_version=version,
            )
        )
    return chunks


# --- Articles -----------------------------------------------------------------------------


def article_chapter(article: Tag) -> str | None:
    """Return the Roman numeral of the chapter that contains the article."""
    for parent in article.parents:
        match = re.fullmatch(r"cpt_([IVXL]+)", str(parent.get("id", "")))
        if match:
            return match.group(1)
    return None


def article_unit_chunks(blocks: list[Tag], chunk_id: str, base: dict[str, Any]) -> list[Chunk]:
    """Chunk one paragraph (or an unnumbered article body): whole, or by point if too long."""
    whole = join_blocks(element_text(block) for block in blocks)
    has_points = any(point_table(block) for block in blocks)
    if len(whole) <= MAX_PARAGRAPH_CHARS or not has_points:
        return [Chunk.model_validate({**base, "chunk_id": chunk_id, "text": whole})]

    parts = list(split_by_point(blocks))
    # Several runs of points (e.g. Art. 43(1) has (a)-(b), then (a)-(d)) would repeat labels,
    # so the id then names the subparagraph: art-43-1-sub2-a.
    several_runs = len({part.run for part in parts if part.key is not None}) > 1

    chunks = []
    for position, part in enumerate(parts, start=1):
        id_part, synthetic = part_id(part, position)
        subparagraph = part.subparagraph if several_runs and part.key is not None else None
        prefix = f"{chunk_id}-sub{subparagraph}" if subparagraph else chunk_id
        chunks.append(
            Chunk.model_validate(
                {
                    **base,
                    "chunk_id": f"{prefix}-{id_part}",
                    "subparagraph": subparagraph,
                    "point": None if part.key is None else id_part,
                    "synthetic_label": synthetic,
                    "text": join_blocks([part.lead_in, part.text]),
                }
            )
        )
    return chunks


def parse_article(article: Tag, version: str) -> list[Chunk]:
    """Create the chunks for one article (`art_N` element)."""
    number = int(str(article["id"]).removeprefix("art_"))
    title = article.find(id=f"art_{number}.tit_1")
    base: dict[str, Any] = {
        "kind": "article",
        "article": number,
        "title": element_text(title) if isinstance(title, Tag) else None,
        "chapter": article_chapter(article),
        "source_url": f"{SOURCE_URL}#art_{number}",
        "source_version": version,
    }

    children = child_tags(article)
    paragraphs = [c for c in children if _PARAGRAPH_ID.match(str(c.get("id", "")))]
    if not paragraphs:
        # No numbered paragraphs: the body is everything except the heading and the title.
        # If it gets split by point, "pt" keeps "art-3-pt-12" apart from paragraph ids.
        body = [c for c in children if not has_class(c, "oj-ti-art") and c is not title]
        chunks = article_unit_chunks(body, f"art-{number}-pt", base)
        if len(chunks) == 1:
            chunks[0].chunk_id = f"art-{number}"
        return chunks

    chunks = []
    for paragraph in paragraphs:
        paragraph_number = int(str(paragraph["id"]).split(".")[1])
        chunks += article_unit_chunks(
            child_tags(paragraph),
            f"art-{number}-{paragraph_number}",
            {**base, "paragraph": paragraph_number},
        )
    return chunks


def parse_articles(soup: BeautifulSoup, version: str) -> list[Chunk]:
    """Create the chunks for all articles."""
    chunks = []
    for article in soup.find_all("div", id=re.compile(r"^art_\d+$")):
        chunks += parse_article(article, version)
    return chunks


# --- Annexes ------------------------------------------------------------------------------


@dataclass
class AnnexState:
    """Where the annex walk currently is: section, numbered heading and the text before items."""

    section: str | None = None
    heading: str | None = None  # number of the current numbered heading, e.g. "1" in Annex X
    heading_text: str = ""
    intro: list[str] = field(default_factory=list)
    heading_body: list[str] = field(default_factory=list)  # text under a heading, no items
    heading_has_items: bool = False
    position: int = 0  # counter for unlabelled items


def annex_title(annex: Tag) -> str | None:
    """Return the annex title, e.g. "High-risk AI systems referred to in Article 6(2)"."""
    titles = [element_text(p) for p in annex.find_all("p", class_="oj-doc-ti", recursive=False)]
    return " ".join(titles[1:]) or None


class AnnexParser:
    """Walk the top-level blocks of one annex and emit one chunk per point or sub-point."""

    def __init__(self, annex: Tag, version: str) -> None:
        """Prepare a parser for one `anx_R` element."""
        self.numeral = str(annex["id"]).removeprefix("anx_")
        self.annex = annex
        self.base: dict[str, Any] = {
            "kind": "annex",
            "annex": self.numeral,
            "title": annex_title(annex),
            "source_url": f"{SOURCE_URL}#anx_{self.numeral}",
            "source_version": version,
        }
        self.state = AnnexState()
        self.chunks: list[Chunk] = []

    def parse(self) -> list[Chunk]:
        """Return all chunks of the annex."""
        for block in child_tags(self.annex):
            if has_class(block, "oj-doc-ti"):
                continue
            cells = point_table(block)
            if has_class(block, "oj-ti-grseq-1"):
                self.on_heading(element_text(block))
            elif cells is not None:
                self.on_item(cells[0], cells[1])
            elif has_class(block, "oj-enumeration-spacing"):
                self.on_enumerated_div(block)
            else:
                self.on_text(element_text(block))
        self.flush_heading()
        if not self.chunks:  # an annex without items becomes one chunk
            self.emit(None, None, False, join_blocks(self.state.intro))
        return self.chunks

    # Event handlers ------------------------------------------------------------------------

    def on_heading(self, text: str) -> None:
        """Handle a section heading, a numbered heading or a plain sub-heading."""
        self.flush_heading()
        section = _SECTION_HEADING.match(text)
        numbered = _NUMBERED_HEADING.match(text)
        if section:
            self.state = AnnexState(section=section.group(1), intro=[text])
        elif numbered:
            self.state.heading = numbered.group(1)
            self.state.heading_text = text
            self.state.heading_body = []
            self.state.heading_has_items = False
            self.state.position = 0
        else:
            self.state.intro.append(text)

    def on_text(self, text: str) -> None:
        """Handle a plain text block: body of a numbered heading, or intro text."""
        if self.state.heading is not None and not self.state.heading_has_items:
            self.state.heading_body.append(text)
        else:
            self.state.intro.append(text)

    def on_enumerated_div(self, block: Tag) -> None:
        """Handle a numbered paragraph written as a div ("1. The provider ..."), as in Annex VI."""
        text = element_text(block)
        match = _NUMBERED_ITEM.match(text)
        if match:
            self.on_item(match.group(1), None, text)
        else:
            self.on_text(text)

    def on_item(self, label: str, content: Tag | None, full_text: str | None = None) -> None:
        """Handle one point: split it by sub-point if it has any, else emit it whole."""
        self.state.heading_has_items = self.state.heading is not None
        self.state.position += 1
        point, synthetic = self.point_id(label)
        lead_in = join_blocks([*self.state.intro, self.state.heading_text])

        if content is None:  # enumerated div: the label is already part of the text
            self.emit(point, None, synthetic, join_blocks([lead_in, full_text or ""]))
            return

        blocks = child_tags(content)
        if any(point_table(block) for block in blocks):
            self.emit_subpoints(point, synthetic, label, lead_in, blocks)
        else:
            text = join_blocks([lead_in, f"{label} {element_text(content)}"])
            self.emit(point, None, synthetic, text)

    def point_id(self, label: str) -> tuple[str, bool]:
        """Return (point id, synthetic?), prefixed with the current numbered heading if any.

        Annex X restarts "(a)" under each heading, so "(a)" under heading 1 becomes "1-a".
        Labels such as "3.1." in Annex VII already start with the heading number.
        """
        key = label_key(label)
        synthetic = key == ""
        point = str(self.state.position) if synthetic else key
        heading = self.state.heading
        if heading and not point.startswith(f"{heading}-"):
            point = f"{heading}-{point}"
        return point, synthetic

    def emit_subpoints(
        self, point: str, synthetic: bool, label: str, lead_in: str, blocks: list[Tag]
    ) -> None:
        """Emit one chunk per sub-point, each starting with the annex and point lead-in."""
        for position, part in enumerate(split_by_point(blocks), start=1):
            sub_id, sub_synthetic = part_id(part, position)
            point_lead = f"{label} {part.lead_in}".strip()
            text = join_blocks([lead_in, point_lead, part.text])
            self.emit(point, sub_id, synthetic or sub_synthetic, text)

    def flush_heading(self) -> None:
        """Emit a numbered heading that had text but no items (e.g. Annex X point 3) as a point."""
        state = self.state
        if state.heading is not None and not state.heading_has_items and state.heading_body:
            text = join_blocks([*state.intro, state.heading_text, *state.heading_body])
            self.emit(state.heading, None, False, text)
        state.heading_body = []

    # Output --------------------------------------------------------------------------------

    def emit(self, point: str | None, subpoint: str | None, synthetic: bool, text: str) -> None:
        """Append one annex chunk; the id is built from annex, section, point and sub-point."""
        parts = [f"anx-{self.numeral}", self.state.section, point, subpoint]
        self.chunks.append(
            Chunk.model_validate(
                {
                    **self.base,
                    "chunk_id": "-".join(part for part in parts if part),
                    "section": self.state.section,
                    "point": point,
                    "subpoint": subpoint,
                    "synthetic_label": synthetic,
                    "text": text,
                }
            )
        )


def parse_annexes(soup: BeautifulSoup, version: str) -> list[Chunk]:
    """Create the chunks for all annexes."""
    chunks = []
    for annex in soup.find_all("div", id=re.compile(r"^anx_[IVXL]+$")):
        chunks += AnnexParser(annex, version).parse()
    return chunks


# --- Public entry points ------------------------------------------------------------------


def parse_regulation(html: bytes) -> list[Chunk]:
    """Parse the full OJ HTML into recital, article and annex chunks, in document order."""
    soup = load_document(html)
    version = source_version(soup)
    return [
        *parse_recitals(soup, version),
        *parse_articles(soup, version),
        *parse_annexes(soup, version),
    ]


def write_jsonl(chunks: Iterable[Chunk], path: Path) -> int:
    """Write chunks as JSON Lines (one chunk per line) and return how many were written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n")
            count += 1
    return count


def build_corpus(source: Path = RAW_HTML_PATH, target: Path = CHUNKS_PATH) -> int:
    """Parse the raw regulation HTML and write the chunk file; return the number of chunks."""
    return write_jsonl(parse_regulation(source.read_bytes()), target)


if __name__ == "__main__":
    print(f"Wrote {build_corpus():,} chunks to {CHUNKS_PATH}")
