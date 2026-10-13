# Step 7.6 — Regression Evaluation

## Codex Task

### Status

PM-FREEZE CANDIDATE.

This task is a draft for PM freeze. Do not treat it as execution authorization unless PM explicitly marks it CODEX-READY.

---

## Context

Phases 0–6 are complete through Step 6.13.

Phase 7 state:

- Step 7.1: DONE.
- Step 7.2: PM accepted.
- Step 7.3: PM threshold approved.
- Step 7.4: offline implementation verified; runtime/human/official baseline deferred.
- Step 7.5: offline implementation PM accepted; runtime/human/official baseline deferred.
- Step 7.7: offline implementation PM accepted; runtime/human/official gates deferred.
- Step 7.6: current Step.

D-102 permits downstream Phase-7 implementation in deterministic/offline mode while runtime dependencies remain deferred.

Step 7.6 evaluates Lesson Chat RAG regression only.

Regression inputs are:

```text
Step 7.3 artifacts → Retrieval Regression
Step 7.4 artifacts → Generation Regression
Step 7.5 artifacts → End-to-End Regression
```

Step 7.7 grading/content-generation evaluation is NOT part of Step 7.6.

---

## Objective

Implement a deterministic regression-comparison layer that compares an explicit Lesson Chat RAG candidate against an explicit baseline and reports:

```text
Retrieval Regression
Generation Regression
End-to-End Regression

+
critical-failure changes
+
per-case transitions
+
holdout stability changes

→ PASS | FAIL | REVIEW_REQUIRED
```

The implementation must work completely in offline deterministic test mode without paid or live provider calls.

It must not fabricate an official runtime baseline or official regression decision.

---

## Frozen Decisions

### D-110 — Holdout Stability Blocking Policy

Pass-family:

```text
STABLE_PASS
UNSTABLE_PASS
```

Fail-family:

```text
UNSTABLE_FAIL
STABLE_FAIL
```

Policy:

```text
pass-family → fail-family
→ blocking FAIL

degradation within same family
→ REVIEW_REQUIRED

improvement
→ non-blocking
```

Required examples:

```text
STABLE_PASS → UNSTABLE_PASS
→ REVIEW_REQUIRED

UNSTABLE_PASS → UNSTABLE_FAIL
→ FAIL

STABLE_PASS → UNSTABLE_FAIL
→ FAIL

STABLE_PASS → STABLE_FAIL
→ FAIL

UNSTABLE_PASS → STABLE_FAIL
→ FAIL

UNSTABLE_FAIL → STABLE_FAIL
→ REVIEW_REQUIRED

STABLE_FAIL → UNSTABLE_FAIL
→ improvement / non-blocking

UNSTABLE_FAIL → UNSTABLE_PASS
→ improvement / non-blocking

UNSTABLE_PASS → STABLE_PASS
→ improvement / non-blocking
```

Comparison policy version is frozen as:

```text
lesson-chat-regression-policy/v1
```

Any future stability-policy change requires a comparison-policy-version bump.

---

## Current Repository Seams

Inspect the actual repository before modification and preserve current conventions.

### Step 7.3

Expected current implementation boundary:

```text
backend/app/evaluation/step73/
```

Consume the existing retrieval artifacts rather than duplicating retrieval evaluation.

Required regression metrics:

```text
Recall@20
Recall@5
Precision@5
nDCG@5
```

Reuse existing case/run/dataset/config identities.

Do not alter Step-7.3 metric semantics.

### Step 7.4

Expected current implementation boundary:

```text
backend/app/evaluation/step74/
```

Consume existing generation artifacts.

Required dimensions:

```text
answer_correctness
faithfulness_groundedness
completeness
language_quality
learning_usefulness
```

Preserve existing critical-failure identities, rubric identity, judge/evaluator policy identity, provider/model identity and prompt identity where represented.

Do not alter Step-7.4 evaluation semantics.

### Step 7.5

Expected current implementation boundary:

```text
backend/app/evaluation/step75/
```

Consume existing E2E artifacts including:

```text
e2e_case_pass
technical status
latency
bucket
critical failures
holdout repeat identity
pass_count / repeat results
```

Reuse existing holdout execution identity and 3-repeat representation.

Do not redesign Step-7.5 evaluation.

---

## Scope

### In Scope

Implement:

- explicit baseline/candidate artifact loading;
- fail-closed compatibility validation;
- retrieval regression comparison;
- generation regression comparison;
- E2E regression comparison;
- technical failure comparison;
- latency comparison;
- critical-failure diff;
- per-case transition diff;
- D-110 holdout stability comparison;
- PASS / FAIL / REVIEW_REQUIRED aggregation;
- comparison-policy versioning;
- deterministic/offline fixtures and tests;
- reproducible regression artifacts;
- Step documentation.

