from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import STEP77_EVALUATOR_VERSION


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return digest(path.read_bytes())


def assert_offline_not_official(manifest: dict) -> None:
    if manifest.get("execution_mode") == "OFFLINE_TEST":
        if manifest.get("official_eligible") is not False or manifest.get("runtime_api_calls") != 0:
            raise ValueError("STEP77_OFFLINE_RUN_CANNOT_BE_OFFICIAL")
        if manifest.get("provider_mode") not in {"FAKE", "REPLAY"}:
            raise ValueError("STEP77_OFFLINE_PROVIDER_MODE_INVALID")
    if manifest.get("human_approved_count", 0) != 0 and manifest.get("execution_mode") == "OFFLINE_TEST":
        raise ValueError("STEP77_OFFLINE_CANNOT_CREATE_HUMAN_APPROVAL")


def _check_safe(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if re.search(r"(api.?key|secret|authorization|chain.?of.?thought|raw.?learner.?credential)", str(key), re.I):
                raise ValueError("STEP77_ARTIFACT_PROHIBITED_FIELD")
            _check_safe(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _check_safe(child)


def build_manifest(*, run_id: str, track: str, execution_mode: str,
                   provider_mode: str, provider: str, model: str,
                   dataset_version: str, dataset_case_count: int,
                   development_case_count: int, holdout_case_count: int,
                   generation_config: dict, prompt_version: str,
                   schema_version: str, annotation_version: str,
                   rubric_version: str, code_commit: str | None = None,
                   extra: dict | None = None, schema_identity: str | None = None,
                   prompt_sha256: str | None = None, dataset_sha256: str | None = None) -> dict:
    manifest = {"run_id": run_id, "track": track, "timestamp": datetime.now(UTC).isoformat(),
        "execution_mode": execution_mode, "official_eligible": False,
        "dataset_version": dataset_version, "dataset_schema_version": "1.0.0",
        "dataset_case_count": dataset_case_count, "development_case_count": development_case_count,
        "holdout_case_count": holdout_case_count, "code_commit": code_commit,
        "provider_mode": provider_mode, "provider": provider, "model": model,
        "generation_config": generation_config, "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha256, "structured_schema_identity": schema_identity,
        "structured_schema_version": schema_version, "dataset_sha256": dataset_sha256,
        "evaluator_version": STEP77_EVALUATOR_VERSION,
        "annotation_version": annotation_version, "rubric_version": rubric_version,
        "replay_origin": None, "runtime_api_calls": 0, "human_approved_count": 0}
    if extra:
        manifest.update(extra)
    assert_offline_not_official(manifest)
    _check_safe(manifest)
    return manifest


def write_artifact(directory: Path, *, manifest: dict, rows: list[dict], summary: dict) -> dict:
    assert_offline_not_official(manifest)
    for row in rows:
        _check_safe(row)
        row_run_id = row.get("run_id", row.get("step77_run_id"))
        if row_run_id is not None and row_run_id != manifest.get("run_id"):
            raise ValueError("STEP77_ARTIFACT_CROSS_RUN_IDENTITY_MISMATCH")
    directory.mkdir(parents=True, exist_ok=True)
    cases = b"".join(canonical_json(row) + b"\n" for row in rows)
    cases_path = directory / "cases.jsonl"
    cases_path.write_bytes(cases)
    persisted_cases = cases_path.read_bytes()
    manifest = {**manifest, "cases_artifact_sha256": digest(persisted_cases), "executed_count": len(rows)}
    _check_safe(summary)
    summary = {**summary, "run_id": manifest["run_id"], "cases_artifact_sha256": manifest["cases_artifact_sha256"]}
    (directory / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
    (directory / "summary.json").write_bytes(canonical_json(summary) + b"\n")
    return {"cases_sha256": digest(persisted_cases), "manifest_sha256": digest((directory / "manifest.json").read_bytes()),
            "summary_sha256": digest((directory / "summary.json").read_bytes())}
