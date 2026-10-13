# Step 7.4 — Generation Evaluation

## Objective

Measure Lesson Chat generation quality with approved evidence held fixed, independently from retrieval quality.

## Why

When retrieval is allowed to vary, a poor answer cannot be attributed cleanly to retrieval or generation. Step 7.4 gives the production generator the frozen Step 7.2 evidence packet and evaluates only the generated answer. It does not run retrieval, reranking, or live external fetch.

## Mental Model

```text
approved fixed evidence + fixed conversation memory
→ production PromptContextBuilder / PromptPackage
→ production LLMRequestSerializer / LLMGenerationService / LLMProvider
→ generated answer
→ D-100 structured judge and later human calibration
```

## Current Execution State

D-101 authorizes offline implementation and deterministic tests. Paid generator/judge calls and official generation runs remain deferred. The repository contains an unbound 30-case DRAFT annotation template; it contains no official Step 7.4 run artifacts and no human-approved labels.

## Core Knowledge

- **Generation-isolated evaluation:** evaluate generation after fixing upstream evidence.
- **Ground truth vs reference answer:** `expected_information[]` is primary for correctness/completeness; `reference_answer` is secondary and is never exact-matched.
- **Claim-level faithfulness:** classify material claims as SUPPORTED, UNSUPPORTED, or CONTRADICTED against only the supplied evidence.
- **Five independent rubric dimensions:** answer correctness, faithfulness/groundedness, completeness, language quality, and learning usefulness, each scored 0/1/2.
- **LLM-as-a-Judge:** one D-100 judge uses strict structured output; no voting, fallback judge, or threshold.
- **Human calibration:** only the exact 30 frozen DEVELOPMENT cases can count, after a person sets HUMAN_APPROVED and the answer hash/run binding validates.
- **Technical vs semantic failure:** a provider or prompt failure has no semantic score; judge failure preserves the generated answer and has no semantic score.
- **Reproducible evaluation artifact:** deterministic manifests, fixed-evidence hashes, prompt hashes, answer hashes, and case ordering make a later run auditable.

## Data Flow

1. Validate the official Step 7.2 dataset and select only APPROVED answerable cases: 45 total, 36 DEVELOPMENT, and 9 HOLDOUT. Exclude NO_EVIDENCE_REFUSAL and OUT_OF_DOMAIN_REFUSAL.
2. Resolve every REQUIRED internal evidence ref by exact stable locator in the accepted fixture pack, or external evidence by exact identity in the accepted reviewed-source registry. Do not add ACCEPTABLE evidence automatically. Never call retrieval, reranking, Tavily, or a URL.
3. Bridge fixed internal evidence to production-shaped `RerankedCandidate` objects using deterministic synthetic UUIDv5 identities. Numeric scores are only structural sentinels and are marked `NOT_APPLICABLE_FIXED_EVIDENCE`; they do not order or evaluate evidence. External reviewed claims use the existing external context evidence DTO.
4. Build `PromptPackage` with the actual `PromptContextBuilder`. Preserve source labels/source map and fail a case technically if a required whole evidence block cannot fit.
5. For MULTI_TURN_CONTEXT, convert the frozen turns to `ConversationMemory`/`MemoryTurn`, preserve chronological role pairs, apply the production maximum-turn and token-budget policy, and keep memory outside evidence blocks and citations.
6. Call the existing `LLMGenerationService` and `LLMProvider` with the accepted production `GenerationConfig` for `gpt-5.4-mini-2026-03-17`. No runtime configuration is changed.
7. Before official Stage A, the runner validates Settings, then performs one real production generator smoke and one exact D-100 structured judge smoke. Both returned model/config identities must match the frozen values. A missing gate fails closed; tests may inject test-only fake smoke evidence but official execution rejects it.
8. Stage A writes the exact 45-case run, hashes the frozen `cases.jsonl` into its manifest, and writes a DRAFT packet for the exact 30 calibration cases only after the complete packet has actually been created. Run status and counts derive from case rows and packet state; offline tests are marked `OFFLINE_TEST_ONLY` and never claim an official Stage A or human packet.
9. `resume-stage-b <run_id>` loads that run without regeneration and defaults to the source-controlled `evaluation/annotations/lesson_chat_generation/v0.1.0/{manifest.json,calibration.jsonl}` package. It validates the annotation manifest/version, exact frozen IDs, run and generated-answer SHA bindings, HUMAN_APPROVED rows, cross-field rubric consistency, and claim evidence before judging frozen outputs. A run-local packet is an artifact copy, not the default source of truth. It finalizes agreement only when the exact 30 calibration cases have successful judge results; 29/30 remains incomplete and creates no finalized agreement artifact.

## Key Design Decisions

