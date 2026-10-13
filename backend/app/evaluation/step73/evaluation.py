from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.validate_dataset import validate_dataset


DATASET = ROOT / "evaluation/datasets/lesson_chat_rag/v0"
FIXTURES = ROOT / "evaluation/fixtures/lesson_chat_rag/v0.1.0"
INTERNAL_TIERS = {"CURRENT_LESSON", "INTERNAL_KB"}


def load_cases(dataset_dir: Path = DATASET) -> tuple[dict, list[dict]]:
    validate_dataset(dataset_dir, mode="STRUCTURAL")
    official = validate_dataset(dataset_dir, mode="OFFICIAL_GATE")
    if official.get("approved_count_total") != 60:
        raise ValueError("Step 7.3 requires all 60 manually approved v0.8.0 cases")
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["dataset_version"] != "v0.8.0" or manifest["approved_count_total"] != 60:
        raise ValueError("Step 7.3 requires the frozen approved v0.8.0 dataset")
    cases = []
    for split, filename in (("DEVELOPMENT", "development.jsonl"), ("HOLDOUT", "holdout.jsonl")):
        for line in (dataset_dir / filename).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["bucket"] != "OUT_OF_DOMAIN_REFUSAL":
                cases.append(row)
    expected = {"DEVELOPMENT": 42, "HOLDOUT": 11}
    counts = {split: sum(row["split"] == split for row in cases) for split in expected}
    if counts != expected:
        raise ValueError(f"Frozen dataset internal case counts changed: {counts}")
    return manifest, cases


def plan_attempts(case: dict) -> list[dict]:
    """Build retrieval-only attempts; multi-turn history is intentionally not sent."""
    tier = case["expected_tier"]
    bucket = case["bucket"]
    lesson = case.get("lesson_context") or {}
    if tier == "CURRENT_LESSON":
        return [dict(tier="CURRENT_LESSON", label="POSITIVE", lesson_locator=lesson["lesson_locator"])]
    if tier == "INTERNAL_KB":
        return [
            dict(tier="CURRENT_LESSON", label="NEGATIVE", lesson_locator=lesson["lesson_locator"]),
            dict(tier="INTERNAL_KB", label="POSITIVE", lesson_locator=None),
        ]
    if tier == "TRUSTED_EXTERNAL":
        current = lesson.get("lesson_locator")
        if not current:
            raise ValueError("TRUSTED_EXTERNAL case must define a current Lesson for both internal-tier negatives")
        return [dict(tier="CURRENT_LESSON", label="NEGATIVE", lesson_locator=current),
                dict(tier="INTERNAL_KB", label="NEGATIVE", lesson_locator=None)]
    if tier == "NONE" and bucket == "NO_EVIDENCE_REFUSAL":
        return [dict(tier="INTERNAL_KB", label="NEGATIVE", lesson_locator=None)]
    raise ValueError(f"Unsupported Step 7.3 case tier/bucket: {tier}/{bucket}")


def evidence_groups(case: dict) -> tuple[list[set[str]], dict[str, int], dict[str, str]]:
    groups: dict[str, set[str]] = defaultdict(set)
    grades: dict[str, int] = {}
    evidence_to_id: dict[str, str] = {}
    for role, grade in (("required_evidence", 2), ("acceptable_evidence", 1)):
        for evidence in case[role]:
            if evidence.get("source_kind") != "INTERNAL_CHUNK":
                continue
            locator = evidence["stable_locator"]
            grades[locator] = max(grade, grades.get(locator, 0))
            evidence_to_id[locator] = evidence["evidence_id"]
            if grade == 2:
                groups[evidence["requirement_id"]].add(locator)
    return list(groups.values()), grades, evidence_to_id


def grade_candidate(locator_ids: set[str], grades: dict[str, int]) -> int:
    return max((grades.get(locator, 0) for locator in locator_ids), default=0)


def _metrics(candidates: list[dict], groups: list[set[str]], grades: dict[str, int], *, positive: bool) -> dict:
    if not positive:
        return {"recall": None, "precision": None, "ndcg": None}
    if not groups:
        raise ValueError("Positive retrieval attempt has no REQUIRED evidence groups")
    def locator_set(candidate: dict) -> set[str]:
        return set(candidate.get("stable_locators") or [])
    def recall(k: int) -> float:
        top = candidates[:k]
        hit = sum(any(locator_set(row) & group for row in top) for group in groups)
        return hit / len(groups)
    top5 = candidates[:5]
    relevant_count = sum(row.get("relevance_grade", 0) > 0 for row in top5)
    required_locators = set().union(*groups)
    gains = []
    seen_groups: set[int] = set()
    for row in top5:
        locators = locator_set(row)
        new_groups = {index for index, group in enumerate(groups)
                      if index not in seen_groups and locators & group}
        if new_groups:
            # Equivalent chunks can support one requirement, but repeated copies of
            # that same requirement do not earn duplicate nDCG gain.
            gains.append(3)
            seen_groups.update(new_groups)
        else:
            acceptable_only = any(grades.get(locator) == 1 and locator not in required_locators
                                  for locator in locators)
            gains.append(1 if acceptable_only else 0)
    dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal_grades = sorted([2] * len(groups) + [1 for locator, grade in grades.items()
                                               if grade == 1 and locator not in required_locators], reverse=True)[:5]
    ideal = sum(((2 ** grade) - 1) / math.log2(index + 2) for index, grade in enumerate(ideal_grades))
    return {"recall20": recall(20), "recall5": recall(5), "precision5": relevant_count / 5,
            "ndcg5": dcg / ideal if ideal else 0.0}


