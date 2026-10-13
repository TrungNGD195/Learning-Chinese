from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from app.evaluation.step76.artifacts import write_comparison_artifacts
from app.evaluation.step76.compare import compare, compare_holdout_transition, holdout_state
from app.evaluation.step76.contracts import ComparisonRequest
from app.evaluation.step76.loader import explicit_side, load_layer_artifact
from app.evaluation.step76.policy import _official_layer_eligible, check_compatibility, classify_delta, classify_latency
from app.evaluation.step76.sample import generate_sample


def _temp_path() -> Path:
    path = Path(__file__).parent / ".step76-test-work" / uuid4().hex
    path.mkdir(parents=True)
    return path


def _request(tmp_path: Path) -> ComparisonRequest:
    generate_sample(tmp_path)
    root = tmp_path / "evaluation" / "fixtures" / "step76" / "v1"
    baseline = explicit_side("baseline", {layer: root / "baseline" / layer for layer in ("step73", "step74", "step75")})
    candidate = explicit_side("candidate", {layer: root / "candidate" / layer for layer in ("step73", "step74", "step75")})
    return ComparisonRequest("test", baseline, candidate, "TEST_ONLY", "2026-10-12T00:00:00Z")


def test_explicit_loader_never_selects_latest_and_checks_hash():
    tmp_path = _temp_path()
    generate_sample(tmp_path)
    run = tmp_path / "evaluation/fixtures/step76/v1/baseline/step73"
    assert load_layer_artifact("step73", run).run_id.endswith("step73-v1")
    with pytest.raises(ValueError, match="Explicit run directory"):
        load_layer_artifact("step73", "latest")
    before = load_layer_artifact("step73", run).source_hashes["cases.jsonl"]
    (run / "cases.jsonl").write_text("{}\n", encoding="utf-8")
    after = load_layer_artifact("step73", run).source_hashes["cases.jsonl"]
    assert before != after


def test_fixture_is_test_only_and_cannot_claim_official():
    tmp_path = _temp_path()
    request = _request(tmp_path)
    result = compare(request)
    assert result["status"] == "PASS"
    assert result["official_eligible"] is False
    with pytest.raises(ValueError, match="latest"):
        explicit_side("latest", {layer: "latest" for layer in ("step73", "step74", "step75")})
    official = replace(request, comparison_mode="OFFICIAL")
    assert compare(official)["status"] == "REVIEW_REQUIRED"
    assert compare(official)["official_eligible"] is False


def test_producer_shaped_fixtures_need_no_step76_only_manifest_fields():
    request = _request(_temp_path())
    for side in (request.baseline, request.candidate):
        for artifact in side.layers.values():
            for forbidden in ("case_set_sha256", "split_assignment_sha256", "metric_definition_id",
                              "metric_policy_version", "critical_failure_semantics_version",
                              "judge_policy_version", "evaluator_policy_version",
                              "holdout_repeat_policy_version", "holdout_repeat_structure"):
                assert forbidden not in artifact.manifest
    assert check_compatibility(request).compatible
    step74_checks = {check["field"]: check["compatible"] for check in check_compatibility(request).checks
                     if check["layer"] == "step74"}
    for field in ("rubric_version", "judge_prompt_version", "human_annotation_version", "judge_identity"):
        assert step74_checks[field] is True


def test_actual_step73_artifact_loads_from_current_producer_contract():
    project_root = Path(__file__).resolve().parents[2]
    run = project_root / "evaluation" / "runs" / "step73-20261008T035722Z-221c5b07"
    artifact = load_layer_artifact("step73", run)
    assert artifact.manifest["dataset_version"] == "v0.8.0"
    assert artifact.manifest["dataset_schema_version"] == "1.0.0"
    assert artifact.cases
    assert all("case_id" in row and "split" in row for row in artifact.cases)


@pytest.mark.parametrize("layer,field,value", [
    ("step73", "dataset_version", "different"),
    ("step74", "dataset_schema_version", "different"),
])
def test_real_identity_mismatch_fails_compatibility(layer, field, value):
    request = _request(_temp_path())
    artifact = request.candidate.layers[layer]
    changed = replace(artifact, manifest={**artifact.manifest, field: value})
    candidate = replace(request.candidate, layers={**request.candidate.layers, layer: changed})
    assert not check_compatibility(replace(request, candidate=candidate)).compatible


def test_derived_case_set_and_split_mismatch_fail_compatibility():
    request = _request(_temp_path())
    artifact = request.candidate.layers["step73"]
    changed_case = replace(artifact, cases=artifact.cases[:-1])
    side = replace(request.candidate, layers={**request.candidate.layers, "step73": changed_case})
    assert not check_compatibility(replace(request, candidate=side)).compatible
    changed_split = replace(artifact, cases=(dict(artifact.cases[0], split="HOLDOUT"), *artifact.cases[1:]))
    side = replace(request.candidate, layers={**request.candidate.layers, "step73": changed_split})
    assert not check_compatibility(replace(request, candidate=side)).compatible