### Out of Scope

Do NOT:

- add Step 7.7 as a regression layer;
- make paid LLM/provider calls;
- run live external provider evaluation;
- create or promote an official runtime baseline;
- add a baseline registry/database;
- auto-select the latest run as baseline;
- implement CI/CD integration;
- wire deployment/release gates;
- start Phase 8;
- tune prompts;
- tune retrieval;
- tune models;
- change production RAG behavior;
- change 7.3/7.4/7.5 metric semantics;
- change evaluation datasets;
- add production monitoring;
- add automated rollback;
- add online A/B testing.

---

## Baseline Contract

Every comparison must receive an explicit:

```text
baseline_run_id
candidate_run_id
```

or equivalent explicit per-layer run/artifact identities when source evaluations use independent run IDs.

Never perform:

```text
latest run
→ automatically baseline
```

There is no requirement to build a baseline registry in Step 7.6.

Official baseline approval remains external/manual PM governance.

Offline deterministic fixtures may act as test baseline/candidate inputs only.

They must never be represented as:

```text
approved production baseline
official candidate
official regression decision
```

---

## Offline / Official Eligibility

Support deterministic offline comparison.

Offline/test source artifacts:

```text
→ regression engine may execute
→ TEST comparison artifact may be produced
→ official comparison eligibility = false
```

Fail closed if code is asked to represent offline/test artifacts as official.

An official comparison can be eligible only when all required upstream source artifacts prove their official eligibility and the baseline has explicit external/manual approval.

Step 7.6 does not create that approval.

No live/provider call is needed for Step 7.6.

---

## Artifact Compatibility

Validate compatibility before numeric comparison.

### Must Match

Require compatible:

```text
dataset identity/version
dataset schema version
case IDs / case set
split assignment
metric definitions
generation rubric identity
judge/evaluator policy identity where applicable
critical-failure semantics
holdout repeat structure
evaluation-policy identities required by source artifacts
```

Layer-specific case-set compatibility:

```text
Step 7.3 baseline cases
==
Step 7.3 candidate cases

Step 7.4 baseline cases
==
Step 7.4 candidate cases

Step 7.5 baseline execution identities
==
Step 7.5 candidate execution identities
```

A material mismatch must fail closed as an incompatible comparison before metric gating.

Do not silently compare incompatible artifacts.

### May Differ

The following are system-under-test identities and may intentionally change between baseline and candidate:

```text
code_commit
embedding profile/model
chunking configuration
retrieval configuration
reranker configuration
RAG evidence threshold
prompt identity/version
LLM model/config
```

Record these differences explicitly.

Do NOT reject a comparison merely because the candidate intentionally changes one of these system components.

---

## Comparison Policy Version

Use exactly:

```text
comparison_policy_version =
lesson-chat-regression-policy/v1
```

Persist this in every regression manifest and summary/report as appropriate.

A future change to any of these requires a policy-version bump:

```text
thresholds
classification formulas
directionality
boundary semantics
compatibility rules
critical-failure gate
stability policy
overall gate semantics
```

Do not silently reinterpret old comparison artifacts under a changed policy.

---

## Metric Classification

Metric classifications:

```text
REGRESSION
STABLE
IMPROVEMENT
```

### Higher-Is-Better Metrics

Applies to:

```text
Recall@20
Recall@5
Precision@5
nDCG@5

answer_correctness
faithfulness_groundedness
completeness
language_quality
learning_usefulness

E2E pass rate
```

Use:

```text
delta = candidate - baseline
```

Classification:

```text
delta < -threshold
→ REGRESSION

abs(delta) <= threshold
→ STABLE

delta > threshold
→ IMPROVEMENT
```

### Thresholds

Retrieval:

```text
threshold = 0.02
```

for each:

```text
Recall@20
Recall@5
Precision@5
nDCG@5
```

Exact:

```text
delta = -0.02
→ STABLE
```

Generation:

```text
threshold = 0.10
```

for each generation dimension on the 0–2 scale.

Exact:

```text
delta = -0.10
→ STABLE
```

E2E pass rate:

```text
threshold = 0.02
```

Exact:

```text
delta = -0.02
→ STABLE
```

### Technical Failure Rate

Lower is better.

Use percentage-point delta:

```text
delta = candidate_rate - baseline_rate
```

Classification:

```text
delta > +0.01
→ REGRESSION

abs(delta) <= 0.01
→ STABLE

delta < -0.01
→ IMPROVEMENT
```

