# PM Control — Implementation Gate

## Purpose

This folder is the implementation control layer for the project. It converts the design/specification set into a controlled execution system for specialist chats and Codex.

The goal is to prevent two common failure modes:

1. Codex fills specification gaps by inventing architecture or behavior.
2. Multiple specialist chats implement locally reasonable but globally inconsistent solutions.

## Current Gate Status

```text
BASELINE SPEC RELEASE v1.0      FROZEN
ARCHITECTURE DECISIONS          FROZEN FOR WAVE 1
CROSS-PHASE CONSISTENCY         PASS
MVP REQUIREMENT COVERAGE        PASS
CURRENT CODEX-READY STEP        3.1 Backend Skeleton
STEP 3.1 PM FREEZE              PASS
LATER EXECUTABLE STEPS          REVIEWED BASELINE; REQUIRE JIT PM FREEZE BEFORE CODEX
```

The project uses a **per-Step execution gate**. The full baseline has been reviewed for product/architecture consistency, but only a Step that has passed its final just-in-time PM freeze may be given to Codex. This prevents a later specification from becoming stale while earlier implementation changes the concrete repository state.

An explicit timed decision/evidence gate is not specification ambiguity. Codex must stop at that gate rather than choose on behalf of the project.

## Source-of-Truth Order

When two documents appear to conflict, use this precedence order:

```text
1. PM-Control/04-Decision-Log-and-Open-Gates.md
2. The current Step Specification being implemented
3. A later-phase specification that intentionally refines an earlier design
4. Earlier Phase/Step specifications
5. Comments, examples, old notes, or generated implementation plans
```

A specialist/Codex agent must not silently resolve a real conflict. Report it to PM.

## Specification Types

### Reference specifications

Phases 0–2 primarily define product, architecture, entities, data model, and constraints. They explain **why** and define contracts that later implementation must preserve.

### Executable specifications

Phases 3–8 contain implementation work. A Codex task should normally implement **one Step at a time**, not an entire Phase.

## Change Control

A change requires PM review before implementation when it changes any of:

- product scope;
- public API contract;
- database schema semantics;
- auth/session model;
- RAG fallback/evidence policy;
- LLM/provider boundary;
- deployment topology;
- persistent storage technology;
- worker/queue architecture;
- security model;
- evaluation gate.

Small implementation details that preserve the specification may use normal engineering judgment.

## Definition of "Codex-ready"

A Step is Codex-ready only when:

- dependencies are implemented or explicitly mocked as the Step allows;
- PM decision gates affecting it are resolved;
- input/output and interfaces are explicit;
- error semantics are explicit;
- files/components or ownership boundaries are clear;
- tests are specified;
- acceptance criteria are testable;
- out-of-scope items are explicit;
- no unresolved contradiction exists with a higher-precedence document.

## Required Specialist Handoff to PM

Every specialist chat must return:

```text
Step
Status
What was done
Key decisions
Files/components changed
Tests/run results
Acceptance criteria status
Concepts added
Tools added
Problems/risks
Decisions needed
Recommended next action
```

PM updates project state only after reviewing this handoff.
