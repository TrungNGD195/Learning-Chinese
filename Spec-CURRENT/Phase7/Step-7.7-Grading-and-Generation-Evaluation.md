# Step 7.7 — AI Grading & Content-Generation Evaluation

## Context
Phase 0 defines AI grading quality as a launch criterion and requires generated exercise/test content to stay in selected scope with mandatory Admin review.

## Objective
Create reproducible evaluation for Step 6.11 free-form grading and Step 6.12 assessment generation.

## Current State
Real AI grading/generation are implemented with one selected V0 provider/model; evaluation artifact conventions from 7.1–7.6 exist.

## In Scope
- human-labeled grading benchmark.
- LLM/Human grading agreement.
- uncertainty behavior.
- generation scope/schema/answerability checks.
- artifacts usable by regression/release review.

## Out of Scope
Fine-tuning, automatic prompt search, replacing Admin review, online A/B testing.

## Functional Requirements
### Grading dataset
Include representative Vietnamese→Chinese, Chinese→Vietnamese and sentence-writing answers: correct, incorrect, partially correct/ambiguous and cases expected to abstain. Human labels must be reviewed/approved.

Primary launch target:
```text
LLM / Human Agreement >= 95%
```
Agreement calculation must document denominator and treatment of human-disagreement/UNCERTAIN cases. Technical failures are reported separately and cannot be hidden as uncertainty.

Also report false-confident error count/rate and uncertainty rate.

### Generation evaluation
For generated assessment drafts measure at least:
- schema validity;
- selected-scope adherence;
- supported question type validity;
- answer/reference consistency/answerability under human review;
- zero automatic publication.

Generated drafts failing scope/schema are critical failures even if wording quality is good.

## Technical Requirements
Use versioned repo-controlled fixtures/annotations and deterministic run artifacts. Provider calls should be cacheable/replayable for evaluation cost control while preserving raw model result metadata.

## Inputs / Outputs
Inputs: approved grading cases, generation configs/scopes, model/prompt versions. Outputs: per-case JSONL, aggregate summary and human-readable report.

## Data Flow
```text
approved eval cases → AI capability → normalized result → compare human/policy ground truth → run artifacts
```

## Interfaces / API / Schema
Reuse service-level interfaces from 6.11/6.12; evaluation should not require frontend/browser flows.

## Files / Components
`evaluation/grading`, `evaluation/generation`, run artifacts/manifests and validators following Phase-7 conventions.

## Config / Env
Evaluation provider/model/prompt version must be recorded. Never commit provider secrets.

## Error Handling
Technical provider/parse failure is counted/reported as technical failure; do not coerce to normal incorrect/uncertain. Invalid human annotation blocks official case approval.

## Testing
Unit-test agreement metric, uncertainty accounting, generation scope checker, schema checker and artifact reproducibility.

## Acceptance Criteria
- [ ] Grading benchmark covers all free-form MVP types.
- [ ] Human labels are reviewed and versioned.
- [ ] LLM/Human Agreement is calculated reproducibly and launch target is >=95%.
- [ ] Technical failure and semantic uncertainty are separated.
- [ ] Generation evaluation checks schema, scope and answer/reference consistency.
- [ ] Auto-publish remains impossible and is explicitly verified.
- [ ] Run artifacts capture model/prompt/config identity.

## Constraints / Non-goals
Do not tune directly on holdout cases to reach the target.

## Open Questions
If agreement target is not met, PM/AI Specialist must choose prompt/model/data remediation before release; do not silently lower the Phase-0 target.
