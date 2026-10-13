from __future__ import annotations

import math
from typing import Any

from .contracts import CompatibilityResult, LAYERS, ComparisonRequest


THRESHOLDS = {
    "retrieval": {"semantic_recall20": 0.02, "reranked_recall5": 0.02, "reranked_precision5": 0.02, "reranked_ndcg5": 0.02},
    "generation": {"answer_correctness": 0.10, "faithfulness_groundedness": 0.10, "completeness": 0.10, "language_quality": 0.10, "learning_usefulness": 0.10},
    "e2e": {"pass_rate": 0.02, "technical_failure_rate": 0.01, "latency_p95_relative_increase": 0.20},
}

# Only compare persisted producer identities, and derive case/split/repeat identities
# from cases.jsonl. Step-7.6-only hashes/policy fields are intentionally not required.
SUT_FIELDS = (
    "code_commit", "embedding_profile", "embedding_model", "embedding_model_version",
    "chunking_version", "chunking_config", "candidate_k", "reranker_model",
    "reranker_model_version", "reranker_config", "retrieval_filter_config",
    "retrieval_scope_policy_version", "RAG_EVIDENCE_CALIBRATION_MODE",
    "runtime_RAG_MIN_RERANK_SCORE_before_run", "rag_min_rerank_score",
    "generator_identity", "generator_provider", "generator_model",
    "generator_prompt_version_or_hash", "judge_identity", "judge_model",
    "prompt_system_identity", "prompt_system_sha256", "llm_generation_config",
)

IDENTITY_FIELDS = {
    "step73": ("dataset_version", "dataset_schema_version"),
    "step74": ("dataset_name", "dataset_version", "dataset_schema_version",
               "eligible_case_policy_version", "fixed_evidence_policy_version",
               "fixed_memory_policy_version", "rubric_version", "judge_prompt_version",
               "human_annotation_version", "technical_failure_policy_version", "judge_identity"),
    "step75": ("dataset_name", "dataset_version", "dataset_schema_version",
               "execution_plan_version", "retrieval_scope_policy_version",
               "e2e_policy_version", "critical_failure_policy_version",
               "human_annotation_version", "judge_prompt_version", "judge_schema_version",
               "e2e_rubric_version", "judge_model", "judge_reasoning_effort",
               "judge_temperature", "judge_max_output_tokens"),
}


def _execution_identity(artifact: Any) -> tuple[dict[str, tuple[str, str, int]], dict[str, tuple[str, str]]]:
    """Return identity→(bucket, split, repeat) and case→(bucket, split)."""
    identities: dict[str, tuple[str, str, int]] = {}
    cases: dict[str, tuple[str, str]] = {}
    for row in artifact.cases:
        case_id = row.get("case_id")
        split = row.get("split")
        bucket = row.get("bucket")
        if not all(isinstance(value, str) and value for value in (case_id, split, bucket)):
            return {}, {}
        prior = cases.setdefault(case_id, (bucket, split))
        if prior != (bucket, split):
            return {}, {}
        repeat_index = 1
        if artifact.layer == "step75":
            repeat_index = row.get("repeat_index")
            if type(repeat_index) is not int or repeat_index < 1:
                return {}, {}
        elif "repeat_index" in row:
            return {}, {}
        identity = f"{case_id}#{repeat_index}" if artifact.layer == "step75" else case_id
        if identity in identities:
            return {}, {}
        identities[identity] = (bucket, split, repeat_index)
    if not identities:
        return {}, {}
    if artifact.layer == "step75":
        repeats: dict[str, list[int]] = {}
        for case_id, (_, split, repeat) in ((key.split("#", 1)[0], value) for key, value in identities.items()):
            repeats.setdefault(case_id, []).append(repeat)
        for case_id, indexes in repeats.items():
            split = cases[case_id][1]
            expected = [1, 2, 3] if split == "HOLDOUT" else [1]
            if sorted(indexes) != expected:
                return {}, {}
    return identities, cases


def _official_layer_eligible(layer: str, artifact: Any) -> bool:
    manifest = artifact.manifest
    if layer == "step73":
        # Step 7.3 has no producer-owned official eligibility assertion today.
        return False
    if layer == "step74":
        return (
            manifest.get("execution_mode") == "OFFICIAL_REAL_RUNTIME"
            and manifest.get("run_status") == "STAGE_B_COMPLETE"
            and manifest.get("human_approved_count") == 30
            and isinstance(manifest.get("runtime_api_calls"), int)
            and manifest["runtime_api_calls"] > 0
            and isinstance(manifest.get("judge_calibration_success_count"), int)
            and manifest["judge_calibration_success_count"] > 0
        )
    return (
        manifest.get("execution_mode") == "OFFICIAL_REAL_RUNTIME"
        and manifest.get("official_baseline_eligible") is True
        and manifest.get("official_run_executed") is True
        and manifest.get("run_status") not in {"OFFLINE_TEST_ONLY", "OFFLINE_TEST"}
        and type(manifest.get("human_approved_count")) is int
        and manifest["human_approved_count"] > 0
    )


def _canonical(value: Any) -> str:
    import json
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _cases_identity(artifact: Any) -> tuple[dict[str, str], dict[str, str]]:
    ids: dict[str, str] = {}
    splits: dict[str, str] = {}
    for row in artifact.cases:
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            return {}, {}
        if artifact.layer == "step75":
            repeat_index = row.get("repeat_index", 1)
            identity = f"{case_id}#{repeat_index}"
        else:
            identity = case_id
            if identity in ids:
                return {}, {}
        bucket = str(row.get("bucket", ""))
        split = str(row.get("split", ""))
        if case_id in splits and splits[case_id] != split:
            return {}, {}
        ids[identity] = bucket
        splits[identity] = split
    return ids, splits


