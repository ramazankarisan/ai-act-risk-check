"""Baseline classifier: retrieve chunks, ask the LLM once, validate the answer.

No rules node and no graph yet. Depends only on the ports, so tests inject fakes and the
eval runner injects real adapters.
"""

from dataclasses import dataclass

from pydantic import BaseModel

from ai_act_check.corpus import Chunk
from ai_act_check.ports import LLMClient, Retriever, Usage
from ai_act_check.risk import RiskClass

SYSTEM_PROMPT = """\
You classify AI use cases under the EU AI Act (Regulation (EU) 2024/1689).

Choose exactly one risk_class:
- prohibited: a practice banned by Article 5.
- high_risk: a high-risk system under Article 6, for example an area listed in Annex III.
- transparency: no high risk, but a transparency duty under Article 50 applies.
- minimal: none of the above; only voluntary codes of conduct apply.
- unclear: the description supports more than one class and a human must decide.

Rules:
- Use only the context chunks given by the user. Do not rely on memory of the law.
- cited_chunk_ids: the ids of the chunks that justify your class, copied exactly from the
  context (for example "art-5-1-f"). Cite only ids that appear in the context.
- needs_review: true if you are uncertain or the case is borderline. It means uncertain,
  not severe: a clear prohibited practice has needs_review false.
- reasoning: two to four sentences explaining the class with reference to the cited chunks.
"""


class BaselineAnswer(BaseModel):
    """The structured answer the LLM must return."""

    risk_class: RiskClass
    cited_chunk_ids: list[str]
    needs_review: bool
    reasoning: str


@dataclass(frozen=True)
class BaselineResult:
    """One classification: the answer, the LLM usage and the chunks the LLM saw."""

    answer: BaselineAnswer
    usage: Usage
    retrieved_ids: list[str]


def format_chunk(chunk: Chunk) -> str:
    """Render one chunk for the prompt: its id in brackets, then title and text."""
    title = f" {chunk.title}:" if chunk.title else ""
    return f"[{chunk.chunk_id}]{title} {chunk.text}"


def build_user_prompt(description: str, chunks: list[Chunk]) -> str:
    """Combine the use-case description and the retrieved chunks into the user message."""
    context = "\n\n".join(format_chunk(chunk) for chunk in chunks)
    return f"Use case:\n{description}\n\nContext chunks:\n{context}"


def classify(
    description: str, llm: LLMClient, retriever: Retriever, top_k: int = 8
) -> BaselineResult:
    """Classify one use-case description with one retrieval and one LLM call."""
    chunks = retriever.search(description, top_k=top_k)
    user = build_user_prompt(description, chunks)
    answer, usage = llm.complete_json(SYSTEM_PROMPT, user, BaselineAnswer)
    return BaselineResult(
        answer=answer, usage=usage, retrieved_ids=[chunk.chunk_id for chunk in chunks]
    )
