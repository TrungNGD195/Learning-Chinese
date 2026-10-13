# Codex Execution Protocol

## Goal

Use Codex as an implementation agent, not as the project architect. Architecture/product decisions remain with PM and the reviewed specifications.

## Unit of Work

Default unit:

```text
one Codex task = one Step Specification
```

Split further only when the Step itself is too large and the split preserves the same interfaces/acceptance criteria.

Never send “implement Phase 3” as one task.

## Required Task Packet

Each specialist chat prepares the following packet before asking Codex to modify code:

```text
1. Step ID + title
2. Owner specialist
3. Objective
4. Current repository state relevant to the Step
5. Exact source-of-truth spec file
6. Dependency specs/interfaces Codex may consult
7. PM decisions affecting the Step
8. In-scope / out-of-scope
9. Required interfaces/schema/API
10. Expected files/components
11. Tests to add/run
12. Acceptance criteria
13. Explicit architecture guardrails
14. Required completion report
```

## Standard Codex Prompt Template

```text
You are implementing Step <ID — TITLE> in the Trung Chinese Learning project.

ROLE
Act as an implementation engineer for this Step. Do not redesign product or architecture.

SOURCE OF TRUTH
Primary: <path to Step spec>
Also read only these dependency/control files:
- PM-Control/00-README-Implementation-Gate.md
- PM-Control/04-Decision-Log-and-Open-Gates.md
- <dependency path(s)>

PRECEDENCE
If documents conflict, follow PM-Control precedence. Do not invent a resolution to a real conflict; report it as BLOCKED.

CURRENT STATE
<specialist summary of relevant code/repo state>

TASK
Implement the Step exactly within scope.

GUARDRAILS
- Do not add unrelated features.
- Do not change public API/schema/lifecycle semantics unless the Step explicitly requires it.
- Do not add a new framework/library when the existing stack can satisfy the requirement.
- Do not rewrite already-applied migrations; create a forward migration when required.
- Do not introduce secrets or production credentials.
- Do not silently replace an error/failure state with a success fallback.
- Preserve typed/stable error codes required by the spec.
- Keep external provider details behind the specified interfaces.

BEFORE EDITING
Return a concise implementation plan containing:
- files to inspect/change;
- interface/schema changes;
- test plan;
- any blocker found.
If no blocker exists, proceed in the same task.

IMPLEMENTATION
Make the minimum coherent changes required by the Step. Keep important domain logic in the specified service/domain boundary rather than route/UI glue.

VERIFICATION
Run the Step's tests plus the smallest relevant regression suite. Run formatter/linter/type-checker/build checks required by the repo for touched code.

COMPLETION REPORT
Return:
- status: DONE | PARTIAL | BLOCKED
- what changed
- files changed
- migrations/schema/API changes
- tests/checks run and results
- acceptance criteria checklist
- deviations from spec (must be explicit; normally none)
- risks/follow-up
```

## Specialist Review After Codex

The specialist must independently check:

```text
Does implementation match the Step rather than merely pass tests?
Did Codex change architecture or scope?
Are API/schema contracts consistent with adjacent Steps?
Are failure paths tested?
Did Codex add unnecessary dependencies?
Did it hide technical failures behind fallback behavior?
Did tests verify business invariants, not only happy paths?
```

Only then send the structured handoff to PM.

## PM Acceptance Gate

PM accepts a Step only when:

- specialist handoff is complete;
- tests/checks pass or documented exceptions are approved;
- every acceptance criterion is mapped to evidence;
- no new cross-phase contradiction exists;
- any new significant decision is captured in Decision Log;
- Step Note/Concepts/Tools/spec are updated to reflect actual implementation.

## Context-Control Rule

Do not give Codex the entire 60-file documentation set by default. Give it:

```text
current Step
PM control files
only direct dependency specs/interfaces
relevant repository files
```

This reduces context dilution while preserving architecture consistency.
