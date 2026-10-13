# Step 6.11 — Free-form AI Grading

## Objective

Replace the unavailable Step-3.4 AI grader for free-form assessment answers with structured production grading while preserving the existing `AIGrader` boundary and `AttemptAnswer` lifecycle.

## Why

Vietnamese-to-Chinese and Chinese-to-Vietnamese translation and sentence-writing answers can have valid partial-credit responses that deterministic exact matching cannot assess reliably.

## Mental Model

```text
Assessment domain owns question truth, score semantics, persistence, pass/progress/unlock.
AI grader owns semantic grading of supplied authoritative material.
Provider owns structured inference transport only.
```

## Core Knowledge

- **Structured Outputs:** The provider returns only `grading_status`, `score`, and `feedback` through a strict Pydantic schema.
- **Semantic abstention:** `UNCERTAIN` means a functioning grader cannot make a defensible semantic judgment. It is distinct from provider failure.
- **Grading domain validation:** Application code validates score/status consistency and derives the existing `GradeResult`.
- **Partial-credit correctness invariant:** A graded answer is correct only when its score equals its full maximum points; partial credit stays numerically useful and is not marked correct.
- **Provider boundary and retry normalization:** OpenAI SDK details stay in one adapter with one application-owned transient retry.
- **External-inference transaction boundary:** Assessment data is materialized before model inference; persistence uses the existing short transaction afterward.

## Data Flow

```text
DB read/materialize including Question.prompt
→ end read transaction
→ construct structured grading request
→ provider-exact token count including the structured-output schema
→ stateless Responses structured inference
→ validate output and derive D-095 correctness
→ short atomic AttemptAnswer/attempt persistence
→ progress/unlock only after successful grading
```

The token-count request and `responses.parse` share the same model, instructions, user input, reasoning effort, truncation mode, and effective strict schema. The schema is sent to the count endpoint as `text.format`, matching the SDK schema generated for `text_format=StructuredGradingOutput`. Output-token limits are checked against the exact input count. No grading input is truncated.

## Key Design Decisions

- Use the existing OpenAI API configuration and `gpt-5.4-mini-2026-03-17` through the official pinned OpenAI Python SDK and Responses API.
- The model does not return `is_correct`; the backend derives it as `score == max_points` for `GRADED` results.
- `UNCERTAIN` requires a null score and null correctness. Technical failures follow the existing `GRADING_FAILED` / `AI_GRADING_UNAVAILABLE` flow.
- `reasoning_summary` and hidden chain-of-thought are omitted.
- Missing API credentials are lazy: startup and deterministic grading do not require them.
- No new answer-length limit, RAG, external retrieval, memory, citations, persistence model, schema, migration, dependency, or public API field was added.
- Inference and transient retries occur after the assessment read transaction ends. Existing attempt persistence, progress, and unlock ownership remain unchanged.

## Reusable Approach

Keep authoritative domain input, prompt construction, provider transport, structured validation, business invariant derivation, and persistence as separate boundaries. Use provider token preflight only as the final input-size gate, and count the same structured request that generation receives.

## Common Mistakes

- Letting the model decide `is_correct`, assessment pass, or curriculum unlock.
- Treating partial credit as fully correct.
- Mapping timeout, missing credentials, schema failure, or input overflow to `UNCERTAIN`.
- Adding grading criteria from unstored curriculum assumptions or retrieval.
- Holding a database transaction during provider inference.
- Persisting hidden reasoning or adding a second grading table.
- Silently truncating learner answer, prompt, reference answer, or rubric.

## Definition of Done

- Only `translate_vi_zh`, `translate_zh_vi`, and `sentence_writing` use AI grading; objective question types remain deterministic.
- The grader receives only the stored prompt/type/reference/rubric/points and validated answer text.
- Full, partial, zero, uncertain, invalid-output, provider-failure, retry, and input-limit behavior is covered by focused tests.
- Assessment failures preserve submitted answers, finalize atomically as `GRADING_FAILED`, and skip progress/unlock.
- Focused and regression suites, full backend pytest, compileall, lock check, and Alembic checks pass without schema drift.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Structured Outputs | AI | 6.11 | Constrains grading results to a strict machine-validated shape |
| Semantic abstention | AI | 6.11 | Represents genuinely ungradable answers separately from errors |
| Grading domain validation | BOTH | 6.11 | Maps provider output into the application’s `GradeResult` safely |
| Partial-credit correctness invariant | BOTH | 6.11 | Derives correctness from full score without discarding partial points |
| External-inference transaction boundary | SYSTEM | 6.11 | Keeps database transactions closed during model latency |
| Provider retry/error normalization | AI | 6.11 | Separates transient transport failures from semantic uncertainty |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| OpenAI Responses API | AI | 6.11 | Performs structured free-form grading inference |
| OpenAI Python SDK (`openai==3.20.0`) | SYSTEM | 6.11 | Provides asynchronous Responses parsing, preflight, and client transport |
| Pydantic | SYSTEM | 6.11 | Defines and validates the strict provider output schema |
