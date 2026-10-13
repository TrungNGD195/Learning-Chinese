# Step 8.2 — Focused Clean-DB Test-Isolation Fix

## Status target

`READY_FOR_SPECIALIST_REVIEW — FOCUSED TEST-ISOLATION FIX`

Do not claim Step 8.2 DONE.
Do not start Step 8.3.
Do not change production behavior, migrations, required seed contents, or pronunciation semantics.

## Problem

On a pristine migration-only PostgreSQL + pgvector test DB, the normal backend suite can fail:

```text
tests/test_database.py::test_required_seed_is_idempotent_and_contains_only_system_rows
```

Expected pronunciation sections:

```text
TONES
INITIALS
FINALS
```

Observed after earlier conversation tests:

```text
TONES
INITIALS
FINALS
TEST_TONES
TEST_INITIALS
TEST_FINALS
```

Root cause:

```text
conversation fixture
→ sees no PronunciationSection rows
→ creates persistent TEST_* PronunciationSection system-like rows
→ scenario cleanup removes PronunciationProgress/users/etc.
→ does not remove PronunciationSection
→ later required-seed test adds canonical rows
→ strict system-seed assertion sees six rows
```

This is shared-state/test-order contamination.

## Frozen contracts

Preserve exactly:

```text
required pronunciation seed =
TONES
INITIALS
FINALS
```

Do not:

- weaken `test_required_seed_is_idempotent_and_contains_only_system_rows`;
- add TEST_* rows to required seed;
- change migrations;
- change production pronunciation behavior;
- globally delete canonical PronunciationSection system rows during scenario cleanup;
- add SQLite;
- change Step 8.2 CI semantics except as needed to validate the fix.

## Minimum implementation

### Primary file

```text
backend/tests/conversation_test_support.py
```

Replace the fallback that creates:

```text
TEST_TONES
TEST_INITIALS
TEST_FINALS
```

with the existing canonical required-seed boundary:

```python
from app.database.seeds.required import seed_required_data
```

Before conversation scenario setup needs pronunciation sections:

```text
await seed_required_data()
```

Then load/reuse only the canonical required pronunciation sections:

```text
TONES
INITIALS
FINALS
```

Prefer an explicit code filter/order instead of an unqualified `select all PronunciationSection` so the fixture depends only on the canonical system contract.

Use these canonical rows when creating the scenario learner's `PronunciationProgress`.

Keep `cleanup_scenario()` responsible only for scenario-owned rows such as `PronunciationProgress`, users, lesson/conversation data, etc.

Do **not** make cleanup delete canonical `PronunciationSection` rows.

### Expected production files changed

None.

### Expected migration files changed

None.

### Expected assertion changes

None.

`backend/tests/test_database.py::test_required_seed_is_idempotent_and_contains_only_system_rows`
must remain strict.

## Why this fix

`PronunciationSection` is required system data, not conversation-fixture-owned data.

Correct ownership:

```text
seed_required_data()
→ owns canonical system rows

conversation fixture
→ reuses canonical rows
→ owns only scenario progress/data

cleanup_scenario()
→ removes scenario-owned data
→ leaves required system seed intact
```

This removes the test-order dependency at its source.

Deleting TEST_* after each test would treat the symptom, preserve duplicate seed logic, and remain brittle.

## Focused verification

Use the dedicated PostgreSQL test DB only:

```text
APP_ENV=test
TEST_DATABASE_URL=.../chinese_learning_test
```

No SQLite.

### V1 — pristine migration-only reproduction boundary

Start with a fresh database:

```text
empty DB
→ alembic upgrade head
```

Before application seed, verify `pronunciation_sections` is empty.

### V2 — conversation fixture behavior

Run conversation-related tests using `seed_user_lesson()`, including at least:

```text
tests/test_conversation_api.py
tests/test_conversation_concurrency.py
relevant tests/test_step68a_rag.py cases using conversation_test_support
```

They must retain their existing behavior.

### V3 — no leaked synthetic system rows

After conversation cleanup, query:

```sql
select code
from pronunciation_sections
order by order_index;
```

Expected exactly:

```text
TONES
INITIALS
FINALS
```

No `TEST_*` rows.

### V4 — original failing seed test

Without resetting between V2 and V4, run:

```text
uv run pytest -q   tests/test_database.py::test_required_seed_is_idempotent_and_contains_only_system_rows
```

Must PASS.

### V5 — test-order independence

Prove both sequences:

```text
fresh DB
→ conversation tests
→ required-seed test
→ PASS
```

and:

```text
fresh DB
→ required-seed test
→ conversation tests
→ required-seed test again
→ PASS
```

No database reset between tests inside each sequence.

### V6 — full backend regression

Run:

```text
uv run pytest -q
```

Expected: no clean-DB seed contamination failure.

Record exact pass/skip counts rather than assuming previous counts.

## Files expected to change

Required:

```text
backend/tests/conversation_test_support.py
```

Only add/modify another test file if the actual repository needs a focused assertion not already covered by the strict required-seed test. Do not change that strict assertion.

## Handoff

Return:

```text
Step
Status
Root cause
Files changed
Exact fixture change
Production files changed: YES/NO
Migration files changed: YES/NO
Focused conversation test results
Original required-seed test result
Order-independence verification
Full backend pytest result
Remaining risks
Decisions needed
Recommended next action
```

Expected success status:

```text
READY_FOR_SPECIALIST_REVIEW — FOCUSED TEST-ISOLATION FIX
```

Decisions needed should be `NONE` unless actual repository evidence contradicts the canonical required-seed boundary.