def test_step75_duplicate_or_missing_repeat_identity_is_incompatible():
    request = _request(_temp_path())
    artifact = request.candidate.layers["step75"]
    bad = replace(artifact, cases=(*artifact.cases[:-1], dict(artifact.cases[-1], repeat_index=2)))
    side = replace(request.candidate, layers={**request.candidate.layers, "step75": bad})
    assert not check_compatibility(replace(request, candidate=side)).compatible


def test_official_eligibility_uses_each_producer_contract():
    request = _request(_temp_path())
    assert _official_layer_eligible("step74", request.baseline.layers["step74"]) is False  # offline fixture
    assert _official_layer_eligible("step75", request.baseline.layers["step75"]) is False
    artifact = request.baseline.layers["step74"]
    official_manifest = {**artifact.manifest, "execution_mode": "OFFICIAL_REAL_RUNTIME",
                         "run_status": "STAGE_B_COMPLETE", "human_approved_count": 30,
                         "runtime_api_calls": 100, "judge_calibration_success_count": 30}
    assert _official_layer_eligible("step74", replace(artifact, manifest=official_manifest)) is True
    assert _official_layer_eligible("step73", request.baseline.layers["step73"]) is False
    e2e = request.baseline.layers["step75"]
    official_e2e_manifest = {**e2e.manifest, "execution_mode": "OFFICIAL_REAL_RUNTIME",
                             "official_baseline_eligible": True, "official_run_executed": True,
                             "run_status": "COMPLETE", "human_approved_count": 30}
    assert _official_layer_eligible("step75", replace(e2e, manifest=official_e2e_manifest)) is True


