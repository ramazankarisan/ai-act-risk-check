"""Run the baseline on every golden case and write a Markdown eval report.

Usage (from the repo root, signed in with `az login`):

    uv run --env-file .env python -m evals.run_eval --provider foundry

Writes reports/eval-v0-<provider>.md.
"""

import argparse
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_act_check.baseline import BaselineResult, classify
from ai_act_check.ports import LLMClient, Retriever
from evals.metrics import (
    citation_precision,
    citation_recall,
    class_accuracy,
    flag_recall,
    review_rate,
)
from evals.schema import GOLDEN_V0_PATH, GoldenCase, Prediction, load_golden

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
PROVIDERS = ["foundry"]
TOP_K = 8

# Estimated list prices in USD per 1 million tokens: (input, output).
# Keys are model id prefixes, matched against the model id the provider reports.
# Azure Global Standard rates as of 2026-11-18; check the Azure OpenAI pricing page before
# relying on them. Reasoning tokens are billed as output tokens.
PRICES_USD_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-5-mini": (0.25, 2.00),
}


@dataclass(frozen=True)
class CaseRun:
    """One golden case, the baseline result for it, and the derived prediction."""

    gold: GoldenCase
    result: BaselineResult
    prediction: Prediction


def to_prediction(case_id: str, result: BaselineResult) -> Prediction:
    """Map the baseline answer onto the eval's prediction shape."""
    return Prediction(
        case_id=case_id,
        predicted_class=result.answer.risk_class,
        cited_articles=result.answer.cited_chunk_ids,
        flagged=result.answer.needs_review,
    )


def run(
    cases: Sequence[GoldenCase], llm: LLMClient, retriever: Retriever, top_k: int = TOP_K
) -> list[CaseRun]:
    """Classify every golden case with the baseline, one after another."""
    runs = []
    for gold in cases:
        print(f"  {gold.id} ...", flush=True)
        result = classify(gold.description, llm, retriever, top_k=top_k)
        runs.append(CaseRun(gold, result, to_prediction(gold.id, result)))
    return runs


def compute_metrics(runs: Sequence[CaseRun]) -> dict[str, float]:
    """Score all runs with the eval metrics."""
    preds = [r.prediction for r in runs]
    golds = [r.gold for r in runs]
    return {
        "class accuracy (definite cases)": class_accuracy(preds, golds),
        "class accuracy (all cases)": class_accuracy(preds, golds, exclude_unclear=False),
        "citation precision": citation_precision(preds, golds),
        "citation recall": citation_recall(preds, golds),
        "flag recall": flag_recall(preds, golds),
        "review rate": review_rate(preds, golds),
    }


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile: the smallest value with at least p% of values at or below."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


