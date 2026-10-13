# Step Specification Quality Checklist

Use this checklist whenever a new Step is created or an implemented Step changes materially.

## Required Sections

- Context
- Objective
- Current state
- In Scope
- Out of Scope
- Functional Requirements
- Technical Requirements
- Inputs / Outputs
- Data Flow
- Interfaces / API / Schema where applicable
- Files / Components
- Config / Env
- Error Handling
- Testing
- Acceptance Criteria
- Constraints / Non-goals
- Open Questions

## Quality Questions

### Problem/Boundary

- Is the problem this Step solves explicit?
- Is ownership clear?
- Are dependencies named?
- Is the Step small enough to implement/review independently?

### Data/Interfaces

- Are inputs/outputs typed or structurally explicit?
- Are schema/API/state transitions explicit?
- Are authoritative sources identified?
- Is transaction ownership clear when data mutates?

### Failure Semantics

- Are semantic/user states separated from infrastructure failure?
- Are retries/idempotency defined where needed?
- Is partial failure cleanup defined?
- Can an old valid version remain available when a rebuild fails?

### Security

- Is authorization server-side?
- Are secrets/provider keys backend-only?
- Is untrusted user/document content treated as data rather than instruction?
- Are upload/URL/provider boundaries validated?

### Testing

- Are business invariants tested?
- Are negative/authorization/failure paths covered?
- Is external AI/network behavior mockable/deterministic in CI?
- Is each acceptance criterion objectively verifiable?

### Scope

- Does the Step avoid adding a framework/queue/service without demonstrated need?
- Are future alternatives kept out of current implementation?
- Are open significant decisions promoted to PM gates instead of left as vague TODOs?

## Pass Rule

A Step fails the Codex-ready gate if a coding agent must choose a significant architecture/product behavior to finish it.
