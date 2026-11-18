"""Tests for the Foundry LLM adapter, using a fake OpenAI-like object (no network)."""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from openai import OpenAI
from pydantic import BaseModel

from ai_act_check.adapters.foundry_llm import (
    DEPLOYMENT_ENV,
    ENDPOINT_ENV,
    FoundryLLMClient,
)


class Answer(BaseModel):
    """Small schema for the tests."""

    label: str


class FakeResponses:
    """Stands in for `openai.resources.responses.Responses`."""

    def __init__(self, response: SimpleNamespace) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    def parse(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return self.response


OK_ANSWER = Answer(label="ok")
OK_USAGE = SimpleNamespace(input_tokens=11, output_tokens=7)


def make_client(
    parsed: Answer | None = OK_ANSWER,
    usage: SimpleNamespace | None = OK_USAGE,
) -> tuple[FoundryLLMClient, FakeResponses]:
    """Build the adapter around a fake OpenAI client."""
    response = SimpleNamespace(output_parsed=parsed, model="gpt-test-2025", usage=usage)
    responses = FakeResponses(response)
    fake = SimpleNamespace(responses=responses)
    return FoundryLLMClient(cast(OpenAI, fake), "my-deployment"), responses


def test_complete_json_passes_prompt_and_schema_to_responses_api() -> None:
    client, responses = make_client()

    client.complete_json("be brief", "classify this", Answer)

    assert responses.kwargs == {
        "model": "my-deployment",
        "instructions": "be brief",
        "input": "classify this",
        "text_format": Answer,
    }


def test_complete_json_returns_parsed_answer_and_usage() -> None:
    client, _ = make_client()

    parsed, usage = client.complete_json("s", "u", Answer)

    assert parsed == Answer(label="ok")
    assert usage.model == "gpt-test-2025"
    assert usage.input_tokens == 11
    assert usage.output_tokens == 7
    assert usage.latency_ms >= 0


def test_complete_json_without_usage_reports_zero_tokens() -> None:
    client, _ = make_client(usage=None)

    _, usage = client.complete_json("s", "u", Answer)

    assert usage.input_tokens == 0
    assert usage.output_tokens == 0


def test_complete_json_without_parsed_output_raises_value_error() -> None:
    client, _ = make_client(parsed=None)

    with pytest.raises(ValueError):
        client.complete_json("s", "u", Answer)


def test_deployment_is_exposed() -> None:
    client, _ = make_client()

    assert client.deployment == "my-deployment"


@pytest.mark.parametrize("missing", [ENDPOINT_ENV, DEPLOYMENT_ENV])
def test_from_env_names_the_missing_env_var(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    monkeypatch.setenv(ENDPOINT_ENV, "https://example.test/api/projects/p")
    monkeypatch.setenv(DEPLOYMENT_ENV, "my-deployment")
    monkeypatch.delenv(missing)

    with pytest.raises(RuntimeError, match=missing):
        FoundryLLMClient.from_env()


def test_from_env_treats_blank_value_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENDPOINT_ENV, "   ")
    monkeypatch.setenv(DEPLOYMENT_ENV, "my-deployment")

    with pytest.raises(RuntimeError, match=ENDPOINT_ENV):
        FoundryLLMClient.from_env()
