# Step 7.6 — Codex Handoff

**Status:** READY_FOR_SPECIALIST_REVIEW — OFFLINE REGRESSION REWORK

## What was done

Compatibility now consumes the actual Step 7.3/7.4/7.5 persisted dataset/schema and evaluation-policy identities, then derives case IDs, split assignments, and Step 7.5 execution identities from producer-shaped rows. Step-7.6-only manifest hashes/policy IDs are not required. Metric semantics without an upstream manifest field remain the fixed semantics implemented by the corresponding current producer.

The Step 7.5 loader/comparator validates one row per execution, requires repeat 1 for DEVELOPMENT and repeats 1–3 for HOLDOUT, then groups by case only after validating raw identity. Output preserves the entire baseline and candidate execution rows plus per-layer, per-repeat critical-failure differences.

Output artifacts expose the required manifest, summary, and case names. Official eligibility is checked separately by producer: Step 7.3 currently supplies no sufficient official proof; Step 7.4 must be `OFFICIAL_REAL_RUNTIME`, `STAGE_B_COMPLETE`, and carry human/judge calibration evidence; Step 7.5 must carry its actual explicit runtime/eligibility flags. The offline fixture is never eligible.

## Files/components changed

- `backend/app/evaluation/step76/policy.py`
- `backend/app/evaluation/step76/compare.py`
- `backend/app/evaluation/step76/loader.py`
- `backend/app/evaluation/step76/artifacts.py`
- `backend/app/evaluation/step76/sample.py`
- `backend/tests/test_step76_regression.py`
- `evaluation/fixtures/step76/v1/**`
- `evaluation/regressions/step76-test-comparison-v1/**`
- `docs/evaluation/step-7.6-regression-evaluation.md`
- `docs/evaluation/step-7.6-codex-handoff.md`

## Key decisions preserved

- `lesson-chat-regression-policy/v1`, all metric thresholds/directions/boundaries, D-110, and hard-failure precedence are unchanged.
- No latest-run baseline selection, baseline promotion, database, migration, schema, dependency, production RAG, runtime configuration, or dataset change.
- Step 7.7 regression and Phase 8 were not started.
- Paid/live calls: 0. Official regression: NOT RUN.

## Verification

- Step 7.6 focused: `47 passed`.
- Step 7.3 unit regression: `13 passed`.
- Step 7.4 generation evaluation regression: `40 passed`.
- Combined focused run: `100 passed`.
- `python -m compileall -q app`: PASS.
- Import smoke for the Step 7.6 comparator and loader: PASS.
- Step 7.5 database-backed integration: SKIP — no dedicated Step 7.5 test module is present; live database integration was not attempted during this offline-only rework.

The deterministic comparison at `evaluation/regressions/step76-test-comparison-v1/` is TEST_ONLY synthetic fixture output, not a benchmark or official result. A real complete compatible Step 7.3/7.4/7.5 baseline/candidate pair is not available in the workspace.

## Acceptance criteria status

Offline producer-shaped compatibility, derived identities, explicit layer run IDs, repeat-preserving output, D-110, per-case transitions, output schemas, reproducibility, and per-layer official fail-closed checks are covered by tests. A production official comparison remains unavailable and was not performed.

## Concepts and tools

Concepts are listed in `step-7.6-concepts-discovered.md`; tools used are listed in `step-7.6-tools-used.md`.

## Problems / risks

Step 7.3 has no producer-owned official-eligibility assertion, so Step 7.6 cannot currently prove an official comparison for that layer. Step 7.4 and Step 7.5 runtime/human eligibility still require real producer artifacts. This is fail-closed behavior, not a synthetic substitute.

## Decisions needed

None for the offline rework.

## Recommended next action

Independent DevOps & QA Specialist review.
