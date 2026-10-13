# Step 7.7 — Offline Implementation Specification

## Context

Step 7.7 evaluates accepted Step 6.11 grading and Step 6.12 content-generation seams. D-106 through D-109 are frozen. This implementation is offline-only.

## Objective

Create evaluation-owned datasets, DRAFT annotation templates, deterministic evaluators, replay identity, and safe offline artifacts without changing product runtime behavior.

## Current State

Production uses `LLMGradingService` and `AssessmentGenerationService` with OpenAI Responses adapters. Existing Admin generation performs scope materialization, output/source-ref/domain validation, and one transaction for the DRAFT plus all Questions.

## In Scope

- Track A: 60 grading cases, 60 DRAFT human annotations, D-106 normalization, D-107 metrics, fake/replay seam, hashes and offline artifacts.
- Track B: 16 generation requests, 48 per-question DRAFT annotations, production-shaped offline provider injection, deterministic policy checks, exact D-109 binding validation, and DRAFT persistence verification.
- Focused tests, Step Note, and this implementation specification.

## Out of Scope

Paid/live provider requests, official benchmark runs, HUMAN_APPROVED annotation creation, production prompt/model/provider tuning, production code behavior changes, DB schema/migrations, RAG/retrieval/external sources, Step 7.6.

## Functional Requirements

Track A uses the actual three supported free-form types and exact D-108 distribution. Provider input contains only the production question and `{text}` learner answer. D-106 normalization is shared with human-label validation. D-107 technical and semantic denominators remain distinct.

Track B uses exact Lesson or selected Lesson/Vocabulary/Grammar IDs, question_count 3, all supported question types and all difficulty values across the suite. Production scope, generation, structured output, domain validation, and DRAFT persistence remain authoritative. Human review is per generated question.

## Technical Requirements

Canonical request identity uses sorted compact UTF-8 JSON and SHA-256 over normalized input, provider/model, prompt/schema identity, generation settings and applicable limits. Replay must be REAL-origin and exact-match. Offline manifests must remain ineligible with zero paid API calls.

## Inputs / Outputs

Inputs: versioned JSONL request/case files and separately versioned DRAFT annotations.
Outputs: run-specific per-track `manifest.json`, `cases.jsonl`, `summary.json`; summaries contain only diagnostics and frozen denominator formulas.

## Data Flow

See `docs/evaluation/step-7.7-ai-grading-content-generation-evaluation.md`, section “Data Flow”.

## Interfaces / Schemas

Evaluation DTOs are in `backend/app/evaluation/step77/contracts.py`. Production DTOs and service seams are linked in the Step Note preflight tables. No public API contract is added.

## Files / Components Changed

Evaluation package `backend/app/evaluation/step77/`, datasets and annotation templates under root `evaluation/`, focused tests under `backend/tests/`, and Step 7.7 documentation.

## Config / Environment

No production configuration change. Track B uses only the safe dedicated `chinese_learning_test` PostgreSQL target. Credential values must never enter logs or artifacts.

## Error Handling

Technical grading failures have null semantic results and safe normalized codes. Generation schema/policy failures are deterministic failures; provider or database errors are technical failures. DRAFT human annotation always defers semantic PASS.

## Testing

Run `uv run pytest -q tests/test_step77_*.py`, compile `app`, and verify locked dependencies remain unchanged. PostgreSQL integration may explicitly skip only if the safe dedicated database is unavailable; never substitute SQLite.

## Acceptance Criteria

Exact dataset/split/cell counts validate; 60 + 48 annotation templates remain DRAFT; the generation path uses production materializer/service/validators/persistence; fake artifacts are ineligible; no schema, migration, dependency, runtime, or product behavior changes occur.

## Focused Offline Rework Requirements

- Require strict UTF-8 decoding for Step-7.7 JSONL sources and readable source text without replacement or mojibake markers.
- Validate HOLDOUT isolation by canonicalizing case payloads without ID/split bookkeeping; reject semantic payload reuse and ID-only copies for both tracks.
- Track-B `generation_case_pass_rate` is `pass=true / (pass=true or false)`; null/deferred cases do not enter the denominator or fail count. Report actual DRAFT, NEEDS_ADJUDICATION, and HUMAN_APPROVED question-annotation totals.
- Replay records carry all available request, provider, model, configuration, prompt/schema, normalized-input, parsed-result, response, origin, and safe diagnostic identities. Both replay adapters must traverse the accepted production service and parser/validator seam; any identity mismatch is stale and fails closed.
- A `--track all` CLI invocation shares one run ID across both track manifests, case rows, and summaries. Each manifest carries the available reproducibility identities and explicit null values where repository/runtime identity is unavailable.

## Constraints / Non-goals

No Step 7.6, paid API calls, live external calls, official evaluation, human scoring, approval, or production behavior changes.

## Open Questions

None for offline implementation. Human semantic review and official runtime execution require later explicit authorization.
