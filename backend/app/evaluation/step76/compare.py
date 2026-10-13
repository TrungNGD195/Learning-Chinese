from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from .contracts import ComparisonRequest, LAYERS
from .policy import THRESHOLDS, check_compatibility, classify_delta, classify_latency


PASS_FAMILY = {"STABLE_PASS", "UNSTABLE_PASS"}
FAIL_FAMILY = {"UNSTABLE_FAIL", "STABLE_FAIL"}


def holdout_state(pass_count: int, execution_count: int = 3) -> str:
    if execution_count != 3 or pass_count not in (0, 1, 2, 3):
        raise ValueError("D-110 holdout state requires exactly three repeats")
    return {3: "STABLE_PASS", 2: "UNSTABLE_PASS", 1: "UNSTABLE_FAIL", 0: "STABLE_FAIL"}[pass_count]


def compare_holdout_transition(baseline_passes: int, candidate_passes: int) -> dict[str, Any]:
    before, after = holdout_state(baseline_passes), holdout_state(candidate_passes)
    if before in PASS_FAMILY and after in FAIL_FAMILY:
        classification = "FAIL"
    elif before in FAIL_FAMILY and after in PASS_FAMILY:
        classification = "IMPROVEMENT"
    elif before in PASS_FAMILY and after in PASS_FAMILY:
        classification = "REVIEW_REQUIRED" if before == "STABLE_PASS" and after == "UNSTABLE_PASS" else "IMPROVEMENT" if before == "UNSTABLE_PASS" and after == "STABLE_PASS" else "STABLE"
    else:
        classification = "REVIEW_REQUIRED" if before == "UNSTABLE_FAIL" and after == "STABLE_FAIL" else "IMPROVEMENT" if before == "STABLE_FAIL" and after == "UNSTABLE_FAIL" else "STABLE"
    return {"baseline_state": before, "candidate_state": after, "classification": classification}


def _metric(summary: dict[str, Any], names: tuple[str, ...]) -> float | None:
    """Read known aggregate shapes without guessing a missing value."""
    containers = []
    pending = [summary]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            containers.append(value)
            pending.extend(child for child in value.values() if isinstance(child, dict))
    for container in containers:
        if not isinstance(container, dict):
            continue
        for name in names:
            if name in container:
                try:
                    value = float(container[name])
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(value):
                    raise ValueError(f"Non-finite metric: {name}")
                return value
    return None


def _mean_dimension(summary: dict[str, Any], dimension: str) -> float | None:
    names = (dimension, dimension.lower(), dimension.upper())
    for key in ("mean_score_by_dimension", "dimension_scores", "metrics_by_split", "metrics_by_bucket"):
        value = summary.get(key)
        if isinstance(value, dict):
            if isinstance(value.get(dimension), (int, float)):
                return float(value[dimension])
            for child in value.values():
                if isinstance(child, dict):
                    for name in names:
                        if isinstance(child.get(name), (int, float)):
                            return float(child[name])
    return _metric(summary, names)


