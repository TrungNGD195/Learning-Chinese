# Step 7.6 — Regression Evaluation

## Objective

Compare explicitly selected Step 7.3 retrieval, Step 7.4 generation, and Step 7.5 end-to-end artifacts. Report metric deltas, per-case changes, critical failures, holdout stability, and a `PASS`, `FAIL`, or `REVIEW_REQUIRED` result. Step 7.7 is not a regression layer.

## Why

Independent evaluation runs own their artifact formats and identities. Compatibility must consume persisted producer identities or derive case, split, and repeat identities from the actual case rows; requiring Step-7.6-only manifest fields incorrectly rejects valid producer output.

## Mental Model

```text
explicit baseline + explicit candidate
  → load producer-shaped artifacts
  → validate persisted semantics and derive row identities
  → compare metrics and critical failures
  → preserve each Step-7.5 execution row
  → derive D-110 holdout state
  → write a reproducible offline comparison
```

Never resolve `latest` into a baseline. TEST_ONLY fixtures cannot prove official eligibility.

## Core Knowledge

The frozen policy is `lesson-chat-regression-policy/v1`. Retrieval metrics use a 0.02 threshold, generation dimensions 0.10, E2E pass rate 0.02, technical failure rate 0.01 (lower is better), and p95 relative latency 0.20 (lower is better). Exact boundaries remain `STABLE`.

D-110 maps three holdout executions to `STABLE_PASS`, `UNSTABLE_PASS`, `UNSTABLE_FAIL`, or `STABLE_FAIL`. Pass-family to fail-family is `FAIL`; same-family degradation is `REVIEW_REQUIRED`; improvement is non-blocking.

## Data Flow

Step 7.3 contributes manifest dataset/schema versions, case rows, split assignments, retrieval aggregates, and scope-violation evidence. Case-set and split identities come from `cases.jsonl`; metric names/meaning are those implemented by the Step 7.3 producer.

Step 7.4 artifacts are read from the producer's `generation/` directory. Compatibility uses its dataset, eligibility/evidence/memory policy, rubric, judge prompt/configuration, human annotation, and technical-failure policy identities. Generator/model/prompt configuration changes are recorded as system-under-test differences.

Step 7.5 stores one execution per row. The comparator validates `(case_id, repeat_index)`, requires one DEVELOPMENT execution or three HOLDOUT executions with indexes 1–3, groups only after validation, and retains the complete execution rows for comparison output. Critical failures include layer, case, code, and repeat identity.

## Key Design Decisions

- Compatibility does not require synthetic fields such as case-set hashes, metric-policy IDs, or nested repeat declarations.
- Dataset/schema identity, case IDs, split assignments, and repeat identity are compared before metrics.
- Step 7.3 currently has no producer-owned official eligibility marker, so official comparison fails closed for that layer.
- Step 7.4 eligibility requires its actual `OFFICIAL_REAL_RUNTIME` Stage-B completion and human/judge calibration evidence.
- Step 7.5 eligibility uses its actual mode and explicit official flags; offline artifacts remain ineligible.
- Output manifest and summary expose the frozen names; `cases.jsonl` includes every Step-7.5 execution row for each case plus per-repeat critical diffs and derived stability.
- Overall gates preserve D-110 and hard-failure precedence. No baseline is promoted.

## Reusable Approach for Another Project

Inspect each upstream artifact writer and a real artifact before designing compatibility. Prefer persisted identities, derive deterministic identities from raw rows when safe, fail closed on missing semantic evidence, and preserve source rows needed to audit aggregates.

## Common Mistakes

- Requiring manifest fields that no upstream writer emits.
- Assuming every layer uses the same official-run marker.
- Converting repeated execution rows to a dictionary keyed only by case ID.
- Comparing only aggregate rates and losing case/repeat critical-failure changes.
- Treating synthetic offline fixtures as an official baseline.

## Definition of Done

Focused offline tests cover producer-shaped artifacts, compatibility mismatches, thresholds, D-110, critical-failure changes, per-case transitions, official guards, output schemas, reproducibility, and repeat preservation. No paid/live calls, production RAG changes, dataset edits, migrations, Step 7.7 regression, Phase 8 work, or PM acceptance claim are included.
