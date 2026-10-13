from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import LAYERS, LayerArtifact, LayerName, STEP_NUMBERS


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path.name}")
    return value


def load_layer_artifact(layer: LayerName, directory: str | Path) -> LayerArtifact:
    """Load one explicitly named run directory; never searches for latest runs."""
    root = Path(directory).resolve()
    artifact_root = root
    if not (root / "cases.jsonl").is_file() and layer == "step74" and (root / "generation" / "cases.jsonl").is_file():
        artifact_root = root / "generation"
    manifest_path, summary_path, cases_path = (artifact_root / name for name in ("manifest.json", "summary.json", "cases.jsonl"))
    if not all(path.is_file() for path in (manifest_path, summary_path, cases_path)):
        raise ValueError("Explicit run directory must contain manifest.json, summary.json, and cases.jsonl")
    manifest, summary = _json(manifest_path), _json(summary_path)
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("Run manifest is missing an explicit run_id")
    if str(manifest.get("evaluation_step", "")) != STEP_NUMBERS[layer]:
        raise ValueError(f"Expected Step {STEP_NUMBERS[layer]} artifact")
    schema_version = manifest.get("dataset_schema_version")
    if schema_version != "1.0.0":
        raise ValueError(f"Unsupported {layer} dataset schema version: {schema_version!r}")
    if not isinstance(manifest.get("dataset_version"), str) or not manifest["dataset_version"].strip():
        raise ValueError(f"{layer} manifest is missing a persisted dataset_version")
    summary_run = summary.get("run_id")
    if summary_run is not None and summary_run != run_id:
        raise ValueError("Manifest and summary run_id differ")
    if summary.get("dataset_version") is not None and summary.get("dataset_version") != manifest.get("dataset_version"):
        raise ValueError("Manifest and summary dataset_version differ")
    cases_hash = sha256_file(cases_path)
    for key in ("cases_artifact_sha256", "cases_file_sha256"):
        expected = manifest.get(key) or summary.get(key)
        if expected is not None and expected != cases_hash:
            raise ValueError(f"{key} does not match cases.jsonl")
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(cases_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"cases.jsonl line {line_number} is not an object")
        cases.append(row)
    hashes = {name: sha256_file(artifact_root / name) for name in ("manifest.json", "summary.json", "cases.jsonl")}
    return LayerArtifact(layer, artifact_root, manifest, summary, tuple(cases), hashes, (root / "SUPERSEDED.txt").exists())


def explicit_side(run_id: str, directories: dict[LayerName, str | Path], *, approved_baseline_run_id: str | None = None):
    from .contracts import ComparisonSide

    if not run_id.strip() or run_id.strip().lower() == "latest":
        raise ValueError("Comparison side requires an explicit identity; 'latest' is forbidden")
    if set(directories) != set(LAYERS):
        raise ValueError("Each comparison side must explicitly supply Step 7.3, 7.4, and 7.5 run directories")
    layers = {layer: load_layer_artifact(layer, directories[layer]) for layer in LAYERS}
    if any(artifact.run_id == "latest" for artifact in layers.values()):
        raise ValueError("The 'latest' selector is not an artifact identity")
    return ComparisonSide(run_id=run_id, layers=layers, approved_baseline_run_id=approved_baseline_run_id)