def _extract_run_metrics(layer: str, artifact: Any) -> dict[str, Any]:
    summary = artifact.summary
    if isinstance(summary.get("regression_metrics"), dict):
        return {"overall": {"overall": summary["regression_metrics"]}}
    if layer == "step73":
        aliases = {
            "semantic_recall20": ("semantic_recall20", "recall20"),
            "reranked_recall5": ("reranked_recall5", "recall5"),
            "reranked_precision5": ("reranked_precision5", "precision5"),
            "reranked_ndcg5": ("reranked_ndcg5", "ndcg5"),
        }
        result: dict[str, Any] = {}
        for group_name, field in (("by_split", "metrics_by_split"), ("by_bucket", "metrics_by_bucket")):
            groups = summary.get(field)
            if isinstance(groups, dict):
                result[group_name] = {str(group): {key: _metric(value, aliases[key]) for key in aliases} for group, value in groups.items() if isinstance(value, dict)}
        overall = summary.get("metrics_overall")
        if isinstance(overall, dict):
            result["overall"] = {"overall": {key: _metric(overall, names) for key, names in aliases.items()}}
        return result
    if layer == "step74":
        dims = ("answer_correctness", "faithfulness_groundedness", "completeness", "language_quality", "learning_usefulness")
        result = {"overall": {"overall": {"dimensions": {dimension: _mean_dimension(summary, dimension) for dimension in dims}}}}
        for group_name, field in (("by_split", "metrics_by_split"), ("by_bucket", "metrics_by_bucket")):
            groups = summary.get(field)
            if isinstance(groups, dict):
                result[group_name] = {str(group): {"dimensions": {dimension: _mean_dimension(value, dimension) for dimension in dims}} for group, value in groups.items() if isinstance(value, dict)}
        return result
    overall = {
        "pass_rate": _metric(summary, ("overall_e2e_hard_validity_pass_rate", "e2e_case_pass_rate", "pass_rate")),
        "technical_failure_rate": _metric(summary, ("technical_failure_rate",)),
        "latency_p95_ms": _metric(summary, ("p95",)),
    }
    result = {"overall": {"overall": overall}}
    buckets = summary.get("quality_rates_by_bucket")
    if isinstance(buckets, dict):
        result["by_bucket"] = {str(bucket): {"pass_rate": _metric(value, ("e2e_case_pass_rate", "pass_rate"))} for bucket, value in buckets.items() if isinstance(value, dict)}
    return result


def _case_rows(artifact: Any) -> dict[str, dict[str, Any]]:
    if artifact.layer != "step75":
        return {row["case_id"]: row for row in artifact.cases if isinstance(row.get("case_id"), str)}
    grouped: dict[str, dict[str, Any]] = {}
    for row in artifact.cases:
        case_id = row.get("case_id")
        if not isinstance(case_id, str):
            continue
        item = grouped.setdefault(case_id, {"case_id": case_id, "split": row.get("split"), "bucket": row.get("bucket"), "repeats": []})
        execution = dict(row)
        item["repeats"].append(execution)
    for item in grouped.values():
        item["repeats"].sort(key=lambda repeat: int(repeat.get("repeat_index", 1)))
        indexes = [repeat.get("repeat_index") for repeat in item["repeats"]]
        if len(indexes) != len(set(indexes)):
            raise ValueError(f"Duplicate Step-7.5 repeat identity for {item['case_id']}")
        passes = sum(repeat.get("e2e_case_pass") is True for repeat in item["repeats"])
        item["pass_count"] = passes
        item["execution_count"] = len(item["repeats"])
        if item["split"] == "HOLDOUT" and item["execution_count"] == 3:
            item["e2e_case_pass"] = passes >= 2
        elif item["execution_count"] == 1:
            item["e2e_case_pass"] = item["repeats"][0].get("e2e_case_pass")
    return grouped


def _repeat_passes(row: dict[str, Any]) -> int | None:
    repeats = row.get("repeats", row.get("attempts"))
    if isinstance(repeats, list):
        if len(repeats) != 3:
            return None
        indexes = [item.get("repeat_index") for item in repeats]
        if sorted(indexes) != [1, 2, 3]:
            return None
        count = 0
        for repeat in repeats:
            passed = repeat.get("e2e_case_pass", repeat.get("passed"))
            if not isinstance(passed, bool):
                return None
            count += int(passed)
        return count
    return None


def _critical_identities(artifact: Any, layer: str) -> set[tuple[str, str, str, int]]:
    found: set[tuple[str, str, str, int]] = set()
    for row in artifact.cases:
        case_id = row.get("case_id")
        if not case_id:
            continue
        failures = row.get("critical_failures", [])
        repeat_index = int(row.get("repeat_index", 1))
        if layer == "step73" and row.get("case_scope_violation"):
            found.add((layer, str(case_id), "CASE_SCOPE_VIOLATION", repeat_index))
        for failure in failures if isinstance(failures, list) else []:
            code = failure if isinstance(failure, str) else failure.get("code") if isinstance(failure, dict) else None
            if code:
                found.add((layer, str(case_id), str(code), repeat_index))
    return found


