# RESEARCH.md — Jev × LLM Agent Framework: Research Report

**Date of investigation:** 2026-09-20. **Model investigated:** TypeSafe AI's Jev, version `jev-1.13.0`. **Deliverable type:** research and planning only; no code was written, no API calls were made, no experiments were run by the author of this report.

**Companion documents:** [ARCHITECTURE.md](ARCHITECTURE.md) (conditional system design) · [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) (phased roadmap) · [DECISION_LOG.md](DECISION_LOG.md) (assumptions, decisions, kill criteria).

**Question this document answers:** *What did we investigate, what did we learn, and what remains uncertain?*

---

## Executive summary

1. **What Jev is.** Jev is TypeSafe AI's first "System One" model: a closed, hosted model that reads text or JSON state and answers typed questions of three kinds, Choice (pick one of up to 255 options), Score (position on 2–10 ordered levels), and Noul (probability that a statement is true), returning probabilities and, for Choice and Score, a confidence statistic, with no text generation. This is verified in the official documentation (§3–§4).
2. **What the documentation supports.** Fast, cheap, parallel evaluation of many independent, single-hop, closed-set judgments over compact state; confidence-gated routing patterns; structured criteria. The documentation also lists nine failure modes, including arithmetic, dates, multi-hop indirection, large irrelevant state, and adversarial content (§4.4).
3. **What independent evidence says.** Within five days of the 2026-09-15 launch, roughly a dozen third-party measurements appeared. They corroborate the direction of the speed and cost claims at smaller multipliers than the vendor's peaks (roughly 2–25× faster and 5–580× cheaper depending on the baseline), show accuracy competitive with cheap LLMs on short, crisply labeled tasks and clearly below them on harder judgments (phishing detection 62.6% vs 81.3% for Claude Haiku 4.5), and find calibration near the noise floor in distribution but 4.4× the floor out of distribution, fixable with a few hundred labels (§4.2–§4.3).
4. **What already exists.** The proposed architecture, an LLM for reasoning with a decision model at bounded decision points, is TypeSafe's own recommended pattern and is already shipped as official integrations by LangChain (classifier plus model-router and tool-risk middleware), Pydantic AI (Jev as a model with fallback), and Vercel (AI Gateway and SDK), plus about 200 community projects including browser agents where Jev selects every action (§5.4). A new general-purpose framework would have weak novelty.
5. **What is missing.** Controlled, independent, end-to-end evidence that inserting a calibrated decision model into an agent loop improves cost per successful task or reliability, with proper baselines (an LLM answering the same typed questions, trained classifiers, oracle and random controls) and calibration measured along trajectories. No such study exists for Jev, and the broader literature shows this is exactly where cascades and routers usually fail to deliver (§5.2, §6).
6. **Research gate: MODIFY.** Do not build a Jev-centric framework. Build a decision-point evaluation harness around an existing agent, validate Jev's specific capabilities on the project's own data first, and run a pre-registered live comparison at two decision points (tool pre-selection and progress monitoring). The design is in [ARCHITECTURE.md](ARCHITECTURE.md); the plan in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) (§8).
7. **Research opportunity.** The open, testable question is whether a calibrated bounded-decision component can allocate proceed / verify / ask / escalate decisions in an agent loop with fewer interventions at a target reliability than LLM self-confidence, and whether its calibration survives along trajectories. This is not answered by existing routing, cascade, or robotics-planning work (§10).

---

## 1. Identification of the exact Jev model

