# AGENTS.md — decision-layer (repo working agreement)

This repo-local file adds project-specific rules on top of the user's global development
rules. Where both apply, the stricter one wins. It is intentionally short; the operational
detail lives in [docs/PLAN.md](docs/PLAN.md).

## Sources of truth

- **Operational plan (what/when/status):** [docs/PLAN.md](docs/PLAN.md). Update it as tasks move.
- **Why we believe things (living):** [docs/DECISION_LOG.md](docs/DECISION_LOG.md). Append dated rows; never rewrite history.
- **Frozen research record (do not edit):** [docs/RESEARCH.md](docs/RESEARCH.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
- **Learning book (teaches the project):** [learning/](learning/); master PDF at `learning/jev-learning-master.pdf`.

## Definition of done (every PLAN.md task, in order)

1. Run the task's verification (its done-criteria) and confirm it passes.
2. Update the task's **Status** in [docs/PLAN.md](docs/PLAN.md).
3. Append a dated row to [docs/DECISION_LOG.md](docs/DECISION_LOG.md) if anything decided, assumed, or risked changed.
4. Add the matching learning-book section and a Build-log entry (`learning/chapters/12_build_log.tex`).
5. Run `make -C learning pdf verify` (rebuilds the master PDF and checks it) and confirm `VERIFY OK`.
6. Make one descriptive commit for the logical unit.

## Evidence labels (use in all docs and the book)

`[DOC]` official TypeSafe docs · `[IND]` independent measurement · `[VENDOR]` vendor claim ·
`[HYP]` our hypothesis · `[MEASURED]` measured by us (with a run ID). No performance claim
ships before the gate that produced it (G1 for per-decision cost, G2 for end-to-end).

## Non-negotiable engineering rules

- **Data:** public or synthetic only. Hosting region and SLA are undocumented; assume egress.
- **Secrets:** allow-list by reference. The executor injects secret values at call time;
  projections and logs carry only secret *names*. A fuzz test must prove no secret string
  appears in any projection or log (EF-15).
- **Authority:** the decision engine advises; deterministic code authorizes. Jev is never the
  security or authorization boundary; DP outputs may only feed narrow/deny/escalate, never
  allow/elevate (EF-16). Fail closed on side effects.
- **Version pinning:** every Jev request pins an explicit version and asserts the returned
  `model` field; a version change hard-fails and quarantines the run (D10).
- **Reproducibility:** all model calls go through the content-hashed record/replay cache; the
  hash excludes wall-clock and counters and is stable across processes (EF-11). Every
  reported number must regenerate from the cache with one command.
- **Errors:** user-facing errors state problem, cause, and fix (EF-DX3).

## Bugs and workflow

Follow the global rules: reproduce a bug with a failing test first, then fix with proof
(test + regression). Use the gstack pipeline for non-trivial work. The learning book and its
master PDF are part of "done," not optional.

## Learning book build

- Engine: **Tectonic** (XeTeX). Bibliography: **BibTeX + natbib** (biber is not installed).
- `make -C learning pdf` builds and refreshes the master PDF; `make -C learning verify` also
  checks the log, greps for `??`, prints the page count, and renders every page to
  `learning/build/pages/` for inspection.
- There is no printed index (makeindex/xindy are unavailable); the Glossary and Source map
  (appendices) plus the table of contents serve lookup.
