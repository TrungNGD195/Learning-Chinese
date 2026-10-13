# Step 7.5 - Targeted Offline Implementation Rework #3 Handoff

Status: `READY_FOR_SPECIALIST_REVIEW - OFFLINE IMPLEMENTATION REWORK #3`

Repository commit/hash: unavailable; this workspace does not contain Git metadata.

## Four offline integrity fixes

- Historical context is seeded pair by pair: persist and flush each USER row, then persist and flush its ASSISTANT row with `reply_to_message_id = user.id`. Pair identities and chronological sequence numbers are captured after materialization. The DB/model integration scenario checks both pairs and the production `ConversationMemoryBuilder` reconstruction.
- A `MULTI_TURN_CONTEXT` case passes context validity only when production memory building ran, memory composition was attached, the provider reports the required historical turns in its actual generation request, the sanitized snapshot is available, memory stays outside current evidence, citation markers are removed, and the semantic context judge reports no violation. Other buckets do not require memory.
- The trace observer preserves exact deterministic production CitationValidator codes. Malformed, missing, unknown-source, source-resolution, and external-URL contract failures remain citation failures; they do not become technical failures. Missing citations map to `REQUIRED_CITATION_MISSING`. An unexpected validator exception remains a technical failure.
- Production `total_latency_ms` starts at learner application submission and ends when its response returns. Later persistence readback is marked `evaluation_only_persistence_readback_latency_ms`; its combined diagnostic is also explicitly evaluation-only and is excluded from production total latency.

## Verification

- Focused Step 7.5 unit and integration definitions: **51 passed, 12 skipped**.
- All 12 DB/model application-path cases skipped before DB connection with `DEDICATED_TEST_DATABASE_URL_OR_REQUIRED_TEST_SETTINGS_UNAVAILABLE`. The dedicated test database setting is unavailable in this environment; therefore those integration assertions are present but not executed here.
- Relevant offline Phase-6 regressions: **111 passed** (citation validator/parser, memory builder/serialization, prompt builder/formatter, rerank formatter, and retrieval scope/filter tests).
- `python -m compileall -q app`: PASS.
- Step-7.5 import smoke: PASS.
- One broader initial regression collection attempt did not start because this shell had no `DATABASE_URL`; the 111-test offline regression run used a non-routable placeholder URL only to satisfy import-time settings and did not connect to a database.
- Pytest cache writes were disabled for the regression run. The focused run emitted a cache-directory access warning; test results were unaffected.

Paid API calls: `0`.
Live external calls: `0`.
Official 84-execution run: `NOT RUN`.
Step 7.2 dataset: unchanged (`v0.8.0`, 60 APPROVED).
Human annotations: 30 DRAFT, 0 NEEDS_ADJUDICATION, 0 HUMAN_APPROVED.
No fabricated runtime bindings or official artifacts.
OOD feature and Step 7.6/7.7: not implemented or started.
RAG threshold, D-103/D-104/D-105, frozen methodology, and production product contracts: unchanged.

## Files changed

- `backend/app/evaluation/step75/database.py`
- `backend/app/evaluation/step75/evaluator.py`
- `backend/app/evaluation/step75/execution.py`
- `backend/app/evaluation/step75/observer.py`
- `backend/evaluation_tests/test_step75_evaluation.py`
- `backend/evaluation_tests/test_step75_production_integration.py`
- `docs/evaluation/step-7.5-end-to-end-rag-evaluation.md`
- `docs/evaluation/step-7.5-offline-implementation-rework-handoff.md`

No schema, migration, dependency, dataset, annotation-state, runtime-threshold, or product RAG change was made.
