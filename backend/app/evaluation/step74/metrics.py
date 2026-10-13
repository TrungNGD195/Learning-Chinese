from __future__ import annotations

from statistics import mean

from .annotations import CALIBRATION_IDS
from .contracts import DIMENSIONS


def dimension_agreement(pairs: list[tuple[int, int]]) -> dict:
    if not pairs:
        raise ValueError("Agreement requires at least one compared case")
    matrix = [[0, 0, 0] for _ in range(3)]
    for human, judge in pairs:
        if human not in (0, 1, 2) or judge not in (0, 1, 2):
            raise ValueError("Scores must be in 0/1/2")
        matrix[human][judge] += 1
    return {
        "exact_agreement_rate": sum(h == j for h, j in pairs) / len(pairs),
        "mean_absolute_score_difference": mean(abs(h - j) for h, j in pairs),
        "confusion_matrix": matrix,
        "human_mean": mean(h for h, _ in pairs),
        "judge_mean": mean(j for _, j in pairs),
    }


def calibration_agreement(annotations: list[dict], judge_results: dict[str, dict], *, run_id: str) -> dict:
    annotation_ids = [row.get("case_id") for row in annotations]
    if (len(annotations) != 30 or len(set(annotation_ids)) != 30
            or set(annotation_ids) != set(CALIBRATION_IDS)
            or len(judge_results) != 30 or set(judge_results) != set(CALIBRATION_IDS)):
        raise ValueError("Agreement baseline requires exactly 30 human/judge case pairs")
    annotations = sorted(annotations, key=lambda row: CALIBRATION_IDS.index(row["case_id"]))
    per_dimension = {}
    exact_rates, all_differences = [], []
    human_critical_cases = judge_critical_cases = critical_agreement = 0
    for dimension in DIMENSIONS:
        pairs = [(row["scores"][dimension], judge_results[row["case_id"]]["scores"][dimension])
                 for row in annotations]
        stats = dimension_agreement(pairs)
        per_dimension[dimension] = stats
        exact_rates.append(stats["exact_agreement_rate"])
        all_differences.extend(abs(a - b) for a, b in pairs)
    for human in annotations:
        judged = judge_results[human["case_id"]]
        hset, jset = set(human["critical_failures"]), set(judged["critical_failures"])
        human_critical_cases += bool(hset)
        judge_critical_cases += bool(jset)
        critical_agreement += hset == jset
    return {
        "agreement_artifact_version": "1.0.0", "run_id": run_id,
        "case_count_expected": 30, "case_count_compared": 30,
        "per_dimension": per_dimension,
        "macro_exact_agreement_rate": mean(exact_rates),
        "overall_mean_absolute_score_difference": mean(all_differences),
        "critical_failure_set_exact_agreement_rate": critical_agreement / 30,
        "human_critical_failure_case_count": human_critical_cases,
        "judge_critical_failure_case_count": judge_critical_cases,
        "agreement_gate": None,
        "notes": "Baseline only; regression/gating deferred to Step 7.6",
    }
