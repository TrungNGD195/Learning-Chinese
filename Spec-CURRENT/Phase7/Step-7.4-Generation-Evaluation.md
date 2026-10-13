# Step 7.4 — Generation Evaluation

## Context

Step 7.3 evaluates retrieval. Step 7.4 isolates Lesson Chat generation by supplying exact approved Step 7.2 evidence to the accepted production prompt and generation seams. D-100 freezes the single judge contract. D-101 currently authorizes offline implementation/tests only; paid runtime is deferred.

## Objective

Build a reproducible generation-isolated evaluation harness for the frozen dataset, fixed evidence, fixed MULTI_TURN memory, production Lesson Chat generation interface, five scoring dimensions, human calibration, D-100 judge, and run artifacts.

## Current state

- Step 7.4 is IN PROGRESS and is not DONE or PM-accepted.
- Dataset is `lesson_chat_rag` `v0.8.0`: 60 APPROVED cases.
- Eligible answerable population: 45 cases, 36 DEVELOPMENT, 9 HOLDOUT.
- D-100 judge model/config is frozen.
- D-101 defers paid runtime evaluation and permits offline implementation/test only.
- Step 7.5, 7.7, and 7.6 have not started and remain out of scope.

## In Scope

- Exact APPROVED-only eligible-case selection and bucket/split assertions.
- Step 7.2 fixed evidence resolution from accepted internal fixture content and the accepted trusted-external reviewed registry.
- Fixed MULTI_TURN conversation memory adapted to existing production memory DTOs and budget rules.
- Existing production `PromptContextBuilder`, `PromptPackage`, `LLMRequestSerializer`, `GenerationConfig`, `LLMGenerationService`, and `LLMProvider` seams.
- Five frozen rubrics, claim-level faithfulness, the three critical generation failures, judge schema, annotation gates, agreement metrics, and Stage A / Stage B orchestration.
- Deterministic offline tests using provider fakes only.
- Documentation and source-controlled unbound DRAFT calibration template.
- Settings preflight and mandatory real generator/D-100 judge smoke gate before official Stage A; offline tests may inject test-only fake smoke results, but official execution may not bypass the real gate.
- Repository-native `resume-stage-b <run_id>` for same-run continuation without regeneration.

## Out of Scope

- Paid API calls, real model smoke tests, official Stage A generation, judge scoring, or official baseline creation under D-101.
- Human semantic annotation or any `HUMAN_APPROVED` status by Codex/LLM.
- Actual retrieval, reranking, vector DB access, Tavily, live external fetch, or ingestion.
- Step 7.5, Step 7.7, Step 7.6, or any threshold/gate.
- Changes to Step 7.2 dataset ground truth or production generator config.

## Functional Requirements

### Eligible cases

Use only approved cases from dataset v0.8.0. Include `CURRENT_LESSON_ANSWERABLE`, `INTERNAL_KB_FALLBACK`, `TRUSTED_EXTERNAL_FALLBACK`, and `MULTI_TURN_CONTEXT`. Exclude `NO_EVIDENCE_REFUSAL` and `OUT_OF_DOMAIN_REFUSAL`. Assert 45 total, DEVELOPMENT 36, HOLDOUT 9, with bucket distributions DEVELOPMENT 16/8/4/8 and HOLDOUT 4/2/1/2 in that bucket order.

### Fixed evidence

Resolve INTERNAL_CHUNK by exact stable locator to accepted source-derived fixture content. Resolve EXTERNAL_URL by exact URL/domain/title identity to the accepted reviewed-source registry; supply only its frozen reviewed claims. Preserve evidence IDs, requirement IDs, provenance, order, and deterministic content hashes. Deduplicate identical physical sources without losing evidence reference identities. REQUIRED refs alone populate prompt context; ACCEPTABLE refs are not added automatically.

Do not invoke retrieval, reranking, or network access. The evaluation-only candidate bridge uses deterministic synthetic identities and numeric structural sentinels marked `NOT_APPLICABLE_FIXED_EVIDENCE`; these values cannot affect ordering, scoring, or judge input.

### Prompt, learning context, and memory

Use the actual `PromptContextBuilder` to produce production `ContextBlock`s, labels, source map, and `PromptPackage`. Any required evidence omitted by token budgeting is a technical failure `FIXED_EVIDENCE_CONTEXT_BUDGET_EXHAUSTED`.

Map available lesson title, locator, and synthetic HSK identity to `LearningContext`; do not pass database IDs. For MULTI_TURN, map dataset turns chronologically into `ConversationMemory` and `MemoryTurn`. Apply the accepted maximum-turn and token-budget behavior. History remains separate from evidence blocks and is never citation provenance.

### Generator