- Dataset is `v0.8.0`; eligible population is fixed at 45 (36 DEVELOPMENT / 9 HOLDOUT).
- Fixed evidence only; actual retrieval, reranking, and live external fetch are excluded.
- MULTI_TURN_CONTEXT uses only dataset history, never live conversation storage.
- Five independent 0/1/2 dimensions are scored separately. There is no overall pass, release, or agreement threshold.
- `expected_information[]` is the main ground truth; external real-world knowledge cannot rescue unsupported claims.
- Critical generation failures are exactly `SERIOUS_FACTUAL_ERROR`, `UNSUPPORTED_CONFIDENT_CLAIM`, and `CONTRADICTED_BY_EVIDENCE`.
- D-100 judge contract is OpenAI Responses API, `gpt-5.4-2026-03-05`, reasoning none, temperature 0, 1600 output tokens, strict structured output, and no tools.
- D-101 currently permits offline implementation/tests only. No paid calls, official baseline, or generated run artifact was created. Official Stage A is gated on Settings preflight plus both real model smokes.
- Human labels remain manual. Codex and the judge cannot approve annotations.

## Human Calibration and Stage B

The source-controlled template under `evaluation/annotations/lesson_chat_generation/v0.1.0/` has the exact 30 IDs, all `DRAFT`, with null run/hash bindings and no semantic scores. Its logical annotation version is `lesson-chat-generation-human/v0.1.0`. Stage A binds it to a run only after successful generation. Stage B recomputes SHA-256 from each frozen answer and compares it with both the annotation and Stage-A case artifact binding before any judge call. It validates annotation/rubric versions, exact IDs/run, all five scores, claim IDs/schema/evidence IDs, and frozen critical-failure enums. Human-approved cross-field combinations must follow the frozen rubric: contradictions require faithfulness 0 and the contradiction flag; flags require their matching claims; serious factual error requires correctness 0; faithfulness 2 cannot coexist with unsupported/contradicted claims or their critical flags. Invalid human labels are rejected rather than corrected or included in agreement. A judge technical failure is never converted to score 0. Agreement metrics are a baseline only and require exactly 30/30 valid comparisons.

The repository-native resume command is `uv run python -m app.evaluation.step74.cli resume-stage-b <run_id>`. It reads existing Stage-A answers and never calls the generator. Final Stage-B cases, summary, agreement, and manifest are written under `generation/stage-b/`; the Stage-A files and case-file digest remain unchanged. An incomplete calibration judge pass returns `JUDGE_CALIBRATION_INCOMPLETE`; it does not write a finalized agreement or mark the run complete.

## Artifact Layout

An authorized real Stage A run writes:

```text
evaluation/runs/<run_id>/generation/
├── manifest.json
├── cases.jsonl
├── summary.json
├── calibration-agreement.json
└── calibration.jsonl     # when all 30 calibration answers succeeded
```

The source-controlled annotation packet is separate from the run directory. Current D-101 execution has created no official run directory.

## Reusable Approach

To isolate a component in an AI pipeline, freeze its upstream inputs, preserve their identities and hashes, invoke the existing production seam, and keep technical failure separate from semantic quality.

## Common Mistakes

- Using production retrieval output as the evaluation evidence.
- Using actual retrieval/reranking or fetching external URLs in a generation-only run.
- Exact-matching the reference answer instead of evaluating atomic expected information.
- Using outside knowledge to mark an unsupported claim as grounded.
- Treating a technical error as semantic score 0.
- Allowing prior assistant memory to become evidence or citation provenance.
- Tuning against HOLDOUT, inventing an agreement threshold, or hiding critical failures in an aggregate score.
- Confusing Lesson Chat generation evaluation with Step 6.12 assessment generation.
- Treating an unbound DRAFT template as Stage A output or a human approval.

## Definition of Done

For the current D-101 authorization, offline implementation and deterministic tests must pass, production seams and frozen contracts must be covered, dataset ground truth and runtime config must remain unchanged, and no paid API calls or official run artifacts may be created. Specialist review is required. Paid smoke tests, official Stage A, human review, and Stage B remain deferred.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Generation-isolated evaluation | AI | 7.4 | Measures generation while upstream evidence is fixed |
| LLM-as-a-Judge | AI | 7.4 | Applies the frozen semantic scoring contract |
| Human calibration | BOTH | 7.4 | Requires manual labels bound to exact generated answers |
| Claim-level faithfulness | AI | 7.4 | Separates supported, unsupported, and contradicted claims |
| Evaluation rubric | AI | 7.4 | Makes five independent 0/1/2 dimensions explicit |
| Technical vs semantic failure | SYSTEM | 7.4 | Prevents infrastructure failures from contaminating quality scores |
| Evaluation run artifact | SYSTEM | 7.4 | Supports reproducibility and review |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| Python | SYSTEM | 7.4 | Evaluation contracts, fixed evidence, runner, artifacts, metrics |
| pytest | SYSTEM | 7.4 | Deterministic offline regression tests |
| uv | SYSTEM | 7.4 | Existing backend environment and test workflow |
| Existing production LLM provider | AI | 7.4 | Generator-under-test seam; no paid calls under D-101 |
| OpenAI Responses API | AI | 7.4 | D-100 judge adapter contract; live calls deferred |
