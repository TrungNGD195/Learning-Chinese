# Lesson Chat RAG Evaluation Assets

This repository directory stores the versioned Step 7.2 EvaluationCase schema,
JSONL split files, manifest, and deterministic validator. It contains
evaluation expectations only; it does not run retrieval, call providers, or
persist database evaluation records.

## Validate

From the repository root:

```text
python evaluation/validate_dataset.py --mode STRUCTURAL
python evaluation/validate_dataset.py --mode OFFICIAL_GATE
```

`STRUCTURAL` verifies schema shape and consistency while allowing DRAFT,
APPROVED, and REJECTED rows. It does not require the official approval counts.
`OFFICIAL_GATE` performs structural validation first and then requires exactly
60 manually approved cases with the frozen split and bucket distribution. An
unmet human approval gate is reported as `REVIEW_REQUIRED`.

Codex or another drafting tool must leave any newly authored or semantically
annotated case as `DRAFT`. The validator cannot determine whether ground truth
is semantically correct or who performed a review; approval is a human workflow
responsibility.

## Versioned Dataset

The initial release is in `datasets/lesson_chat_rag/v0/`. See its README and
manifest for current row counts and the official-gate contract. JSONL rows are
ordered by stable `case_id`, use UTF-8, and contain one JSON object per line.
