# Regression comparison: test

- Status: **FAIL**
- Mode: `TEST_ONLY`
- Policy: `lesson-chat-regression-policy/v1`
- Baseline: `baseline`
- Candidate: `candidate`

## Compatibility

- Compatible producer-shaped artifacts.

## System configuration differences

```json
{
  "step73": {
    "code_commit": {
      "baseline": "fixture-base",
      "candidate": "fixture-candidate"
    }
  },
  "step74": {},
  "step75": {}
}
```

## Retrieval Regression

```json
{
  "by_bucket:CURRENT_LESSON_ANSWERABLE": {
    "reranked_ndcg5": 0.010000000000000009,
    "reranked_precision5": 0.010000000000000009,
    "reranked_recall5": 0.010000000000000009,
    "semantic_recall20": 0.010000000000000009
  },
  "by_split:DEVELOPMENT": {
    "reranked_ndcg5": 0.010000000000000009,
    "reranked_precision5": 0.010000000000000009,
    "reranked_recall5": 0.010000000000000009,
    "semantic_recall20": 0.010000000000000009
  },
  "by_split:HOLDOUT": {
    "reranked_ndcg5": 0.010000000000000009,
    "reranked_precision5": 0.010000000000000009,
    "reranked_recall5": 0.010000000000000009,
    "semantic_recall20": 0.010000000000000009
  },
  "overall:overall": {
    "reranked_ndcg5": 0.010000000000000009,
    "reranked_precision5": 0.010000000000000009,
    "reranked_recall5": 0.010000000000000009,
    "semantic_recall20": 0.010000000000000009
  }
}
```

## Generation Regression

```json
{
  "by_bucket:CURRENT_LESSON_ANSWERABLE": {
    "answer_correctness": 0.020000000000000018,
    "completeness": 0.020000000000000018,
    "faithfulness_groundedness": 0.020000000000000018,
    "language_quality": 0.020000000000000018,
    "learning_usefulness": 0.020000000000000018
  },
  "by_split:DEVELOPMENT": {
    "answer_correctness": 0.020000000000000018,
    "completeness": 0.020000000000000018,
    "faithfulness_groundedness": 0.020000000000000018,
    "language_quality": 0.020000000000000018,
    "learning_usefulness": 0.020000000000000018
  },
  "by_split:HOLDOUT": {
    "answer_correctness": 0.020000000000000018,
    "completeness": 0.020000000000000018,
    "faithfulness_groundedness": 0.020000000000000018,
    "language_quality": 0.020000000000000018,
    "learning_usefulness": 0.020000000000000018
  },
  "overall:overall": {
    "answer_correctness": 0.020000000000000018,
    "completeness": 0.020000000000000018,
    "faithfulness_groundedness": 0.020000000000000018,
    "language_quality": 0.020000000000000018,
    "learning_usefulness": 0.020000000000000018
  }
}
```

## End-to-End Regression

```json
{
  "latency": {
    "baseline_ms": 1100.0,
    "candidate_ms": 1080.0,
    "classification": "STABLE",
    "relative_delta": -0.01818181818181818,
    "threshold": 0.2
  },
  "pass": 0.0,
  "technical_failure": 0.0
}
```

## Holdout stability

```json
[
  {
    "baseline_pass_count": 3,
    "baseline_stability_state": "STABLE_PASS",
    "baseline_state": "STABLE_PASS",
    "candidate_pass_count": 3,
    "candidate_stability_state": "STABLE_PASS",
    "candidate_state": "STABLE_PASS",
    "case_id": "fixture-holdout-01",
    "classification": "STABLE",
    "stability_change": "STABLE_PASS->STABLE_PASS",
    "stability_gate": "STABLE"
  }
]
```

## Critical-failure changes

```json
{
  "new": [
    {
      "case_id": "fixture-holdout-01",
      "code": "CAND_REPEAT_THREE",
      "layer": "step75",
      "repeat_index": 3
    }
  ],
  "persisting": [
    {
      "case_id": "fixture-dev-01",
      "code": "REPEAT_ONE_RETAINED",
      "layer": "step75",
      "repeat_index": 1
    },
    {
      "case_id": "fixture-holdout-01",
      "code": "REPEAT_ONE_RETAINED",
      "layer": "step75",
      "repeat_index": 1
    }
  ],
  "resolved": [
    {
      "case_id": "fixture-holdout-01",
      "code": "BASE_REPEAT_TWO",
      "layer": "step75",
      "repeat_index": 2
    }
  ]
}
```

## Gate results

```json
{
  "holdout_pass_to_fail": false,
  "new_critical_failure": true,
  "numeric_regression": false,
  "overall_status": "FAIL",
  "unresolved_review": false
}
```

This is an offline comparison. It does not promote a baseline or make an official release decision.
