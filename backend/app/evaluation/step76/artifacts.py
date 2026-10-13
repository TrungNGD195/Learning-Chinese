from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .compare import _case_rows, compare
from .contracts import ComparisonRequest, LAYERS
from .policy import IDENTITY_FIELDS, SUT_FIELDS


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _canonical_jsonl(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _codes(row: dict[str, Any]) -> list[str]:
    failures = row.get("critical_failures", [])
    result = []
    for failure in failures if isinstance(failures, list) else []:
        code = failure if isinstance(failure, str) else failure.get("code") if isinstance(failure, dict) else None
        if code:
            result.append(str(code))
    return sorted(result)


def _case_critical(artifacts: dict[str, Any]) -> set[tuple[str, str, int, str]]:
    found = {(layer, str(row.get("case_id")), int(row.get("repeat_index", 1)), code)
             for layer, artifact in artifacts.items() for row in artifact.cases for code in _codes(row)}
    found.update(("step73", str(row["case_id"]), 1, "CASE_SCOPE_VIOLATION")
                 for row in artifacts["step73"].cases
                 if row.get("case_scope_violation") is True and row.get("case_id"))
    return found


def _layer_identities(request: ComparisonRequest, side_name: str) -> dict[str, Any]:
    side = getattr(request, side_name)
    identities = {}
    for layer, artifact in side.layers.items():
        manifest = artifact.manifest
        selected = set(IDENTITY_FIELDS[layer]) | {key for key in SUT_FIELDS if key in manifest}
        identities[layer] = {
            "run_id": artifact.run_id, "evaluation_step": manifest.get("evaluation_step"),
            "dataset_version": manifest.get("dataset_version"),
            "dataset_schema_version": manifest.get("dataset_schema_version"),
            "producer_identities": {key: manifest[key] for key in sorted(selected) if key in manifest},
            "directory": str(artifact.directory), "source_hashes": artifact.source_hashes,
        }
    return identities


def _case_artifact_rows(request: ComparisonRequest, result: dict[str, Any]) -> list[dict[str, Any]]:
    base_artifact = request.baseline.layers["step75"]
    cand_artifact = request.candidate.layers["step75"]
    before = _case_rows(base_artifact)
    after = _case_rows(cand_artifact)
    case_transitions = {item["case_id"]: item for item in result["case_transitions"]}
    stability = {item["case_id"]: item for item in result["holdout_transitions"]}
    baseline_critical = _case_critical(request.baseline.layers)
    candidate_critical = _case_critical(request.candidate.layers)
    all_case_ids = set(before) | set(after)
    all_case_ids.update(identity[1] for identity in baseline_critical | candidate_critical)
    output = []
    for case_id in sorted(all_case_ids):
        a, b = before.get(case_id), after.get(case_id)
        a_codes = {(layer, repeat, code) for layer, found_case, repeat, code in baseline_critical if found_case == case_id}
        b_codes = {(layer, repeat, code) for layer, found_case, repeat, code in candidate_critical if found_case == case_id}
        transition = case_transitions.get(case_id)
        stable = stability.get(case_id)
        row: dict[str, Any] = {
            "case_id": case_id,
            "split": (a or b or {}).get("split"),
            "bucket": (a or b or {}).get("bucket"),
            "baseline_result": None if a is None else a.get("e2e_case_pass"),
            "candidate_result": None if b is None else b.get("e2e_case_pass"),
            "transition": transition.get("classification") if transition else stable.get("stability_gate") if stable else "UNCHANGED",
            "baseline_critical_failures": [{"layer": layer, "repeat_index": repeat, "code": code} for layer, repeat, code in sorted(a_codes)],
            "candidate_critical_failures": [{"layer": layer, "repeat_index": repeat, "code": code} for layer, repeat, code in sorted(b_codes)],
            "new_critical_failures": [{"layer": layer, "repeat_index": repeat, "code": code} for layer, repeat, code in sorted(b_codes - a_codes)],
            "resolved_critical_failures": [{"layer": layer, "repeat_index": repeat, "code": code} for layer, repeat, code in sorted(a_codes - b_codes)],
            "baseline_executions": [] if a is None else a["repeats"],
            "candidate_executions": [] if b is None else b["repeats"],
        }
        if stable:
            row.update({key: stable[key] for key in ("baseline_stability_state", "candidate_stability_state", "stability_change", "stability_gate")})
        output.append(row)
    return output


def write_comparison_artifacts(request: ComparisonRequest, output_root: str | Path) -> dict[str, Any]:
    """Write the stable Step-7.6 manifest/summary/case contract."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", request.comparison_id) or request.comparison_id in (".", ".."):
        raise ValueError("comparison_id must be a simple portable path component")
    root = Path(output_root) / request.comparison_id
    root.mkdir(parents=True, exist_ok=True)
    result = compare(request)
    case_rows = _case_artifact_rows(request, result)
    cases_bytes = b"".join(_canonical_jsonl(row) for row in case_rows)
    summary_bytes = _canonical_json(result)
    report = [
        f"# Regression comparison: {request.comparison_id}", "",
        f"- Status: **{result['status']}**", f"- Mode: `{request.comparison_mode}`",
        "- Policy: `lesson-chat-regression-policy/v1`",
        f"- Baseline: `{request.baseline.run_id}`", f"- Candidate: `{request.candidate.run_id}`", "",
        "## Compatibility", "", *[f"- {issue}" for issue in result["compatibility"]["issues"]],
        "" if result["compatibility"]["issues"] else "- Compatible producer-shaped artifacts.", "",
        "## System configuration differences", "", "```json",
        json.dumps(result["compatibility"]["system_under_test_differences"], ensure_ascii=False, sort_keys=True, indent=2), "```", "",
        "## Retrieval Regression", "", "```json", json.dumps(result["retrieval_metric_deltas"], sort_keys=True, indent=2), "```", "",
        "## Generation Regression", "", "```json", json.dumps(result["generation_dimension_deltas"], sort_keys=True, indent=2), "```", "",
        "## End-to-End Regression", "", "```json", json.dumps({"pass": result["e2e_pass_delta"], "technical_failure": result["technical_failure_delta"], "latency": result["latency_delta"]}, sort_keys=True, indent=2), "```", "",
        "## Holdout stability", "", "```json", json.dumps(result["holdout_transitions"], sort_keys=True, indent=2), "```", "",
        "## Critical-failure changes", "", "```json", json.dumps(result["critical_failure_diff"], sort_keys=True, indent=2), "```", "",
        "## Gate results", "", "```json", json.dumps(result["gate_results"] | {"overall_status": result["status"]}, sort_keys=True, indent=2), "```", "",
        "This is an offline comparison. It does not promote a baseline or make an official release decision.",
    ]
    report_bytes = ("\n".join(report).rstrip() + "\n").encode("utf-8")
    base_version = request.baseline.layers["step73"].manifest.get("dataset_version")
    schema_version = request.baseline.layers["step73"].manifest.get("dataset_schema_version")
    manifest: dict[str, Any] = {
        "comparison_id": request.comparison_id,
        "baseline_run_id": request.baseline.run_id,
        "candidate_run_id": request.candidate.run_id,
        "retrieval_baseline_run_id": request.baseline.layers["step73"].run_id,
        "retrieval_candidate_run_id": request.candidate.layers["step73"].run_id,
        "generation_baseline_run_id": request.baseline.layers["step74"].run_id,
        "generation_candidate_run_id": request.candidate.layers["step74"].run_id,
        "e2e_baseline_run_id": request.baseline.layers["step75"].run_id,
        "e2e_candidate_run_id": request.candidate.layers["step75"].run_id,
        "dataset_version": base_version, "schema_version": schema_version,
        "comparison_policy_version": "lesson-chat-regression-policy/v1",
        "timestamp": request.timestamp or datetime.now(UTC).isoformat(),
        "execution_mode": "TEST_ONLY" if request.comparison_mode == "TEST_ONLY" else "OFFICIAL_REQUEST",
        "official_comparison_eligible": bool(result["official_eligible"]),
        "compatibility_result": result["compatibility"],
        "baseline_source_identities": _layer_identities(request, "baseline"),
        "candidate_source_identities": _layer_identities(request, "candidate"),
        "source_artifact_paths": {side: {layer: str(artifact.directory) for layer, artifact in getattr(request, side).layers.items()} for side in ("baseline", "candidate")},
        "source_artifact_hashes": {side: {layer: artifact.source_hashes for layer, artifact in getattr(request, side).layers.items()} for side in ("baseline", "candidate")},
        "status": result["status"], "files": {"summary.json": _sha256(summary_bytes), "cases.jsonl": _sha256(cases_bytes), "report.md": _sha256(report_bytes)},
        "baseline_promoted": False, "step77_included": False,
    }
    contents = {"summary.json": summary_bytes, "cases.jsonl": cases_bytes, "report.md": report_bytes, "manifest.json": _canonical_json(manifest)}
    for name, content in contents.items():
        (root / name).write_bytes(content)
    return {"directory": str(root), "status": result["status"], "files": {name: _sha256(content) for name, content in contents.items()}, "summary": result}
