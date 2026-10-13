# Regression comparison: test

- Status: **PASS**
- Mode: `TEST_ONLY`
- Policy: `lesson-chat-regression-policy/v1`
- Baseline: `baseline`
- Candidate: `candidate`

## Interpretation

This report compares only the explicitly supplied Step 7.3, 7.4, and 7.5 artifacts. Step 7.7 is not a regression layer.
TEST_ONLY artifacts are ineligible for official release decisions. No baseline is promoted by this operation.

## Compatibility

- All required compatibility checks passed.

## Metrics

```json
{
  "step73": {
    "groups": {
      "overall": {
        "overall": {
          "reranked_ndcg5": {
            "baseline": 0.75,
            "candidate": 0.76,
            "classification": "STABLE",
            "delta": 0.010000000000000009,
            "direction": "higher_is_better",
            "threshold": 0.02
          },
          "reranked_precision5": {
            "baseline": 0.7,
            "candidate": 0.71,
            "classification": "STABLE",
            "delta": 0.010000000000000009,
            "direction": "higher_is_better",
            "threshold": 0.02
          },
          "reranked_recall5": {
            "baseline": 0.8,
            "candidate": 0.81,
            "classification": "STABLE",
            "delta": 0.010000000000000009,
            "direction": "higher_is_better",
            "threshold": 0.02
          },
          "semantic_recall20": {
            "baseline": 0.91,
            "candidate": 0.92,
            "classification": "STABLE",
            "delta": 0.010000000000000009,
            "direction": "higher_is_better",
            "threshold": 0.02
          }
        }
      }
    }
  },
  "step74": {
    "groups": {
      "overall": {
        "overall": {
          "answer_correctness": {
            "baseline": 1.1,
            "candidate": 1.2,
            "classification": "STABLE",
            "delta": 0.09999999999999987,
            "direction": "higher_is_better",
            "threshold": 0.1
          },
          "completeness": {
            "baseline": 1.2,
            "candidate": 1.3,
            "classification": "STABLE",
            "delta": 0.10000000000000009,
            "direction": "higher_is_better",
            "threshold": 0.1
          },
          "faithfulness_groundedness": {
            "baseline": 1.0,
            "candidate": 1.1,
            "classification": "STABLE",
            "delta": 0.10000000000000009,
            "direction": "higher_is_better",
            "threshold": 0.1
          },
          "language_quality": {
            "baseline": 1.0,
            "candidate": 1.1,
            "classification": "STABLE",
            "delta": 0.10000000000000009,
            "direction": "higher_is_better",
            "threshold": 0.1
          },
          "learning_usefulness": {
            "baseline": 1.1,
            "candidate": 1.2,
            "classification": "STABLE",
            "delta": 0.09999999999999987,
            "direction": "higher_is_better",
            "threshold": 0.1
          }
        }
      }
    }
  },
  "step75": {
    "groups": {
      "overall": {
        "overall": {
          "latency_p95": {
            "baseline_ms": 1100.0,
            "candidate_ms": 1080.0,
            "classification": "STABLE",
            "relative_delta": -0.01818181818181818,
            "threshold": 0.2
          },
          "pass_rate": {
            "baseline": 0.9,
            "candidate": 0.91,
            "classification": "STABLE",
            "delta": 0.010000000000000009,
            "direction": "higher_is_better",
            "threshold": 0.02
          },
          "technical_failure_rate": {
            "baseline": 0.02,
            "candidate": 0.01,
            "classification": "STABLE",
            "delta": -0.01,
            "direction": "lower_is_better",
            "threshold": 0.01
          }
        }
      }
    }
  }
}
```

## D-110 holdout transitions

```json
[
  {
    "baseline_state": "STABLE_PASS",
    "candidate_state": "STABLE_PASS",
    "case_id": "fixture-holdout-01",
    "classification": "STABLE"
  }
]
```

## Bucket changes

```json
[]
```

## Critical failure changes

```json
{
  "new": [],
  "persisting": [],
  "resolved": []
}
```
