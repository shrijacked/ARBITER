# DECISION_LOG.md — Decisions, Assumptions, and Uncertainty Register

**Status:** Living register. Dates are absolute (YYYY-MM-DD). Everything below was established during the research phase ending 2026-09-20; no implementation exists.

**Companion documents:** [RESEARCH.md](RESEARCH.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

**Question this document answers:** *What do we currently believe, why do we believe it, and what could change our minds?*

Evidence labels follow [ARCHITECTURE.md §0](ARCHITECTURE.md#0-how-to-read-this-document): **[DOC]** official docs · **[IND]** independent measurement · **[VENDOR]** vendor claim · **[HYP]** our hypothesis.

---

## 1. Core hypothesis and sub-hypotheses

| ID | Statement | Status (2026-09-20) | Basis |
|---|---|---|---|
| H0 | Agent systems benefit from separating bounded decision-making from open-ended reasoning, with a dedicated decision model serving the former. | **Partially supported, unproven end-to-end.** | Separation into proposer + grounded scorer improves success in robotics and web agents when the scorer has information the proposer lacks (SayCan, Web-Shepherd, hybrid SWE verifiers; [RESEARCH.md §5.3](RESEARCH.md#53-uncertainty-aware-agents-verifiers-and-dual-process-designs)). No controlled software-agent study isolates the split from confounds. |
| H1 | Jev can select the correct tool from a large catalog (DP2) with accuracy close to an LLM's own choice, at a fraction of the cost and latency. | **Plausible, vendor-supported, not independently measured on real catalogs.** | [VENDOR] skill-suggestion cookbook 16.8%→7.3% wrong loads on 488 requests; [IND] intent classification within ~4 points of a frontier LLM but below a supervised encoder ([jev-baselines-eval](https://github.com/ickma2311/jev-baselines-eval)); harness exists without published numbers ([jev-eval-agent](https://github.com/vinilana/jev-eval-agent)). |
| H2 | Inserting a calibrated decision component at DP2 and DP4 reduces cost per successful task or steps per task without reducing pass^k. | **Open. This is the MVP hypothesis.** | No end-to-end controlled evidence exists for any Jev-in-agent-loop configuration ([RESEARCH.md §5.4](RESEARCH.md#54-what-already-exists-specifically-for-jev-in-agents)). |
| H3 | Jev can judge progress (done / stuck / drifted) from a compact projection of recent actions. | **Untested.** | Only synthetic recipe demonstrations ([jev-skill](https://github.com/wuyoscar/jev-skill)); vendor "done" gate in jev-eval-agent without numbers. |
| H4 | Jev's probabilities are calibrated enough to gate actions after per-task recalibration. | **Partially supported.** | [IND] in-distribution ECE near noise floor; out-of-distribution ECE 0.107 vs 0.024 floor, type-dependent direction ([jev-ood-calibration](https://github.com/scienthoon/jev-ood-calibration)); isotonic recalibration on a few hundred labels reached ECE ≈ 0.01 on one dataset ([Jev-Calibration](https://github.com/AnthusAI/Jev-Calibration)); confidence exactly 1.0 on wrong answers observed ([jev-baselines-eval](https://github.com/ickma2311/jev-baselines-eval)). |
| H5 | The benefit, if any, is specific to Jev rather than to having typed decision points at all. | **Open; the design assumes it may be false.** | Arm A2 (LLM answering the same typed questions) exists to test this ([IMPLEMENTATION_PLAN.md §6.2](IMPLEMENTATION_PLAN.md#62-experimental-arms)). One independent grading study found a cheap LLM agreeing slightly *more* with the frontier reference than Jev at similar cost class ([Good Start Labs](https://goodstartlabs.com/research/verification-is-the-bottleneck)). |

---

## 2. Major assumptions

Design assumptions A1–A7 are defined in [ARCHITECTURE.md §12](ARCHITECTURE.md#12-design-assumptions). Additional research-phase assumptions:

| ID | Assumption | Label | Consequence if false |
|---|---|---|---|
| R1 | The official documentation reviewed on 2026-09-20 accurately describes `jev-1.13.0` behavior and limits. | [DOC] | Re-verify limits in Phase 0 (T0.1). |
| R2 | Independent measurements published within five days of launch (2026-09-15 to 2026-09-20) are indicative, though small and unreproduced. | [IND, weak] | Treat every third-party number as provisional; Phase 0 re-measures what matters. |
| R3 | Early-access status will not block a student project (gateway access exists). | [DOC + VENDOR] | Use LLM-adapter or Laya as the decision component; research question survives. |
| R4 | The vendor's evaluation dashboard, which scores agreement with a frontier-model consensus rather than human ground truth, is not usable as accuracy evidence. | Methodological | We do not cite its accuracy figures as accuracy; we cite them as agreement. |
| R5 | Vendor speed/cost multipliers (up to 193.6× / 444.6×) are best-case and do not describe agent-loop conditions. | [VENDOR, self-caveated] | Independent ranges of roughly 2–25× faster and 5–580× cheaper depending on baseline ([RESEARCH.md §4.2](RESEARCH.md#42-performance-evidence)) are used for planning. |

---

## 3. Decisions made

| ID | Date | Decision | Rationale | Alternatives considered | Reversible? |
|---|---|---|---|---|---|
| D1 | 2026-09-20 | **Research gate = MODIFY.** Do not build a general Jev × LLM framework; build a decision-point evaluation harness with a two-decision-point live MVP. | Jev's documented scope is narrow (closed-set, single-hop, compact state); official integrations already exist in LangChain and Pydantic AI; the missing thing is controlled evidence. [RESEARCH.md §8](RESEARCH.md#8-research-gate-assessment). | GO (build framework): rejected, weak novelty and unsupported dependencies. STOP: rejected, speed/cost are independently corroborated and the research question is real. | Yes, at G2. |
| D2 | 2026-09-20 | Recommended architecture is **LLM-first with Jev advisory at enumerated decision points** (A/E), not Jev-first. | Only variant whose Jev dependencies are all [DOC]/[IND]; Jev-first requires an enumerable action space. [ARCHITECTURE.md §11](ARCHITECTURE.md#11-alternative-architectures-considered). | Jev-first (browser evidence only), orchestrator model (regress), parallel (cost). | Yes; browser track optional in Phase 3. |
| D3 | 2026-09-20 | **Decision component is pluggable**; Jev is one implementation among LLM-adapter, trained encoder, Laya, rules. | Required to attribute effects; the vendor's own MIT adapter enables it; a supervised encoder beat Jev on Banking77 [IND]. | Jev-only harness: rejected as unfalsifiable. | No (core design). |
| D4 | 2026-09-20 | **Gate on max probability by default**, log the `confidence` field, recalibrate per decision point and model version. | Independent studies found `confidence` less calibrated than max probability [IND]; vendor documents thresholds are domain- and version-specific [DOC]. | Vendor `confidence` as default: rejected pending T0.6. | Yes (U2). |
| D5 | 2026-09-20 | **MVP decision points = DP2 (tool pre-selection) and DP4 (progress monitoring).** DP3 (risk) is advisory-only and measured, at most, in shadow mode. | DP2 has ground truth and fits Choice; DP4 tests the "cheap enough to ask every step" claim; DP3 is documented as unsafe to rely on and already widely deployed by others. | DP7 model routing first: deferred, heavily studied elsewhere. DP3 first: rejected for safety scope. | Yes (G0 MODIFY path). |
| D6 | 2026-09-20 | **Pre-register Phase 2** with hash-pinned arms, metrics, thresholds. | Router/cascade evaluations commonly suffer from post-hoc thresholds and missing controls; one independent Jev study demonstrated the practice. | Exploratory-only: rejected. | No. |
| D7 | 2026-09-20 | **Use only public or synthetic data** in all phases. | Hosting region and SLAs undocumented [DOC gap]; secrets and personal data would reach a third-party API. | — | No. |
| D8 | 2026-09-20 | **Do not implement anything during the research phase.** Deliverables are four Markdown documents. | User requirement. | — | — |
| D9 | 2026-09-20 | **Defer any library extraction until after G2.** | Prevents scope creep into a framework (non-goal N1). | Build library first: rejected. | Yes, at G2. |
| D10 | 2026-09-20 | **Pin an explicit Jev version in every request** and assert on the `model` field. | `jev-latest` was observed re-pointing mid-run [IND]; thresholds are version-specific. | Use alias: rejected. | No. |

---

## 4. Alternatives considered and set aside

| Alternative | Why set aside | Could return if |
|---|---|---|
| General-purpose agent framework with Jev as the decision engine | Weak novelty (LangChain middleware, Pydantic AI model, ~200 community projects); unsupported dependencies for planning-level decisions | Never in this form; a thin library may follow D9 |
| Jev as the security/permission gate | Adversarial content is a documented weakness [DOC]; third-party guidance says advisory only; LangChain's middleware refuses but does not approve | Only as one advisory signal behind deterministic policy |
| Jev for context compaction as the MVP | Interesting community activity but harder ground truth and a documented "sees tool calls, not outputs" limitation ([Reticle](https://www.reticle.sh/blog/typesafe-jev-playbook)) | Phase 3 |
| Browser Jev-first agent as the MVP | Strongest existing Jev-first evidence, but domain-specific and self-reported; would duplicate fastbrowse | Phase 3 replication track |
| Fine-tuned encoder instead of Jev from the start | Requires labels first; Jev's zero-shot property is what makes it worth testing as a bootstrapping tool | Arm A3 exists; may become primary after G1 |

---

## 5. Confirmed findings vs provisional recommendations

### 5.1 Confirmed findings (verified in official docs or by independent measurement; see [RESEARCH.md §4](RESEARCH.md#4-verified-capability-assessment))

| Finding | Label |
|---|---|
| Jev = `jev-1.13.0`, aliases `jev-latest`/`jev-preview`; endpoint `POST /v1/systemone`; primitives Choice (≤255 options), Score (2–10 levels), Noul (0–1); text-only; 64k tokens per request, 32k for state + longest question; $0.042 per million input tokens, output free. | [DOC] |
| Questions in one request are evaluated in parallel and independently; adding questions barely changes latency. | [DOC], [IND] (batching cookbook re-run by independents not found; vendor measured 12.2× cheaper/10× faster for 13 questions) |
| Documented weaknesses: literal reading, arithmetic/counting, date comparison, indirection, large irrelevant state, adversarial content, contradictory criteria, no structural invariants across primitives, no generation. | [DOC] |
| Independent latency: ~0.24–0.9 s median per call depending on location and concurrency; tail of 10–35 s observed at 100 concurrent calls. | [IND] |
| Independent accuracy: competitive with cheap LLMs on short-input classification (spam, sentiment, news, intents); clearly below Claude Haiku 4.5 on a 2,000-email phishing set (62.6% vs 81.3%) and below a supervised encoder on Banking77 (0.832 vs 0.933). | [IND] |
| Independent calibration: near noise floor in distribution; 4.4× floor out of distribution; Choice/Score overconfident, Noul underconfident; recalibration on hundreds of labels can reduce ECE to ~0.01; exact-1.0 probabilities on wrong answers occur. | [IND] |
| Official Jev integrations already exist for LangChain (classifier + model-router and tool-risk middleware), Pydantic AI (Jev as a model with fallback), and Vercel AI Gateway/SDK. | [DOC of those vendors] |
| Vendor accuracy dashboard measures agreement with a frontier-model consensus, not ground truth; aggregate 67.8% vs best 74.1%. | [VENDOR, self-disclosed method] |
| No paper, weights, parameter count, or training details for Jev or RLCD are public. | [DOC gap] |

### 5.2 Provisional recommendations (ours; may change with Phase 0–2 evidence)

| Recommendation | Depends on |
|---|---|
| Use Jev only at closed-set, single-hop decision points over ≤32k-token projections. | Confirmed findings above |
| Start with DP2 + DP4; keep DP3 advisory. | D5 |
| Gate on recalibrated max probability, per DP and version. | H4, D4 |
| Treat A2 (LLM same-interface) as the primary comparison, not LLM-only. | H5 |
| Expect the honest result to be "cost/latency benefit at equal or slightly lower decision accuracy"; design metrics to detect that. | [IND] pattern across studies |

---

## 6. Open technical questions

| ID | Question | How to resolve | Phase |
|---|---|---|---|
| Q1 | How does DP2 accuracy scale with catalog size (20 → 255) and distractor density on realistic tool descriptions? | T0.3 probe; Phase 1 real catalogs | 0–1 |
| Q2 | What projection size maximizes DP4 accuracy before context rot dominates? | T0.4 with 3 vs 5 vs 10 actions | 0 |
| Q3 | How large are wording and option-order effects on the project's own questions, and can freezing wording control them? | T0.5 | 0 |
| Q4 | Does max probability or the vendor `confidence` field gate better after recalibration, per primitive type? | T0.6 | 0 |
| Q5 | Does step-level calibration hold along trajectories (checkpoint ECE), or degrade late in long runs? | Phase 2 trajectory-indexed ECE | 2 |
| Q6 | Is the end-to-end benefit (if any) attributable to Jev, to typed decision points, or to extra compute? | Arms A2, A5, A6, A7 | 2 |
| Q7 | What is the escalation rate at target accuracy, and how does it compare with a nano-class LLM and a trained encoder? | T1.6 cascade simulation | 1 |
| Q8 | How often does Jev re-propose an already-failed tool, and does the deterministic loop cap suffice? | Phase 2 logs | 2 |
| Q9 | Which host framework minimizes glue: LangChain middleware hooks, Pydantic AI `TypeSafeModel` + `FallbackModel`, or a thin custom runtime? | Prototype in Phase 1 (U4) | 1 |
| Q10 | Are the vendor's rate limits (250k tokens/s, 1,200 requests/min, "adjusting dynamically") stable enough for multi-seed runs? | T0.1 and Phase 1 logs | 0–1 |

---

## 7. Risks and potential failure modes

| ID | Risk | Likelihood | Impact | Mitigation | Early signal |
|---|---|---|---|---|---|
| R1 | Jev underperforms LLM's own tool choice on real catalogs | Medium | High | Two-stage selection; encoder arm; G0/G1 thresholds | T0.3 accuracy gap > 5 pts |
| R2 | Calibration unusable → no confidence gating story | Medium | High | Filter mode at extreme bands; report as finding | T0.6 ECE > 0.05 after refit |
| R3 | Vendor access, pricing, or region constraints | Medium | Medium | Cache; gateway; drop-in alternatives | 429 storms; pricing page changes |
| R4 | Version drift invalidates thresholds mid-study | Medium | High | Pin version; assert `model`; refit | `model` field changes |
| R5 | Overhead of extra requests erases savings | Medium | High | Batch; cap concurrency; drop DP5 | p95 > 1.5 s |
| R6 | Misattribution (benefit from structure, not Jev) | High | High | Arms A2/A5/A6/A7; pre-registration | A2 ≈ A1 |
| R7 | Benchmark noise (user simulator, contamination) hides effects | Medium | Medium | ≥3 seeds; pass^k; CIs; log inspection | Wide CIs |
| R8 | Adversarial observations steer decisions | Medium | Medium (advisory only) | Deterministic authority; DP5 as filter | Injection probes flip DP2/DP4 |
| R9 | Scope creep into framework building | High | Medium | N1, D9 | New abstractions without an arm needing them |
| R10 | Vendor pricing not sustainable (self-acknowledged) | Unknown | Medium | Report cost at multiple hypothetical prices | Pricing change |

---

## 8. Evidence that would support continuing

| After | Evidence |
|---|---|
| Phase 0 | DP2 top-1 within 5 points of the LLM-adapter baseline; recalibrated ECE ≤ 0.05; p95 ≤ 1.5 s at concurrency 4; coverage ≥ 50% at target precision ([IMPLEMENTATION_PLAN.md §4](IMPLEMENTATION_PLAN.md#4-phase-0--capability-validation-35-weeks) G0). |
| Phase 1 | At least one decision point where a component is accurate, calibrated after refit, and ≥3× cheaper per decision than the LLM's decision-equivalent tokens (G1). |
| Phase 2 | A1 lowers cost per successful task ≥ 25% or steps ≥ 20% with pass^4 within 2 points of A0; A1 beats A5; A1 not dominated by A6 (G2). |
| Externally | A TypeSafe technical report with calibration curves; independent reproduction of a Jev-in-loop result; stable pricing and published SLAs. |

## 9. Evidence that would justify abandoning or substantially changing the idea

| Evidence | Consequence |
|---|---|
| Jev > 10 points below the LLM-adapter on DP2 and DP4 after decomposition (G0 STOP) | Drop Jev path; keep harness; publish negative result |
| No component reaches usable calibration after refit | Reframe to "typed decision points as filters"; drop gating claims |
| Oracle arm A4 shows no end-to-end gain | Decision points chosen are not the bottleneck; change DP or benchmark |
| A2 matches A1 in Phase 2 | Contribution is component-agnostic; Jev is a cost option, not the thesis |
| Trained encoder (A3) dominates on accuracy, calibration, and cost | Shift to "Jev as label bootstrapper for task-specific classifiers" |
| API access lost with no acceptable substitute | Pause |
| A controlled, independent study answers H2 before Phase 2 | Re-scope toward the open questions in [RESEARCH.md §10](RESEARCH.md#10-broader-research-opportunity) |

---

## 10. Change log

| Date | Change |
|---|---|
| 2026-09-20 | Initial register created from the research phase. Hypotheses H0–H5, assumptions R1–R5, decisions D1–D10, questions Q1–Q10, risks R1–R10. |
