from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


LayerName = Literal["step73", "step74", "step75"]
LAYERS: tuple[LayerName, ...] = ("step73", "step74", "step75")
STEP_NUMBERS = {"step73": "7.3", "step74": "7.4", "step75": "7.5"}


@dataclass(frozen=True)
class LayerArtifact:
    layer: LayerName
    directory: Path
    manifest: dict[str, Any]
    summary: dict[str, Any]
    cases: tuple[dict[str, Any], ...]
    source_hashes: dict[str, str]
    superseded: bool = False

    @property
    def run_id(self) -> str:
        return str(self.manifest["run_id"])


@dataclass(frozen=True)
class ComparisonSide:
    """One explicit system identity and its three explicit evaluation runs."""

    run_id: str
    layers: dict[LayerName, LayerArtifact]
    approved_baseline_run_id: str | None = None


@dataclass(frozen=True)
class ComparisonRequest:
    comparison_id: str
    baseline: ComparisonSide
    candidate: ComparisonSide
    comparison_mode: Literal["TEST_ONLY", "OFFICIAL"] = "TEST_ONLY"
    timestamp: str = ""


@dataclass(frozen=True)
class CompatibilityResult:
    compatible: bool
    checks: tuple[dict[str, Any], ...]
    issues: tuple[str, ...]
    system_under_test_differences: dict[str, dict[str, Any]]

