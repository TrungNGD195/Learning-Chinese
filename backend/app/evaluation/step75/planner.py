from __future__ import annotations

import hashlib


DATASET_VERSION = "v0.8.0"
BUCKETS = {
    "CURRENT_LESSON_ANSWERABLE",
    "INTERNAL_KB_FALLBACK",
    "TRUSTED_EXTERNAL_FALLBACK",
    "NO_EVIDENCE_REFUSAL",
    "OUT_OF_DOMAIN_REFUSAL",
    "MULTI_TURN_CONTEXT",
}


def plan_executions(cases: list[dict]) -> list[dict]:
    """Create the frozen 84-row plan without duplicating DEVELOPMENT cases."""
    by_id = {case.get("case_id"): case for case in cases}
    if len(by_id) != len(cases) or None in by_id:
        raise ValueError("E2E_CASE_IDS_MISSING_OR_DUPLICATED")
    if len(cases) != 60 or any(case.get("dataset_version") != DATASET_VERSION for case in cases):
        raise ValueError("E2E_DATASET_MUST_BE_APPROVED_V0_8_0_60_CASES")
    if any(case.get("review_status") != "APPROVED" for case in cases):
        raise ValueError("E2E_DATASET_CONTAINS_UNAPPROVED_CASE")
    if {case.get("bucket") for case in cases} != BUCKETS:
        raise ValueError("E2E_DATASET_BUCKET_SET_MISMATCH")
    splits = {
        "DEVELOPMENT": [case for case in cases if case.get("split") == "DEVELOPMENT"],
        "HOLDOUT": [case for case in cases if case.get("split") == "HOLDOUT"],
    }
    if len(splits["DEVELOPMENT"]) != 48 or len(splits["HOLDOUT"]) != 12:
        raise ValueError("E2E_DATASET_SPLIT_COUNTS_MISMATCH")
    plan = []
    for case in sorted(cases, key=lambda row: row["case_id"]):
        repeats = (1,) if case["split"] == "DEVELOPMENT" else (1, 2, 3)
        if case["split"] not in splits:
            raise ValueError("E2E_DATASET_SPLIT_INVALID")
        for repeat in repeats:
            identity = f"{case['case_id']}:{repeat}"
            execution_id = "e2e-" + hashlib.sha256(identity.encode()).hexdigest()[:24]
            plan.append({"execution_id": execution_id, "case_id": case["case_id"],
                         "split": case["split"], "bucket": case["bucket"],
                         "repeat_index": repeat})
    if len(plan) != 84 or len({row["execution_id"] for row in plan}) != 84:
        raise ValueError("E2E_PLAN_CARDINALITY_INVALID")
    return plan
