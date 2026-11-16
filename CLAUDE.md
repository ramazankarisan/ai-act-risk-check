# AI Act Risk Check

Classifies an AI use-case description under the EU AI Act (Regulation (EU) 2024/1689) as
prohibited / high_risk / transparency / minimal / unclear, with article citations, review flags and trace IDs.
Portfolio project for production AI-engineering practice. Principle: rules calculate, the LLM judges,
a human decides. Anything unclear is flagged, not guessed.

## Commands

```bash
uv sync                                         # install deps
uv run pytest                                   # tests
uv run ruff check .                             # lint
uv run ruff format .                            # format
uv run uvicorn ai_act_check.api:app --reload    # dev server on :8000
```

## Folder map

| Path | Purpose |
|---|---|
| `src/ai_act_check/` | Application package (core, interfaces, adapters, API) |
| `src/ai_act_check/api.py` | FastAPI app |
| `tests/` | pytest tests |
| `data/` | Corpus: EUR-Lex law text and Commission guidelines. `data/raw/*.html` is committed |
| `evals/` | Golden set and eval metrics |
| `reports/` | Eval run outputs and baselines |
| `.github/workflows/` | CI: lint and tests |

## Architecture rule

- The core is vendor-neutral: pydantic, pytest, and later LangGraph and OpenTelemetry.
- Cloud services sit behind small `typing.Protocol` interfaces: `LLMClient`, `Retriever`, later `Extractor`.
- Azure is the first implementation, not a dependency of the core. Never import a vendor SDK in core modules.

## Rules

- **Public data only**: EUR-Lex law text, Commission guidelines, self-written synthetic cases.
  No personal or client data.
- **Code style**: simple, fully typed code with small functions and docstrings on public functions.
- **Human-authored parts**: the golden-set cases, the metric implementations (bodies of `evals/metrics.py`)
  and the deterministic rules node are written by hand. Do not generate them. Leave stubs that raise
  `NotImplementedError`, marked with `# TODO(ramazan)`.
- **Tests**: pytest tests may be generated, including tests for the rules node and metrics.
  CI and hooks check them.
- **Dependencies**: ask before adding any dependency not listed in the current step, including dev tools.
- **Small PR-sized changes**: one concern per change. CI (ruff and pytest) must pass.