Exact:

```text
+0.01
→ STABLE
```

### p95 Latency

Lower is better.

Use relative delta:

```text
relative_delta =
(candidate_p95 - baseline_p95)
/
baseline_p95
```

Require baseline p95 to be finite and greater than zero.

Classification:

```text
relative_delta > +0.20
→ REGRESSION

abs(relative_delta) <= 0.20
→ STABLE

relative_delta < -0.20
→ IMPROVEMENT
```

Exact:

```text
+20%
→ STABLE
```

Do not apply the higher-is-better sign rule blindly to technical failures or latency.

---

## Critical-Failure Comparison

Critical failures are independent blocking gates.

Preserve source critical-failure identities wherever possible.

Do not introduce a lossy generic remapping merely for Step 7.6.

Represent a critical-failure occurrence with enough identity to distinguish it, equivalent to:

```text
layer
case_id
critical_failure_code
repeat_index?   # where repeated holdout execution makes it relevant
```

Compute:

```text
candidate occurrences - baseline occurrences
→ NEW_CRITICAL_FAILURES

baseline occurrences - candidate occurrences
→ RESOLVED_CRITICAL_FAILURES

intersection
→ REMAINING_CRITICAL_FAILURES
```

Rule:

```text
any new blocking critical failure
→ hard FAIL
```

Metric improvements cannot compensate.

Resolved and remaining critical failures must still be reported.

---

## Holdout Stability

Derive state from the existing 3-execution Step-7.5 representation:

```text
3/3 PASS
→ STABLE_PASS

2/3 PASS
→ UNSTABLE_PASS

1/3 PASS
→ UNSTABLE_FAIL

0/3 PASS
→ STABLE_FAIL
```

Apply D-110 exactly.

Do not average the three executions and lose state-transition information.

Store both baseline and candidate stability state per holdout case.

Store a stability transition/gate result.

---

## Per-Case Transitions

For ordinary boolean E2E case results:

```text
PASS → PASS
→ UNCHANGED_PASS

PASS → FAIL
→ REGRESSED_CASE

FAIL → PASS
→ FIXED_CASE

FAIL → FAIL
→ UNCHANGED_FAIL
```

Regression output must preserve at minimum:

```text
FIXED_CASES
REGRESSED_CASES
UNCHANGED_PASS
UNCHANGED_FAIL
NEW_CRITICAL_FAILURES
RESOLVED_CRITICAL_FAILURES
```

Equal aggregate pass rates must not hide different cases being fixed and regressed.

For holdout cases, additionally preserve:

```text
baseline_stability_state
candidate_stability_state
stability_change
stability_gate
```

---

## Overall Gate Precedence

Determine final comparison status in this precedence:

```text
1. Any NEW blocking critical failure?
   → FAIL

2. Any numeric metric classified REGRESSION?
   → FAIL

3. Any D-110 pass-family → fail-family stability transition?
   → FAIL

4. Any unresolved REVIEW_REQUIRED condition?
   → REVIEW_REQUIRED

5. Otherwise
   → PASS
```

Hard FAIL always overrides REVIEW_REQUIRED.

Example:

```text
STABLE_PASS → UNSTABLE_PASS
→ REVIEW_REQUIRED

AND

new blocking critical failure
→ FAIL

final status
→ FAIL
```

Never treat REVIEW_REQUIRED as PASS.

---

## Regression Artifact

Write comparisons under:

```text
evaluation/regressions/<comparison_id>/
├── manifest.json
├── summary.json
├── cases.jsonl
└── report.md
```

Follow existing repository artifact-writing/hash/reproducibility conventions where reusable.

Do not create a parallel artifact framework if current evaluation utilities already provide appropriate primitives.

### manifest.json

Must contain at least:

```text
comparison_id
baseline_run_id
candidate_run_id

dataset_version
schema_version

comparison_policy_version
timestamp

execution_mode
official_comparison_eligible

compatibility_result

baseline source identities
candidate source identities

source artifact hashes/identities
```

If the three source evaluation layers use independent run IDs, preserve explicit per-layer baseline/candidate run identities rather than pretending one run ID covers all source evaluations.

### summary.json

Must contain at least:

```text
retrieval_metric_deltas
retrieval_metric_classifications

generation_dimension_deltas
generation_dimension_classifications

e2e_pass_delta
e2e_pass_classification

technical_failure_delta
technical_failure_classification

latency_delta
latency_classification

bucket_level_deltas

stability_deltas
stability_gate_results

critical_failure_deltas

fixed_case_count
regressed_case_count
unchanged_pass_count
unchanged_fail_count

gate_results
overall_status
```

