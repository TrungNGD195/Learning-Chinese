# Step 7.7 — Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Four-state grading normalization | AI | 7.7 | Keeps D-106 agreement on UNCERTAIN, ZERO_CREDIT, PARTIAL_CREDIT, and FULL_CREDIT. |
| Human-eligible semantic denominator | SYSTEM | 7.7 | Excludes DRAFT/adjudication annotations and technical failures from semantic agreement. |
| Provider replay identity | SYSTEM | 7.7 | Binds replay output to provider input, model/config, prompt, schema, and origin run. |
| Holdout leakage fingerprint | SYSTEM | 7.7 | Detects content/config reuse even when case IDs differ. |
| Question-bound generation annotation | AI | 7.7 | Applies D-109 review at exact generated-question granularity. |
| Deferred-result denominator | SYSTEM | 7.7 | Keeps null/deferred human review outside boolean generation pass-rate math. |
| Shared evaluation run identity | SYSTEM | 7.7 | Binds both track artifacts to the same invocation for reproducibility. |
| Atomic DRAFT persistence | BOTH | 7.7 | Checks generated drafts cannot be partly saved or auto-published. |
| Content-derived annotation binding | SYSTEM | 7.7 | Recomputes each D-109 hash from immutable content and actual artifact bytes. |
| REAL-origin replay provenance | SYSTEM | 7.7 | Rejects replay without hash-verified REAL run evidence and matching identities. |
| Complete benchmark coverage gate | SYSTEM | 7.7 | Proves exact dataset, execution, and annotation coverage before eligibility. |
| Provider observer/proxy | SYSTEM | 7.7 | Preserves safe typed diagnostics across the production GradingUnavailable boundary. |
