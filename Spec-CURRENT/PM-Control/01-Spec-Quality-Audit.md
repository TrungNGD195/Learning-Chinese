# Specification Quality Audit

## Audit Scope

Reviewed the full specification set across product definition, system design, data model, backend, frontend, ingestion, RAG/AI, evaluation, and production readiness.

Review dimensions:

```text
MVP requirement coverage
cross-phase consistency
schema/API consistency
state-machine consistency
failure semantics
RAG correctness
security boundaries
Codex implementability
testing/acceptance testability
scope control / over-engineering risk
production-readiness gaps
specialist ownership/dependencies
```

## Severity Model

- **BLOCKER** — implementation can produce incorrect architecture/product behavior or cannot be completed without invention.
- **MAJOR** — likely to create inconsistent implementation, unsafe behavior, or a missing MVP capability.
- **MINOR** — stale wording/checklist/reference that can mislead an agent but does not change core architecture.

## Findings and Remediation

| ID | Severity | Finding | Risk | Remediation | Status |
|---|---|---|---|---|---|
| A-01 | BLOCKER | Phase 0 required real free-form AI grading but no implementation Step existed. | MVP can ship with fake grader. | Added Step 6.11 and Step 7.7 evaluation coverage. | FIXED |
| A-02 | BLOCKER | Phase 0 required AI lesson exercise/test generation but no implementation Step existed. | Admin AI-generation requirement missing entirely. | Added Step 6.12, 6.13 and Step 7.7. | FIXED |
| A-03 | BLOCKER | RAG considered evidence usable merely because a candidate existed. | Vector search almost always returns a nearest neighbor; INTERNAL_KB/external/refusal tiers could become dead paths and hallucination risk rises. | Step 6.5/6.8 now use calibrated rerank evidence gate and distinguish semantic no-evidence from technical failure. | FIXED |
| A-04 | BLOCKER | `messages.content NOT NULL` conflicted with creation of `ASSISTANT/PENDING` before generation. | Conversation lifecycle cannot be persisted without dummy content or schema violation. | Assistant PENDING/FAILED may use NULL; USER and COMPLETED assistant content remain non-empty by invariant. | FIXED |
| A-05 | MAJOR | Phase 2 citation schema conflicted with Phase 6 citation contract/migration. | Duplicate/incompatible migrations and API mismatch. | Phase 2 target schema reconciled with Step 6.10; Step 6.10 requires schema reconciliation rather than duplicate create. | FIXED |
| A-06 | MAJOR | Document used one status while ingestion required independent machine-processing and human-review state. | Invalid lifecycle combinations and unclear approval behavior. | Canonical `processing_status` + `review_status` introduced. | FIXED |
| A-07 | MAJOR | Auth/Profile UI was only a route skeleton. | Product auth flows not actually usable. | Added Step 4.6. | FIXED |
| A-08 | MAJOR | Admin content/statistics UI was only a skeleton and APIs lacked several required admin use cases. | Admin cannot operate curriculum/content/metrics. | Expanded Step 3.4; added Step 4.7. | FIXED |
| A-09 | MAJOR | Document ingestion had backend pipeline but no Admin workflow UI. | Admin cannot upload/review/approve documents end-to-end. | Added Step 5.8. | FIXED |
| A-10 | MAJOR | Product required learner password change but no executable API/UI contract existed. | Auth/Profile flow could not fulfill the stated product requirement. | Added `POST /api/v1/auth/change-password` in Step 3.5 and corresponding Step 4.6 UI behavior, including refresh-session revocation semantics. | FIXED |
| A-11 | MAJOR | Production requirements had no explicit implementation phase for CI/deploy/rate-limit/backup/restore/observability. | Product success criteria cannot be demonstrated before release. | Added Phase 8, Steps 8.1–8.4. | FIXED |
| A-12 | MAJOR | Approved Phase-5 chunks did not have an explicit post-embedding activation path. | Knowledge can be “approved” but not retrieval-ready, or an incomplete version can become active. | Step 6.2 now defines chunk→embedding→vector readiness→atomic activation; failed build preserves previous active version. | FIXED |
| A-13 | MAJOR | V0 multi-turn evaluation implied query rewriting/history-aware retrieval that Step 6.9 did not implement. | Evaluation can fail by testing a capability outside scope. | Multi-turn dataset now requires history for generation interpretation while current query alone still retrieves sufficient evidence. | FIXED |
| A-14 | MAJOR | 120 hand-authored evaluation cases were an oversized hard gate for a 3–4 month learning project. | Evaluation work can dominate implementation. | 60 approved cases is minimum implementation gate; 120 is portfolio target. | FIXED |
| A-15 | MAJOR | 100 MB upload limit was hard-coded despite synchronous processing and unknown deployment limits. | Memory/timeouts/DoS risk and unrealistic V0 default. | `DOCUMENT_MAX_UPLOAD_MB`, development default 20 MB; higher limit requires representative testing/PM approval. | FIXED |
| A-16 | MAJOR | Out-of-domain evaluation label could be interpreted as requiring a separate classifier service. | Unnecessary extra LLM call/over-engineering. | V0 uses system-domain restriction + evidence gate + deterministic safe refusal; evaluation label does not require classifier. | FIXED |
| A-17 | MINOR | Frontend CORS example used port 3000 while Vite default is 5173. | Local auth/API integration confusion. | Updated to 5173. | FIXED |
| A-18 | MINOR | `GRAMMER` typo in retrieval filter. | Enum/filter mismatch. | Corrected to `GRAMMAR`. | FIXED |
| A-19 | MINOR | Residual Phase-10 references existed although current roadmap ends at Phase 8. | Broken dependency/reference trail. | Re-pointed to Phase 8/current evaluation work. | FIXED |
| A-20 | MINOR | Older phase documents intentionally said tools/providers were unresolved, which could be mistaken for current state. | Coding agent may ignore later stack decisions. | Added historical-phase notes and PM precedence rules. | FIXED |

## Timed Decisions — Not Current Specification Defects

The architecture-level choices required to start implementation are resolved in `04-Decision-Log-and-Open-Gates.md`. Remaining items are deliberately timed decisions and evidence gates, not permission for Codex to guess:

- choose the concrete LLM provider/model before provider-specific Step 6.7 implementation;
- choose the external retrieval provider and reviewed domain allowlist before Step 6.8-B is enabled;
- benchmark local embedding/reranker runtime before deciding whether production needs hosted inference;
- profile representative documents before deciding whether synchronous ingestion must evolve to a worker/queue;
- choose concrete production DB/storage/email/hosting vendors in Step 8.3.

None of these blocks Wave 1 / Step 3.1.

## Final Audit Assessment

The previous spec set was **not safe to hand directly to Codex** because several MVP capabilities were absent and multiple contracts contradicted each other.

After the remediation in this reviewed set:

```text
Product requirement coverage    COMPLETE for stated MVP
Architecture boundaries         EXPLICIT
Cross-phase contracts           CONSISTENT after reconciliation
Failure semantics               EXPLICIT for critical AI/data paths
Testing/acceptance              IMPLEMENTABLE
Open architecture choices       RESOLVED OR TIME-BOXED TO THE AFFECTED STEP
Codex autonomy required         LIMITED TO LOCAL IMPLEMENTATION DETAILS
```

A Step may start only when the decisions that affect that Step are already resolved; later timed decisions must not be pulled forward or guessed.