def attempt_metrics(candidates: list[dict], case: dict, *, positive: bool) -> dict:
    groups, grades, evidence_ids = evidence_groups(case)
    for candidate in candidates:
        matched = sorted(locator for locator in candidate.get("stable_locators", []) if grades.get(locator, 0) > 0)
        candidate["relevance_grade"] = grade_candidate(set(candidate.get("stable_locators") or []), grades)
        candidate["matched_evidence_id"] = evidence_ids[matched[0]] if matched else None
    return _metrics(candidates, groups, grades, positive=positive)


def metric_deltas(before: dict, after: dict) -> dict:
    return {name: (None if before.get(name) is None else after[name] - before[name])
            for name in ("recall5", "precision5", "ndcg5")}


def acceptance_rates(attempts: list[dict], threshold: float) -> dict:
    positive = [item for item in attempts if item["label"] == "POSITIVE"]
    negative = [item for item in attempts if item["label"] == "NEGATIVE"]
    def tier_rate(rows: list[dict], predicate) -> float | None:
        return sum(predicate(row) for row in rows) / len(rows) if rows else None
    def true(row: dict) -> bool:
        return any(c["relevance_grade"] > 0 and c["rerank_score"] >= threshold for c in row["reranked_candidates"][:5])
    def false(row: dict) -> bool:
        scores = [c["rerank_score"] for c in row["reranked_candidates"][:5]]
        return bool(scores) and max(scores) >= threshold
    result = {
        "true_evidence_acceptance_rate_overall": tier_rate(positive, true),
        "false_evidence_acceptance_rate_overall": tier_rate(negative, false),
        "positive_attempts_accepted": sum(true(r) for r in positive),
        "negative_attempts_falsely_accepted": sum(false(r) for r in negative),
    }
    for tier in sorted(INTERNAL_TIERS):
        result[f"true_evidence_acceptance_rate_{tier.lower()}"] = tier_rate([r for r in positive if r["tier"] == tier], true)
        result[f"false_evidence_acceptance_rate_{tier.lower()}"] = tier_rate([r for r in negative if r["tier"] == tier], false)
    return result


def threshold_sweep(development_attempts: list[dict]) -> dict:
    positives = [a for a in development_attempts if a["label"] == "POSITIVE"]
    negatives = [a for a in development_attempts if a["label"] == "NEGATIVE"]
    positive_by_tier = {tier: sum(a["tier"] == tier for a in positives) for tier in INTERNAL_TIERS}
    negative_by_tier = {tier: sum(a["tier"] == tier for a in negatives) for tier in INTERNAL_TIERS}
    scores = sorted({c["rerank_score"] for a in development_attempts
                     for c in a["reranked_candidates"][:5] if math.isfinite(c["rerank_score"])})
    if not scores or not positives or not negatives or any(not positive_by_tier[t] or not negative_by_tier[t] for t in INTERNAL_TIERS):
        return {"candidates": [], "pareto_frontier": [], "recommended_threshold": None,
                "recommendation_status": "REVIEW_REQUIRED"}
    candidates = [*scores, math.nextafter(scores[-1], math.inf)]
    sweep = [{"threshold": threshold, **acceptance_rates(development_attempts, threshold)} for threshold in candidates]
    frontier = []
    for row in sweep:
        better = any(
            other["false_evidence_acceptance_rate_overall"] <= row["false_evidence_acceptance_rate_overall"]
            and other["true_evidence_acceptance_rate_overall"] >= row["true_evidence_acceptance_rate_overall"]
            and (other["false_evidence_acceptance_rate_overall"] < row["false_evidence_acceptance_rate_overall"]
                 or other["true_evidence_acceptance_rate_overall"] > row["true_evidence_acceptance_rate_overall"])
            for other in sweep
        )
        if not better:
            frontier.append(row)
    min_false = min(row["false_evidence_acceptance_rate_overall"] for row in sweep)
    tied = [row for row in sweep if row["false_evidence_acceptance_rate_overall"] == min_false]
    max_true = max(row["true_evidence_acceptance_rate_overall"] for row in tied)
    tied = [row for row in tied if row["true_evidence_acceptance_rate_overall"] == max_true]
    max_min_tier_true = max(min(row[f"true_evidence_acceptance_rate_{t.lower()}"] for t in INTERNAL_TIERS) for row in tied)
    tied = [row for row in tied if min(row[f"true_evidence_acceptance_rate_{t.lower()}"] for t in INTERNAL_TIERS) == max_min_tier_true]
    recommendation = max(tied, key=lambda row: row["threshold"])
    valid = (recommendation["positive_attempts_accepted"] > 0 and all(
        recommendation[f"true_evidence_acceptance_rate_{t.lower()}"] > 0 for t in INTERNAL_TIERS))
    return {"candidates": sweep, "pareto_frontier": frontier,
            "recommended_threshold": recommendation["threshold"] if valid else None,
            "recommendation_status": "RECOMMENDATION_READY_FOR_PM" if valid else "REVIEW_REQUIRED",
            "recommendation_tradeoff": recommendation if valid else None}
