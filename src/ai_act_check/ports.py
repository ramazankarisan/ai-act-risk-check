"""Ports: the small interfaces the core depends on. Adapters implement them.

The core never imports a vendor SDK. It asks for "something that can complete JSON" or
"something that can search chunks", and the caller passes in a concrete adapter.
"""

from typing import Protocol

from pydantic import BaseModel

from ai_act_check.corpus import Chunk


class Usage(BaseModel):
    """Cost and speed of one LLM call."""

    model: str  # model id reported by the provider
    input_tokens: int
    output_tokens: int
    latency_ms: float


class LLMClient(Protocol):
    """Anything that turns a prompt into a validated pydantic object."""

    # `[T: BaseModel]` is a type parameter: whatever schema class you pass in,
    # you get an instance of that same class back.
    def complete_json[T: BaseModel](
        self, system: str, user: str, schema: type[T]
    ) -> tuple[T, Usage]:
        """Send the prompt and return the answer parsed as `schema`, plus usage."""
        ...


class Retriever(Protocol):
    """Anything that finds the corpus chunks most relevant to a query."""

    def search(self, query: str, top_k: int = 8) -> list[Chunk]:
        """Return up to `top_k` chunks, best match first."""
        ...