Use `GenerationConfig.from_settings` and the existing production `LLMGenerationService`/`LLMProvider` seam. Require model `gpt-5.4-mini-2026-03-17`; retain the accepted temperature 0.2, 800 output-token limit, no reasoning, 60 second timeout, at most one transient retry, and no tools, web search, or model fallback. Do not change production configuration.

Generation failure produces no semantic scores and `judge_status=NOT_RUN`. Blank answers are technical failures. Successful answers retain provider/model, attempt, latency, token usage, and SHA-256.

### Rubric and judge

Score exactly `ANSWER_CORRECTNESS`, `FAITHFULNESS_GROUNDEDNESS`, `COMPLETENESS`, `LANGUAGE_QUALITY`, and `LEARNING_USEFULNESS`, each independently on 0/1/2. Use `expected_information[]` as primary correctness/completeness truth and `reference_answer` only as a secondary reference. Do not create an aggregate pass threshold.

Represent material claims as SUPPORTED, UNSUPPORTED, or CONTRADICTED, with support IDs constrained to the supplied evidence. Support exactly `SERIOUS_FACTUAL_ERROR`, `UNSUPPORTED_CONFIDENT_CLAIM`, and `CONTRADICTED_BY_EVIDENCE`.

The D-100 adapter uses OpenAI Responses API, `gpt-5.4-2026-03-05`, reasoning effort none, temperature 0, 1600 output tokens, strict JSON Schema output, no tools, no fallback, and no multi-judge voting. Judge technical failure preserves the answer and yields no semantic scores. Never request or persist hidden chain-of-thought.

### Human calibration and agreement

Enforce the exact frozen 30 DEVELOPMENT IDs. Source-controlled template rows are unbound `DRAFT`, with no scores or human labels. The logical annotation version is `lesson-chat-generation-human/v0.1.0`. Stage A binds run ID and generated-answer hash only after successful generation and freezes the SHA-256 of its complete `cases.jsonl` in the run manifest. Stage B requires all exact 30 annotations manually marked HUMAN_APPROVED, validates the exact annotation/rubric versions, case/run binding, five scores, claim IDs/schema/evidence IDs, critical failure enums, and recomputed answer hashes against both annotation and Stage-A artifact. Changed or stale bindings return HUMAN_CALIBRATION_STALE before judging. Stage B reuses existing outputs and never regenerates. Codex/LLM never self-approve.

Stage B may finalize only after successful judge results exist for all and only the exact 30 calibration IDs. A missing/failed/extra comparison yields `JUDGE_CALIBRATION_INCOMPLETE`; it must not write a finalized agreement artifact or mark the run complete. A 29/30 denominator is not accepted.

Stage B writes final artifacts under `<run>/generation/stage-b/`. It preserves the Stage-A manifest, answers, and case-file hash unchanged; the Stage-B manifest records the Stage-A manifest/case digests it consumed.

Calculate exact agreement, MAE, 3×3 confusion matrix, human/judge means per dimension, macro exact agreement, overall MAE, and critical-failure-set agreement. Report baseline only; no threshold.

## Technical Requirements

- Pure offline case selection, fixed evidence, prompt assembly, result processing, annotation validation, and metrics.
- Production calls are injectable for deterministic tests; official Stage A rejects a non-production generator provider and invokes its own Settings + real-model smoke gate before creating a run directory.
- D-100 judge is behind an isolated judge interface and accepts injectable fake Responses clients for unit tests.
- Secret values never enter artifacts, source, logs, tests, or review ZIP.
- Run artifacts are deterministic JSON/JSONL except for run ID and timestamps.
- Stage A writes under `evaluation/runs/<run_id>/generation/`; it creates no DB records.
- No new dependencies, schema/migrations, or changes to Step 7.2 fixtures/dataset.

## Inputs / Outputs

Inputs:

- `evaluation/datasets/lesson_chat_rag/v0/` official manifest and case JSONL.
- Accepted `evaluation/fixtures/lesson_chat_rag/v0.1.0/` internal sources.
- Accepted `evaluation/fixtures/lesson_chat_rag/trusted_external/v0.1.0/reviewed-sources.json` registry.
- Existing backend Settings, prompt, memory, and LLM provider contracts.
- Later Stage B: manually reviewed annotation packet bound to Stage-A hashes.

Outputs for a separately authorized real Stage A:

```text
evaluation/runs/<run_id>/generation/
├── manifest.json
├── cases.jsonl
├── summary.json
├── calibration-agreement.json
└── calibration.jsonl
```

Current D-101 implementation run produces no official run artifacts. Source-controlled annotation template is `evaluation/annotations/lesson_chat_generation/v0.1.0/`.

## Data Flow

