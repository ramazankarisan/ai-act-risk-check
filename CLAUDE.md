# AI Act Risk Check

Classifies an AI use-case description under the EU AI Act (Regulation (EU) 2024/1689) as
prohibited / high_risk / transparency / minimal / unclear, with article citations, review flags and trace IDs.
Portfolio project for production AI-engineering practice. Principle: rules calculate, the LLM judges,
a human decides. Anything unclear is flagged, not guessed.

## Commands

```bash
uv sync                                         # install deps
uv run pre-commit install                       # once per clone: commit, commit-msg, pre-push hooks
uv run pytest                                   # tests
uv run pytest --cov --cov-report=term-missing   # tests with coverage
uv run mypy                                     # type check (strict)
uv run ruff check .                             # lint
uv run ruff format .                            # format
uv run pre-commit run --all-files               # all commit-stage hooks, like CI
uv run uvicorn ai_act_check.api:app --reload    # dev server on :8000
uv run python scripts/download_ai_act.py        # fetch AI Act OJ HTML once (skips if present)
uv run python -m ai_act_check.corpus            # build data/corpus/ai_act_chunks.jsonl
uv run --env-file .env python -m evals.run_eval --provider foundry  # eval baseline (needs az login)
```

## Guardrails

| Stage | Checks |
|---|---|
| pre-commit (staged files) | ruff check --fix, ruff format, whitespace/EOF, YAML/TOML, merge markers, large files (>1 MB, `data/raw/` excluded), private keys, gitleaks, `uv lock --check`, no commits on `main` |
| commit-msg | Conventional Commits (`feat:`, `fix:`, `chore:`, `ci:`, `docs:`, `test:`, `refactor:` …) |
| pre-push | mypy strict, pytest |
| CI (`ci.yml`, every PR and push to `main`) | all pre-commit hooks on all files, mypy, pytest with coverage |
| Security (`security.yml`) | pip-audit on locked deps: weekly, and when `uv.lock` changes |
| Dependabot | weekly grouped update PRs for uv deps and GitHub Actions |
| Claude Code hook | after each edit Claude makes: ruff format + ruff check --fix on that `.py` file |

Workflow: branch off `main` → small commits → push → PR → CI green → merge. `main` is protected.
Do not bypass hooks with `--no-verify`.

## Subagents

| Agent | Model | Can | Use |
|---|---|---|---|
| `locator` | haiku | read only | where is X / what calls Y / find a corpus article |
| `test-runner` | haiku | run checks only (hook-enforced, no `--fix`) | run ruff, mypy and pytest; report failures only |
| `test-writer` | sonnet | write in `tests/` only (hook-enforced) | add tests, including xfail tests for hand-written stubs |
| `convention-reviewer` | sonnet | read-only git (hook-enforced) | review the branch diff against the rules above |

Agent tool limits are enforced by PreToolUse hooks in `.claude/hooks/` (requires `jq`). They guard
against mistakes; they are not a security sandbox.

Delegation rules:
- Before opening a PR, run `convention-reviewer` on the branch and resolve BLOCKER and MAJOR findings.
- Before committing, run `test-runner` (or the equivalent commands) and report failures.
- Use `test-writer` for new tests. Use `locator` for multi-file lookups.

## Folder map

| Path | Purpose |
|---|---|
| `src/ai_act_check/` | Application package (core, interfaces, adapters, API) |
| `src/ai_act_check/api.py` | FastAPI app |
| `src/ai_act_check/ports.py` | `LLMClient` and `Retriever` Protocols the core depends on |
| `src/ai_act_check/adapters/` | Port implementations: BM25 retriever, Microsoft Foundry LLM client |
| `src/ai_act_check/baseline.py` | One-call baseline classifier (retrieve, prompt, validate) |
| `src/ai_act_check/corpus.py` | Parses the AI Act OJ HTML into `Chunk`s (recitals, article paragraphs/points, annex points) |
| `scripts/` | One-off scripts, e.g. `download_ai_act.py` |
| `tests/` | pytest tests |
| `data/raw/` | Downloaded source HTML, committed byte-identical (whitespace hooks skip it) |
| `data/corpus/` | Generated chunk files (`ai_act_chunks.jsonl`); rebuild with `python -m ai_act_check.corpus` |
| `evals/` | Golden set, eval metrics and `run_eval.py` (writes `reports/eval-v0-<provider>.md`) |
| `reports/` | Eval run outputs and baselines |
| `.github/workflows/` | CI (`ci.yml`) and dependency audit (`security.yml`) |
| `.claude/` | Claude Code settings, deny rules and hooks |
| `.claude/agents/` | Project subagents (see below) |

## Architecture rule

- The core is vendor-neutral: pydantic, pytest, and later LangGraph and OpenTelemetry.
- Cloud services sit behind small `typing.Protocol` interfaces: `LLMClient`, `Retriever`, later `Extractor`.
- Azure is the first implementation, not a dependency of the core. Never import a vendor SDK in core modules.

## Rules

- **Public data only**: EUR-Lex law text, Commission guidelines, self-written synthetic cases.
  No personal or client data.
- **Code style**: simple, fully typed code with small functions and docstrings on public functions.
- **Human-authored parts**: the deterministic rules node is written by hand. Do not generate it.
  Leave stubs that raise `NotImplementedError`, marked with `# TODO(ramazan)`.
- **Eval metrics**: Claude may implement the bodies of `evals/metrics.py`; the maintainer reviews
  every change. The docstrings are the spec: do not change them without asking.
- **Golden set**: Claude may draft golden cases, always with `review_status: draft` and a `source`
  (chunk ids or a named Commission guideline). Only the maintainer sets `accepted` or `changed`.
  Never change the label, source or status of a case that is not `draft`.
- **Tests**: pytest tests may be generated, including tests for the rules node and metrics.
  CI and hooks check them.
- **Dependencies**: ask before adding any dependency not listed in the current step, including dev tools.
- **Small PR-sized changes**: one concern per change. CI (ruff and pytest) must pass.
