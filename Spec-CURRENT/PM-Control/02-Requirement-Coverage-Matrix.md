# MVP Requirement Coverage Matrix

## Purpose

This matrix checks whether each major product capability in Phase 0 has an implementation owner and verification path.

| Requirement group | Primary implementation specs | Verification/evaluation | Owner | Coverage |
|---|---|---|---|---|
| Registration/login/reset/change-password/session/profile | 3.5, 4.6 | 8.1 | App Engineering | COVERED |
| Learner dashboard/progress | 3.4, 4.3 | 8.1 | App Engineering | COVERED |
| Pronunciation-foundation completion gate | 3.4, 4.3 | 8.1 | App Engineering | COVERED |
| HSK/curriculum/lesson unlock rules | 2.x, 3.4, 4.3 | 8.1 | Data + App | COVERED |
| Lesson vocabulary/grammar/theory | 2.x, 3.4, 4.3 | 8.1 | Data + App | COVERED |
| Objective exercises/tests | 3.4, 4.3 | 8.1 | App Engineering | COVERED |
| Free-form AI grading + uncertainty | 3.4, 6.11, 6.13 | 7.7, 8.1 | AI + App | COVERED |
| Attempts/history/retries/progress mutation | 2.x, 3.4, 4.3 | 8.1 | Data + App | COVERED |
| Lesson AI chat | 3.6, 4.4, 6.1–6.10 | 7.1–7.6, 8.1 | AI + App | COVERED |
| Current lesson → internal KB → trusted external fallback | 6.3–6.8 | 7.2–7.6 | AI Engineering | COVERED; provider gated |
| Citations | 2.3, 6.10, 4.4 | 7.4–7.6 | AI + App | COVERED |
| AI domain restriction/refusal | 6.6, 6.8 | 7.2, 7.5 | AI Engineering | COVERED |
| Conversation persistence/memory | 2.x, 3.6, 6.9 | 7.5, 8.1 | App + AI | COVERED |
| Admin HSK/curriculum/content management | 3.4, 4.7 | 8.1 | App Engineering | COVERED |
| AI lesson-exercise generation | 6.12, 6.13 | 7.7, 8.1 | AI + App | COVERED |
| AI periodic-test generation | 6.12, 6.13 | 7.7, 8.1 | AI + App | COVERED |
| Human review/publish for AI content | 3.4, 4.7, 6.12, 6.13 | 7.7, 8.1 | App + AI | COVERED |
| Document upload/parse/clean/transform/chunk/reprocess | 5.1–5.8 | 8.1 | Data + App | COVERED |
| Embedding/vector readiness/version activation | 6.1–6.3 | 7.3, 8.1 | AI + Data | COVERED |
| Admin statistics | 3.4, 4.7 | 8.1 | App Engineering | COVERED |
| Security/authz/file validation/secret handling | 3.2, 3.5, 5.2, 8.4 | 8.1, 8.4 | App + DevOps/QA | COVERED |
| Basic AI/auth rate limiting | 8.4 | 8.4 | DevOps/QA | COVERED |
| Performance targets / expected scale | 7.5, 8.1, 8.3 | production-shaped smoke/load checks | DevOps/QA + AI | COVERED; topology/model gated |
| Daily DB backup + verified restore | 8.4 | restore drill | DevOps/QA | COVERED; provider gated |
| CI/containerized dev/reproducible checks | 8.2 | CI itself | DevOps/QA | COVERED |
| Production deployment/external adapters | 8.3 | 8.3–8.4 | DevOps/QA + PM | COVERED; provider gated |

## Coverage Rule

`COVERED; provider gated` means the behavior and interface are specified, but the concrete vendor/model/provider is intentionally not selected by Codex. PM must resolve the gate before that production-shaped adapter is implemented.
