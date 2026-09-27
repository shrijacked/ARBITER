# ARBITER

Agent Runtime for Bounded Inference, Triage, Evaluation and Routing.

`arbiter` is a Python package for typed decision points on an LLM agent you already run. A cheap engine answers a closed question and returns probabilities. Deterministic code then acts, narrows the agent's options, or escalates. The engine advises. Code authorizes.

This repository is at version `0.0.0`. It does not make cost, latency, or accuracy claims. Those wait for the gates in [docs/PLAN.md](docs/PLAN.md).

## What is here

- An allow-list of secret **names**. Projections and logs record the name. The executor injects the value at call time. A registered secret value in model-visible state fails closed.
- An append-only JSONL decision log. Each line round-trips. Lines are not rewritten.

Not built yet: projection builders, engines, the policy table, calibrators, a framework adapter, and the CLI. The operational plan is [docs/PLAN.md](docs/PLAN.md).

## What this is not

- Not an agent framework, and not a replacement for LangChain, Pydantic AI, or the OpenAI Agents SDK.
- Not an authorization boundary. Decision-point output may only narrow, deny, or escalate.
- Not a Jev client yet. No network calls and no model SDK are included.

## Develop

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
make check
```

`make check` runs ruff, mypy, and pytest.

Copy [.env.example](.env.example) to `.env` if you need keys later. `.env` is gitignored. Leave the values empty until a task actually calls a provider. The names in `.env.example` are the allow-list.

## Layout

| Path | What it is |
|---|---|
| `src/arbiter/` | The package |
| `tests/` | pytest |
| `docs/PLAN.md` | What gets built, in what order |
| `docs/DECISION_LOG.md` | Why we believe the current decisions |
| `docs/RESEARCH.md`, `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_PLAN.md` | Frozen research record |
