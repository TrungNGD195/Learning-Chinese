# Step 7.7 — Focused Track-B Classification Rework Handoff

## Status

`READY_FOR_SPECIALIST_REVIEW — OFFLINE TRACK-B CLASSIFICATION REWORK`

This handoff does not claim Step 7.7 DONE or PM acceptance.

## Rework performed

- Track-B classification now receives the actual production discriminated request: `LessonExerciseGenerationRequest` or `PeriodicTestGenerationRequest`. The classifier reads `request.question_count`; it no longer depends on a synthetic `requested_question_count` request field. The downstream production provider DTO still uses its real `requested_question_count` field where that provider contract requires it.
- Structured schema parsing is separate from deterministic policy/domain checks. Only failure to parse into `StructuredAssessmentGenerationOutput` maps to `SCHEMA_INVALID`.
- A valid parsed output with a count mismatch sets `requested_count_valid=false`, remains a deterministic failure, and introduces no new critical-failure enum.
- A production-supported but request-disallowed type sets `supported_question_types_valid=false` and `UNSUPPORTED_QUESTION_TYPE` while `schema_valid=true`.
- Invalid/out-of-scope source refs set `source_refs_valid=false` / `scope_adherent=false` and `OUT_OF_SCOPE_GENERATION` while `schema_valid=true`.
- A real production domain-validator rejection sets `domain_validation_valid=false` and keeps `schema_valid=true`. The dimension is left unevaluated when production would stop at an earlier request-count/type/source check. Deterministic failure status survives human-label evaluation even when no frozen critical enum exists for that dimension.
- No frozen decisions, dataset counts/splits, provider/model/prompt, production generation semantics, schema, migration, dependency, production configuration, or Track-A behavior changed.

## Production request contract

`backend/app/ai/generation/schemas.py` defines the discriminated `AssessmentGenerationRequest` union. Track-B tests instantiate both `LessonExerciseGenerationRequest` and `PeriodicTestGenerationRequest` through the real Pydantic `TypeAdapter`; both carry `question_count` as the authoritative field.

## Classification dimensions

| Failure condition | `schema_valid` | Deterministic dimension | Critical failure |
|---|---:|---|---|
| Provider payload cannot parse as `StructuredAssessmentGenerationOutput` | false | parse failed | `SCHEMA_INVALID` |
| Parsed output count differs from `request.question_count` | true | `requested_count_valid=false` | none added |
| Supported type is excluded by request | true | `supported_question_types_valid=false` | `UNSUPPORTED_QUESTION_TYPE` |
| Source ref is missing, duplicated, or outside selected scope | true | `source_refs_valid=false`, `scope_adherent=false` | `OUT_OF_SCOPE_GENERATION` |
| Production domain validator rejects parsed content | true | `domain_validation_valid=false` | preserve existing typed semantic; no schema mislabel |

## Verification

- Focused Track-B classification: **8 passed**.
- Actual production request contracts: **2 passed** (Lesson Exercise and Periodic Test).
- Schema failure: **1 passed**.
- Count mismatch: **2 passed** (including deterministic failure preservation without a new enum).
- Unsupported/disallowed type: **1 passed**.
- Scope/source violation: **1 passed**.
- Domain-validation classification: **1 passed**.
- Full Track-A regression selection: **36 passed**.
- Official eligibility regression: **50 passed**.
- Artifact/reproducibility regression: **37 passed**.
- Full Step-7.7 focused suite: **137 passed, 1 skipped**.
- Step-6.12 production generation regression excluding database-dependent lifecycle tests: **23 passed, 5 deselected**.
- `uv run python -m compileall -q app`: **PASS**.
- PostgreSQL lifecycle: **SKIP** — safe test target `step77.invalid` did not resolve (`psycopg.OperationalError`). No SQLite substitution or database writes were attempted.

## Frozen state and guardrails

- Track A: 60 cases; 45 DEVELOPMENT / 15 HOLDOUT; source annotations remain DRAFT.
- Track B: 16 requests; 12 DEVELOPMENT / 4 HOLDOUT; 8 LESSON_EXERCISE / 8 PERIODIC_TEST; 48 source annotations remain DRAFT.
- `HUMAN_APPROVED`: **0**.
- Paid calls: **0**; live external calls: **0**; official benchmark: **NOT RUN**.
- Production config changed: **NO**; schema/migration changed: **NO**; Step 7.6 started: **NO**.

## Problems / risks

Five production generation integration tests require the safe dedicated PostgreSQL database and were deselected because it was unavailable. The offline focused suite and non-DB production regressions pass.

## Recommended next action

Independent Specialist review.
