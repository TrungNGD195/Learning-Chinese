# Step 7.2 — Build Evaluation Dataset

## Objective

Create the repo-controlled `EvaluationCase` contract, versioned JSONL layout,
manifest, structural validation, and official V0 approval gate for Lesson Chat
RAG. Step 7.2 stores reviewed expectations for later evaluation; it does not
execute benchmarks or redefine the Step 7.1 taxonomy.

## Data Flow

```text
permitted project content / reviewed fixture / product policy
→ draft case + ground-truth annotations
→ structural validation
→ manual semantic review
→ APPROVED or REJECTED
→ official gate counts APPROVED cases only
```

## EvaluationCase Contract

The versioned JSON Schema defines one complete Lesson Chat RAG request
expectation: stable `case_id`, schema and dataset versions, bucket and split,
question and optional conversation/lesson context, atomic
`expected_information`, optional `reference_answer`, evidence annotations,
expected scope/tier/behavior, answer properties, citation source identities,
critical-failure expectations, and review status.

Internal evidence uses a stable locator and source title, with an optional
fixture `chunk_id`. Every REQUIRED evidence item must have a
`requirement_id`, including singleton evidence. Equal requirement IDs denote
equivalent evidence members for Step 7.3. ACCEPTABLE evidence may omit that
field. External references use `EXTERNAL_URL` metadata and are validated
locally; no URL is fetched. Machine-readable critical-failure labels map
one-to-one to Step 7.1 meanings: `SERIOUS_FACTUAL_ERROR` (serious factual
error), `UNSUPPORTED_CONFIDENT_CLAIM` (confident unsupported claim or
hallucination), `FABRICATED_CITATION_OR_SOURCE` (fabricated citation/source),
`CITATION_PROVENANCE_MISMATCH` (citation provenance mismatch),
`OUT_OF_DOMAIN_ANSWER` (out-of-domain answer instead of refusal),
`CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE` (confident answer with
insufficient evidence), `RETRIEVAL_SCOPE_VIOLATION` (retrieval scope
violation), `TIER_FALLBACK_POLICY_VIOLATION` (tier/fallback policy violation),
`TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE` (technical failure treated as
no-evidence), and `REQUIRED_CITATION_MISSING` (required citation missing).
No numeric severity weights are assigned.

## Dataset and Approval Gate

The V0 JSONL files are split by `DEVELOPMENT` and `HOLDOUT`. The manifest
records all-row counts separately from APPROVED-only counts. The official
initial gate is exactly 60 APPROVED cases, split 48/12, with the frozen bucket
distribution:

| Bucket | Approved total | Development | Holdout |
|---|---:|---:|---:|
| CURRENT_LESSON_ANSWERABLE | 20 | 16 | 4 |
| INTERNAL_KB_FALLBACK | 10 | 8 | 2 |
| TRUSTED_EXTERNAL_FALLBACK | 5 | 4 | 1 |
| NO_EVIDENCE_REFUSAL | 8 | 6 | 2 |
| OUT_OF_DOMAIN_REFUSAL | 7 | 6 | 1 |
| MULTI_TURN_CONTEXT | 10 | 8 | 2 |

The 120-case portfolio is a later target, not this gate. Codex must not
self-approve ground truth: newly authored or semantically annotated cases
remain DRAFT until manually reviewed. The initial dataset contains one
synthetic out-of-domain refusal DRAFT; there are no reviewed answerable/fallback
annotations, and no evidence or external source was fabricated. Therefore the
structure can validate while the official gate remains `REVIEW_REQUIRED`.

`TRUSTED_EXTERNAL_FALLBACK` is representable as a deterministic evaluation
fixture expectation. It does not enable external retrieval, configure a
runtime allowlist, or implement Step 6.8-B.

## Validation Modes

Run from the repository root:

```text
python evaluation/validate_dataset.py --mode STRUCTURAL
python evaluation/validate_dataset.py --mode OFFICIAL_GATE
```

`STRUCTURAL` validates JSON/JSONL, case/schema fields and enums, evidence
roles and identities, bucket invariants, split separation, and manifest counts.
It allows DRAFT, APPROVED, and REJECTED rows without requiring 60 approvals.
It cannot judge semantic truth or infer whether a multi-turn query is
retrieval-sufficient; those require manual review.

`OFFICIAL_GATE` runs structural checks first, then counts APPROVED cases only
and enforces exactly 60 total, 48 DEVELOPMENT, 12 HOLDOUT, and the approved
bucket distribution above. A structurally valid dataset that has not passed
manual review returns `REVIEW_REQUIRED`.

## Concepts Discovered

- EvaluationCase ground-truth contract | QA
- Required evidence equivalence groups | QA
- Human approval state and official dataset gate | QA
- Structural versus official-gate validation | QA

## Tools Used

- Python standard library | SYSTEM
- JSON Schema | SYSTEM
- JSON Lines (JSONL) | SYSTEM

## Scope Boundaries

This Step adds no database schema or migration, runtime RAG behavior, public
API, dependency, metric, calibration, judge, benchmark runner, regression/CI
gate, or external network/provider behavior. It does not start Step 7.3.
