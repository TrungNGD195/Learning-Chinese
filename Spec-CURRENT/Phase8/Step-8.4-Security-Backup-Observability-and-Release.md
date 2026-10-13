# Step 8.4 — Security, Backup/Restore, Observability & Release Gate

## Context
Phase 0 requires security baseline, AI endpoint rate limiting, daily backup and release-quality evidence. Deployment exists from 8.3.

## Objective
Close the production-readiness gate with focused hardening, restore verification, minimum observability and final release evidence.

## Current State
Production-shaped environment exists and E2E/evaluation suites are passing candidates.

## In Scope
AI endpoint rate limiting; security headers/cookie/CORS/CSRF review for same-site topology; upload/security review; backup schedule >= daily; documented restore and performed restore verification; structured logs/health/readiness/operator metrics sufficient for MVP; final release checklist.

## Out of Scope
SOC2 program, SIEM platform, 24/7 SRE, WAF tuning program, disaster-recovery multi-region architecture.

## Functional Requirements
- Rate-limit expensive AI endpoints using stable 429 semantics and user/IP strategy appropriate to authenticated MVP.
- Daily persistent DB backup at minimum; object-storage retention/backups per chosen provider risk.
- Perform at least one restore test into isolated environment and verify representative data/invariants.
- Logs identify request/stage/error without passwords/tokens/API keys/raw private content by default.
- Final release requires E2E + Phase-7 quality gates + restore evidence.

## Technical Requirements
Use hosting/provider native capabilities where sufficient rather than adding a new observability/backup platform. Document RPO/RTO as practical MVP expectations after provider capabilities are known.

## Inputs / Outputs
Production config + backup artifacts + test/evaluation reports → release decision evidence.

## Data Flow
Runtime events → structured logs/metrics; persistent DB → scheduled backup → isolated restore verification.

## Interfaces / API / Schema
Rate-limited endpoints preserve normal API contract and standard error envelope. Health/readiness endpoints may be refined without exposing secrets.

## Files / Components
Security checklist, backup/restore runbook, observability config/docs, release report.

## Config / Env
Rate limits and retention settings environment-driven where practical. Secrets remain platform-managed.

## Error Handling
Backup failure, restore failure or critical quality/security failure blocks release; do not downgrade to warning solely to ship.

## Testing
Rate-limit tests, cookie/CORS/CSRF/security-header checks, backup job evidence, restore drill, log redaction checks, final E2E/evaluation regression run.

## Acceptance Criteria
- [ ] AI endpoints have tested basic rate limiting.
- [ ] Production cookie/CORS/CSRF posture matches same-site decision.
- [ ] Database backup runs at least daily.
- [ ] A restore has been successfully verified in isolation.
- [ ] Logs/health provide actionable diagnostics without secret leakage.
- [ ] E2E, regression and AI quality release gates pass.
- [ ] Final release report records evidence and remaining known limitations.

## Constraints / Non-goals
Use minimum operational tooling sufficient for a small MVP/portfolio deployment.

## Open Questions
None after 8.3 vendor selection; provider-specific backup/observability mechanics must be documented here.
