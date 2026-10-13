# Step 7.7 — Focused PostgreSQL Regression Fix

## Mode

Focused regression fix only.

Do NOT run official Phase-7 evaluation.
Do NOT change D-106..D-109, thresholds, prompts, provider/model policy, or human-review semantics.
Do NOT start Step 8.2.
Do NOT claim Step 7.7 DONE.

## Symptom

Full backend regression exposed one failure:

```text
backend/tests/test_step77_evaluation.py::test_track_b_real_postgres_admin_generation_draft_and_atomic_failure
```

Expected:

```text
persisted_assessment_status == "DRAFT"
```

Observed:

```text
persisted_assessment_status == None
```

The same run then hit fixture cleanup blocking because a generated Assessment row still referenced the synthetic Step-7.7 Lesson fixture.

## Root Cause — Frozen for this focused fix

Production persistence succeeds first:

```text
admin_service.generate_assessment_draft(...)
→ exercise_service.persist_generated_assessment_draft(...)
→ Assessment(status="DRAFT")
→ Questions persisted
→ transaction commits
```

After persistence, Step-7.7 evaluator builds `generated_draft_content` and hashes it with:

```text
canonical_json(draft_dict)
→ json.dumps(...)
```

The persisted response contains Python `UUID` objects, including at least:

```text
assessment.lesson_id
question.id
question.assessment_id
option.id
```

`canonical_json()` uses plain `json.dumps` with no UUID encoder.

Therefore the evaluator raises:

```text
TypeError: Object of type UUID is not JSON serializable
```

This happens AFTER the production transaction commits but BEFORE `execute_generation_case()` updates:

```text
persisted_assessment_id
persisted_assessment_status
persisted_question_count
generated_draft_sha256
generated_draft_content
```

The generic evaluator exception handler then returns the default values, including:

```text
persisted_assessment_status = None
```

The database row is still present as a committed DRAFT, which also explains the later fixture-cleanup FK block.

Classification:

```text
Step-7.7 evaluator/artifact-normalization bug
NOT production assessment-generation persistence bug
NOT DRAFT lifecycle semantic failure
NOT transaction-commit failure
```

## Objective

Make Track-B persisted draft evidence JSON-safe before hashing/artifact binding, while preserving the exact frozen lifecycle semantics:

```text
AI generation
→ persisted Assessment status DRAFT
→ never auto-publish
```

No production behavior change is required.

## In Scope

- Step-7.7 evaluator JSON-safe normalization for generated persisted draft content.
- Focused tests proving persisted IDs are canonical JSON-safe strings.
- Re-run the failing dedicated-PostgreSQL integration test.
- Re-run focused Step-7.7 tests and broader relevant regressions.

## Out of Scope

Do NOT change:

- production generation semantics;
- Assessment status lifecycle;
- persistence transaction boundaries;
- provider/model/prompt configuration;
- D-106..D-109;
- human annotation/review status rules;
- official evaluation artifacts or thresholds;
- Step 8.2.

## Required Implementation Approach

Inspect the current implementation before editing:

```text
backend/app/evaluation/step77/generation.py
backend/app/evaluation/step77/artifacts.py
backend/tests/test_step77_evaluation.py
backend/app/admin/service.py
backend/app/exercise/service.py
backend/app/exercise/repository.py
```

Preserve production code unless new evidence contradicts this root cause.

### Preferred fix boundary

Fix JSON normalization inside Step-7.7 evaluator/artifact preparation.

Before calling `canonical_json()` on persisted draft content, convert non-JSON-native identity values to the canonical artifact representation.

At minimum:

```text
UUID
→ canonical string form
```

Do not stringify arbitrary values indiscriminately.

Preserve existing primitive types such as:

```text
str
int
float
bool
null
lists/dicts
```

Do not change semantic field values.

The normalized `generated_draft_content` itself must be the same JSON-safe object that is hashed and later written/validated. Do not hash one representation while storing another.

### Do not use assertion weakening