### cases.jsonl

Per relevant case preserve:

```text
case_id

baseline_result
candidate_result
transition

baseline_critical_failures[]
candidate_critical_failures[]
new_critical_failures[]
resolved_critical_failures[]

baseline_stability_state?
candidate_stability_state?
stability_change?
stability_gate?

notes?
```

### report.md

Include human-readable:

```text
baseline and candidate identities
compatibility result
system-configuration differences

Retrieval Regression
Generation Regression
End-to-End Regression

bucket-level changes
fixed/regressed cases
holdout stability transitions
critical-failure changes

gate results
final PASS / FAIL / REVIEW_REQUIRED
```

---

## Interfaces / Implementation Boundary

Create a focused Step-7.6 evaluation module following existing evaluation conventions.

Prefer small explicit boundaries equivalent to:

```text
artifact loading
compatibility validation
metric comparison
critical-failure diff
stability comparison
case transition comparison
overall gate aggregation
artifact writing
```

Exact filenames should follow the repository's existing Phase-7 structure after inspection.

Do not modify production RAG services merely to support regression comparison.

Do not make provider calls from this module.

---

## Deterministic Fixtures

Create deterministic TEST-only baseline and candidate artifact fixtures sufficient to exercise all regression rules.

Fixtures must be clearly marked test/offline and must fail official-eligibility checks.

Do not manufacture official runtime provenance.

Fixtures should reuse actual Step-7.3/7.4/7.5 artifact schemas or the production loaders for those artifacts.

Do not build synthetic schemas that drift from actual source contracts.

---

## Required Tests

### Baseline

Test:

```text
explicit baseline_run_id
→ required

no latest-run auto-selection

offline/test run
→ cannot be official baseline
```

### Compatibility

Test:

```text
compatible artifacts
→ accepted

dataset mismatch
→ incompatible

schema mismatch
→ incompatible

case-set mismatch
→ incompatible

split mismatch
→ incompatible

holdout repeat-identity mismatch
→ incompatible

system-config differences
→ recorded
→ not automatically incompatible

comparison_policy_version
→ persisted
```

### Retrieval

Test all primary metrics independently.

Required examples:

```text
Recall@20 -3pp
→ REGRESSION

Recall@20 exactly -2pp
→ STABLE

positive change >2pp
→ IMPROVEMENT
```

Also test:

```text
Recall@5
Precision@5
nDCG@5
```

classification independently.

### Generation

Required:

```text
-0.05
→ STABLE

exact -0.10
→ STABLE

degradation greater than 0.10
→ REGRESSION
```

Test each of the five dimensions independently.

### E2E

Required:

```text
pass-rate exact -2pp
→ STABLE

pass-rate degradation >2pp
→ REGRESSION
```

### Technical Reliability

Required:

```text
technical-failure increase exactly +1pp
→ STABLE

increase >1pp
→ REGRESSION

sufficient decrease
→ IMPROVEMENT
```

### Latency

Required:

```text
exact +20%
→ STABLE

+25%
→ REGRESSION

sufficient decrease
→ IMPROVEMENT

baseline p95 <= 0
→ comparison rejected / invalid
```

### Critical Failures

Required:

```text
new critical
→ FAIL

resolved critical
→ reported

unchanged critical
→ retained

metric improvement + new critical
→ FAIL
```

### D-110 Stability

Test at minimum:

```text
STABLE_PASS → UNSTABLE_PASS
→ REVIEW_REQUIRED

UNSTABLE_PASS → UNSTABLE_FAIL
→ FAIL

STABLE_PASS → UNSTABLE_FAIL
→ FAIL

STABLE_PASS → STABLE_FAIL
→ FAIL

UNSTABLE_PASS → STABLE_FAIL
→ FAIL

UNSTABLE_FAIL → STABLE_FAIL
→ REVIEW_REQUIRED

STABLE_FAIL → UNSTABLE_FAIL
→ improvement / non-blocking

UNSTABLE_FAIL → UNSTABLE_PASS
→ improvement / non-blocking

UNSTABLE_PASS → STABLE_PASS
→ improvement / non-blocking
```

Verify hard-gate precedence:

```text
STABLE_PASS → UNSTABLE_PASS
+
new blocking critical failure
→ final FAIL
```

### Per-Case

Required:

```text
PASS → FAIL
→ REGRESSED_CASE

FAIL → PASS
→ FIXED_CASE

PASS → PASS
→ UNCHANGED_PASS

FAIL → FAIL
→ UNCHANGED_FAIL
```