```text
validate approved dataset v0.8.0
→ exact 45 eligible cases
→ resolve exact fixed evidence / fixed history
→ production PromptContextBuilder
→ production LLMGenerationService (later paid Stage A)
→ immutable answer and hash
→ 30-case DRAFT human packet
→ STOP for human calibration
→ later approved Stage B: validate hashes, call one judge, score and report baseline
```

## Interfaces / schema

- Fixed evidence objects preserve all approved evidence IDs and requirements; external entries contain only reviewed registry claims.
- Candidate bridge uses existing `RerankedCandidate`/`ContextEvidence` structures; scores carry `NOT_APPLICABLE_FIXED_EVIDENCE` semantics.
- Fixed history maps to existing `ConversationMemory`/`MemoryTurn`.
- Judge result schema requires version, matching case ID, all five score/rationale pairs, claim list, valid evidence IDs, critical-failure enum, and concise overall rationale; extra fields are forbidden.
- Human annotation status is `DRAFT`, `NEEDS_ADJUDICATION`, or `HUMAN_APPROVED` and has run/hash binding. Claim IDs are deterministic `C1..Cn`; HUMAN_APPROVED claims may cite only evidence supplied to their case.
- Judge results receive deterministic cross-field validation; contradictory claims, faithfulness score, and critical flags must agree with the frozen rubric before a result is accepted.
- Stage-A manifest, case rows, summary, and agreement metadata cross-check run, dataset, policy, model/config identities, split/bucket counts, calibration count, runtime mode, and technical denominators.

## Files/components

- `backend/app/evaluation/step74/`: eligibility, fixed evidence, prompt/memory adapter, schemas, judge, annotations, metrics, artifacts, runner, CLI.
- `backend/tests/test_step74_generation_evaluation.py`: deterministic offline tests.
- `evaluation/annotations/lesson_chat_generation/v0.1.0/`: exact unbound DRAFT template.
- `docs/evaluation/step-7.4-generation-evaluation.md`: implementation note.

## Config/env

- Generator uses existing application Settings only; no model/config edits.
- Judge D-100 config is evaluation-owned and frozen as above.
- API credentials are read only through existing Settings and never serialized.
- D-101 current mode makes zero paid API requests. `offline-preflight` makes no API calls. `execute-live-stage-a` runs mandatory real smokes before generation. `resume-stage-b <run_id>` loads and verifies the same run and annotation packet; no alternate flag bypasses smoke or hash checks.

## Error handling

- Invalid dataset/count/bucket, missing or changed evidence fixture, and wrong model config fail closed.
- Prompt evidence budget exhaustion is a normalized generator technical failure.
- Provider exceptions are represented only by normalized error codes; no raw exception text or credentials are stored.
- Blank generated text is technical failure, not semantic score zero.
- Generator failure skips judge; judge failure preserves output and has no score.
- Missing human approval yields REVIEW_REQUIRED; mismatched answer hash yields HUMAN_CALIBRATION_STALE.
- Missing smoke pass, wrong returned model/config identity, changed Stage-A case artifact, annotation-version drift, or incomplete 30-case judge coverage fails closed without finalization.

## Testing

- Focused tests assert exact eligibility, fixed evidence resolution, no network interfaces, source labels/map, budget failure, MULTI_TURN separation, production generator service serialization, model preflight, technical failures, D-100 config/schema/cross-field validation, fakeable but mandatory real-smoke gate, exact annotation/hash/schema gate, resume-without-regeneration, exact 30/30 finalization, metrics, DRAFT template, and cross-artifact identity/count consistency.
- Provider execution in tests is fake; `run_stage_a` rejects fake providers to prevent mock outputs from becoming official artifacts.
- Run relevant existing prompt, LLM service/serializer/provider, tokenizer, and memory tests.
- Run compileall and `uv lock --check`.
- Paid API smoke tests and official Stage A are deferred under D-101.

## Acceptance Criteria

- Dataset ground truth stays unchanged at v0.8.0 and selection asserts exactly 45 / 36 / 9.
- Excluded buckets do not enter; fixed evidence and history come only from accepted fixture inputs.
- Retrieval, reranking, and live fetch are not called.
- Actual production prompt/generator seams and production configuration are preserved.
- All five rubrics, claim validation, critical failures, technical semantics, annotation gate/hash logic, D-100 schema, and agreement arithmetic are tested.
- Offline focused and relevant regression tests pass with zero paid calls.
- No HUMAN_APPROVED annotation, official run artifact, Stage B execution, or Step 7.5/7.7/7.6 work is performed under D-101.
- Documentation and focused review ZIP are prepared for independent specialist review.

## Constraints / Non-goals

No retrieval/reranking/network evidence; no production model changes; no dataset changes; no real API calls under D-101; no human scoring/approval by Codex; no thresholds, database schema, migrations, new dependencies, Step 7.5, Step 7.7, or Step 7.6.

## Open Questions

None.
