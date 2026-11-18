"""LLMClient for a Microsoft Foundry project, keyless via Microsoft Entra ID.

Uses `azure-ai-projects` to get an OpenAI client that is already authenticated with
`DefaultAzureCredential` (for example after `az login`), then calls the Responses API
with structured output. No API keys.
"""

import os
import time
from typing import Self

from openai import OpenAI
from pydantic import BaseModel

from ai_act_check.ports import Usage

ENDPOINT_ENV = "AZURE_AI_PROJECT_ENDPOINT"  # e.g. https://<resource>.services.ai.azure.com/api/projects/<project>
DEPLOYMENT_ENV = "AZURE_AI_MODEL_DEPLOYMENT_NAME"  # name of the model deployment in the project


class FoundryLLMClient:
    """Calls a model deployment in a Foundry project. Implements the `LLMClient` port."""

    def __init__(self, openai_client: OpenAI, deployment: str) -> None:
        """Use an already authenticated OpenAI client and a deployment name."""
        self._openai = openai_client
        self.deployment = deployment

    @classmethod
    def from_env(cls) -> Self:
        """Build a client from the env vars, signed in with `DefaultAzureCredential`."""
        endpoint = _require_env(ENDPOINT_ENV)
        deployment = _require_env(DEPLOYMENT_ENV)

        # Imported here so the rest of the package loads without touching Azure.
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential

        project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
        return cls(project.get_openai_client(), deployment)

    def complete_json[T: BaseModel](
        self, system: str, user: str, schema: type[T]
    ) -> tuple[T, Usage]:
        """Ask the deployment for a JSON answer that matches `schema`, and time the call."""
        start = time.perf_counter()
        response = self._openai.responses.parse(
            model=self.deployment, instructions=system, input=user, text_format=schema
        )
        latency_ms = (time.perf_counter() - start) * 1000

        parsed = response.output_parsed
        if parsed is None:
            raise ValueError(f"deployment {self.deployment!r} returned no parsed output")
        usage = Usage(
            model=response.model,
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0,
            latency_ms=latency_ms,
        )
        return parsed, usage


def _require_env(name: str) -> str:
    """Return the env var's value, or raise with a hint if it is missing."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"set {name} (see .env.example)")
    return value
