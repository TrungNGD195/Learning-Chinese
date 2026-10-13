# Step 3.4 — Business APIs

## Objective

Add learner-facing curriculum, lesson, pronunciation, assessment, progress and history APIs, plus the scoped Admin content and lifecycle APIs defined by the Step 3.4 execution task.

## Why

The API layer turns the accepted PostgreSQL schema into product use cases while keeping access, grading, progression and lifecycle rules on the backend. It does not add tables or credentials/authentication.

## Mental Model

```text
HTTP router → application service → repository / SQLAlchemy session
                       ├─ validates learner ownership and content availability
                       ├─ grades deterministic questions or calls AIGrader boundary
                       └─ commits attempt + progress atomically
```

Curriculum state is derived from published targets and persisted learner outcomes. A client cannot set unlock state or submit a learner ID. Step 3.4 uses a temporary injectable current-user boundary whose default behavior is the D-011 401.

## Core Knowledge

- One `IN_PROGRESS` attempt is resumed; terminal attempts remain historical.
- Deterministic grading reads answer keys from relational question/options data and never calls an AI grader.
- The unavailable AI grader raises a technical failure; it is not represented as an uncertain grade.
- Progress is derived and updated by ProgressService after successful scored submissions.
- Admin lifecycle changes are explicit actions, not generic status patches.

## Domain Boundaries

- Routers own HTTP path, dependency and Pydantic request/response contracts.
- Curriculum owns HSK catalog, lesson content and curriculum ordering; Progress owns learner state, completion and unlock rules.
- Exercise owns assessment/attempt/grading use cases and delegates all persistence to its repository.
- Admin orchestrates Admin use cases and delegates curriculum/content persistence to Curriculum, assessment persistence to Exercise, and aggregate statistics to its own repository.
- Repositories own SQLAlchemy persistence operations and never commit; services own business rules and transaction boundaries.
- When the final theory item completes, Progress checks historical graded passing lesson-exercise attempts and applies the same completion/unlock path used after a passing submission.
- Admin is an orchestration boundary: lifecycle, curriculum-content and question validation rules live in CurriculumService and ExerciseService.
- D-009 configs use typed Pydantic product schemas; learner matching/reorder schemas omit answer keys, and fill-blank schemas expose no reference or accepted answers.
- Existing Vocabulary/Grammar attachments require only the shared entity ID and order; new entity fields beyond the required product fields remain optional when the schema permits them.

## Data Flow

Learner requests use the configured API prefix, resolve the temporary user dependency, read through the request-scoped async session, and return explicitly assembled payloads. Attempt submission validates the complete answer set, releases the read transaction before the AI boundary, then persists answers, attempt result and any progress changes in one short transaction.

## Key Design Decisions

- No schema migration or dependency change was needed.
- Learner serializers omit answer-key fields until a submitted result is reviewed.
- Theory and pronunciation progress use idempotent inserts.
- Curriculum unlock is derived from ordered units, lesson completion, passing attempts and pronunciation completion.
- Admin operations preserve shared vocabulary/grammar records and historical attempt/progress data.

## Reusable Approach

Model each endpoint as a use case, validate ownership and state in a service, return explicit DTO-shaped dictionaries, and keep transaction boundaries around the smallest atomic write set. Put replaceable external grading behind an application protocol.

## Common Mistakes

- Returning ORM entities or question answer keys directly.
- Treating a technical grader outage as a wrong or uncertain answer.
- Keeping a database transaction open while waiting on an external grader.
- Mutating unlock flags or deleting historical progress during content edits.
- Accepting an arbitrary learner ID from request payloads.

## Definition of Done

The implementation exposes the Step 3.4 learner, assessment, history/progress and Admin routes, preserves the Step 3.1–3.3 schema/dependencies, passes migration consistency and the PostgreSQL test suite, and remains ready for independent App Engineering review. This note does not assert PM acceptance.

## Concepts Actually Used

| Concept | Category |
|---|---|
| REST / use-case API contract | SYSTEM |
| Router → Service → Repository | SYSTEM |
| Dependency injection / current-user seam | SYSTEM |
| Transaction atomicity | SYSTEM |
| Idempotency | SYSTEM |
| Lifecycle state machine | SYSTEM |
| Derived progression/unlock state | SYSTEM |
| Deterministic grading | SYSTEM |
| AIGrader application boundary | AI |
| Ownership enforcement | SYSTEM |
| Pagination / whitelisted filtering | SYSTEM |

## Tools Actually Used

| Tool | Category |
|---|---|
| Python | SYSTEM |
| uv | SYSTEM |
| FastAPI | SYSTEM |
| Pydantic | SYSTEM |
| SQLAlchemy | SYSTEM |
| psycopg 3 | SYSTEM |
| PostgreSQL | DE |
| pytest | SYSTEM |