def compare(request: ComparisonRequest) -> dict[str, Any]:
    compatibility = check_compatibility(request)
    result: dict[str, Any] = {
        "comparison_id": request.comparison_id,
        "comparison_mode": request.comparison_mode,
        "policy_version": "lesson-chat-regression-policy/v1",
        "comparison_policy_version": "lesson-chat-regression-policy/v1",
        "baseline_run_id": request.baseline.run_id,
        "candidate_run_id": request.candidate.run_id,
        "compatibility": {"compatible": compatibility.compatible, "checks": list(compatibility.checks), "issues": list(compatibility.issues), "system_under_test_differences": compatibility.system_under_test_differences},
        "metrics": {}, "bucket_changes": [], "critical_failure_diff": {}, "case_transitions": [], "holdout_transitions": [],
        "issues": list(compatibility.issues), "status": "REVIEW_REQUIRED",
        "official_eligible": request.comparison_mode == "OFFICIAL" and compatibility.compatible,
    }
    for layer in LAYERS:
        before = _case_rows(request.baseline.layers[layer])
        after = _case_rows(request.candidate.layers[layer])
        for case_id in sorted(before.keys() & after.keys()):
            if before[case_id].get("bucket") != after[case_id].get("bucket"):
                result["bucket_changes"].append({"layer": layer, "case_id": case_id, "baseline_bucket": before[case_id].get("bucket"), "candidate_bucket": after[case_id].get("bucket")})
    if not compatibility.compatible:
        result["status"] = "FAIL" if any("superseded" in issue.lower() for issue in compatibility.issues) else "REVIEW_REQUIRED"
        result["retrieval_metric_deltas"] = {}
        result["retrieval_metric_classifications"] = {}
        result["generation_dimension_deltas"] = {}
        result["generation_dimension_classifications"] = {}
        result["e2e_pass_delta"] = None
        result["e2e_pass_classification"] = "REVIEW_REQUIRED"
        result["technical_failure_delta"] = None
        result["technical_failure_classification"] = "REVIEW_REQUIRED"
        result["latency_delta"] = None
        result["latency_classification"] = "REVIEW_REQUIRED"
        result["bucket_level_deltas"] = {}
        result["stability_deltas"] = []
        result["stability_gate_results"] = {}
        result["critical_failure_deltas"] = {"new": [], "resolved": [], "persisting": []}
        result.update({"fixed_case_count": 0, "regressed_case_count": 0,
                       "unchanged_pass_count": 0, "unchanged_fail_count": 0})
        result["gate_results"] = {"new_critical_failure": False, "numeric_regression": False,
                                   "holdout_pass_to_fail": False, "unresolved_review": True}
        result["overall_status"] = result["status"]
        return result

    numeric_regression = False
    missing = False
    for layer in LAYERS:
        left = _extract_run_metrics(layer, request.baseline.layers[layer])
        right = _extract_run_metrics(layer, request.candidate.layers[layer])
        metrics: dict[str, Any] = {"groups": {}}
        common_scopes = set(left) & set(right)
        if not common_scopes:
            missing = True
        for scope in sorted(common_scopes):
            left_groups, right_groups = left[scope], right[scope]
            if not isinstance(left_groups, dict) or not isinstance(right_groups, dict):
                missing = True
                continue
            common_groups = set(left_groups) & set(right_groups)
            if not common_groups:
                missing = True
                continue
            metrics["groups"][scope] = {}
            for group in sorted(common_groups):
                a_group, b_group = left_groups[group], right_groups[group]
                group_metrics: dict[str, Any] = {}
                if layer == "step73":
                    for name, threshold in THRESHOLDS["retrieval"].items():
                        a, b = a_group.get(name), b_group.get(name)
                        if a is None or b is None:
                            missing = True
                            group_metrics[name] = {"classification": "REVIEW_REQUIRED", "reason": "required metric missing"}
                        else:
                            group_metrics[name] = classify_delta(float(a), float(b), threshold, higher_is_better=True)
                            numeric_regression |= group_metrics[name]["classification"] == "REGRESSION"
                elif layer == "step74":
                    for dimension, threshold in THRESHOLDS["generation"].items():
                        a = a_group.get("dimensions", {}).get(dimension)
                        b = b_group.get("dimensions", {}).get(dimension)
                        if a is None or b is None:
                            missing = True
                            group_metrics[dimension] = {"classification": "REVIEW_REQUIRED", "reason": "required dimension missing"}
                        else:
                            group_metrics[dimension] = classify_delta(float(a), float(b), threshold, higher_is_better=True)
                            numeric_regression |= group_metrics[dimension]["classification"] == "REGRESSION"
                else:
                    check_names = [("pass_rate", THRESHOLDS["e2e"]["pass_rate"], True)]
                    if scope == "overall":
                        check_names += [("technical_failure_rate", THRESHOLDS["e2e"]["technical_failure_rate"], False)]
                    for name, threshold, high in check_names:
                        a, b = a_group.get(name), b_group.get(name)
                        if a is None or b is None:
                            missing = True
                            group_metrics[name] = {"classification": "REVIEW_REQUIRED", "reason": "required metric missing"}
                        else:
                            group_metrics[name] = classify_delta(float(a), float(b), threshold, higher_is_better=high)
                            numeric_regression |= group_metrics[name]["classification"] == "REGRESSION"
                    if scope == "overall":
                        a, b = a_group.get("latency_p95_ms"), b_group.get("latency_p95_ms")
                        if a is None or b is None:
                            missing = True
                            group_metrics["latency_p95"] = {"classification": "REVIEW_REQUIRED", "reason": "required p95 latency missing"}
                        else:
                            group_metrics["latency_p95"] = classify_latency(float(a), float(b), THRESHOLDS["e2e"]["latency_p95_relative_increase"])
                            numeric_regression |= group_metrics["latency_p95"]["classification"] == "REGRESSION"
                metrics["groups"][scope][group] = group_metrics
        result["metrics"][layer] = metrics

    before_critical = set().union(*(_critical_identities(request.baseline.layers[layer], layer) for layer in LAYERS))
    after_critical = set().union(*(_critical_identities(request.candidate.layers[layer], layer) for layer in LAYERS))
    result["critical_failure_diff"] = {
        "new": [dict(layer=x[0], case_id=x[1], code=x[2], repeat_index=x[3]) for x in sorted(after_critical - before_critical)],
        "resolved": [dict(layer=x[0], case_id=x[1], code=x[2], repeat_index=x[3]) for x in sorted(before_critical - after_critical)],
        "persisting": [dict(layer=x[0], case_id=x[1], code=x[2], repeat_index=x[3]) for x in sorted(before_critical & after_critical)],
    }
    transitions: list[dict[str, Any]] = []
    base_rows, cand_rows = _case_rows(request.baseline.layers["step75"]), _case_rows(request.candidate.layers["step75"])
    for case_id in sorted(base_rows.keys() & cand_rows.keys()):
        a, b = base_rows[case_id], cand_rows[case_id]
        before_pass = a.get("e2e_case_pass", a.get("passed"))
        after_pass = b.get("e2e_case_pass", b.get("passed"))
        if isinstance(before_pass, bool) and isinstance(after_pass, bool):
            transition = "FIXED_CASE" if not before_pass and after_pass else "REGRESSED_CASE" if before_pass and not after_pass else "UNCHANGED_PASS" if before_pass else "UNCHANGED_FAIL"
            result["case_transitions"].append({"case_id": case_id, "baseline_pass": before_pass, "candidate_pass": after_pass, "classification": transition})
        before_pass, after_pass = _repeat_passes(a), _repeat_passes(b)
        if before_pass is None or after_pass is None:
            continue
        transition = compare_holdout_transition(before_pass, after_pass)
        transitions.append({"case_id": case_id, "baseline_pass_count": before_pass,
                            "candidate_pass_count": after_pass,
                            "baseline_stability_state": transition["baseline_state"],
                            "candidate_stability_state": transition["candidate_state"],
                            "stability_change": f"{transition['baseline_state']}->{transition['candidate_state']}",
                            "stability_gate": transition["classification"], **transition})
    result["holdout_transitions"] = transitions
    fail_transition = any(item["classification"] == "FAIL" for item in transitions)
    review_transition = any(item["classification"] == "REVIEW_REQUIRED" for item in transitions)
    if result["critical_failure_diff"]["new"]:
        result["status"] = "FAIL"
    elif numeric_regression or fail_transition:
        result["status"] = "FAIL"
    elif missing or review_transition:
        result["status"] = "REVIEW_REQUIRED"
    else:
        result["status"] = "PASS"
    # Frozen consumer-facing summary names are emitted explicitly alongside helper data.
    result["retrieval_metric_deltas"] = _metric_projection(result["metrics"].get("step73", {}))
    result["retrieval_metric_classifications"] = _classification_projection(result["metrics"].get("step73", {}))
    result["generation_dimension_deltas"] = _metric_projection(result["metrics"].get("step74", {}))
    result["generation_dimension_classifications"] = _classification_projection(result["metrics"].get("step74", {}))
    e2e_overall = result["metrics"].get("step75", {}).get("groups", {}).get("overall", {}).get("overall", {})
    result["e2e_pass_delta"] = e2e_overall.get("pass_rate", {}).get("delta")
    result["e2e_pass_classification"] = e2e_overall.get("pass_rate", {}).get("classification", "REVIEW_REQUIRED")
    result["technical_failure_delta"] = e2e_overall.get("technical_failure_rate", {}).get("delta")
    result["technical_failure_classification"] = e2e_overall.get("technical_failure_rate", {}).get("classification", "REVIEW_REQUIRED")
    result["latency_delta"] = e2e_overall.get("latency_p95", {})
    result["latency_classification"] = e2e_overall.get("latency_p95", {}).get("classification", "REVIEW_REQUIRED")
    result["bucket_level_deltas"] = _bucket_delta_projection(result["metrics"])
    result["stability_deltas"] = result["holdout_transitions"]
    result["stability_gate_results"] = {row["case_id"]: row["stability_gate"] for row in result["holdout_transitions"]}
    result["critical_failure_deltas"] = result["critical_failure_diff"]
    counts = {name: 0 for name in ("fixed_case_count", "regressed_case_count", "unchanged_pass_count", "unchanged_fail_count")}
    for row in result["case_transitions"]:
        key = {"FIXED_CASE": "fixed_case_count", "REGRESSED_CASE": "regressed_case_count",
               "UNCHANGED_PASS": "unchanged_pass_count", "UNCHANGED_FAIL": "unchanged_fail_count"}.get(row["classification"])
        if key:
            counts[key] += 1
    result.update(counts)
    result["gate_results"] = {"new_critical_failure": bool(result["critical_failure_diff"].get("new")),
                              "numeric_regression": numeric_regression,
                              "holdout_pass_to_fail": fail_transition,
                              "unresolved_review": missing or review_transition}
    result["overall_status"] = result["status"]
    return result


def _metric_projection(metrics: dict[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for scope, groups in metrics.get("groups", {}).items():
        for group, values in groups.items():
            projected[f"{scope}:{group}"] = {name: value.get("delta") for name, value in values.items()}
    return projected


def _classification_projection(metrics: dict[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for scope, groups in metrics.get("groups", {}).items():
        for group, values in groups.items():
            projected[f"{scope}:{group}"] = {name: value.get("classification") for name, value in values.items()}
    return projected


def _bucket_delta_projection(metrics: dict[str, Any]) -> dict[str, Any]:
    output = {}
    for layer, values in metrics.items():
        bucket_groups = values.get("groups", {}).get("by_bucket", {})
        if bucket_groups:
            output[layer] = bucket_groups
    return output