def test_step75_row_per_repeat_preserved_in_case_output_and_repeat_critical_diff():
    request = _request(_temp_path())
    base = request.baseline.layers["step75"]
    candidate = request.candidate.layers["step75"]
    base_rows = tuple(dict(row, critical_failures=(
        ["REPEAT_ONE_RETAINED"] if row.get("repeat_index") == 1 else
        ["BASE_REPEAT_TWO"] if row.get("repeat_index") == 2 else []))
        for row in base.cases)
    cand_rows = tuple(dict(row, critical_failures=(
        ["REPEAT_ONE_RETAINED"] if row.get("repeat_index") == 1 else
        ["CAND_REPEAT_THREE"] if row.get("repeat_index") == 3 else []))
        for row in candidate.cases)
    baseline = replace(base, cases=base_rows)
    candidate = replace(candidate, cases=cand_rows)
    request = replace(request,
        baseline=replace(request.baseline, layers={**request.baseline.layers, "step75": baseline}),
        candidate=replace(request.candidate, layers={**request.candidate.layers, "step75": candidate}))
    result = write_comparison_artifacts(request, _temp_path())
    root = Path(result["directory"])
    rows = [json.loads(line) for line in (root / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    holdout = next(row for row in rows if row["case_id"] == "fixture-holdout-01")
    assert [row["repeat_index"] for row in holdout["baseline_executions"]] == [1, 2, 3]
    assert all("trace" in row and "technical_ok" in row for row in holdout["baseline_executions"])
    assert holdout["baseline_critical_failures"] == [
        {"layer": "step75", "repeat_index": 1, "code": "REPEAT_ONE_RETAINED"},
        {"layer": "step75", "repeat_index": 2, "code": "BASE_REPEAT_TWO"},
    ]
    assert holdout["new_critical_failures"] == [{"layer": "step75", "repeat_index": 3, "code": "CAND_REPEAT_THREE"}]
    assert holdout["resolved_critical_failures"] == [{"layer": "step75", "repeat_index": 2, "code": "BASE_REPEAT_TWO"}]
    assert {item["code"] for item in result["summary"]["critical_failure_diff"]["persisting"]} == {"REPEAT_ONE_RETAINED"}
    assert result["status"] == "FAIL"


@pytest.mark.parametrize("passes,state", [(3,"STABLE_PASS"),(2,"UNSTABLE_PASS"),(1,"UNSTABLE_FAIL"),(0,"STABLE_FAIL")])
def test_d110_derives_states_from_actual_step75_execution_rows(passes, state):
    request = _request(_temp_path())
    artifact = request.candidate.layers["step75"]
    rows = (artifact.cases[0],) + tuple(dict(row, e2e_case_pass=index <= passes)
                                        for index, row in enumerate(artifact.cases[1:], 1))
    changed = replace(artifact, cases=rows)
    result = compare(replace(request, candidate=replace(request.candidate,
        layers={**request.candidate.layers, "step75": changed})))
    transition = result["holdout_transitions"][0]
    assert transition["candidate_stability_state"] == state


def test_regression_artifact_manifest_and_summary_contracts():
    request = _request(_temp_path())
    result = write_comparison_artifacts(request, _temp_path())
    root = Path(result["directory"])
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    assert manifest["comparison_policy_version"] == "lesson-chat-regression-policy/v1"
    assert manifest["timestamp"] and manifest["dataset_version"] == "v0.8.0"
    assert manifest["official_comparison_eligible"] is False
    assert manifest["retrieval_baseline_run_id"] and manifest["generation_candidate_run_id"] and manifest["e2e_candidate_run_id"]
    for key in ("retrieval_metric_deltas", "retrieval_metric_classifications", "generation_dimension_deltas",
                "generation_dimension_classifications", "e2e_pass_delta", "technical_failure_delta",
                "latency_delta", "bucket_level_deltas", "stability_deltas", "stability_gate_results",
                "critical_failure_deltas", "fixed_case_count", "regressed_case_count", "unchanged_pass_count",
                "unchanged_fail_count", "gate_results", "overall_status"):
        assert key in summary


def test_compatibility_fails_closed_before_metrics():
    tmp_path = _temp_path()
    request = _request(tmp_path)
    artifact = request.candidate.layers["step73"]
    manifest = {**artifact.manifest, "dataset_version": "different"}
    changed = replace(artifact, manifest=manifest)
    candidate = replace(request.candidate, layers={**request.candidate.layers, "step73": changed})
    result = compare(replace(request, candidate=candidate))
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["metrics"] == {}
    assert any("dataset_version" in issue for issue in result["compatibility"]["issues"])


@pytest.mark.parametrize("baseline,candidate,threshold,high,expected", [
    (0.8, 0.77, 0.02, True, "REGRESSION"),
    (0.8, 0.79, 0.02, True, "STABLE"),
    (0.8, 0.82, 0.02, True, "STABLE"),
    (0.8, 0.83, 0.02, True, "IMPROVEMENT"),
    (0.02, 0.04, 0.01, False, "REGRESSION"),
    (0.02, 0.01, 0.01, False, "STABLE"),
])
def test_metric_directionality_and_exact_boundaries(baseline, candidate, threshold, high, expected):
    assert classify_delta(baseline, candidate, threshold, higher_is_better=high)["classification"] == expected


def test_all_four_retrieval_metrics_and_five_generation_dimensions_are_compared():
    tmp_path = _temp_path()
    result = compare(_request(tmp_path))
    retrieval = result["metrics"]["step73"]["groups"]["overall"]["overall"]
    generation = result["metrics"]["step74"]["groups"]["overall"]["overall"]
    assert set(retrieval) == {"semantic_recall20", "reranked_recall5", "reranked_precision5", "reranked_ndcg5"}
    assert set(generation) == {"answer_correctness", "faithfulness_groundedness", "completeness", "language_quality", "learning_usefulness"}
    assert all(item["classification"] == "STABLE" for item in retrieval.values())


def test_numeric_regression_causes_fail_and_group_changes_are_reported():
    tmp_path = _temp_path()
    request = _request(tmp_path)
    artifact = request.candidate.layers["step73"]
    summary = {**artifact.summary, "regression_metrics": {"semantic_recall20": 0.70, "reranked_recall5": .81, "reranked_precision5": .71, "reranked_ndcg5": .76}}
    changed = replace(artifact, summary=summary)
    result = compare(replace(request, candidate=replace(request.candidate, layers={**request.candidate.layers, "step73": changed})))
    assert result["status"] == "FAIL"
    assert result["metrics"]["step73"]["groups"]["overall"]["overall"]["semantic_recall20"]["classification"] == "REGRESSION"


def test_new_critical_failure_overrides_unresolved_metric_review():
    request = _request(_temp_path())
    artifact = request.candidate.layers["step74"]
    summary = {**artifact.summary, "mean_score_by_dimension": None}
    rows = (dict(artifact.cases[0], critical_failures=["SERIOUS_FACTUAL_ERROR"]), artifact.cases[1])
    changed = replace(artifact, summary=summary, cases=rows)
    result = compare(replace(request, candidate=replace(request.candidate, layers={**request.candidate.layers, "step74": changed})))
    assert result["status"] == "FAIL"


@pytest.mark.parametrize("candidate_passes,expected", [(2,"REVIEW_REQUIRED"),(1,"FAIL")])
def test_holdout_transition_controls_overall_gate(candidate_passes, expected):
    request = _request(_temp_path())
    artifact = request.candidate.layers["step75"]
    rows = (artifact.cases[0],) + tuple(dict(row, e2e_case_pass=index <= candidate_passes)
        for index, row in enumerate(artifact.cases[1:], 1))
    changed = replace(artifact, cases=rows)
    result = compare(replace(request, candidate=replace(request.candidate, layers={**request.candidate.layers, "step75": changed})))
    assert result["status"] == expected


def test_bucket_change_is_reported_without_collapsing_valid_case_identity():
    request = _request(_temp_path())
    artifact = request.candidate.layers["step73"]
    rows = (dict(artifact.cases[0], bucket="NO_EVIDENCE_REFUSAL"), artifact.cases[1])
    changed = replace(artifact, cases=rows)
    result = compare(replace(request, candidate=replace(request.candidate, layers={**request.candidate.layers, "step73": changed})))
    assert result["status"] == "PASS"
    assert result["bucket_changes"] == [{"layer": "step73", "case_id": "fixture-dev-01", "baseline_bucket": "CURRENT_LESSON_ANSWERABLE", "candidate_bucket": "NO_EVIDENCE_REFUSAL"}]


def test_non_finite_metrics_and_invalid_latency_rejected():
    with pytest.raises(ValueError, match="Non-finite"):
        classify_delta(math.nan, 1.0, 0.02, higher_is_better=True)
    with pytest.raises(ValueError, match="finite"):
        classify_latency(0, 10)
    with pytest.raises(ValueError, match="finite"):
        classify_latency(100, math.inf)
    assert classify_latency(100, 120)["classification"] == "STABLE"
    assert classify_latency(100, 121)["classification"] == "REGRESSION"
    assert classify_latency(100, 79)["classification"] == "IMPROVEMENT"


@pytest.mark.parametrize("count,state", [(3,"STABLE_PASS"),(2,"UNSTABLE_PASS"),(1,"UNSTABLE_FAIL"),(0,"STABLE_FAIL")])
def test_d110_repeat_state_mapping(count, state):
    assert holdout_state(count) == state


@pytest.mark.parametrize("baseline,candidate,expected", [
    (3, 2, "REVIEW_REQUIRED"), (1, 0, "REVIEW_REQUIRED"),
    (2, 3, "IMPROVEMENT"), (0, 1, "IMPROVEMENT"),
    (3, 1, "FAIL"), (2, 0, "FAIL"), (3, 3, "STABLE"), (0, 0, "STABLE"),
])
def test_d110_frozen_transitions(baseline, candidate, expected):
    assert compare_holdout_transition(baseline, candidate)["classification"] == expected


def test_new_critical_failure_hard_fails_even_if_metrics_improve():
    tmp_path = _temp_path()
    request = _request(tmp_path)
    artifact = request.candidate.layers["step74"]
    rows = (dict(artifact.cases[0], critical_failures=["SERIOUS_FACTUAL_ERROR"]), artifact.cases[1])
    changed = replace(artifact, cases=rows)
    result = compare(replace(request, candidate=replace(request.candidate, layers={**request.candidate.layers, "step74": changed})))
    assert result["status"] == "FAIL"
    assert result["critical_failure_diff"]["new"] == [{"layer": "step74", "case_id": "fixture-dev-01", "code": "SERIOUS_FACTUAL_ERROR", "repeat_index": 1}]


@pytest.mark.parametrize("before,after,expected", [(False,True,"FIXED"),(True,False,"REGRESSED"),(True,True,"UNCHANGED_PASS"),(False,False,"UNCHANGED_FAIL")])
def test_per_case_transitions(before, after, expected):
    request = _request(_temp_path())
    artifact = request.candidate.layers["step75"]
    first = dict(artifact.cases[0], e2e_case_pass=after)
    changed = replace(artifact, cases=(first, *artifact.cases[1:]))
    # The compatibility side is left intact; exercise the exported transition through compare on a DEV row.
    base_artifact = request.baseline.layers["step75"]
    base_row = dict(base_artifact.cases[0], e2e_case_pass=before)
    base_changed = replace(base_artifact, cases=(base_row, *base_artifact.cases[1:]))
    modified = replace(request, baseline=replace(request.baseline, layers={**request.baseline.layers, "step75": base_changed}), candidate=replace(request.candidate, layers={**request.candidate.layers, "step75": changed}))
    result = compare(modified)
    normalized = {"FIXED": "FIXED_CASE", "REGRESSED": "REGRESSED_CASE"}.get(expected, expected)
    assert result["case_transitions"][0]["classification"] == normalized


def test_artifact_is_deterministic_and_self_hashing():
    tmp_path = _temp_path()
    request = _request(tmp_path)
    first = write_comparison_artifacts(request, tmp_path / "one")
    second = write_comparison_artifacts(request, tmp_path / "two")
    assert first["files"] == second["files"]
    root = Path(first["directory"])
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"]["summary.json"] == first["files"]["summary.json"]
    assert manifest["official_comparison_eligible"] is False
    assert manifest["step77_included"] is False
    assert {"manifest.json", "summary.json", "cases.jsonl", "report.md"} == {p.name for p in root.iterdir()}