Do NOT change:

```text
assert result["persisted_assessment_status"] == "DRAFT"
```

to accept `None`.

The evaluator must report the real persisted DRAFT lifecycle correctly.

## Focused Regression Tests

Add/update focused tests proving:

1. Persisted generated draft content containing UUID-valued assessment/question/option identities is normalized to JSON-safe canonical strings.
2. `canonical_json(generated_draft_content)` succeeds.
3. The generated draft hash is stable over the normalized content.
4. The dedicated PostgreSQL integration test returns:

```text
persisted_assessment_status == "DRAFT"
persisted_question_count == 3
draft_lifecycle_valid is True
```

5. The generated Assessment row can be reloaded from a fresh DB read and is actually `DRAFT`.
6. Failed provider generation still creates no partial Assessment rows.
7. Cleanup succeeds and leaves no fixture-linked generated Assessment behind.

## Dedicated PostgreSQL Verification

Use the existing guarded test environment only:

```text
APP_ENV=test
TEST_DATABASE_URL=<dedicated chinese_learning_test PostgreSQL+pgvector DB>
```

Do NOT use SQLite.
Do NOT use production DB.

Run the exact failing test first:

```text
pytest -q backend/tests/test_step77_evaluation.py::test_track_b_real_postgres_admin_generation_draft_and_atomic_failure
```

Adapt path/cwd to the repository's normal backend workflow.

Then run the focused Step-7.7 suite:

```text
pytest -q tests/test_step77_evaluation.py
```

Do NOT run official Step-7.7 benchmark/evaluation commands.

## Broader Regression Verification

After focused tests pass, run relevant existing regression groups covering:

```text
Step 6.12 AI assessment generation
Step 7.7 evaluator
Step 7.6 regression suite
admin assessment lifecycle
```

Then, if the dedicated test environment is available, run the ordinary backend regression suite required by Step 8.1 preservation.

Do not run official Phase-7 evaluation.

## Expected Files to Change

Primary expected file:

```text
backend/app/evaluation/step77/generation.py
```

Focused tests may require:

```text
backend/tests/test_step77_evaluation.py
```

Only change `artifacts.py` if repository inspection shows a reusable evaluator-wide normalization contract is clearly preferable and does not alter frozen artifact semantics.

Production files such as these are NOT expected to change:

```text
backend/app/admin/service.py
backend/app/exercise/service.py
backend/app/exercise/repository.py
backend/app/database/models/assessment.py
```

If actual evidence requires production changes, STOP and report the conflict instead of silently expanding scope.

## Artifact / Contract Impact

Expected:

```text
Step-7.7 frozen semantic contracts: unchanged
D-106..D-109: unchanged
human-review policy: unchanged
generation DRAFT lifecycle: unchanged
```

The fix only makes evaluator-owned persisted draft evidence JSON-safe and truthfully report the already-persisted DRAFT state.

Do not fabricate HUMAN_APPROVED labels.

## Acceptance Criteria

- exact failing PostgreSQL integration test passes;
- reloaded generated Assessment is `DRAFT`;
- persisted question count remains correct;
- provider failure remains atomic;
- JSON serialization no longer fails on UUID identities;
- generated draft content and hash use the same normalized representation;
- fixture cleanup succeeds;
- focused Step-7.7 tests pass;
- relevant Step-6.12 / Step-7.6 / Admin assessment regressions pass;
- no production generation semantics change;
- no official Phase-7 evaluation run;
- no threshold/policy/provider/prompt changes.

## Required Handoff

Return:

```text
Step
Status
Exact root cause confirmed
Files changed
Normalization approach
Focused test commands/results
Dedicated PostgreSQL reproduction/result
Broader regression results
Production behavior impact
Step-7.7 artifact/contract impact
Problems/risks
Decisions needed
Recommended next action
```

Expected successful status:

```text
READY_FOR_SPECIALIST_REVIEW — FOCUSED REGRESSION FIX
```

Do not claim Step 7.7 DONE.
