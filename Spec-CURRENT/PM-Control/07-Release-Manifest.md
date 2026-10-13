# Release Manifest — Specification Baseline v1.0

## Release Identity

```text
Project: LLM + RAG Web App học tiếng Trung cho người mới bắt đầu
Spec baseline: v1.0-reviewed
Release date: 2026-09-18
PM execution model: one Codex task = one frozen Step Specification
Current frozen executable Step: 3.1 Backend Skeleton
```

## Contents

The release contains **60 numbered Phase/Step specifications** plus PM control documents.

```text
Phase 0  Product definition                         5 Steps
Phase 1  System/architecture                       5 Steps
Phase 2  Data model/schema                         5 Steps
Phase 3  Backend/application                       6 Steps
Phase 4  Frontend                                  7 Steps
Phase 5  Data ingestion                            8 Steps
Phase 6  AI/RAG                                   13 Steps
Phase 7  Evaluation                                7 Steps
Phase 8  QA/deployment/release                     4 Steps
----------------------------------------------------------
Total                                             60 Steps
```

Root context documents:

```text
README.md
PROJECT_CONTEXT.md
```

PM control documents:

```text
00 Implementation Gate
01 Specification Quality Audit
02 Requirement Coverage Matrix
03 Ownership and Execution Waves
04 Decision Log and Open Gates
05 Codex Execution Protocol
06 Step Specification Quality Checklist
07 Release Manifest
08 Final Validation Report
```

## Frozen Architecture Decisions for Wave 1

- same-site logical web topology;
- one LLM provider + one model at a time for V0; concrete model/provider selected later before Step 6.7;
- internal RAG first, trusted external fallback later;
- local embedding/reranker baseline first, production decision after measurement;
- synchronous ingestion V0 with `DOCUMENT_MAX_UPLOAD_MB=20`, worker only after evidence;
- production infrastructure vendors deferred to Phase 8.

See `04-Decision-Log-and-Open-Gates.md` for authoritative wording.

## Important Corrections Included

This release includes the reviewed corrections for:

- no standalone GLOBAL/General Chat in MVP;
- assistant PENDING/FAILED nullable message content invariant;
- canonical citation persistence contract;
- independent document processing/review states;
- RAG evidence gating based on calibrated rerank score;
- reranker technical failure separated from semantic no-evidence;
- 6.8-A → 7.3 calibration checkpoint → normal runtime evidence gate;
- 60-case initial evaluation gate / 120-case portfolio target;
- missing Auth/Profile, Admin, Document UI, AI grading/generation, evaluation, and Phase 8 Steps;
- password-change API/UI coverage;
- bounded synchronous upload default and production evidence gates.

## Execution Rule

This release is the **baseline source of truth**, not permission to run every Step immediately.

Before each executable Step:

```text
PM checks repository state
→ PM checks affected decisions/dependencies
→ PM normalizes/finalizes the Step if implementation reality changed
→ Step receives FROZEN/CODEX-READY status
→ exactly one specialist owns it
→ exactly one Codex task implements it
→ specialist reviews/tests
→ PM accepts or sends REWORK
```

Only **Step 3.1** is frozen for execution at this release point.
