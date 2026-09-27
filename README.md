# ARBITER

Agent Runtime for Bounded Inference, Triage, Evaluation and Routing.

`arbiter` is a Python package for typed decision points on an LLM agent you already run. A cheap engine answers a closed question and returns probabilities. Deterministic code then acts, narrows the agent's options, or escalates. The engine advises. Code authorizes.

This repository is at version `0.0.0`. It does not make cost, latency, or accuracy claims. Those wait for the gates in [docs/PLAN.md](docs/PLAN.md).

## What is here

- An allow-list of secret **names**. Projections and logs record the name. The executor injects the value at call time. A registered secret value in model-visible state fails closed.
- An append-only JSONL decision log. Each line round-trips. Lines are not rewritten.
- A content-hashed replay cache. The hash ignores clocks, counters, and floats. A miss falls back.
- Typed Choice, Score, and Noul questions. Choice always includes `other`. Bad shapes are rejected before a call.
- Projection builders for DP2 and DP4. They stay inside a token budget and do not copy secret values.
- Fake, oracle, and random engines. A missing probability is a normal return.
- A policy table with both max-probability and confidence bands. A side effect runs only when deterministic code opens the gate.
- Isotonic, histogram, and temperature calibrators, plus Brier, ECE, AUROC, and coverage. Fits under 200 labels are refused. Temperature scaling needs logits.
- Fallbacks for rate limit, overload, timeout, a malformed answer, and an out-of-range choice. The fallback sees the full context.

Not built yet: a live Jev or LLM engine, a framework adapter, and the CLI. Those wait on a provider key and on the G0 freeze in [docs/PLAN.md](docs/PLAN.md).

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
