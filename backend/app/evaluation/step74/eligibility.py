from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.validate_dataset import validate_dataset

DATASET_ROOT = ROOT / "evaluation/datasets/lesson_chat_rag/v0"
INCLUDED_BUCKETS = {
    "CURRENT_LESSON_ANSWERABLE",
    "INTERNAL_KB_FALLBACK",
    "TRUSTED_EXTERNAL_FALLBACK",
    "MULTI_TURN_CONTEXT",
}
EXCLUDED_BUCKETS = {"NO_EVIDENCE_REFUSAL", "OUT_OF_DOMAIN_REFUSAL"}
EXPECTED_SPLIT_BUCKETS = {
    "DEVELOPMENT": {
        "CURRENT_LESSON_ANSWERABLE": 16,
        "INTERNAL_KB_FALLBACK": 8,
        "TRUSTED_EXTERNAL_FALLBACK": 4,
        "MULTI_TURN_CONTEXT": 8,
    },
    "HOLDOUT": {
        "CURRENT_LESSON_ANSWERABLE": 4,
        "INTERNAL_KB_FALLBACK": 2,
        "TRUSTED_EXTERNAL_FALLBACK": 1,
        "MULTI_TURN_CONTEXT": 2,
    },
}


def select_eligible_cases(dataset_dir: Path = DATASET_ROOT) -> tuple[dict, list[dict]]:
    structural = validate_dataset(dataset_dir, mode="STRUCTURAL")
    official = validate_dataset(dataset_dir, mode="OFFICIAL_GATE")
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("dataset_version") != "v0.8.0" or official.get("approved_count_total") != 60:
        raise ValueError("Step 7.4 requires the official approved dataset v0.8.0")
    rows = []
    for split, filename in (("DEVELOPMENT", "development.jsonl"), ("HOLDOUT", "holdout.jsonl")):
        for line in (dataset_dir / filename).read_text(encoding="utf-8").splitlines():
            case = json.loads(line)
            if case.get("review_status") == "APPROVED" and case.get("bucket") in INCLUDED_BUCKETS:
                rows.append(case)
            elif case.get("bucket") not in INCLUDED_BUCKETS | EXCLUDED_BUCKETS:
                raise ValueError("Unknown frozen evaluation bucket")
    rows.sort(key=lambda item: (item["split"], item["case_id"]))
    counts = {split: Counter(row["bucket"] for row in rows if row["split"] == split)
              for split in EXPECTED_SPLIT_BUCKETS}
    if len(rows) != 45 or sum(row["split"] == "DEVELOPMENT" for row in rows) != 36 \
            or sum(row["split"] == "HOLDOUT" for row in rows) != 9:
        raise ValueError("Frozen Step 7.4 eligible count/split mismatch")
    for split, expected in EXPECTED_SPLIT_BUCKETS.items():
        if dict(counts[split]) != expected:
            raise ValueError(f"Frozen Step 7.4 bucket distribution mismatch for {split}")
    if any(row["bucket"] in EXCLUDED_BUCKETS for row in rows):
        raise ValueError("Excluded bucket entered eligible generation set")
    return {"dataset_manifest": manifest, "structural": structural, "official": official}, rows
