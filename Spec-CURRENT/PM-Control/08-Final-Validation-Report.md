# Final Validation Report — Baseline v1.0

## Validation Result

```text
Baseline architecture/product consistency: PASS
MVP requirement coverage:                PASS
Decision log for Wave 1:                 PASS
Step-reference integrity:                PASS
Markdown structural scan:                PASS
Step 3.1 Codex-ready freeze:             PASS
Current implementation permission:       Step 3.1 only
```

## Automated Structural Checks

Validated on 2026-09-18:

- 60 unique Step IDs detected;
- no duplicate Step ID;
- every explicit `Step X.Y` reference resolves to an existing Step;
- no Markdown file has an unmatched fenced-code delimiter;
- no active requirement remains for standalone `GLOBAL` chat in V0;
- old `100 MB`, `GRAMMER`, `Phase 10`, nullable-message, and semantic-reranker-fallback strings that remain are historical/audit/non-goal wording rather than active contradictory requirements.

## Cross-Phase Invariants Rechecked

### Product scope

- learner AI chat is lesson-scoped in MVP;
- standalone General/Global Chat is out of scope;
- free-form AI grading and admin AI assessment generation have implementation + evaluation coverage.

### Persistence/lifecycle

- `ASSISTANT/PENDING` and `ASSISTANT/FAILED` may have null content;
- completed assistant/user content must be non-empty;
- document processing state is independent from human review state;
- approval does not by itself make knowledge retrieval-active;
- knowledge activation occurs only after chunk/embedding/vector readiness and preserves the previous active version on failed rebuild.

### RAG

- nearest-neighbor existence is not sufficient evidence;
- usable evidence requires calibrated rerank score in normal runtime;
- reranker technical failure is a technical failure, not semantic no-evidence and not a fallback-tier trigger;
- Step 6.8-A may collect scores in calibration mode;
- Step 7.3 selects/records `RAG_MIN_RERANK_SCORE` before normal-runtime evidence gating is closed;
- external fallback stays disabled until its concrete provider + reviewed allowlist are selected;
- multi-turn evaluation does not require history-aware query rewriting in V0.

### Scope/complexity control

- no queue/worker is introduced before ingestion profiling demonstrates need;
- no multi-provider LLM routing is introduced in V0;
- no separate AI microservice is introduced;
- production vendors are selected at deployment time, not during Wave 1.

## Why Later Steps Still Have a Just-in-Time Freeze

A specification can be logically correct today but become stale after earlier Steps create real files, migrations, generated OpenAPI types, or measured AI/data behavior. Therefore PM does not mark all future executable Steps as permanently Codex-ready at once.

The gate is:

```text
reviewed baseline
+ actual repository state
+ affected decisions/evidence
= frozen Step task packet
```

This is deliberate context control, not unresolved architecture.

## Step 3.1 Freeze Result

Step 3.1 has been normalized to the current Step Specification checklist and explicitly contains:

- Context / Objective / Current State;
- In Scope / Out of Scope;
- Functional / Technical requirements;
- Inputs / Outputs;
- Data Flow;
- Interfaces/API/Schema;
- Files/Components;
- Config/Env;
- Error Handling;
- Testing;
- Acceptance Criteria;
- Constraints/Non-goals;
- Open Questions;
- Step documentation/knowledge capture and Definition of Done.

No architecture-significant open question blocks Step 3.1.

## Release Decision

**PASS: Wave 1 may begin with Step 3.1 only.**

Do not send Step 3.2 or any later Step to Codex until PM explicitly freezes it after Step 3.1 acceptance.

## Canonical Package Note

The downloadable `Trung-Chinese-Learning-Spec-CURRENT` package is the current source of truth. It additionally contains `README.md` and `PROJECT_CONTEXT.md` for stable Codex orientation, and intentionally excludes temporary Step-specific task packets from the specification baseline.
