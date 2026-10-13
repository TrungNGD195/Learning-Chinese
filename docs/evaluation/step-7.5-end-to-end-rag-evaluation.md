# Step 7.5 ? End-to-End RAG Evaluation

## Objective

Evaluate Lesson Chat across retrieval, fallback/refusal, generation, citations, memory, persistence, and technical failures using the actual production-shaped request path. The current deliverable is offline implementation and deterministic verification only.

## Why

Layer-isolated metrics cannot prove the composed system follows its evidence, tier-priority, and response contracts. A captured trace makes the actual system behavior auditable before comparing it to expected labels.

## Mental Model

```text
actual learner request
? production application-service path
? retrieval / reranking / context / memory / generation / citations / persistence
? trace actual events only
? compare expected labels after execution
? hard-validity E2E result
```

## Core Knowledge

- **End-to-end evaluation:** observe behavior across a complete RAG request rather than inferring it from isolated stages.
- **Execution trace:** preserve actual tier attempts, evidence identity, context, generation, citation, persistence, timing, and technical status.
- **Expected-vs-actual policy evaluation:** dataset labels are consumed only after trace capture. They do not configure retrieval or provider behavior.
- **Semantic vs technical failure:** infrastructure errors remain technical failures and cannot be converted to semantic no-evidence.
- **Citation correctness vs coverage:** correctness asks whether current cited labels support claims; coverage asks whether grounding-required claims have supporting current citations.
- **Memory/evidence isolation:** conversation history can inform interpretation but cannot become evidence or resolve historical citation labels.
- **Stochastic repeats:** DEVELOPMENT runs once per case; HOLDOUT cases are planned for three repeats.
- **Artifact reproducibility:** canonical serialization and hashes bind future annotations to exact run outputs.

## Data Flow

The offline implementation defines the 60-case v0.8.0 plan (48 DEVELOPMENT and 12 HOLDOUT), trace/result contracts, deterministic post-execution evaluation, D-100 judge adapter, reviewed external fixture provider, and an unbound human annotation template. No official E2E run is executed in offline mode.

The future runtime path must enter through the learner message application service. It must use real local retrieval and reranking, exact production evidence threshold, production PromptContextBuilder/ConversationMemoryBuilder/LLMGenerationService/CitationValidator and persistence. Only the paid LLM provider and live external search boundary may be replaced in offline integration tests. Gold evidence is never injected into retrieval.

The targeted offline rework adds evaluation-local observers around the existing orchestrator seams. They capture each tier's actual retrieved candidates, reranked scores, configured evidence gate, the exact PromptPackage source map, and sanitized memory returned by the production memory builder. After the learner service commits, trace persistence is read back from Message, MessageRetrieval, and MessageCitation. The trace is validated against E2EExecutionTrace before expected labels are compared. No production API or database schema is added.

Trusted external requirements use exact required EXTERNAL_URL identities; internal chunk requirements continue to use Step 7.3 equivalence groups. A positive retrieval result requires every required requirement group to be satisfied. A below-threshold selected context is a gate failure even when context construction succeeded. Citation failures remain separate from the three D-103 generation-critical findings.

## Key Design Decisions

- **D-103:** `e2e_case_pass` is the exact AND of retrieval, generation, citation, context, fallback, refusal, technical validity, and an empty critical-failure set. No numeric quality threshold is introduced.
- **D-104:** the Step-7.5 judge uses its own prompt/schema and D-100 provider/model configuration. The real judge is not called offline.
- **D-105:** current production has no explicit OOD guard, distinct OOD runtime result, or OOD response contract. `actual_behavior` comes only from production trace. An OOD expected label is comparison-only: answer/fallback yields `OUT_OF_DOMAIN_ANSWER`; generic no-evidence remains `REFUSE_NO_EVIDENCE` and fails without that critical; technical failure remains `TECHNICAL_FAILURE`. No OOD behavior is synthesized and no OOD feature is implemented.
- The current approved dataset is v0.8.0: 60 cases, 48 DEVELOPMENT / 12 HOLDOUT, and 84 planned executions. 120 is a later portfolio target.
- `retrieval_ok` reuses Step-7.3 evidence requirement/equivalent-group semantics and independently checks runtime gate and scope.
- The trusted external adapter reads the accepted reviewed fixture pack and does not fetch URLs.
- Offline artifacts cannot be marked official-baseline eligible. Human templates remain 30 DRAFT / 0 HUMAN_APPROVED and have no fabricated run bindings.

## Reusable approach

For a composed AI pipeline, keep execution independent from expected labels, retain stage-level evidence, replace only unavoidable paid/network boundaries, and calculate pass criteria after execution with deterministic policies. Bind human reviews to canonical output hashes.

## Common Mistakes

