# Step 6.12 — AI Assessment Generation

## Objective

Generate reviewable DRAFT `LESSON_EXERCISE` and `PERIODIC_TEST` assessments from Admin-selected authoritative curriculum knowledge.

## Why

AI can draft question content. Scope, schema, data integrity, lifecycle, and publication remain backend/Admin controlled.

## Mental Model

```text
AI proposes structured content
≠
AI owns business state
```

## Core Knowledge

- Structured generation and strict Pydantic output validation
- Programmatic source-scope validation using runtime provenance refs
- Provider-exact token preflight and one bounded transient retry
- One atomic transaction for Assessment, scope links, Questions, and Options
- Human review remains mandatory before the existing REVIEW and PUBLISHED lifecycle

`source_refs[]` validation proves that generated questions refer to Admin-selected source items. It does not prove complete semantic entailment. The implementation adds no semantic-judge model; constrained generation, mandatory Admin review, and later evaluation remain the quality controls.

## Data Flow

```text
Admin request + require_admin
→ validate strict LESSON_EXERCISE / PERIODIC_TEST scope
→ read Lesson/Vocabulary/Grammar and copy scalar DTOs
→ close read transaction
→ build versioned prompt and exact structured request
→ provider token preflight (same model/instructions/input/reasoning/schema)
→ OpenAI Responses structured generation, outside DB transaction
→ validate count, types, source refs, and all seven D-009 question mappings
→ one transaction: Assessment(DRAFT), exact scope links, Questions, Options
→ materialize canonical Admin response before transaction commit
→ return committed response
→ Admin edits/reviews through existing lifecycle
```

## Key Design Decisions

- D-096: generation sources are Lesson, Vocabulary, and Grammar only. No Document, RAG, or external/web content.
- D-097: backend-owned question count is 1–10.
- D-098: difficulty is `EASY | MEDIUM | HARD`, prompt-only and not persisted.
- D-099: `AI_GENERATION_MAX_OUTPUT_TOKENS=4000` is backend-owned for this feature. Existing `LLM_MAX_OUTPUT_TOKENS=800` remains unchanged for grading and other capabilities.
- Provider/model, timeout, temperature, retries, and input limit reuse the frozen Step 6.7/6.11 settings. SDK retries remain zero; the application retries transient failures at most once.
- `source_refs` are runtime-only validation metadata. No difficulty, source ref, prompt, or raw provider output is persisted.
- Every generated Assessment is DRAFT. No generated result is automatically published.

## Reusable Approach

```text
human selects authoritative scope
→ backend materializes trusted data
→ model returns a strict proposal
→ programmatic scope and domain validation
→ atomic domain persistence
→ human review
```

## Common Mistakes

- Trusting prompt-only scope enforcement instead of validating exact runtime refs.
- Treating valid `source_refs` as proof of full semantic entailment.
- Mapping malformed/incomplete provider output to an infrastructure-unavailable response.
- Reading or constructing the generated assessment response after its transaction has committed.
- Letting provider output mutate the database directly.
- Holding a database transaction while waiting for AI inference.
- Persisting a valid subset after another generated question fails validation.
- Auto-publishing AI output.
- Adding RAG or web retrieval without a product requirement.
- Creating a second assessment persistence model for AI drafts.

## Definition of Done

- Admin-only endpoint is present in FastAPI OpenAPI with strict discriminated request variants and a 201 canonical Admin response.
- Both generation kinds materialize only their selected authoritative curriculum scope.
- All seven existing question types map through the existing D-009 validator.
- Exact provider preflight, bounded retry, and no-open-transaction behavior are verified.
- A single all-or-nothing transaction persists only a DRAFT.
- Focused tests, backend regression, Alembic checks, and frontend generated-contract checks pass.
- No migration, schema, runtime dependency, RAG, or Step 6.13 UI change is introduced.
