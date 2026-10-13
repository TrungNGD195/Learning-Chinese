# Step 7.6 — Implementation Specification

This implementation follows `Spec-CURRENT/Phase7/Step-7.6-Regression-Evaluation.md` plus the focused PM rework instructions included in the review ZIP.

## Inputs

The caller must identify baseline and candidate systems plus explicit Step 7.3, 7.4, and 7.5 artifact directories for both. Each directory must contain `manifest.json`, `summary.json`, and `cases.jsonl` (Step 7.4's producer `generation/` subdirectory layout is accepted). The loader does not discover runs or choose a baseline.

## Producer compatibility

Compatibility consumes identities actually persisted by the selected upstream producer, and deterministically derives case-set, split, and Step 7.5 execution identities from raw `cases.jsonl` rows. It does not require Step-7.6-only manifest fields such as case-set hashes, split hashes, generic metric-policy IDs, or nested holdout-repeat declarations.

Step 7.3 identity is dataset version/schema plus producer case rows and its emitted retrieval metrics/scope evidence. Step 7.4 identity includes its dataset, eligibility/evidence/memory policies, rubric, judge configuration/prompt, human annotation, and technical-failure policy. Step 7.5 identity includes its dataset, execution plan, retrieval-scope/E2E/critical policies, judge/rubric/annotation identities, and raw `(case_id, repeat_index)` rows. SUT model/configuration/prompt changes are recorded and are not automatically compatibility failures.

Step 7.5 is one execution per row. The comparer validates the raw identities before grouping by case; DEVELOPMENT must have repeat 1, and HOLDOUT must have repeats 1, 2, and 3. Each full source execution row remains in the output case artifact.

## Official eligibility

Eligibility is checked per producer. Step 7.3 has no current persisted official-eligibility proof and therefore fails closed for official comparison. Step 7.4 uses its actual `OFFICIAL_REAL_RUNTIME` Stage-B and human/judge calibration state. Step 7.5 uses its actual execution mode and explicit official flags. All layers and explicit external/manual baseline approval are required; offline fixtures are ineligible.

## Compatibility and comparison

Compatibility is resolved before metrics. Missing or differing persisted dataset/schema/policy identities, derived case sets/splits, invalid repeat identity, or superseded artifacts blocks metric comparison. Metric semantics without a producer manifest field are the semantics defined by the current producer and are not invented as a required manifest marker. Metrics retain the frozen thresholds and directionality; finite values are required. D-110 and critical-failure identities retain layer, case, code, and repeat.

## Gate and artifacts

Status precedence is new critical failure → `FAIL`; numeric regression → `FAIL`; D-110 pass-family to fail-family → `FAIL`; unresolved compatibility or metric evidence → `REVIEW_REQUIRED`; otherwise `PASS`. The result includes explicit retrieval/generation/E2E deltas and classifications, stability gates, per-case changes, and critical-failure diffs.

The four artifacts are manifest, summary, per-case JSONL, and Markdown report under `evaluation/regressions/<comparison_id>/`. The JSONL retains baseline/candidate execution evidence per repeat. Files are reproducible for fixed source artifacts and request timestamp. Offline results remain TEST_ONLY, cannot establish official eligibility, and never promote a baseline.
