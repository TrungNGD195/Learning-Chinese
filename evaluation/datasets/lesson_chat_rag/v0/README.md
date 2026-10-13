# Lesson Chat RAG V0 Dataset (v0.8.0)

Version `v0.8.0` contains 60 approved Step 7.2 evaluation cases: 20
CURRENT_LESSON_ANSWERABLE, 10 INTERNAL_KB_FALLBACK, 5
TRUSTED_EXTERNAL_FALLBACK, 8 NO_EVIDENCE_REFUSAL, 7 OUT_OF_DOMAIN_REFUSAL, and
10 MULTI_TURN_CONTEXT.

Current contents:

| Status/count | Value |
|---|---:|
| DRAFT | 0 |
| APPROVED | 60 |
| REJECTED | 0 |
| DEVELOPMENT rows | 48 |
| HOLDOUT rows | 12 |
| CURRENT_LESSON_ANSWERABLE | 20 APPROVED (16 DEVELOPMENT / 4 HOLDOUT) |
| INTERNAL_KB_FALLBACK | 10 APPROVED (8 DEVELOPMENT / 2 HOLDOUT) |
| TRUSTED_EXTERNAL_FALLBACK | 5 APPROVED (4 DEVELOPMENT / 1 HOLDOUT) |
| NO_EVIDENCE_REFUSAL | 8 APPROVED (6 DEVELOPMENT / 2 HOLDOUT) |
| OUT_OF_DOMAIN_REFUSAL | 7 APPROVED (6 DEVELOPMENT / 1 HOLDOUT) |
| MULTI_TURN_CONTEXT | 10 APPROVED (8 DEVELOPMENT / 2 HOLDOUT) |

The TRUSTED_EXTERNAL_FALLBACK source registry is evaluation-only. It does not
select a provider, configure a domain allowlist, or implement Step 6.8-B runtime
retrieval. The later 120-case portfolio target is not a Step 7.2 gate.