def price_for(model: str) -> tuple[float, float] | None:
    """Return (input, output) USD per 1M tokens for the longest matching prefix, if any."""
    matches = [prefix for prefix in PRICES_USD_PER_1M if model.startswith(prefix)]
    if not matches:
        return None
    return PRICES_USD_PER_1M[max(matches, key=len)]


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Estimated USD cost, or None if the model has no price in the config."""
    price = price_for(model)
    if price is None:
        return None
    return (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000


def build_report(runs: Sequence[CaseRun], provider: str, deployment: str, run_at: datetime) -> str:
    """Render the Markdown report: run info, metrics, cost and latency, per-case table."""
    if not runs:
        raise ValueError("no case runs to report")
    sections = [
        _header(runs, provider, deployment, run_at),
        _metrics_section(runs),
        _cost_section(runs),
        _cases_section(runs),
    ]
    return "\n\n".join(sections)


def _models(runs: Sequence[CaseRun]) -> list[str]:
    """The distinct model ids the provider reported, sorted."""
    return sorted({r.result.usage.model for r in runs})


def _header(runs: Sequence[CaseRun], provider: str, deployment: str, run_at: datetime) -> str:
    """Title and run information."""
    models = ", ".join(f"`{m}`" for m in _models(runs))
    return "\n".join(
        [
            f"# Eval v0: baseline on {provider}",
            "",
            f"- Run at: {run_at:%Y-%m-%d %H:%M} UTC",
            f"- Deployment: `{deployment}`",
            f"- Model id: {models}",
            f"- Golden set: {len(runs)} cases, retrieval: BM25 top {TOP_K}",
        ]
    )


def _metrics_section(runs: Sequence[CaseRun]) -> str:
    """Overall metrics table, with the ideal review rate as a reading aid."""
    ideal_rate = sum(r.gold.should_flag for r in runs) / len(runs)
    lines = ["## Metrics", "", "| metric | value |", "|---|---|"]
    lines += [f"| {name} | {value:.2f} |" for name, value in compute_metrics(runs).items()]
    lines += [
        "",
        f"Review rate should be close to {ideal_rate:.2f} (share of cases that need review);"
        " read it together with flag recall.",
    ]
    return "\n".join(lines)


def _cost_section(runs: Sequence[CaseRun]) -> str:
    """Token totals, estimated cost and latency percentiles."""
    models = _models(runs)
    input_tokens = sum(r.result.usage.input_tokens for r in runs)
    output_tokens = sum(r.result.usage.output_tokens for r in runs)
    latencies = [r.result.usage.latency_ms for r in runs]
    # One price only makes sense when every call used the same model.
    cost = estimate_cost(models[0], input_tokens, output_tokens) if len(models) == 1 else None
    cost_text = "n/a (no price configured)" if cost is None else f"${cost:.4f}"
    return "\n".join(
        [
            "## Cost and latency",
            "",
            "| item | value |",
            "|---|---|",
            f"| input tokens | {input_tokens:,} |",
            f"| output tokens | {output_tokens:,} |",
            f"| total tokens | {input_tokens + output_tokens:,} |",
            f"| estimated cost | {cost_text} |",
            f"| latency p50 | {percentile(latencies, 50):,.0f} ms |",
            f"| latency p95 | {percentile(latencies, 95):,.0f} ms |",
        ]
    )


def _cases_section(runs: Sequence[CaseRun]) -> str:
    """Per-case table, then the model's reasoning for each case."""
    lines = [
        "## Per case",
        "",
        "| id | expected | predicted | ok | flag should/got | expected ids | cited ids"
        " | precision | recall | latency ms | tokens |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines += [_case_row(r) for r in runs]
    lines += ["", "## Reasoning", ""]
    for r in runs:
        lines += [
            f"**{r.gold.id}** ({r.prediction.predicted_class}): {r.result.answer.reasoning}",
            "",
        ]
    return "\n".join(lines).rstrip()


def _case_row(r: CaseRun) -> str:
    """One per-case table row."""
    gold, pred, usage = r.gold, r.prediction, r.result.usage
    ok = "yes" if pred.predicted_class == gold.expected_class else "no"
    flags = f"{_yes_no(gold.should_flag)}/{_yes_no(pred.flagged)}"
    precision = citation_precision([pred], [gold])
    recall = citation_recall([pred], [gold])
    tokens = usage.input_tokens + usage.output_tokens
    return (
        f"| {gold.id} | {gold.expected_class} | {pred.predicted_class} | {ok} | {flags}"
        f" | {_ids(gold.expected_articles)} | {_ids(pred.cited_articles)}"
        f" | {precision:.2f} | {recall:.2f} | {usage.latency_ms:,.0f} | {tokens:,} |"
    )


def _yes_no(value: bool) -> str:
    """Render a bool as yes or no."""
    return "yes" if value else "no"


def _ids(ids: Sequence[str]) -> str:
    """Render chunk ids as a comma-separated list, or a dash if empty."""
    return ", ".join(ids) if ids else "-"


def make_llm(provider: str) -> tuple[LLMClient, str]:
    """Build the LLM adapter for a provider; returns the client and its deployment name."""
    if provider == "foundry":
        # Imported here so tests and other providers never load the Azure SDK.
        from ai_act_check.adapters.foundry_llm import FoundryLLMClient

        client = FoundryLLMClient.from_env()
        return client, client.deployment
    raise ValueError(f"unknown provider {provider!r}; choose from {PROVIDERS}")


def main(argv: Sequence[str] | None = None) -> None:
    """Parse arguments, run the eval and write the report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    parser.add_argument("--golden", type=Path, default=GOLDEN_V0_PATH)
    args = parser.parse_args(argv)

    from ai_act_check.adapters.bm25_retriever import BM25Retriever

    cases = load_golden(args.golden)
    llm, deployment = make_llm(args.provider)
    print(f"Running {len(cases)} cases on {args.provider} ({deployment})")
    runs = run(cases, llm, BM25Retriever.from_corpus())

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"eval-v0-{args.provider}.md"
    out.write_text(build_report(runs, args.provider, deployment, datetime.now(UTC)) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