def check_compatibility(request: ComparisonRequest) -> CompatibilityResult:
    issues: list[str] = []
    checks: list[dict[str, Any]] = []
    sut_changes: dict[str, dict[str, Any]] = {}
    if not request.comparison_id.strip() or not request.baseline.run_id.strip() or not request.candidate.run_id.strip():
        issues.append("Explicit comparison and side identities are required")
    if request.comparison_mode not in ("TEST_ONLY", "OFFICIAL"):
        issues.append("Comparison mode must be TEST_ONLY or OFFICIAL")
    if request.baseline.run_id.strip().lower() == "latest" or request.candidate.run_id.strip().lower() == "latest":
        issues.append("The 'latest' selector is not an explicit baseline or candidate identity")
    if request.baseline.run_id == request.candidate.run_id:
        issues.append("Baseline and candidate system identities must differ")
    for layer in LAYERS:
        before = request.baseline.layers.get(layer)
        after = request.candidate.layers.get(layer)
        if before is None or after is None:
            issues.append(f"Missing explicit {layer} baseline/candidate artifact")
            continue
        if before.layer != layer or after.layer != layer:
            issues.append(f"Artifact layer identity does not match requested {layer}")
        if before.run_id.strip().lower() == "latest" or after.run_id.strip().lower() == "latest":
            issues.append(f"{layer} run identity may not use the 'latest' selector")
        if before.run_id == after.run_id:
            issues.append(f"{layer} baseline and candidate run identities must differ")
        if before.superseded or after.superseded:
            issues.append(f"{layer} artifact is marked superseded")
        for field in IDENTITY_FIELDS[layer]:
            left, right = before.manifest.get(field), after.manifest.get(field)
            ok = left is not None and right is not None and _canonical(left) == _canonical(right)
            checks.append({"layer": layer, "field": field, "compatible": ok})
            if not ok:
                issues.append(f"{layer} compatibility field missing or different: {field}")
        left_ids, left_cases = _execution_identity(before)
        right_ids, right_cases = _execution_identity(after)
        same_ids = bool(left_ids) and set(left_ids) == set(right_ids)
        same_splits = bool(left_cases) and {key: value[1] for key, value in left_cases.items()} == {key: value[1] for key, value in right_cases.items()}
        checks.extend(({"layer": layer, "field": "case_set", "compatible": same_ids}, {"layer": layer, "field": "split_assignment", "compatible": same_splits}))
        if not same_ids:
            issues.append(f"{layer} case set is missing, duplicated, or different")
        if not same_splits:
            issues.append(f"{layer} split assignments are missing or different")
        checks.append({"layer": layer, "field": "repeat_identity", "compatible": bool(left_ids) and bool(right_ids) and set(left_ids) == set(right_ids)})
        diff: dict[str, Any] = {}
        for field in SUT_FIELDS:
            left, right = before.manifest.get(field), after.manifest.get(field)
            if left != right:
                diff[field] = {"baseline": left, "candidate": right}
        sut_changes[layer] = diff
    for side_name, side in (("baseline", request.baseline), ("candidate", request.candidate)):
        versions = {artifact.manifest.get("dataset_version") for artifact in side.layers.values()}
        schemas = {artifact.manifest.get("dataset_schema_version") for artifact in side.layers.values()}
        if len(versions) != 1 or None in versions:
            issues.append(f"{side_name} layers do not share one persisted dataset version")
        if len(schemas) != 1 or None in schemas:
            issues.append(f"{side_name} layers do not share one persisted dataset schema version")
    eligible = request.comparison_mode == "OFFICIAL"
    if eligible:
        if request.baseline.approved_baseline_run_id != request.baseline.run_id:
            issues.append("OFFICIAL comparison requires the explicitly approved baseline identity")
        for side_name, side in (("baseline", request.baseline), ("candidate", request.candidate)):
            for layer in LAYERS:
                artifact = side.layers[layer]
                if not _official_layer_eligible(layer, artifact):
                    issues.append(f"{layer} {side_name} official eligibility is not proven by its producer contract")
    return CompatibilityResult(not issues, tuple(checks), tuple(dict.fromkeys(issues)), sut_changes)


def classify_delta(baseline: float, candidate: float, threshold: float, *, higher_is_better: bool) -> dict[str, Any]:
    values = (baseline, candidate, threshold)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("Non-finite metrics or threshold are not permitted")
    delta = candidate - baseline
    degradation = -delta if higher_is_better else delta
    if degradation > threshold and not math.isclose(degradation, threshold, rel_tol=1e-12, abs_tol=1e-12):
        state = "REGRESSION"
    elif degradation < -threshold and not math.isclose(degradation, -threshold, rel_tol=1e-12, abs_tol=1e-12):
        state = "IMPROVEMENT"
    else:
        state = "STABLE"
    return {"baseline": baseline, "candidate": candidate, "delta": delta, "threshold": threshold, "direction": "higher_is_better" if higher_is_better else "lower_is_better", "classification": state}


def classify_latency(baseline_p95: float, candidate_p95: float, relative_threshold: float = 0.20) -> dict[str, Any]:
    if not math.isfinite(float(baseline_p95)) or baseline_p95 <= 0 or not math.isfinite(float(candidate_p95)) or candidate_p95 < 0:
        raise ValueError("p95 latency must be finite; baseline must be greater than zero")
    relative = (candidate_p95 - baseline_p95) / baseline_p95
    state = "REGRESSION" if relative > relative_threshold else "IMPROVEMENT" if relative < -relative_threshold else "STABLE"
    return {"baseline_ms": baseline_p95, "candidate_ms": candidate_p95, "relative_delta": relative, "threshold": relative_threshold, "classification": state}