### Final Status

Required:

```text
all clean
→ PASS

numeric hard regression
→ FAIL

new critical
→ FAIL

pass-family → fail-family
→ FAIL

same-family degradation only
→ REVIEW_REQUIRED

review condition + hard failure
→ FAIL
```

### Artifacts

Verify:

```text
manifest + summary + cases + report created

exact baseline/candidate identities preserved

comparison policy version preserved

offline fixtures remain non-official

artifact output deterministic/reproducible

summary counts agree with cases

report decision agrees with summary

source identities/hashes are preserved where required
```

No paid/provider calls may occur.

---

## Error Handling

Fail closed for:

```text
missing baseline/candidate artifact
unknown artifact/schema version
incompatible datasets
incompatible case sets
invalid repeat structure
invalid metric value
non-finite numeric values
invalid latency denominator
unknown required critical-failure representation
official request using ineligible offline artifacts
```

Do not silently drop malformed cases or unavailable required metrics.

Use typed Step-7.6 evaluation errors consistent with current Phase-7 conventions.

Do not expose raw provider/database secrets or unrelated internal data.

---

## Documentation

Produce/update Step-7.6 documentation containing:

### Step Note

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- reusable approach for another project
- Common Mistakes
- Definition of Done

### Concepts

Record only concepts actually used, expected to include:

```text
Regression baseline — BOTH
Artifact compatibility — BOTH
Regression threshold — BOTH
Metric directionality — BOTH
Critical-failure gate — AI
Holdout stability — AI
Per-case transition diff — BOTH
Regression policy versioning — SYSTEM
```

### Tools

Record only tools actually used.

Likely, if present in implementation:

```text
Python — SYSTEM
Pydantic — SYSTEM
pytest — SYSTEM
```

Do not record alternatives or unused tooling.

---

## Acceptance Criteria

Step-7.6 offline implementation is acceptable for Specialist review when:

- explicit baseline/candidate identities are required;
- latest-run auto-baseline selection does not exist;
- offline fixtures cannot masquerade as official runs;
- no baseline registry/database was added;
- compatibility fails closed before comparison;
- intentional system-config changes are recorded without automatically invalidating comparison;
- Retrieval, Generation and E2E regression are reported separately;
- all four retrieval metrics use frozen 2pp threshold semantics;
- all five generation dimensions use frozen 0.10 semantics;
- E2E pass rate uses frozen 2pp semantics;
- technical failure rate uses correct lower-is-better +1pp semantics;
- p95 latency uses correct relative +20% semantics;
- all exact threshold boundaries are STABLE;
- new blocking critical failures force FAIL;
- critical-failure identities are preserved without lossy remapping;
- per-case fixed/regressed/unchanged transitions are reported;
- holdout stability states derive from 3 repeats correctly;
- D-110 is implemented exactly;
- same-family stability degradation produces REVIEW_REQUIRED;
- pass-family → fail-family produces FAIL;
- hard FAIL gates override REVIEW_REQUIRED;
- final status is exactly PASS / FAIL / REVIEW_REQUIRED;
- comparison policy is exactly `lesson-chat-regression-policy/v1`;
- regression artifacts contain manifest, summary, cases and report;
- deterministic fixture tests cover all required boundaries/transitions;
- no paid/live provider call occurs;
- no production RAG behavior is changed;
- no Step-7.7 regression layer is introduced;
- no CI/CD/deployment/Phase-8 work is added;
- Step documentation, Concepts and Tools are updated.

---

## Required Codex Handoff

Return:

```text
Step
Status
What was done
Key decisions preserved
Files/components changed
Tests run/results
Artifact paths
Acceptance Criteria status
Concepts added
Tools added
Problems/risks
Decisions needed
Recommended next action
```

Codex must not claim Step 7.6 DONE or PM acceptance.

Expected successful handoff status:

```text
READY_FOR_SPECIALIST_REVIEW — OFFLINE REGRESSION IMPLEMENTATION
```

If a real conflict with frozen PM decisions or accepted repository contracts is discovered:

```text
BLOCKED — DECISION NEEDED
```

Do not silently redesign the policy.

---

## Constraints

- One frozen Step only.
- No architecture expansion.
- No new service/framework without an actual Step-7.6 requirement.
- No DB migration unless an unexpected existing authoritative contract proves one is strictly required; if that occurs, stop and report the conflict rather than inventing persistence.
- No live provider/network requirement.
- No official benchmark execution.
- No baseline promotion.
- No Step 7.7 regression.
- No Phase 8.
- Do not authorize future Steps.