| Attribute | Finding | Source | Label |
|---|---|---|---|
| Name and version | **Jev**, current release **`jev-1.13.0`**; aliases `jev-latest` (SDK default) and `jev-preview` both resolve to `jev-1.13.0` as of 2026-09-20. Most cookbooks were run on `jev-1.12`. | [Models](https://docs.typesafe.ai/models); response examples show `"model": "jev-1.13.0"` ([Choice](https://docs.typesafe.ai/primitives/choice)) | Verified in official docs |
| Developer | TypeSafe AI, San Francisco, founded 2024. Founders: Diogo Almeida (CEO; former OpenAI, co-author of InstructGPT, listed on RLHF/ChatGPT work), Sasha Sheng (COO; ex-Meta/FAIR), Erik Gafni (CTO). | [Team](https://typesafe.ai/team); [SiliconANGLE](https://siliconangle.com/2026/09/16/typesafe-ai-exits-stealth-with-40m-to-build-ai-for-use-by-software/) | Developer statement plus press |
| Funding | $40M seed led by DCVC; ~$200M valuation reported by Forbes (via SiliconANGLE). | [SiliconANGLE](https://siliconangle.com/2026/09/16/typesafe-ai-exits-stealth-with-40m-to-build-ai-for-use-by-software/); [The Register](https://www.theregister.com/ai-and-ml/2026/09/16/typesafe-ai-debuts-model-for-machines-that-plays-doom/5296711) | Press |
| Announcement | 2026-09-15, "Introducing System One Models & Jev". | [Launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev) | Developer |
| Model class | "System One model": evaluates state and returns typed decisions and probabilities; named after Kahneman's fast/intuitive System 1. | [System One](https://docs.typesafe.ai/concepts/system-one) | Verified in official docs |
| Training | "Reinforcement Learning for Calibrated Decisions (RLCD)"; contrasted with RLHF and RLVR. Loss, reward, data, and procedure are **not disclosed**. | [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer); [MindStudio analysis](https://www.mindstudio.ai/blog/typesafe-jev-rlcd-vs-rlhf) | Claimed by developer, not verifiable |
| Architecture | "Novel model architecture", "parallel sampler", non-autoregressive; **no paper, weights, or parameter count**. CEO on Hacker News: "architecture is close to the chest for now, but we have talked about writing a paper." | [Launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev); [HN thread](https://news.ycombinator.com/item?id=49717558) | Claimed by developer |
| Endpoint | `POST https://api.typesafe.ai/v1/systemone`, bearer auth; Python SDK `typesafe-sdk` (v0.7.0 on 2026-09-18), JavaScript SDK `@typesafe-ai/sdk`. | [API](https://docs.typesafe.ai/api); [Python changelog](https://docs.typesafe.ai/sdk/python/changelog); [JS SDK](https://docs.typesafe.ai/sdk/javascript) | Verified in official docs |
| Availability | Early access with waitlist at the vendor; also served through Vercel AI Gateway as `typesafe-ai/jev` (2026-09-16) and listed on OpenRouter with verified pricing (per an independent aggregator). | [Homepage](https://typesafe.ai/); [Vercel changelog](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway); [JevBench methodology](https://jevbench.xyz/methodology) | Verified (vendor pages of Vercel; aggregator for OpenRouter) |

---

## 2. Research methodology

**Process followed (in this order):**

1. Read the mandated entry point, [docs.typesafe.ai/introduction](https://docs.typesafe.ai/introduction).
2. Retrieved the documentation index ([llms.txt](https://docs.typesafe.ai/llms.txt)) and followed every listed section: concepts, primitives, confidence, patterns, cookbooks, demos, SDKs, API, models, known issues, legal, agent skill.
3. Followed official external links: launch blog post, manifesto, team page, GitHub organization and repositories (SDKs, skills, LLM-backed adapter), evaluations dashboard.
4. Searched for independent evidence: press coverage, the Hacker News launch thread, third-party reviews, and, most importantly, independent benchmark repositories and blog posts with methodology and raw numbers.
5. Searched for existing Jev integrations in agent frameworks and community projects.
6. Delegated three literature surveys (agent frameworks and tool calling; routers, cascades, and classifiers; uncertainty-aware agents and evaluation methodology) and cross-checked the returned sources.
7. Only after steps 1–6: critiqued the hypothesis, set the research gate, and designed architecture, MVP, and evaluation.

**Evidence labels used throughout all four documents:**

| Label | Meaning |
|---|---|
| **Verified in official documentation** | Stated on a docs.typesafe.ai page (link given). Describes intended behavior and limits; it is not a measurement of accuracy. |
| **Claimed by the developer, not independently verified** | Vendor blog, cookbooks, evals dashboard, homepage. Cookbooks include cached raw API responses, which makes them inspectable but still vendor-run. |
| **Supported by independent evidence** | Third-party measurement with stated methodology. Almost all such evidence is one to five days old, small (n = 12 to ~19,000), unreproduced by a second party, and from authors of varying expertise. It is indicative, not conclusive. |
| **Plausible but untested** | Follows from documented behavior but no measurement exists. |
| **Unknown or unsupported** | Not documented, or documented as unsupported. |

**Limitations of this investigation:** Web pages were retrieved through a fetch-and-extract tool that returns structured summaries of page content; long pages may have been condensed, and playground or console pages behind login were not accessed. No API calls were made; no numbers in this report were produced by the author. All third-party numbers are quoted as reported by their authors. Model behavior and pricing may have changed after 2026-09-20.

---

## 3. Official documentation review

### 3.1 Pages reviewed

All pages listed in the official index were reviewed except where noted in §3.2. Key takeaways per page:

| Section | Page | Key takeaways for this project |
|---|---|---|
| Introduction | [Introduction](https://docs.typesafe.ai/introduction) | Jev = flagship, first System One model; three primitives; questions evaluated in parallel and in isolation; "atomic questions, composed in code"; decompose multi-factor judgments. |
| Introduction | [Quick start](https://docs.typesafe.ai/introduction/quickstart) | Endpoint, request/response shape, Python SDK (`pip install typesafe-sdk`, Python ≥ 3.10), coding-agent skill install. |
| Introduction | [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer) | RLCD vs RLHF/RLVR; calibration defined at group level: outcomes at probability 0.8 should occur about 80% of the time; "not a guarantee about any single answer". |
| Concepts | [System One](https://docs.typesafe.ai/concepts/system-one) | Text-only input (strings, JSON, arrays); "does not write replies, produce code, or generate explanations"; escalate to "a person or a reasoning model" on low confidence. |
| Concepts | [State](https://docs.typesafe.ai/concepts/state) | One state per request; string/object/array; objects recommended; English primary, other languages lower accuracy. |
| Concepts | [How to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) | Explicit contrast with "LLM agents"; "keep code in control"; use code when possible; decompose state and questions; ~100 ms claim; "Self-consistent" claim; route on uncertainty by plotting confidence vs accuracy. |
| Concepts | [Use case map](https://docs.typesafe.ai/concepts/use-case-map) | Lists "Harness Engineering: smart model routing and semantic context retrieval", "Model Routing", "LLM Guardrails", "Universal Verification"; decision-shape table (classification, detection, scoring, routing, search, retrieval, ranking, verification, feature extraction, structured extraction). |
| Primitives | [Primitives](https://docs.typesafe.ai/primitives), [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul), [Advanced structure](https://docs.typesafe.ai/primitives/advanced) | Choice ≤ 255 options, include "other"; Score 2–10 levels, score = probability-weighted mean of level numbers, "weak numerical calibration" for interpolation; Noul has no separate confidence; answers independent; backtick path references into JSON state; structured `what`/`not_for`/`examples` criteria; hierarchical classification via chained Choice. |
| Core | [Confidence](https://docs.typesafe.ai/confidence) | `confidence` is "a statistic computed from the probability distribution"; formula not given ("we'll keep to a separate cookbook"); three-band pattern; thresholds "scale with risk"; "start with conservative thresholds, test with your own data". |
| Patterns | [Patterns](https://docs.typesafe.ai/patterns), [Fan-out](https://docs.typesafe.ai/patterns/fan-out), [Confidence routing](https://docs.typesafe.ai/patterns/confidence-routing), [Composite scoring](https://docs.typesafe.ai/patterns/composite-scoring), [Intent routing](https://docs.typesafe.ai/patterns/intent-routing) | Speculative fan-out; confidence as second axis; weighted composition in code; intent routing to "deterministic logic, a specialist LLM, or a human" (example thresholds 0.5–0.85). |
| Cookbooks (18) | [Self-consistency: Nouls](https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook), [Self-consistency: Choices](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook), [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions), [Re-ranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe), [Line-by-line search](https://docs.typesafe.ai/cookbooks/semantic_find), [Structure recovery](https://docs.typesafe.ai/cookbooks/autoformat), [Function calling](https://docs.typesafe.ai/cookbooks/function_calling), [Skill suggestion](https://docs.typesafe.ai/cookbooks/skill_suggestion), [Entity alignment](https://docs.typesafe.ai/cookbooks/entity_alignment), [Classifying RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages), [Citation check](https://docs.typesafe.ai/cookbooks/citation_check), [LLM guardrails](https://docs.typesafe.ai/cookbooks/llm_guardrails), [SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade), [Date extraction](https://docs.typesafe.ai/cookbooks/date_extraction_cookbook), [Pre-parsed value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook), [Hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification), [Autoresearch feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery), [Classification using confidence](https://docs.typesafe.ai/cookbooks/classification_using_confidence) | Vendor-run worked examples with cached responses. Agent-relevant ones: skill suggestion (tool/skill pre-selection), function calling (closed-set arguments), SDE cascade (Jev as verifier gating escalation to a reasoning model), guardrails (input/output screening), RAG passages (relevance and injection filtering), citation check (claim verification). Numbers in §4.2. |
| Demos | [Demos](https://docs.typesafe.ai/demos), [Smart home](https://docs.typesafe.ai/demos/smart-home) | Speculative fan-out; **an LLM splits compound requests** and handles general questions; Jev handles intent/device/action classification. |
| SDKs | [Client SDKs](https://docs.typesafe.ai/sdk), [Python](https://docs.typesafe.ai/sdk/python), [Usage](https://docs.typesafe.ai/sdk/python/usage), [Async client](https://docs.typesafe.ai/sdk/python/api/clients/async), [Retries](https://docs.typesafe.ai/sdk/python/api/retries), [Exceptions](https://docs.typesafe.ai/sdk/python/api/exceptions), [Changelog](https://docs.typesafe.ai/sdk/python/changelog), [JavaScript](https://docs.typesafe.ai/sdk/javascript) | Sync/async clients; RetryPolicy defaults (2 retries, 0.5→5 s backoff, 30 s budget, retries 408/429/5xx); typed exceptions incl. `TypeSafeAPIResponseValidationError`; `response_model` for Pydantic typing; env vars `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`, `TYPESAFE_DEFAULT_MODEL`; three releases in four days (0.5.7 → 0.7.0) with breaking changes. |
| API | [API reference](https://docs.typesafe.ai/api) | Fields `state`, `model`, `questions`; errors 401/422/429/529; retry with backoff. |
| Models | [Models](https://docs.typesafe.ai/models) | `jev-1.13.0`; $42 per billion input tokens, output free; 250,000 tokens/s and 1,200 requests/min, "adjusting dynamically"; 64k tokens per request, 32k for state + longest question; not fine-tuned per customer; no training on requests; enterprise zero data retention. |
| Known issues | [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) | Nine failure modes with workarounds (§4.4). The single most important page for this project. |
| Integration | [Agent skill](https://docs.typesafe.ai/agent-skill); [SKILL.md](https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md) | Guidance for coding agents building on TypeSafe: "Typed output guarantees the interface, not truth"; "Do not conflate confidence with workflow correctness or authorization"; patterns "Routing & Arguments", "Verification Cascades", "Stateful Guidance". |
| Legal | [Legal](https://docs.typesafe.ai/legal) | DPA, MCA, privacy policy; no-training commitment; ZDR for enterprise; no SLA or hosting-region statement found. |
| Off-docs official | [Launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [Manifesto](https://typesafe.ai/manifesto), [Homepage](https://typesafe.ai/), [Team](https://typesafe.ai/team), [Evals dashboard](https://evals.typesafe.ai), [GitHub org](https://github.com/typesafe-ai), [system-one-adapter-python](https://github.com/typesafe-ai/system-one-adapter-python), [typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python), [skills](https://github.com/typesafe-ai/skills) | Claims and caveats in §4.2; the MIT adapter is a "drop-in replacement for `typesafe_sdk`'s `system_one` evaluation API, backed by LLM APIs" intended for cost/speed/quality comparisons. |

### 3.2 Pages not accessible or not individually reviewed

| Item | Status |
|---|---|
| [Playground](https://console.typesafe.ai/playground) and console | Requires login; not accessed. No API key was used. |
| Blog index (`typesafe.ai/blog`) and "The Bitterest Lesson" post | Returned 404 at the URLs tried; the "AI: too good to be true, too bad to be useful" post (2026-06-19) returned only header/footer content to the extractor. Not reviewed. |
| JavaScript SDK per-class reference pages (~60 pages) | Only the JavaScript overview page was reviewed; the class/interface pages were not individually read. |
| Python SDK `questions`, `responses`, `common`, `constants` reference pages | Not individually read; covered indirectly by the usage and async-client pages. |
| Full text of legal documents (DPA, MCA, privacy policy) | Only the legal index page was read. |

### 3.3 Documentation gaps that affect design

| Gap | Why it matters | Where noted |
|---|---|---|
| **No calibration curves, ECE, or accuracy-vs-confidence plots** for any task; only a two-bucket example (n = 60). | The entire value proposition of confidence gating depends on this. | [Classification using confidence](https://docs.typesafe.ai/cookbooks/classification_using_confidence); confirmed as a gap by third parties ([agentpedia](https://agentpedia.codes/blog/jev-system-one-models)). |
| **`confidence` formula undisclosed.** | Cannot reason about its properties; independent testers found max-probability better calibrated. | [Confidence](https://docs.typesafe.ai/confidence) |
| **Architecture, parameters, training data, RLCD details undisclosed.** | Cannot assess generalization or contamination. | [Launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev) |
| **No SLA, uptime, hosting region, or p95/p99 latency under load.** | Agent loops are latency-sensitive; third parties report outages of minutes and tail latencies of tens of seconds. | [Legal](https://docs.typesafe.ai/legal); [teatree issue](https://github.com/souliane/teatree/issues/4819); [Aman Kumar](https://amankumar.ai/blogs/jev-measured) |
| **Rate limits "adjusting dynamically"**; one independent study had to cut its sample from 300 to 208 because of rate limits. | Multi-seed evaluations may be throttled. | [Models](https://docs.typesafe.ai/models); [jev-baselines-eval](https://github.com/ickma2311/jev-baselines-eval) |
| **Version and deprecation policy** for aliases. | `jev-latest` was observed resolving to a new version during a run. | [Consistency: Choices](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook) |
| **Minor inconsistency:** the Choice page's request example uses a `selectedModels` array while every other page uses a `model` string. | Suggests an API field in flux; pin to the API reference. | [Choice](https://docs.typesafe.ai/primitives/choice) vs [API](https://docs.typesafe.ai/api) |
| **Pricing sustainability** explicitly unproven by the vendor ("we can't prove it isn't subsidized"). | Cost-based conclusions may not hold. | Reported in [Flowtivity](https://flowtivity.ai/blog/jev-typesafe-ai-decision-model/) quoting vendor footnotes |

---

## 4. Verified capability assessment

### 4.1 Identity, access, and pricing

| Item | Value | Source | Label |
|---|---|---|---|
| Endpoint / auth | `POST /v1/systemone`, `Authorization: Bearer` | [API](https://docs.typesafe.ai/api) | Verified |
| Input | `state`: string, JSON object, or array of text; text only; English primary | [State](https://docs.typesafe.ai/concepts/state), [Models](https://docs.typesafe.ai/models) | Verified |
| Output | `answers` keyed by question id: Choice → `choice`, `probabilities`, `confidence`; Score → `score`, `legend`, `probabilities`, `confidence`; Noul → `noul`; plus `model`, `usage` | [API](https://docs.typesafe.ai/api) | Verified |
| Limits | Choice ≤ 255 options; Score 2–10 levels; 64k tokens per request; 32k for state + longest question | [API](https://docs.typesafe.ai/api), [Models](https://docs.typesafe.ai/models) | Verified |
| Pricing | $0.042 per million input tokens; output free | [Models](https://docs.typesafe.ai/models) | Verified (list price) |
| Rate limits | 250,000 tokens/s; 1,200 requests/min; dynamic | [Models](https://docs.typesafe.ai/models) | Verified (stated) |
| Data handling | Not used for training; ZDR for enterprise | [Models](https://docs.typesafe.ai/models), [Legal](https://docs.typesafe.ai/legal) | Verified (stated) |
| Access | Early access; Vercel AI Gateway; OpenRouter listing | §1 | Verified |

### 4.2 Performance evidence

**Latency.**

| Source | Setting | Result | Label |
|---|---|---|---|
| Vendor launch post | "End-to-end" | 70–500 ms; demo 0.114 s vs 8.566 s for GPT-5.6 Terra | Vendor |
| Vendor how-to-build | — | "~100 ms" | Vendor |
| Vendor cookbooks | 14-question and 8-question rubric calls, sequential | 111 ms and 114 ms mean | Vendor (cached) |
| Vendor skill-suggestion cookbook | Two requests over a 182-skill roster | "~12 seconds" for the full cycle | Vendor (cached) |
| Vendor evals dashboard | Per case, four workflows | 0.3–0.5 s | Vendor |
| Every (Mike Taylor / Dan Shipper) | 12 passages, 4 checks each | 0.35 s median per passage vs 8.83 s for Claude Fable 5.1 at high effort | Independent |
| jev-baselines-eval | Banking77/CLINC150, one call per item | 0.44 s median, 0.71 s p95; nano LLM 0.85/1.52 s; frontier 1.51/5.57 s; ratio 2.2× on same items, "not a measurement of model inference speed" | Independent |
| jev-phishing-bench | From France | 239 ms p50 (network floor 163 ms) vs Haiku 4.5 687 ms | Independent |
| jev-benchmark (tool-call risk) | 60 calls | 421.6 ms p50, 542 ms p95 | Independent |
| Aman Kumar | 20 concurrent | 0.8–0.9 s median; at 100 concurrent, rare calls of 10–35 s | Independent |
| wotai-dev | 149 rows | 455 ms p50 vs Haiku 631 ms; measured speedup 1.4–3.7×, not 20–200× | Independent |

**Cost.** List price is verified. Independent cost ratios vs LLMs range from about 5× (vs a low-reasoning small LLM on 2–4 options) to about 580× (vs a frontier model at high effort), because the ratio is dominated by the comparison model's output tokens and reasoning ([Aman Kumar](https://amankumar.ai/blogs/jev-measured); [Every](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds)). Good Start Labs computed $160 per million verdicts for Jev vs $260 for DeepSeek V4.1 Flash, $400 for GPT-5.6 Luna, and $33,000 for Claude Fable 5.1 ([Good Start Labs](https://goodstartlabs.com/research/verification-is-the-bottleneck)). The vendor's own 193.6× / 444.6× figures are described by the vendor as "the higher end of real world gains" against LLMs run through its probability-requesting adapter.

**Accuracy: vendor evaluations.** The [evals dashboard](https://evals.typesafe.ai) scores agreement with a reference formed by averaging GPT-6 Astra and Claude Fable 5.1 at high thinking, not human ground truth. Aggregate over four workflows: Jev 67.8% at $0.0004 and 0.4 s per case; best comparator Sol (workflow) 74.1% at $0.0836 and 23.3 s; Opus 5 (workflow) 73.1%; Terra (workflow) 67.9%; Sonnet 5 (workflow) 67.8%. Per workflow, Jev: security incidents 61.7% (best 66.2%), agent-trace observability 71.6% (best 76.6%), invoice processing 61.8% (best 79.1%), customer service 76.0% (best 78.3%). The dashboard also shows every LLM scoring higher in the decomposed "workflow" harness than with the same policy as a single prompt. **Label: claimed by developer; method self-disclosed; not accuracy.**

**Accuracy and efficiency: vendor cookbooks.** All run by TypeSafe with cached responses, mostly on `jev-1.12`; inspectable but not independent. **Label: claimed by developer.**

| Cookbook | Setup | Reported result |
|---|---|---|
| [Parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions) | 13 questions over a ~54k-character GDPR article, 5 repeats | One batched call vs 13 sequential calls: 12.2Ã cheaper, 10.0Ã faster; answers unchanged |
| [Skill suggestion](https://docs.typesafe.ai/cookbooks/skill_suggestion) | 182 skills, 488 requests, Claude Haiku 4.5 agent | Wrong loads 16.8% â 7.3%; needless loads 9.8% â 4.0%; two requests per cycle, "~12 seconds" with caching |
| [Re-ranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe) | CLERC legal corpus, 40 queries Ã 30 BM25 candidates | Top-1 5% â 18%; top-10 38% â 62%; 1,200 calls for -e.0645 |
| [Classification using confidence](https://docs.typesafe.ai/cookbooks/classification_using_confidence) | 60 SEC filings, 75 groups | Confidence â¥ 0.9: 27/30 correct; < 0.9: 12/30; fallback to broader division lifts unsure cases to 21/30 |
| [Citation check](https://docs.typesafe.ai/cookbooks/citation_check) | RFC 7519, 8 citations (4 corrupted) | 8/8 correct; unsupported case flagged at confidence 0.27 |
| [LLM guardrails](https://docs.typesafe.ai/cookbooks/llm_guardrails) | 10 prompts, 5 replies | Expected routing on all; melatonin-dosage question at 0.55 sent to review |
| [Classifying RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages) | 81 passages, 6 queries, one planted injection | Injected passage ranked #1 by similarity, caught by injection score 0.99; ~2 s median per passage |
| [SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade) | 100 extraction prompts; mini LLM â Jev per-field verifier â reasoning LLM | Cascade frontier "up-and-left of every single model"; described as a "historical snapshot" |
| [Hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification) | 4 labeled examples, beam width 3 | Beam 4/4 vs greedy 2/4 |
| [Structure recovery](https://docs.typesafe.ai/cookbooks/autoformat) | One ~800-word memo, two dependent requests | 78 questions, 0.8 s, -e.0003 |
| [Self-consistency (Nouls / Choices)](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook) | One claim / one post, 15 repeats | Jev 111â114 ms and ~-e.00004 per rubric call vs Claude Haiku 4.5 1.8â3.9 s; label agreement 90.8% â 99.2% with a 0.60 abstention band |
| [Function calling](https://docs.typesafe.ai/cookbooks/function_calling) | 10 functions, 28 closed-set arguments | Per-command confidence = minimum over argument judgments; no accuracy benchmark |

**Accuracy: independent measurements.**

| Study (date) | Task, n | Jev | Comparators | Label |
|---|---|---|---|---|
| [Aman Kumar](https://amankumar.ai/blogs/jev-measured) (2026-09-18) | Enron spam 300; SST-2 300; AG News 300; Banking77 300 | 98.7; 95.7; 91.3; 76.0 | GPT-5.4-mini 97.7; 92.7; 88.3; 78.7 · GPT-5.6-Luna 98.0; 93.0; 89.7; 81.7 | Independent |
| Same | Production page gates (1,005 each) and email triage (800), outcome-labeled | "Filter, not replacement": P&lt;0.1 was 99.7% correct on 82% of items; middle band 0.1–0.9 was 6–83% correct; value extraction 68.6% with probability swings of 0.5 between runs | Existing LLM pipeline | Independent |
| [jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) (2026-09-17) | PhishNChips v5.2, 2,000 emails | 62.6% [60.5–64.7]; AUROC 0.689; ECE 0.154 | Claude Haiku 4.5 81.3%; AUROC 0.837; ECE 0.097. Regex baseline 91.6%. Five narrow Jev signals + logistic regression 95.0%, AUROC 0.982, ECE 0.027 (Haiku on same signals 93.2%). A 4B model LoRA-tuned on 1,000 emails: 97.4%, ECE 0.010 ([issue #1](https://github.com/anisselbd/jev-phishing-bench/issues/1)) | Independent |
| [jev-spam-eval](https://github.com/bitnovus/jev-spam-eval) | 5,733 (main) and 3,300 (fresh) emails, 3-way | Text-only 93.62%; with URL/header enrichment 97.98%; with evidence-focused wording 98.64% | TF-IDF logistic regression 98.74–98.87%; on 853 recent phishing, Jev recall 95.31% vs LR 75.26% | Independent |
| [jev-baselines-eval](https://github.com/ickma2311/jev-baselines-eval) (2026-09-18, pre-registered) | Banking77 n=208; CLINC150 n=200 | 0.832; 0.870 | GPT-5.4-nano 0.793; 0.795 · GPT-5.6 Terra 0.875; 0.915 · bge-small + logistic regression 0.933 (Banking77). Cascade to 90.5%: Jev escalates 22.0% vs nano 48.5%, 95% CI for the difference [−0.53, +0.60], verdict "AMBIGUOUS" | Independent |
| [jev-benchmark](https://github.com/themsquared/jev-benchmark) (2026-09-17) | Agent tool-call risk, 60 hand-labeled | 91.7% overall; 100% clear (34), 71.4% ambiguous (14), 91.7% adversarial (12); every wrong answer had confidence &lt; 0.8 | None (no LLM keys) | Independent |
| [wotai-dev](https://github.com/wotai-dev/typesafe-jev-tools) | 149-row primary task; two secondary | 66.0% (ECE 0.121); business category 79.9%; commit type 50.0% | Haiku 4.5: 66.0% (ECE 0.122); 83.2%; 42.0%. Jev flagged uncertainty on 34.7% vs 2.7% | Independent |
| [Every](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds) (2026-09-15) | 12 synthetic passages, 7 planted defects | 6/7 | Claude Fable 5.1 7/7 | Independent, tiny |
| [Good Start Labs](https://goodstartlabs.com/research/verification-is-the-bottleneck) (2026-09-15) | 6,003 rubric checks on 1,203 financial-research answers | 91.5% agreement with Fable 5.1; 86–92% with each of five LLMs | LLM–LLM agreement 88–95%; DeepSeek V4.1 Flash 93.5% agreement with Fable at $260 per million vs Jev $160. **No human ground truth.** | Independent (agreement only) |
| [fastbrowse](https://github.com/agent-labs-dev/fastbrowse) (Jev-first browser agent, self-reported by its authors) | 14 answer tasks × 3 passes | 40/42 passes, 17.0 s median, $0.011 per task | Hosted Browser Use 14/42, 27.5 s, $0.40; all 28 failures exceeded a $0.25 cap. Separate 21-task run: fastbrowse 61/63, jev-ultrafast 11/18 | Independent of vendor, not third-party reproduced |
| [Laya benchmark](https://huggingface.co/datasets/Luni/laya-jev-benchmark) | Phishing 2,000; typed-decisions 400 | 0.626; 0.727 | Laya 421M open-weights: 0.505 raw / 0.611 calibrated; 0.766 after fine-tuning on the benchmark | Independent (Laya's authors) |

**Reading across these:** Jev is competitive with or slightly better than small LLMs on short inputs with crisp labels, worse on long inputs requiring whole-document judgment (phishing bodies, invoices, value extraction), and generally below a supervised classifier trained on in-domain labels. Decomposing a hard judgment into several narrow questions and combining them in code repeatedly closed the gap (phishing 62.6% → 95.0%), which is exactly the vendor's design guidance.

### 4.3 Calibration evidence

The vendor documents calibration as a group-level property and provides one worked example: on 60 SEC filings classified into 75 groups, answers with confidence ≥ 0.9 were 27/30 correct (90%) and those below were 12/30 (40%) ([Classification using confidence](https://docs.typesafe.ai/cookbooks/classification_using_confidence)). No reliability curves or ECE are published by the vendor.

| Study | Setting | Finding | Label |
|---|---|---|---|
| [jev-ood-calibration](https://github.com/scienthoon/jev-ood-calibration) (2026-09-19, via Vercel gateway, 4,621 calls, ~$0.06) | Three public benchmarks; 900 rule-generated support tickets the model cannot have seen | In distribution: OpenBookQA ECE 0.024 at a 0.024 noise floor; CommonsenseQA 0.032 (floor 0.019); HellaSwag 0.029 (floor 0.018). Out of distribution: ECE 0.107 vs 0.024 floor (4.4×), refit temperature 2.74. **Per type:** Choice overconfident (T=3.29), Score overconfident (T=3.40, ECE 0.325 on an unknowable label with mean stated probability 0.74 at 44.7% accuracy), Noul underconfident (T=0.66). The vendor `confidence` field was less calibrated than max probability on every set (0.035 / 0.078 / 0.18). Exact-zero probabilities on correct options observed. | Independent |
| [Jev-Calibration (AnthusAI)](https://github.com/AnthusAI/Jev-Calibration) | 8,801 sentiment examples, `jev-1.13.0` | Raw ECE 0.117 (Noul) and 0.160 (Choice); above 0.95 confidence 100% accurate; 60–80% band only 54% accurate. Isotonic regression → ECE 0.008 / 0.016; ~100 labels already reach 0.048. Confidence separates right from wrong better than Llama 3.1-8B (AUROC 0.83 vs 0.72). | Independent |
| [jev-baselines-eval](https://github.com/ickma2311/jev-baselines-eval) | CLINC150 | Confidence exactly 1.0 on 102 of 200 items, 6 of them wrong; creates a discontinuity no threshold resolves. Error-ranking AUROC 0.853 (Banking77) but 0.734 (CLINC150), below the nano LLM's 0.816 there. | Independent |
| [jev-benchmark](https://github.com/themsquared/jev-benchmark) | 60 tool-call risk cases | ECE 0.071; every incorrect answer had hedged confidence; 50 of 60 predictions in the 0.9–1.0 bin at 98% accuracy. | Independent, small |
| [jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) | 2,000 emails | ECE 0.154 vs Haiku 0.097; label flips 2.2% between identical passes; wording changed accuracy by −4 to +0.6 points. | Independent |
| [Aman Kumar](https://amankumar.ai/blogs/jev-measured) | Public sets pooled | Confidence ≥ 0.9: 96% accurate (82% of items); below 0.9: 55–72%. Production: P(yes) &lt; 0.1 was 99.7% correct. | Independent |
| Samuel Sacco (reported by [Aman Kumar](https://amankumar.ai/blogs/jev-measured) and [jev-exploration](https://github.com/SamuelSacco/jev-exploration/issues/1)) | 800-item difficulty ladder | ECE 2.1–2.5× the noise floor; probabilities "overstate the low end and understate the high end"; everything ≥ 0.9 correct, covering 21–32% of items. | Independent (secondary report) |
| Vendor consistency cookbooks | 15 repeats of one claim / one post | Mean per-question probability SD 0.0102 (Noul) and 0.0098 (Choice); Claude Haiku 4.5 at temperature 0 was more repeatable (0.0012); reasoning LLMs 2.5–5.6× more variable than Jev. | Vendor (cached) |

**Assessment.** Probabilities are informative and rank errors reasonably well; they are not reliably calibrated out of the box on new tasks, the direction of miscalibration depends on primitive type, and the extreme bands (≥ 0.9, ≤ 0.1) are where independent testers found them trustworthy. Post-hoc recalibration with a few hundred labels works in the one study that tried it. Thresholds must be fitted per task, per primitive, per model version. **Label: claimed by developer as calibrated; independently supported as "useful after recalibration"; not supported as calibrated zero-shot out of distribution.**

### 4.4 Documented limitations

From [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) (all **verified in official documentation**):

| # | Failure mode | Documented workaround | Relevance to agents |
|---|---|---|---|
| 1 | Literal reading: answers the question as written, not the intent | State exact conditions; split ambiguous questions | Question wording becomes a versioned artifact |
| 2 | Math and numbers: "not a calculator"; counting unreliable; Score interpolation weakly calibrated | Arithmetic in code; use scores only for thresholds | Budgets, counts, and comparisons must stay in code |
| 3 | Date and time comparison: dates read as text | Extract components with Choice; compute in code | Deadlines and ordering in code |
| 4 | Indirection: double negatives, multi-hop, properties of properties | Direct instructions; name state parts | Excludes planning-level reasoning |
| 5 | Large state with irrelevant detail: accuracy falls ("context rot") | Filter in code; Noul relevance filter | Agent histories must be projected, not passed whole |
| 6 | Adversarial content: state not treated as hostile | Explicit criteria; test before production | Cannot be the security boundary |
| 7 | Contradictory instructions and criteria; counterintuitive mappings | Align wording | Criteria design discipline |
| 8 | No structural invariants: Noul vs Choice framings disagree (0.22 vs 0.01); complements sum to 1.19 | Do not transfer thresholds between primitives | Per-primitive calibration |
| 9 | Generation: "not trained to generate text" | Convert to bounded selection; use generative models | LLM required for arguments and text |

Additional documented constraints from official framework integrations: option-order sensitivity; Jev "does not revise answers when validators reject them"; may re-propose the same tool; no streaming; thresholds should be pinned to a Jev version ([Pydantic AI](https://pydantic.dev/docs/ai/models/typesafe/)). LangChain's tool-risk middleware "refuses risky calls. It does not request approval" and warns against sending secrets ([LangChain](https://docs.langchain.com/oss/python/integrations/providers/typesafe)). Vendor skill guidance: "Typed output guarantees the interface, not truth" ([SKILL.md](https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md)).

### 4.5 Capability assessment table (required format)

| Question | Finding | Source | Confidence |
|---|---|---|---|
| What does Jev actually do? | Evaluates typed questions (Choice, Score, Noul) against a text/JSON state and returns probabilities (plus a confidence statistic for Choice/Score). No text generation, no explanations. Multiple independent questions per request, evaluated in parallel. | [Introduction](https://docs.typesafe.ai/introduction), [System One](https://docs.typesafe.ai/concepts/system-one), [Primitives](https://docs.typesafe.ai/primitives) | Verified in official documentation |
| What inputs does it accept? | `state` as string, JSON object, or array of text; questions with `type`, `instructions` (string/object/array), `criteria`. Text only; English primary. ≤ 32k tokens for state + longest question. | [State](https://docs.typesafe.ai/concepts/state), [Advanced](https://docs.typesafe.ai/primitives/advanced), [Models](https://docs.typesafe.ai/models) | Verified |
| What outputs does it produce? | Per question: Choice `choice`/`probabilities`/`confidence`; Score `score`/`legend`/`probabilities`/`confidence`; Noul `noul`. Plus `model` and token `usage`. | [API](https://docs.typesafe.ai/api) | Verified |
| What are Choice, Score, and Noul? | Choice: one of ≤ 255 unordered options. Score: position on 2–10 ordered, described levels; probability-weighted mean. Noul: probability a statement is true; no separate confidence. | [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul) | Verified |
| How are confidence estimates represented and interpreted? | `confidence` ∈ [0,1], "a statistic computed from the probability distribution", formula undisclosed; interpreted as peakedness; three-band routing suggested; calibration defined at group level. Independently: max probability better calibrated than `confidence`; OOD miscalibration 4.4× floor; type-dependent direction; recalibratable. | [Confidence](https://docs.typesafe.ai/confidence); [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer); §4.3 studies | Representation verified; calibration claimed by developer, partially supported independently |
| Which agent tasks could it plausibly support? | Intent/route classification; tool or skill pre-selection from a catalog; relevance and injection screening of observations; claim-vs-evidence verification; advisory risk classification of proposed actions; escalation gating via confidence. Not: planning, argument/text generation, arithmetic, multi-hop reasoning, security boundary. See DP1–DP7 in [ARCHITECTURE.md §3](ARCHITECTURE.md#3-decision-point-taxonomy). | [Use case map](https://docs.typesafe.ai/concepts/use-case-map); cookbooks; §4.2 | Routing/classification: verified and independently supported. Tool pre-selection: vendor-supported. Progress monitoring: plausible but untested. |
| What integration mechanisms are documented? | HTTP API; Python and JavaScript SDKs (sync/async, retries, typed answers); coding-agent skill; official LangChain (`langchain-typesafe`) and Pydantic AI (`TypeSafeModel`) integrations; Vercel AI Gateway and AI SDK `experimental_evaluate`; MIT LLM-backed adapter for comparisons. | §3.1; [LangChain](https://docs.langchain.com/oss/python/integrations/providers/typesafe); [Pydantic AI](https://pydantic.dev/docs/ai/models/typesafe/); [Vercel](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway) | Verified |
| What limitations or unknowns remain? | Documented: nine failure modes (§4.4). Unknown: architecture, training, calibration curves, SLA, hosting region, tail latency under load, pricing sustainability, alias/deprecation policy. Early access status. SDK breaking changes days apart. | §3.3, §4.4 | Limitations verified; unknowns are unknown |

---

## 5. Existing systems and related work

This section condenses three literature surveys commissioned for this report (agent frameworks and tool calling; routers, cascades, and classifiers; uncertainty-aware agents and evaluation). Full source lists are in §13.

### 5.1 Agent frameworks, tool calling, and durable execution

**How frameworks choose the next action.** In every major agent SDK (LangChain `create_agent`, OpenAI Agents SDK, Claude Agent SDK, Pydantic AI, Google ADK, CrewAI agents, smolagents) the LLM picks the next action by emitting a tool call; multi-agent handoff is the same mechanism dressed as a `transfer_to_<agent>` tool ([OpenAI handoffs](https://openai.github.io/openai-agents-python/handoffs/), [ADK](https://adk.dev/workflows/collaboration/), [Claude subagents](https://code.claude.com/docs/en/agent-sdk/subagents)). Graph layers move decisions into deterministic callables: LangGraph `add_conditional_edges` ([docs](https://docs.langchain.com/oss/python/langgraph/graph-api)), CrewAI Flow `@router` ([docs](https://docs.crewai.com/en/concepts/flows)), ADK router nodes ([docs](https://adk.dev/graphs/routes/)), `pydantic_graph` return-type unions ([docs](https://pydantic.dev/docs/ai/graph/graph/)). Anthropic's design guidance frames this as workflows (predictable) vs agents (model-driven) ([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)).

**Decision seams already exist.** Every framework exposes a pre-action interception point whose contract is "a callable returning an enum, a boolean, or a node name": Claude Agent SDK `PreToolUse` → `allow|deny|ask|defer` ([hooks](https://code.claude.com/docs/en/agent-sdk/hooks)); LangChain middleware `wrap_tool_call` / `wrap_model_call` that can short-circuit ([middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom)); OpenAI `@tool_input_guardrail` and `needs_approval` ([guardrails](https://openai.github.io/openai-agents-python/guardrails/), [HITL](https://openai.github.io/openai-agents-python/human_in_the_loop/)); ADK `before_tool_callback` and `require_confirmation` ([callbacks](https://adk.dev/callbacks/types-of-callbacks/), [confirmation](https://adk.dev/tools-custom/confirmation/)); Pydantic AI `prepare_tools`, `WrapperToolset`, `requires_approval` ([toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/), [deferred tools](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/)). Escalation is universally a boolean or callable, **never a probability**. Anthropic already inserts a model at this seam: Claude Agent SDK `permissionMode: "auto"` is "model-classified approvals" ([permissions](https://code.claude.com/docs/en/agent-sdk/permissions)).

**Tool calling and structured outputs guarantee shape, not probability.** OpenAI structured outputs and Anthropic strict tool use guarantee schema validity ([OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs), [Anthropic](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use)). Hosted APIs do not return probabilities over tool choices: OpenAI logprobs cover message content only and are to be removed for its newest reasoning models ([API reference](https://developers.openai.com/api/docs/api-reference/chat/create), [migration guide](https://developers.openai.com/api/docs/guides/latest-model)); Anthropic's Messages API has no logprobs and documents that forced `tool_choice` returns 400 on Claude Fable 5.1 and Mythos 5.1 ([define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)). Constrained-decoding libraries (Outlines, Guidance/llguidance, XGrammar) return the string, not a distribution; Outlines' request to add choice probabilities has been open since 2023 ([issue](https://github.com/dottxt-ai/outlines/issues/479)). Open-weight serving (vLLM `structured_outputs` `choice` plus `logprobs`, SGLang `return_logprob`) is the one path to a genuine option distribution ([vLLM](https://docs.vllm.ai/en/latest/features/structured_outputs.html)).

**Tool selection at scale.** Vendors already narrow catalogs before the model decides: Anthropic's Tool Search Tool with `defer_loading` for up to 10,000 tools, whose docs say accuracy "degrades once you exceed 30–50 available tools" ([Tool Search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)); OpenAI `allowed_tools` and "fewer than 20 functions" guidance ([function calling](https://developers.openai.com/api/docs/guides/function-calling)); MCP `tools/list`; Agent Skills' progressive disclosure ([Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)). BFCL treats *not calling a tool* as a first-class answer and weights hallucination measurement at 10% in V4 ([BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html), [categories](https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/TEST_CATEGORIES.md)); ToolRet finds strong IR models still weak at pure tool retrieval ([ToolRet](https://arxiv.org/abs/2503.01763)).

**Durable execution.** Temporal, Inngest, Restate, DBOS and LangGraph persistence all place non-deterministic model calls behind journaled step boundaries; Temporal's OpenAI Agents plugin puts "the agent loop, tool selection, and handoffs" in the Workflow and model calls in Activities ([Temporal](https://docs.temporal.io/develop/python/integrations/openai-agents)). A decision model's typed output fits this pattern as journaled, replay-safe state.

### 5.2 Model routers, cascades, and lightweight classifiers

**Routers.** RouteLLM trains strong-vs-weak win-probability routers on ~65k Chatbot Arena preference pairs; router overhead ≤ 0.4% of GPT-4 generation cost; routers trained on Arena data alone were near-random on MMLU/GSM8K until in-domain data was added ([paper](https://arxiv.org/abs/2406.18665), [blog](https://www.lmsys.org/blog/2024-07-01-routellm/)). Hybrid LLM predicts the quality gap with DeBERTa ([paper](https://arxiv.org/abs/2404.14618)). Arch-Router (1.5B) routes to natural-language policies at 51 ms on an L40S ([paper](https://arxiv.org/abs/2506.16655)). RouterBench found "none of the routing algorithms significantly outperform the baseline Zero router" (probabilistic mixing) ([paper](https://arxiv.org/abs/2403.12031)); LLMRouterBench (33 models, 391k instances) finds contemporary routers "nearly indistinguishable" and traces the gap to "model-recall failures" ([paper](https://arxiv.org/html/2601.07206v1)). Commercial routers (Martian, Not Diamond, OpenRouter auto-router) publish claims without named baselines ([Not Diamond](https://www.notdiamond.ai/), [OpenRouter](https://openrouter.ai/docs/guides/routing/routers/auto-router)).

**Cascades.** FrugalGPT uses a DistilBERT reliability scorer ([paper](https://arxiv.org/abs/2305.05176)); AutoMix uses k=8 self-verification samples plus a POMDP to absorb verifier noise ([paper](https://arxiv.org/abs/2310.12963)); MoT cascades on answer consistency and reaches ~40% of GPT-4 cost ([paper](https://arxiv.org/abs/2310.03094)). Theory: confidence-based deferral provably fails when the downstream model is a specialist, under label noise, and under distribution shift ([When does confidence-based cascade deferral suffice?](https://arxiv.org/abs/2307.02764)). RouterBench found cascades beat individual LLMs only when the correctness-judge error is ≤ 0.1 and "deteriorated rapidly" above 0.2. A 2026 decision-theoretic study found a lightweight *pre-generation* router beat the best cascade on four of five datasets because cascades pay the cheap model before deciding ([Is escalation worth it?](https://arxiv.org/abs/2605.06350)). **Implication for Jev:** its cheapness makes it a pre-generation classifier rather than a cascade rung, but its error rate on the specific decision, not its latency, determines whether a cascade gains anything.

**Small classifiers and verifiers.** SetFit matches RoBERTa-Large fine-tuned on 3k examples with 8 labels per class ([blog](https://huggingface.co/blog/setfit)); dual-encoder intent classifiers train in minutes on CPU for Banking77's 77 intents ([paper](https://arxiv.org/abs/2003.04807)); ModernBERT encoders run at millisecond latency ([paper](https://arxiv.org/abs/2412.13663)). Safety classifiers (Llama Guard 3/4, ShieldGemma, Prompt Guard 2 at 19–92 ms on an A100, OpenAI moderation, Anthropic Constitutional Classifiers) cover injection and policy screening ([Prompt Guard 2](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M), [Constitutional Classifiers](https://arxiv.org/abs/2501.18837)). NLI zero-shot classification (bart-large-mnli) gives entailment probabilities without training but modest accuracy ([Yin et al.](https://arxiv.org/abs/1909.00161)). **Laya** (Convai Innovations, Apache 2.0, 421M ModernBERT-large, 33–40 ms on a T4) is an open-weights model with the same three primitives and a similar RLCD-style objective using proper scoring rules; it needs fine-tuning to be competitive and degrades on 77-option Choice (0.425 vs Jev 0.870) ([model card](https://huggingface.co/convaiinnovations/laya)).

**LLM confidence.** Base models are well calibrated on lettered multiple choice; RLHF "hurts calibration significantly" ([Kadavath et al.](https://arxiv.org/abs/2207.05221), [GPT-4 report](https://arxiv.org/html/2303.08774v4)); chat-model probabilities are miscalibrated but still rank correctness ([paper](https://arxiv.org/abs/2402.13213)); verbalized confidence beats RLHF logprobs but is overconfident ([Tian et al.](https://arxiv.org/abs/2305.14975), [Xiong et al.](https://arxiv.org/abs/2306.13063)); confidence tokens trained into the model beat both ([Self-REF](https://arxiv.org/abs/2410.13284)). **Implication:** an LLM *can* provide usable option-level confidence for a same-interface baseline, via logprobs on open weights or via structured/verbalized probabilities on hosted models (which is what TypeSafe's adapter does), but it needs recalibration on the task just as Jev does.

**Methodological pitfalls documented in this literature:** wrong baselines (compare to best-single-model and Zero router), uncounted router/verifier cost, single cherry-picked thresholds, proxy ground truth from LLM judges, ignored distribution shift, saturated benchmarks, accuracy conflated with calibration, unreproducible vendor numbers, latency without hardware, no adversarial evaluation ([Rerouting LLM routers](https://arxiv.org/abs/2501.01818)). These map directly onto the controls in §9.

### 5.3 Uncertainty-aware agents, verifiers, and dual-process designs

**Asking for help with calibrated uncertainty.** KnowNo (robotics) applies split conformal prediction to option logprobs with ~400 calibration examples, reducing help requests 10–24% versus naive thresholding at matched success ([Ren et al. 2023](https://arxiv.org/abs/2307.01928)); Introspective Planning tightens the sets further ([Liang et al. 2024](https://arxiv.org/abs/2402.06529)). These assume fixed 4–5 option menus and exchangeable calibration data. For software agents: a Sept 2026 taxonomy proposes trajectory-checkpoint ECE and shows step-level calibration does not imply trajectory-level calibration, and that agents' self-reported confidence does not consistently beat a simple baseline ([arXiv 2609.07395](https://arxiv.org/abs/2609.07395)); agents "abstain never or too late" across 13 systems ([Agentic abstention](https://arxiv.org/abs/2606.28733)); simply permitting agents to quit raised safety +0.39 on a 0–3 scale ([Selectively quitting](https://arxiv.org/abs/2510.16492)); conformal sets for tool selection exist for single-shot choice ([Prune 'n Predict](https://arxiv.org/abs/2501.00555)) and online conformal thresholds for model orchestration on QA ([CCPO](https://arxiv.org/abs/2511.11828)).

**Proposer plus scorer.** SayCan multiplies an LLM's usefulness score by a learned affordance value function ([Ahn et al. 2022](https://arxiv.org/abs/2204.01691)); web agents gain 10–17 points from step-level value models and process reward models trained on preferences ([Web-Shepherd](https://arxiv.org/abs/2505.15277), [AgentPRM](https://arxiv.org/abs/2511.08325)); hybrid execution-based plus learned verifiers lift SWE-bench Verified from ~42% to 51% ([R2E-Gym](https://arxiv.org/abs/2504.07164)). The recurring condition for gains is that the scorer has information the proposer lacks (execution results, environment state, trained preferences), not that it is a separate model per se. Limits: imperfect verifiers impose an accuracy ceiling and optimal best-of-N is often below 10 ([Inference scaling fLaws](https://arxiv.org/abs/2411.17501)); best-of-N reward-hacks at large N ([paper](https://arxiv.org/abs/2503.21878)); cross-family verification beats self-verification and gains shrink as solver and verifier converge ([When does verification pay off?](https://arxiv.org/abs/2512.02304)); intrinsic self-correction does not help ([Huang et al. 2024](https://arxiv.org/abs/2310.01798)); parallel test-time scaling shows a "verification gap" for general agents ([paper](https://arxiv.org/abs/2602.18998)).

**Dual-process architectures.** "Thinking Fast and Slow in AI" and SOFAI are position papers ([Booch et al.](https://arxiv.org/abs/2010.06002), [SOFAI](https://arxiv.org/abs/2110.01834)); SwiftSage pairs a small fine-tuned model with GPT-4 on ScienceWorld ([paper](https://arxiv.org/abs/2305.17390)); Talker-Reasoner is an architectural proposal without a benchmark ([paper](https://arxiv.org/abs/2410.08328)); AdaptThink learns when to think on single-turn math (−53% tokens) ([paper](https://arxiv.org/abs/2505.13417)). HAL found that higher reasoning effort *reduced* accuracy in the majority of agent runs ([HAL](https://arxiv.org/abs/2510.11977)). **No controlled study isolates a decision/reasoning split from confounds in software-agent benchmarks with cost accounting.** Jev's own framing ("System One") is the vendor's, not an established category.

**Evaluation methodology.** "AI Agents That Matter" documents a retry baseline beating an elaborate agent at 1/50 of the cost and calls for accuracy–cost Pareto frontiers ([Kapoor et al.](https://arxiv.org/abs/2407.01502)); τ-bench introduced pass^k (GPT-4o pass^8 below 25% on retail) ([paper](https://arxiv.org/abs/2406.12045)); τ²-bench adds dual control ([paper](https://arxiv.org/abs/2506.07982)); the ABC checklist found τ-bench counted empty responses as success and SWE-bench Verified has insufficient tests ([ABC](https://arxiv.org/abs/2507.02825)); OpenAI retired SWE-bench Verified after an audit found flawed tests in 59.4% of hard tasks ([Epoch review](https://epoch.ai/benchmarks/swe-bench-verified/review)); log analysis is necessary for credible evaluation ([paper](https://arxiv.org/abs/2605.08545)).

### 5.4 What already exists specifically for Jev in agents

| Artifact | Type | What it does | Evidence it works |
|---|---|---|---|
| [LangChain `langchain-typesafe`](https://docs.langchain.com/oss/python/integrations/providers/typesafe) (2026-09-17) | Official integration | `TypeSafeClassifier` as a Runnable over messages; experimental `ModelRouterMiddleware` (route each run to a fast or strong model) and `AutoModeMiddleware` (Noul risk probability per tool call; refuses risky calls); custom `TriageMiddleware` example; LangSmith tracing | Vendor claims restated ("up to 200× faster and 400× lower cost"); no measurements |
| [Pydantic AI `TypeSafeModel`](https://pydantic.dev/docs/ai/models/typesafe/) | Official integration | Jev as a model: each output field becomes a question; route selection among tools then argument fill in a second request; `FallbackModel` on unsupported arguments or context overflow; hooks to judge tool calls | Extensive documented limitations; no measurements |
| [Vercel AI Gateway / AI SDK `experimental_evaluate`](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway) (2026-09-16); eve tool approval default; `fx` permission reviewer | Official (Vercel) | Gateway access; Jev as evaluator; permission review of coding-agent tool calls via Jev | No published measurements found |
| [jev-eval-agent](https://github.com/vinilana/jev-eval-agent) | Community harness | Compares LLM-direct tool selection (100 mocked tools) vs Jev pre-selecting one tool per step with a confidence-gated "done" check; 6 tasks, 8 LLMs; records steps, distractor calls, cost, latency | Results directory exists; **no aggregate numbers published in README**; single open issue asks for open-weights baselines |
| [fastbrowse](https://github.com/agent-labs-dev/fastbrowse) (Agent Labs, pre-alpha) and [jev-ultrafast](https://github.com/browser-use/jev-ultrafast) (Browser Use) | Community Jev-first browser agents | Code indexes page controls; Jev picks operation + target per step; LLM plans, reads, and types text; code gates irreversible actions and secrets | Self-reported head-to-head vs hosted Browser Use (§4.2); jev-ultrafast Google Flights search in 7.1 s |
| Routers: [JevRouter](https://github.com/BillionsBobby/JevRouter), [jev-tool-router](https://github.com/esinocchi/jev-tool-router), [jev-classifier](https://github.com/felpsdev/jev-classifier), `jev-router` variants | Community | Route requests to cheapest capable model / tool / subagent | None published |
| Context pruning: `fast-jev-compaction`, `pi-fast-jev-compaction`, `openclaw-jev-compaction`, `yoshi` | Community | Jev judges which tool-call history to keep instead of summarizing | Anecdotal "1M → 86K tokens"; "Jev sees tool calls, not outputs" limitation noted |
| Permission gates: `pi-verdict`, `jev-axi`, `jev-decisions` | Community | Allow/ask/deny per tool call | `jev-axi` self-reports 44/44 on labeled calls |
| MCP servers: `jev-mcp` (2), `decide-mcp`, `jev-use` | Community | Expose Jev decisions as MCP tools | None |
| [jevassert](https://github.com/dtduc-git/jevassert) | Community tooling | Record/replay regression tests with accuracy, ECE, Brier, coverage, cost, latency gates | Reusable for §9 |
| [awesome-jev](https://github.com/yibie/awesome-jev) | Index | 203 entries in 13 categories, 31 under "agent decisions"; maintainers warn "inclusion is not endorsement" and note bulk same-day scaffolded submissions | — |
| [JevBench](https://jevbench.xyz/methodology) | Independent aggregator | Tiered evidence (A–D), per-run limitations, cost calculator; "nothing qualifies as reproduced" | — |

### 5.5 Overlap, difference, reuse, and framework-vs-plugin

- **Overlap:** the original hypothesis (Jev for bounded decisions, LLM for reasoning, runtime for execution) is the vendor's own architecture guidance and is implemented in two official framework integrations, two browser agents, and dozens of community tools.
- **Genuinely different, if anything:** not the plumbing. What no one has published is a **controlled, pre-registered, end-to-end comparison with proper baselines and trajectory-level calibration measurement**. The evidence gap, not a missing framework, is the opportunity.
- **Reusable components:** LangChain middleware hooks or Pydantic AI `TypeSafeModel`/`FallbackModel` as the host; TypeSafe's MIT LLM-backed adapter as the same-interface baseline; jevassert's record/replay format; Laya as an open-weights alternative; τ²-bench / BFCL as environments; HAL/ABC checklists for methodology.
- **Framework vs plugin:** a new agent framework is not justified. All surveyed frameworks expose the needed decision seams; platform vendors are themselves moving into this layer (model-classified approvals, tool search, allowed-tools); frameworks churn quickly. What is missing as a component is a calibrated per-option probability with typed abstain/escalate outputs and cross-framework adapters, plus calibration-aware evaluation. The recommended shape is middleware plus an evaluation harness.

---

## 6. Critical analysis of the original hypothesis

### 6.1 The twelve questions

| # | Question | Assessment |
|---|---|---|
| 1 | Is separating decision-making from reasoning a useful abstraction? | **Useful as an engineering abstraction, unproven as a performance claim.** Making decisions explicit runtime constructs with typed answer spaces improves inspectability and testability regardless of which model answers them. The literature shows gains from a separate scorer *when it has information the proposer lacks*; the separation itself is not the mechanism (§5.3). |
| 2 | Aren't many decisions themselves a form of reasoning? | **Yes, and the docs agree.** Jev is documented to fail on indirection, multi-hop, arithmetic, and date comparison (§4.4). The decisions that qualify are single-hop pattern judgments over compact evidence: "is this passage relevant", "which of these tools matches", "does this reply refuse". Anything requiring deliberation must be decomposed in code or left to the LLM. |
| 3 | Can Jev decide better, faster, or cheaper than an LLM? | **Faster and cheaper: independently supported** (2–25× faster, 5–580× cheaper, depending on baseline). **Better: not supported.** Independent accuracy is at or slightly above small LLMs on short crisp tasks, below them on long or fuzzy ones, and below supervised classifiers (§4.2). The honest expectation is "cheaper decisions at equal or slightly lower accuracy". |
| 4 | Can tool calling, structured outputs, constrained decoding, or simpler classifiers achieve the same? | **Shape, yes; calibrated probability, mostly no on hosted APIs.** Structured outputs guarantee schema, not probability; hosted logprobs do not cover tool choices; constrained decoders return strings (§5.1). Open-weight serving with choice-masked logprobs can. Simpler classifiers: a bge-small + logistic regression beat Jev on Banking77 (0.933 vs 0.832) and a 4B LoRA on 1,000 labels beat it on phishing (97.4% vs 62.6%), but both need labels; Jev's distinctive property is zero-shot typed questions with probabilities. |
| 5 | Does adding Jev introduce latency, cost, complexity, or failure modes? | **Yes, all four.** Extra network calls per step (0.3–0.9 s median, tails of tens of seconds under load), extra tokens, projection-building code, threshold maintenance per version, an additional vendor dependency with early-access status and dynamic rate limits, and new failure modes (context overflow, option-order sensitivity, adversarial steering). Whether the net is positive is the MVP question. |
| 6 | Could Jev make a locally reasonable but globally wrong decision? | **Yes, by construction.** Each question is evaluated in isolation against a projection; Jev has no memory of goals beyond what the projection contains, and accuracy degrades if the projection is enlarged (context rot). Global objectives must be injected into projections deterministically (acceptance criteria, current sub-goal), and completion must be verified by code ([ARCHITECTURE.md §5–§7](ARCHITECTURE.md#5-agent-lifecycle-and-data-flow)). |
| 7 | How should uncertainty and disagreement be handled? | Confidence bands per decision point fitted from labels; max probability as the gating statistic by default; Jev advisory so the LLM proceeds within permissions on disagreement; disagreements logged as the most valuable labels; Noul and Choice framings treated as different questions ([ARCHITECTURE.md §6](ARCHITECTURE.md#6-model-interaction-and-orchestration-strategy)). |
| 8 | Which decisions should remain deterministic software? | Everything Jev is documented to do badly and everything with authority: arithmetic, counting, dates, budgets, schema validation, permission lists, secret handling, side-effect verification, loop caps, and final success determination. The vendor's own guidance is "use code when possible". |
| 9 | How should global objectives, memory, and long-term goals influence local decisions? | Through deterministic projection: the runtime places the task spec, acceptance criteria, and current plan step into each decision's state; long-term memory enters only through retrieval that is itself relevance-filtered. Jev has no cross-request state. |
| 10 | Does Jev's documented functionality align with autonomous agents' requirements? | **Partially.** It aligns with per-step triage, routing, and verification over bounded options. It does not align with planning, argument generation, long-context reasoning, or safety-critical gating. The vendor's smart-home demo itself uses an LLM to split compound requests. |
| 11 | General framework, or plugin/library/runtime? | **Plugin plus evaluation harness.** See §5.5. |
| 12 | What would make this meaningfully different from existing systems? | Rigorous evidence: pre-registered arms, same-interface LLM baseline, trained-classifier baseline, oracle and random controls, matched compute, pass^k, trajectory-level calibration, and released logs. Nothing in the Jev ecosystem has this yet. |

### 6.2 Status of each responsibility proposed for Jev

| Proposed responsibility | Status | Evidence |
|---|---|---|
| Classification / routing of intents | **Documented and independently supported** | Intent routing pattern; Banking77/CLINC150 studies |
| Tool / skill pre-selection from a large catalog | **Documented pattern; vendor-supported; independently plumbed but unmeasured** | Skill suggestion cookbook; jev-eval-agent (no numbers); Pydantic AI route selection |
| Next-action selection over an enumerated action space (browser) | **Independently demonstrated by project authors, not third-party reproduced** | fastbrowse, jev-ultrafast |
| Argument generation | **Unsupported** (no generation); closed-set arguments only | Jaggedness §9; function-calling cookbook |
| Planning / decomposition | **Unsupported** | System One page; smart-home demo delegates splitting to an LLM |
| Verification of claims against evidence | **Vendor-supported (small); independently supported as agreement, not accuracy** | Citation check (8 cases); Good Start Labs 91.5% agreement |
| Guardrails / injection screening | **Vendor-supported; adversarial content is a documented weakness** | Guardrails and RAG cookbooks; jaggedness §6; 1/12 adversarial miss |
| Progress monitoring (done / stuck / drift) | **Hypothetical** | Synthetic recipes only |
| Escalation via confidence | **Documented pattern; independently supported after recalibration; ambiguous in the one pre-registered cascade test** | Confidence docs; calibration studies; jev-baselines-eval |
| Memory / context pruning | **Hypothetical with community activity** | Compaction tools; no controlled evidence |
| Security boundary / authorization | **Unsupported; explicitly warned against** | Jaggedness §6; LangChain and vendor skill guidance |

### 6.3 Strongest arguments for and against

**For.** (1) The cost and latency advantages are real and independently corroborated in direction; they change what is affordable per step, which is the one thing an LLM-only loop cannot buy. (2) Probabilities over options are a genuinely missing primitive in hosted LLM APIs, and independent studies show they rank errors usefully and recalibrate with modest labels. (3) Decomposition into narrow questions repeatedly recovered accuracy in independent tests, matching the vendor's design philosophy and making the approach engineerable. (4) The plumbing exists in two major frameworks, so a project can spend its effort on evidence rather than integration.

**Against.** (1) Accuracy is not better than cheap LLMs and is worse than supervised classifiers; if labels exist, a small trained model is cheaper still and better calibrated. (2) Calibration is imperfect out of distribution and type-dependent; the vendor `confidence` field is the least calibrated statistic; saturation at 1.0 breaks thresholds; step-level calibration may not hold along trajectories. (3) Agent-loop overhead, tail latency under concurrency, early-access status, undisclosed architecture, SDK churn, and unproven pricing are real project risks. (4) Routers and cascades in the literature mostly fail to beat simple baselines once evaluated properly; there is no reason to assume Jev is exempt. (5) The idea is not novel as a system; its value depends entirely on producing evidence others have not.

---

## 7. Promising and unsuitable use cases

| Application | Problem | Decisions involved (DP) | Component split | Why separation might help | Jev's verified support for the role | Simpler alternatives | Improvement that would justify complexity |
|---|---|---|---|---|---|---|---|
| **Coding agents** | Tool-rich loops, risky shell actions, long histories | DP2 tool pre-selection; DP3 advisory risk; DP4 stuck detection; DP5 history pruning | LLM plans and writes code; Jev triages; code enforces permissions and tests | Cheap per-step checks over many tools | DP2 vendor-supported; DP3 91.7% on 60 cases; DP4/DP5 hypothetical | Allow-lists, Anthropic Tool Search, LLM self-checks | Fewer distractor calls and steps at equal pass^k; lower cost per solved task |
| **Research agents** | Relevance triage of many retrieved passages; citation verification | DP5 relevance/injection; DP6 claim support | LLM synthesizes; Jev screens per passage; code assembles evidence blocks | Per-item screening is expensive with an LLM | RAG-passages and citation cookbooks (vendor); Good Start Labs agreement | Cross-encoder rerankers, NLI models | Higher answer accuracy or lower cost at equal accuracy with more passages screened |
| **Browser / computer use** | Enumerable page controls; many steps | Next action (Choice over indexed controls); irreversible-action check | Jev selects action/target; LLM plans and types; code verifies | Cannot click a non-existent control; very low per-step cost | Self-reported 40/42 vs 14/42 (fastbrowse) | LLM-generated selectors; Browser Use | Third-party replication of the self-reported gains |
| **Customer support agents** | Intent, urgency, escalation | DP1 intent; DP7 escalation | Jev routes; LLM answers; code handles deterministic lookups | Canonical vendor use case | Intent routing pattern; Banking77-class accuracy | Fine-tuned intent classifier if labels exist | Lower cost with equal CSAT/resolution; fewer wrong routes |
| **Workflow automation** | Many bounded judgments over documents | Composite scoring; verification cascades | Jev scores; code combines; LLM only on escalation | The vendor's core positioning | Evals dashboard (agreement); SDE cascade (vendor) | Rules; supervised models | Pareto improvement in cost vs quality on human-labeled data |
| **RAG** | Noisy retrieval, false premises, injected passages | DP5 per-passage | Jev filters; LLM generates | Cheap filtering before generation | RAG-passages cookbook (vendor, 81 passages) | Rerankers; injection classifiers | Fewer hallucinations / injections at equal recall |
| **Multi-agent orchestration** | Which subagent handles a subtask; whether a report warrants waking a parent | DP1/DP7 | Jev routes; LLM agents execute | Cheap routing between agents | Community only (JarvisCore) | Handoff tools; deterministic routers | Fewer unnecessary escalations |
| **AI infrastructure / observability** | Grading traces at scale; regression gates | DP6 as offline judge | Jev grades; LLM judge on disagreements | Volume makes LLM judges expensive | Good Start Labs, Langfuse, Arize (agreement only) | LLM-as-judge; rubric graders | Agreement with human labels at a fraction of cost; disagreement mining |
| **Long-running autonomous agents** | Drift, loops, false "done" | DP4 | Jev monitors each step; code verifies completion | Only affordable with a cheap judge | **Untested** | Loop counters; periodic LLM reflection | Earlier stuck detection, fewer wasted steps, no loss in pass^k |

**Where the architecture is likely unnecessary or harmful:** short single-tool tasks (overhead dominates); tasks whose decisions need whole-document reasoning or arithmetic; any place where Jev would be the authorization boundary; deployments needing an auditable rationale for each decision (Jev returns none); tasks with abundant labels where a trained classifier is cheaper and better; non-English inputs (documented lower accuracy).

---

## 8. Research gate assessment

**Assessment: MODIFY.**

**Why not GO.** The original concept, a general-purpose framework in which Jev handles "structured decisions, classifications, routing, action selection" for agents, rests on capabilities that split three ways: routing and classification are documented and independently supported; tool pre-selection and verification are vendor-supported but unmeasured in agent loops; action selection as the default mechanism, planning-adjacent decisions, and progress monitoring are hypothetical or unsupported. The framework itself would have weak novelty against official LangChain and Pydantic AI integrations. Building the framework first would spend most effort on plumbing that already exists.

**Why not STOP.** The speed and cost properties are independently corroborated in direction; probabilities over options are a real missing primitive in hosted LLM APIs; independent calibration studies show the signal is recalibratable; the plumbing exists so a project can go straight to measurement; and the research question (§10) is open in the literature independent of Jev. The one pre-registered cascade test was ambiguous, not negative.

**What MODIFY means.** Redesign the project around the narrow, supported capability: bounded, single-hop, closed-set judgments over compact state with confidence gating. Make **capability validation on the project's own data the first milestone** (Phase 0 in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)), then an offline decision-point benchmark, then a pre-registered live comparison at two decision points. Treat Jev as one pluggable decision component; the harness must be complete without it.

**Evidence relied on:** §3–§5. **Key uncertainties:** DP2 accuracy on real catalogs; DP4 feasibility; calibration along trajectories; net latency in loops; vendor stability (§12). **Assumptions:** A1–A7 in [ARCHITECTURE.md §12](ARCHITECTURE.md#12-design-assumptions) and R1–R5 in [DECISION_LOG.md §2](DECISION_LOG.md#2-major-assumptions).

**Distinguishing the general research direction from Jev:** the question of how agents should allocate decisions across cheap calibrated components, LLMs, and code is worth studying regardless of Jev; Jev is currently the most accessible instance of a zero-shot typed-decision model, with Laya as an open-weights alternative and an LLM-backed adapter as a same-interface baseline. The gate is a project decision, not a verdict on Jev.

---

## 9. Evaluation methodology

All experiments below are **future work**. None have been conducted. Numbers are targets or thresholds, not results. The concrete arms, metrics, and gates are specified in [IMPLEMENTATION_PLAN.md §5–§6](IMPLEMENTATION_PLAN.md#5-phase-1--offline-decision-point-benchmark-610-weeks).

### 9.1 Systems compared

1. **LLM-only agent** (full catalog, LLM self-reports completion).
2. **Jev-only workflow**, only where appropriate: offline decision datasets (DP1/DP2/DP4 instances) where Jev answers without an LLM; not as a full agent.
3. **Jev + LLM hybrid** at DP2 and DP4 ([ARCHITECTURE.md §4](ARCHITECTURE.md#4-recommended-architecture-decision-gated-llm-agent)).
4. **Alternatives at the same interface:** LLM answering the same typed questions via TypeSafe's MIT adapter; fine-tuned encoder; Laya; deterministic rules; oracle and random controls; LLM-only with matched extra compute.

### 9.2 Benchmark tasks

Primary candidates: τ²-bench domains with an enlarged, distractor-rich tool catalog; BFCL v3 multi-turn; a purpose-built 100+-tool mocked catalog extending jev-eval-agent. Offline decision datasets are derived from LLM-only trajectories plus human labels on ambiguous cases. SWE-bench Verified is excluded (contamination and flawed tests). Rationale and selection process: [IMPLEMENTATION_PLAN.md §8.1](IMPLEMENTATION_PLAN.md#81-benchmark-candidates-resolve-in-t07).

### 9.3 Metrics

| Metric | Purpose | Operationalization |
|---|---|---|
| End-to-end task success | Does the agent complete the task? | pass^k for k ∈ {1, 4, 8} with bootstrap 95% CIs |
| Cost per successful task | Is the hybrid economically useful? | All tokens and calls, including Jev and fallbacks, in USD ÷ successes |
| End-to-end latency | Does it improve response time? | Wall-clock p50/p95 per task |
| Decision accuracy | Are its decisions correct? | DP2 top-1/top-3 vs ground truth; DP4 vs outcome-derived labels; offline and in-loop |
| Tool-call validity | Does it produce valid actions? | Schema-valid and permitted calls ÷ total; distractor-call rate |
| Robustness | Ambiguous or changing situations? | Performance on ambiguous-labeled subset; wording/order perturbations; adversarial observations |
| Escalation rate | How often is more reasoning or a human needed? | Fraction of decisions routed to fallback/human; coverage at target precision |
| Failure recovery | Recovery from wrong decisions or tool failures? | Recovery rate and steps-to-recover after injected tool errors |
| Calibration | Is confidence trustworthy? | ECE with noise floor, reliability tables, AUROC for error ranking, per DP and per primitive; ECE per trajectory checkpoint |

### 9.4 Controls and how to avoid misleading comparisons

- **Same-interface baseline.** The strongest confound is "typed decision points help regardless of model". Arm A2 (LLM via adapter, identical projections and questions) isolates Jev's contribution.
- **Matched compute.** Arm A6 gives the LLM-only agent the same extra budget the hybrid spends on Jev.
- **Structure control.** Arm A5 uses random decisions through the same policy table; any gain of A1 over A5 is attributable to decision quality, not to narrowing per se.
- **Oracle upper bound.** Arm A4 shows whether the decision points chosen matter at all in the benchmark.
- **Calibration ablation.** Arm A7 disables confidence gating.
- **Pre-registration** of arms, thresholds, seeds, and analysis; thresholds fitted on a disjoint calibration split; no threshold changes after seeing test results.
- **Cost accounting** of every call; report accuracy–cost Pareto frontiers, not single points.
- **Reliability** via pass^k and ≥ 3 seeds; report CIs.
- **Version pinning** of Jev (explicit version, assert on `model`) and LLM snapshots; scaffold fixed.
- **Ground truth** from benchmark outcomes and human labels, never from an LLM judge alone; where an LLM judge is used for auxiliary labels, use a different model family than the agent.
- **Log inspection** for shortcuts and benchmark gaming; release logs and the record/replay cache.
- **Adversarial slice** for DP2/DP4/DP5 with injected instructions in observations.

### 9.5 Ablations

Remove or replace one element at a time: decision component (Jev / adapter / encoder / Laya / rules); confidence gating on/off; projection size (3 / 5 / 10 recent actions); two-stage vs single-stage tool selection; DP2 alone, DP4 alone, both; question wording variants; option order permutations; catalog size (20 / 50 / 100 / 255); concurrency (1 / 4 / 8).

### 9.6 Failure analysis

Categorize every wrong decision: distractor tool; long or irrelevant state; wording ambiguity; unknowable from projection; adversarial content; version drift; saturation at 1.0. Report by category with examples; treat disagreements between components as the primary labeling queue.

### 9.7 Reproducibility

Record/replay cache of all model responses committed with results; raw per-decision JSONL; pre-registration hash; environment lockfile; exact catalog versions; one command regenerates every table without API calls; public or synthetic data only.

---

## 10. Broader research opportunity

**Question:** *How should an autonomous agent allocate decisions and reasoning across specialized models, general-purpose LLMs, and deterministic software?*

Relevant threads and what they establish (§5.3): conformal asking-for-help works for fixed menus in robotics; step-level calibration does not imply trajectory-level calibration; agents abstain too late; scorers help when they hold information the proposer lacks; imperfect verifiers cap gains; cascades and routers usually fail against proper baselines; higher reasoning effort can hurt agents. None of this has been tested with a **cheap, zero-shot, typed-decision model whose cost makes per-step querying affordable**.

**Primary, concretely testable research question (proposed):**

> In tool-use agent benchmarks with pass^k and full cost accounting, does a calibrated bounded-decision component that outputs one of {proceed, verify, ask, escalate} at each step, with thresholds fitted by conformal or isotonic calibration on trajectory outcomes, achieve a target reliability with fewer interventions and lower cost than (a) LLM self-reported confidence, (b) an LLM answering the same typed questions, and (c) a supervised classifier, and does its calibration hold across trajectory checkpoints?

**Secondary questions** (each open per §5.3): which uncertainty signal should feed the gate (option probabilities, verbalized confidence, sample agreement, cross-family verifier); whether uncertainty-triggered verification preserves best-of-N gains at 30–70% of the cost; whether per-step reasoning-effort routing driven by the gate beats fixed effort; how fast coverage degrades under scaffold and task drift and whether online recalibration restores it; whether a decision policy can be learned from bandit outcome feedback without Goodharting on an imperfect verifier; whether the split raises pass^k more than pass@1.

**What would make the contribution meaningful beyond integrating two models:** (1) a decision-point taxonomy with ground-truth extraction from trajectories, reusable across frameworks; (2) trajectory-level calibration measurement of a non-LLM decision component, which does not exist; (3) pre-registered controls that separate "typed decisions", "extra compute", and "this specific model"; (4) a negative result would itself be publishable given the vendor and community claims.

**Themes covered:** adaptive model selection (DP7), uncertainty-aware routing (§6.1 Q7), cost-aware inference (§5.2), decision policies (policy table vs learned), model specialization (Jev vs encoder vs LLM), learning from execution outcomes (bandit gate, Phase 3), coordination between specialized models (disagreement mining), reliability and safety of delegated decisions (advisory-only authority, adversarial slices).

---

## 11. Key findings, limitations, and uncertainties

**Key findings.**
1. Jev is a narrowly scoped, well-documented decision model with real speed and cost advantages and a clearly documented list of things it cannot do.
2. Its accuracy is competitive with cheap LLMs on short, crisply labeled judgments and below them (and below supervised classifiers) on hard or long-input judgments.
3. Its probabilities are informative but not reliably calibrated zero-shot out of distribution; recalibration with a few hundred labels appears to work; the vendor `confidence` statistic is the weakest gating signal in independent tests.
4. The proposed architecture already exists as official integrations; novelty must come from evidence.
5. No controlled end-to-end study of a decision model inside an agent loop exists, for Jev or otherwise.

**Limitations of this report.** No experiments were run; all third-party evidence is days old, small, unreproduced, and from authors of varying rigor; several vendor pages were unreachable; long pages were read through an extraction tool; pricing and behavior may change.

**Uncertainties.** DP2 accuracy on real catalogs; DP4 feasibility; calibration along trajectories; net latency in loops under realistic concurrency; vendor stability and pricing; whether Laya or an adapter-backed LLM would serve the research question equally well.

---

## 12. Remaining questions and evidence needed

| Question | Evidence needed | Who could produce it |
|---|---|---|
| Does Jev's calibration hold on agent-generated state? | Reliability curves per DP and per trajectory checkpoint on the project's own decision dataset | Phase 0–2 of this project |
| How accurate is DP2 on realistic catalogs of 50–255 tools with distractors? | Labeled decision set; comparison to LLM native choice and to a trained encoder | Phase 0–1 |
| Is progress monitoring (DP4) answerable from a compact projection? | Outcome-labeled trajectories; projection-size sweep | Phase 0–1 |
| Does the end-to-end hybrid beat matched-compute LLM-only? | Pre-registered arms A0–A7 | Phase 2 |
| What is the tail latency under the project's concurrency? | p95/p99 at 1/4/8 concurrent over thousands of calls | Phase 0 |
| Are the vendor's calibration claims true in general? | A TypeSafe technical report with ECE and reliability curves; or a large independent multi-task study | TypeSafe; independent researchers |
| Is the pricing durable? | Time; published SLAs | TypeSafe |
| Does a fine-tuned open model (Laya, small encoder) make Jev unnecessary for a given task? | Same decision dataset, same metrics | Phase 1 |

---

## 13. Sources

**Official TypeSafe documentation (docs.typesafe.ai):** [Introduction](https://docs.typesafe.ai/introduction) · [llms.txt index](https://docs.typesafe.ai/llms.txt) · [Quick start](https://docs.typesafe.ai/introduction/quickstart) · [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer) · [System One](https://docs.typesafe.ai/concepts/system-one) · [State](https://docs.typesafe.ai/concepts/state) · [How to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) · [Use case map](https://docs.typesafe.ai/concepts/use-case-map) · [Primitives](https://docs.typesafe.ai/primitives) · [Choice](https://docs.typesafe.ai/primitives/choice) · [Score](https://docs.typesafe.ai/primitives/score) · [Noul](https://docs.typesafe.ai/primitives/noul) · [Advanced structure](https://docs.typesafe.ai/primitives/advanced) · [Confidence](https://docs.typesafe.ai/confidence) · [Patterns](https://docs.typesafe.ai/patterns) · [Fan-out](https://docs.typesafe.ai/patterns/fan-out) · [Confidence routing](https://docs.typesafe.ai/patterns/confidence-routing) · [Composite scoring](https://docs.typesafe.ai/patterns/composite-scoring) · [Intent routing](https://docs.typesafe.ai/patterns/intent-routing) · [Demos](https://docs.typesafe.ai/demos) · [Smart home](https://docs.typesafe.ai/demos/smart-home) · [SDKs](https://docs.typesafe.ai/sdk) · [Python SDK](https://docs.typesafe.ai/sdk/python) · [Python usage](https://docs.typesafe.ai/sdk/python/usage) · [Async client](https://docs.typesafe.ai/sdk/python/api/clients/async) · [Retries](https://docs.typesafe.ai/sdk/python/api/retries) · [Exceptions](https://docs.typesafe.ai/sdk/python/api/exceptions) · [Python changelog](https://docs.typesafe.ai/sdk/python/changelog) · [JavaScript SDK](https://docs.typesafe.ai/sdk/javascript) · [API](https://docs.typesafe.ai/api) · [Models](https://docs.typesafe.ai/models) · [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) · [Agent skill](https://docs.typesafe.ai/agent-skill) · [Legal](https://docs.typesafe.ai/legal) · all 18 cookbooks linked in §3.1.

**Other official TypeSafe sources:** [Launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev) · [Manifesto](https://typesafe.ai/manifesto) · [Homepage](https://typesafe.ai/) · [Team](https://typesafe.ai/team) · [Evals dashboard](https://evals.typesafe.ai) · [GitHub org](https://github.com/typesafe-ai) · [system-one-adapter-python](https://github.com/typesafe-ai/system-one-adapter-python) · [typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python) · [skills / SKILL.md](https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md).

**Official integrations by other vendors:** [LangChain TypeSafe](https://docs.langchain.com/oss/python/integrations/providers/typesafe) · [LangChain blog](https://www.langchain.com/blog/building-a-harness-with-jev) · [Pydantic AI TypeSafe](https://pydantic.dev/docs/ai/models/typesafe/) · [Vercel changelog](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway) · [Vercel explainer](https://vercel.com/i/what-is-jev) · [Langfuse](https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals) · [Arize](https://arize.com/blog/typesafe-jev-llm-judge/).

**Independent measurements of Jev:** [Every](https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds) · [Good Start Labs](https://goodstartlabs.com/research/verification-is-the-bottleneck) · [Aman Kumar](https://amankumar.ai/blogs/jev-measured) · [jev-phishing-bench](https://github.com/anisselbd/jev-phishing-bench) and [issue #1](https://github.com/anisselbd/jev-phishing-bench/issues/1) · [jev-spam-eval](https://github.com/bitnovus/jev-spam-eval) · [jev-ood-calibration](https://github.com/scienthoon/jev-ood-calibration) · [Jev-Calibration](https://github.com/AnthusAI/Jev-Calibration) · [jev-baselines-eval](https://github.com/ickma2311/jev-baselines-eval) · [jev-benchmark](https://github.com/themsquared/jev-benchmark) · [typesafe-jev-tools](https://github.com/wotai-dev/typesafe-jev-tools) · [jev-exploration](https://github.com/SamuelSacco/jev-exploration/issues/1) · [Laya model card](https://huggingface.co/convaiinnovations/laya) and [benchmark](https://huggingface.co/datasets/Luni/laya-jev-benchmark) · [JevBench](https://jevbench.xyz/methodology).

**Jev agent projects and indexes:** [jev-eval-agent](https://github.com/vinilana/jev-eval-agent) · [fastbrowse](https://github.com/agent-labs-dev/fastbrowse) and [PR #30](https://github.com/agent-labs-dev/fastbrowse/pull/30) · [jev-ultrafast](https://github.com/browser-use/jev-ultrafast) · [jevassert](https://github.com/dtduc-git/jevassert) · [jev-skill](https://github.com/wuyoscar/jev-skill) · [awesome-jev](https://github.com/yibie/awesome-jev) · [teatree design issue](https://github.com/souliane/teatree/issues/4819).

**Press and commentary:** [The Register](https://www.theregister.com/ai-and-ml/2026/09/16/typesafe-ai-debuts-model-for-machines-that-plays-doom/5296711) · [SiliconANGLE](https://siliconangle.com/2026/09/16/typesafe-ai-exits-stealth-with-40m-to-build-ai-for-use-by-software/) · [Hacker News thread](https://news.ycombinator.com/item?id=49717558) · [OrcaRouter](https://www.orcarouter.ai/blog/jev-typesafe-system-one-what-we-know) · [ActionBox](https://actionbox.cloud/blog/typesafe-ai-jev-review/) · [Kingy](https://kingy.ai/blog/typesafe-jev-review-the-ai-model-that-doesnt-generate-text/) · [Forkast](https://forkast.news/typesafe-ais-jev-is-not-an-llm-and-that-may-be-the-point/) · [MindStudio](https://www.mindstudio.ai/blog/typesafe-jev-rlcd-vs-rlhf) · [agentpedia](https://agentpedia.codes/blog/jev-system-one-models) · [explainx](https://www.explainx.ai/blog/jev-speed-cost-claims-fact-check-2026) · [Reticle](https://www.reticle.sh/blog/typesafe-jev-playbook) · [Flowtivity](https://flowtivity.ai/blog/jev-typesafe-ai-decision-model/) · [refix](https://www.refix.ai/news/jev-for-ai-agents/).

**Agent frameworks and tool calling (primary docs):** [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) · [LangChain middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom) · [OpenAI Agents SDK handoffs](https://openai.github.io/openai-agents-python/handoffs/), [guardrails](https://openai.github.io/openai-agents-python/guardrails/), [HITL](https://openai.github.io/openai-agents-python/human_in_the_loop/) · [Claude Agent SDK hooks](https://code.claude.com/docs/en/agent-sdk/hooks), [permissions](https://code.claude.com/docs/en/agent-sdk/permissions), [subagents](https://code.claude.com/docs/en/agent-sdk/subagents) · [Anthropic define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools), [strict tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use), [Tool Search](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool), [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) · [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [chat API](https://developers.openai.com/api/docs/api-reference/chat/create), [latest model guide](https://developers.openai.com/api/docs/guides/latest-model) · [ADK callbacks](https://adk.dev/callbacks/types-of-callbacks/), [routes](https://adk.dev/graphs/routes/), [confirmation](https://adk.dev/tools-custom/confirmation/), [collaboration](https://adk.dev/workflows/collaboration/) · [Pydantic AI toolsets](https://pydantic.dev/docs/ai/tools-toolsets/toolsets/), [deferred tools](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/), [graph](https://pydantic.dev/docs/ai/graph/graph/) · [CrewAI flows](https://docs.crewai.com/en/concepts/flows) · [Outlines issue #479](https://github.com/dottxt-ai/outlines/issues/479) · [vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html) · [BFCL leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html), [categories](https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/TEST_CATEGORIES.md) · [ToolRet](https://arxiv.org/abs/2503.01763) · [Temporal OpenAI Agents](https://docs.temporal.io/develop/python/integrations/openai-agents) · [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).

**Routers, cascades, classifiers, calibration (papers and docs):** [RouteLLM](https://arxiv.org/abs/2406.18665), [blog](https://www.lmsys.org/blog/2024-07-01-routellm/) · [Hybrid LLM](https://arxiv.org/abs/2404.14618) · [Arch-Router](https://arxiv.org/abs/2506.16655) · [RouterBench](https://arxiv.org/abs/2403.12031) · [LLMRouterBench](https://arxiv.org/html/2601.07206v1) · [FrugalGPT](https://arxiv.org/abs/2305.05176) · [AutoMix](https://arxiv.org/abs/2310.12963) · [MoT cascades](https://arxiv.org/abs/2310.03094) · [Confidence-based deferral](https://arxiv.org/abs/2307.02764) · [Is escalation worth it?](https://arxiv.org/abs/2605.06350) · [Rerouting LLM routers](https://arxiv.org/abs/2501.01818) · [SetFit](https://huggingface.co/blog/setfit) · [Banking77 dual encoders](https://arxiv.org/abs/2003.04807) · [ModernBERT](https://arxiv.org/abs/2412.13663) · [Prompt Guard 2](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M) · [Constitutional Classifiers](https://arxiv.org/abs/2501.18837) · [NLI zero-shot](https://arxiv.org/abs/1909.00161) · [Kadavath et al.](https://arxiv.org/abs/2207.05221) · [GPT-4 report](https://arxiv.org/html/2303.08774v4) · [Miscalibrated but predictive](https://arxiv.org/abs/2402.13213) · [Tian et al.](https://arxiv.org/abs/2305.14975) · [Xiong et al.](https://arxiv.org/abs/2306.13063) · [Self-REF](https://arxiv.org/abs/2410.13284) · [Not Diamond](https://www.notdiamond.ai/) · [OpenRouter auto-router](https://openrouter.ai/docs/guides/routing/routers/auto-router).

**Uncertainty-aware agents, verifiers, evaluation (papers):** [KnowNo](https://arxiv.org/abs/2307.01928) · [Introspective Planning](https://arxiv.org/abs/2402.06529) · [UQ taxonomy for agents](https://arxiv.org/abs/2609.07395) · [Agentic abstention](https://arxiv.org/abs/2606.28733) · [Selectively quitting](https://arxiv.org/abs/2510.16492) · [Prune 'n Predict](https://arxiv.org/abs/2501.00555) · [CCPO](https://arxiv.org/abs/2511.11828) · [SayCan](https://arxiv.org/abs/2204.01691) · [Web-Shepherd](https://arxiv.org/abs/2505.15277) · [AgentPRM](https://arxiv.org/abs/2511.08325) · [R2E-Gym](https://arxiv.org/abs/2504.07164) · [Inference scaling fLaws](https://arxiv.org/abs/2411.17501) · [Best-of-N hacking](https://arxiv.org/abs/2503.21878) · [When does verification pay off?](https://arxiv.org/abs/2512.02304) · [LLMs cannot self-correct](https://arxiv.org/abs/2310.01798) · [TTS verification gap](https://arxiv.org/abs/2602.18998) · [Thinking Fast and Slow in AI](https://arxiv.org/abs/2010.06002) · [SOFAI](https://arxiv.org/abs/2110.01834) · [SwiftSage](https://arxiv.org/abs/2305.17390) · [Talker-Reasoner](https://arxiv.org/abs/2410.08328) · [AdaptThink](https://arxiv.org/abs/2505.13417) · [AI Agents That Matter](https://arxiv.org/abs/2407.01502) · [HAL](https://arxiv.org/abs/2510.11977) · [τ-bench](https://arxiv.org/abs/2406.12045) · [τ²-bench](https://arxiv.org/abs/2506.07982) · [ABC](https://arxiv.org/abs/2507.02825) · [Log analysis](https://arxiv.org/abs/2605.08545) · [Epoch SWE-bench Verified review](https://epoch.ai/benchmarks/swe-bench-verified/review).