- Injecting gold evidence into E2E retrieval.
- Letting expected labels drive actual execution or synthesizing an OOD refusal from an expected OOD label.
- Faking retrieval because generation is replaced with a test provider.
- Treating memory as evidence or allowing historical citations to resolve in the current message.
- Turning technical failure into no-evidence fallback.
- Using one average to hide critical failures.
- Calling offline latency a production baseline.
- Using a judge instead of CitationValidator for structural validity.
- Adding release thresholds in Step 7.5.

## Definition of Done

Offline implementation review requires deterministic planner/evaluator/judge/annotation/artifact contracts and relevant tests. Database/model integration is skipped with an explicit reason when safe local prerequisites are unavailable. Offline implementation review is not final Step 7.5 DONE or PM acceptance; it does not execute the official 84-run benchmark or create a baseline.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| End-to-end evaluation | BOTH | 7.5 | Evaluates behavior across the composed request path |
| Execution trace | SYSTEM | 7.5 | Preserves actual stage outcomes for audit |
| Tier-policy evaluation | AI | 7.5 | Checks evidence priority and fallback behavior |
| Semantic citation evaluation | AI | 7.5 | Checks claim support and citation coverage |
| Memory/evidence isolation | AI | 7.5 | Keeps history separate from evidence authority |
| Deterministic dependency substitution | SYSTEM | 7.5 | Replaces only paid/network boundaries in offline tests |
| Stochastic repeat evaluation | AI | 7.5 | Plans three HOLDOUT executions per case |
| Semantic vs technical failure | SYSTEM | 7.5 | Prevents infrastructure faults becoming refusal outcomes |
| Reproducible E2E artifact | BOTH | 7.5 | Binds results and annotations to canonical hashes |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| Python | SYSTEM | 7.5 | Evaluation contracts, planner, evaluator, and artifacts |
| pytest | SYSTEM | 7.5 | Deterministic contract verification |
| uv | SYSTEM | 7.5 | Existing backend environment workflow |
| OpenAI Responses judge adapter | AI | 7.5 | D-104 runtime-ready configuration; no API call in offline work |

## Verification State

Offline tests verify planner shape, all five trusted-external identities, complete requirement coverage, runtime gate/priority observation, source-map and persisted provenance checks, memory sanitization, D-103/D-105 outcome mapping, unbound DRAFT rules, and artifact protection. Six production-path PostgreSQL/model integration tests are authored; each explicitly skips when the isolated test DB or exact pinned local models are unavailable. No official E2E run, judge call, paid API call, live external network call, or human annotation is performed by this offline task.

## Rework #2 verification additions

Historical messages are materialized with production `reply_to_message_id` pairs and increasing sequence numbers. The evaluation trace records the exact sanitized memory snapshot consumed by generation and supplies that same snapshot to the fake Step-7.5 judge. Omitted eligible history identities are retained for review; memory is explicitly marked as having no evidence authority.

Runtime policy criticals derive from actual tier attempts, rerank scores, evidence gates, transitions, and technical/generation outcomes. The offline summary includes planned and executed totals, split/bucket aggregates, per-bucket pass rates, critical-failure distributions, five judged generation dimensions, test-only latency/token summaries, and raw HOLDOUT repeat stability.

Six DB/model-gated bucket tests now assert their production path and final lifecycle. Six more narrow-seam tests inject retrieval, reranker, context-budget, LLM-provider, CitationValidator, and finalization failures. Answer-producing application-path tests use the real Step-7.5 fake-judge protocol and verify score/claim/citation/context propagation. Reviewed annotation validation binds to the exact run ID and canonical frozen `cases.jsonl` hash/content.

Latest offline verification: 38 focused tests passed; 12 DB/model application-path tests skipped before database access because the dedicated test database setting is unavailable. Relevant Phase-6 regressions passed (117); compile and import checks passed. Paid API calls, live external requests, official runs, dataset changes, and HUMAN_APPROVED annotations remain at zero.

## Targeted offline implementation rework #3

Historical pairs are now inserted and flushed in order so each assistant reply points to the materialized corresponding user ID. Multi-turn context validity now requires an observed production memory-builder invocation, composed memory, required turns reported as applied to generation, a sanitized snapshot, citation-marker isolation, and a passing semantic context judge. Non-multi-turn cases retain no memory requirement.

CitationValidator observation now captures exact deterministic failure codes and keeps those output-contract failures distinct from unexpected validator exceptions. Production-boundary total latency ends at the application response; later persistence readback uses explicitly evaluation-only timing fields and is excluded from production total-latency summaries.

Verification: 51 focused Step-7.5 tests passed; 12 DB/model tests skipped because `TEST_DATABASE_URL`/required test settings are unavailable. Relevant offline Phase-6 tests: 111 passed. `compileall -q app` and Step-7.5 import smoke passed. No API calls, live external calls, official run, dataset edits, or human approvals were made.
