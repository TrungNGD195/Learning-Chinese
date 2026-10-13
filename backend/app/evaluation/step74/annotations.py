from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import (
    AnnotationStatus, HumanGenerationAnnotation, HUMAN_ANNOTATION_VERSION,
    RUBRIC_VERSION,
)

ROOT = Path(__file__).resolve().parents[4]
ANNOTATION_ROOT = ROOT / "evaluation/annotations/lesson_chat_generation/v0.1.0"
CALIBRATION_IDS = (
    "current-hsk1-l01-001", "current-hsk1-l01-005", "current-hsk1-l01-006",
    "current-hsk1-l02-001", "current-hsk1-l02-003", "current-hsk1-l02-004",
    "current-hsk1-l02-005", "current-hsk1-l03-001", "current-hsk1-l03-004",
    "current-hsk1-l03-005", "ikb-fallback-de-ge-001", "ikb-fallback-de-ge-002",
    "ikb-fallback-numbers-er-liang-001", "ikb-fallback-numbers-er-liang-002",
    "ikb-fallback-numbers-er-liang-003", "ikb-fallback-pronouns-001",
    "ikb-fallback-pronouns-002", "ikb-fallback-pronouns-003",
    "trusted-external-bi-comparison-001", "trusted-external-dou-placement-001",
    "trusted-external-shenme-placement-001", "trusted-external-zai-location-001",
    "multiturn-age-question-jisui-001", "multiturn-family-introduction-zheshi-001",
    "multiturn-family-possession-measure-word-001", "multiturn-name-confirmation-ma-001",
    "multiturn-numbers-counting-to-quantity-001", "multiturn-reciprocal-question-ne-001",
    "multiturn-self-introduction-jiao-001", "multiturn-teacher-greeting-politeness-001",
)


def answer_sha256(answer: str) -> str:
    return hashlib.sha256(answer.encode("utf-8")).hexdigest()


def validate_calibration_subset(cases: list[dict]) -> list[dict]:
    by_id = {case["case_id"]: case for case in cases}
    if len(by_id) != len(cases) or set(CALIBRATION_IDS) - by_id.keys():
        raise ValueError("Frozen human calibration case IDs are missing or duplicated")
    selected = [by_id[case_id] for case_id in CALIBRATION_IDS]
    if any(case["split"] != "DEVELOPMENT" or case["review_status"] != "APPROVED"
           for case in selected):
        raise ValueError("Human calibration set must contain only approved DEVELOPMENT cases")
    return selected


def make_draft_packet(rows: list[dict], *, run_id: str | None = None) -> list[dict]:
    indexed = {row["case_id"]: row for row in rows}
    if len(indexed) != len(rows) or set(CALIBRATION_IDS) - indexed.keys():
        raise ValueError("Cannot bind calibration packet: a frozen case output is missing")
    packet = []
    for case_id in CALIBRATION_IDS:
        row = indexed[case_id]
        answer = row.get("generated_answer")
        digest = row.get("generated_answer_sha256")
        if (row.get("generator", {}).get("status") != "SUCCESS" or not answer
                or digest != answer_sha256(answer) or row.get("run_id") != run_id):
            raise ValueError("Cannot bind calibration packet to a failed or changed answer")
        packet.append(HumanGenerationAnnotation(
            case_id=case_id, generation_run_id=run_id,
            generated_answer_sha256=digest, review_status=AnnotationStatus.DRAFT,
        ).model_dump(mode="json"))
    return packet


def validate_annotations(annotations: list[dict], rows: list[dict], *, require_approved: bool) -> list[dict]:
    annotation_ids = [row.get("case_id") for row in annotations]
    if len(annotations) != 30 or len(set(annotation_ids)) != 30 or set(annotation_ids) != set(CALIBRATION_IDS):
        raise ValueError("Calibration packet has duplicate/missing IDs or is not the exact frozen 30-case set")
    row_ids = [row.get("case_id") for row in rows]
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("Stage-A artifact contains duplicate case IDs")
    results = {row["case_id"]: row for row in rows}
    parsed = [HumanGenerationAnnotation.model_validate(row).model_dump(mode="json") for row in annotations]
    for row in parsed:
        result = results.get(row["case_id"])
        if result is None or result.get("case_id") not in CALIBRATION_IDS:
            raise ValueError("Calibration annotation references a non-frozen case")
        if result.get("split") != "DEVELOPMENT":
            raise ValueError("Calibration annotation must bind a DEVELOPMENT case")
        if row["annotation_version"] != HUMAN_ANNOTATION_VERSION or row["rubric_version"] != RUBRIC_VERSION:
            raise ValueError("HUMAN_CALIBRATION_VERSION_MISMATCH")
        if row["generation_run_id"] != result.get("run_id"):
            raise ValueError("Human annotation run binding is stale")
        answer = result.get("generated_answer")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("HUMAN_CALIBRATION_STALE")
        recomputed_hash = answer_sha256(answer)
        if result.get("generated_answer_sha256") != recomputed_hash or row["generated_answer_sha256"] != recomputed_hash:
            raise ValueError("HUMAN_CALIBRATION_STALE")
        if require_approved and row["review_status"] != AnnotationStatus.HUMAN_APPROVED:
            raise ValueError("REVIEW_REQUIRED")
        if require_approved:
            if row.get("scores") is None or row.get("claim_faithfulness") is None:
                raise ValueError("REVIEW_REQUIRED")
            evidence_ids = set(result.get("fixed_evidence_ids") or [])
            for claim in row["claim_faithfulness"]:
                unknown = set(claim["supporting_evidence_ids"]) - evidence_ids
                if unknown:
                    raise ValueError("Human annotation references evidence not supplied to the case")
    return parsed


def annotation_package_paths(annotation_file: Path | None = None) -> tuple[Path, Path]:
    """Resolve the human source of truth; by default this is the canonical repo package."""
    calibration = annotation_file or (ANNOTATION_ROOT / "calibration.jsonl")
    return calibration.parent / "manifest.json", calibration


def validate_annotation_manifest(manifest: dict, *, run_id: str) -> None:
    if manifest.get("annotation_version") != HUMAN_ANNOTATION_VERSION \
            or manifest.get("rubric_version") != RUBRIC_VERSION \
            or manifest.get("dataset_version") != "v0.8.0":
        raise ValueError("HUMAN_CALIBRATION_VERSION_MISMATCH")
    if manifest.get("case_ids") != list(CALIBRATION_IDS) or manifest.get("case_count") != 30:
        raise ValueError("HUMAN_CALIBRATION_CASE_SET_MISMATCH")
    if manifest.get("generation_run_id") != run_id:
        raise ValueError("HUMAN_CALIBRATION_RUN_ID_MISMATCH")


def load_annotation_package(annotation_file: Path | None = None) -> tuple[dict, list[dict]]:
    manifest_path, calibration_path = annotation_package_paths(annotation_file)
    if not manifest_path.is_file() or not calibration_path.is_file():
        raise ValueError("REVIEW_REQUIRED")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    annotations = [json.loads(line) for line in calibration_path.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    return manifest, annotations


def write_source_controlled_template(root: Path = ANNOTATION_ROOT) -> None:
    """Write unbound DRAFT templates only; Stage A supplies hashes/run IDs later."""
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "annotation_name": "Lesson Chat Generation Human Calibration",
        "annotation_version": HUMAN_ANNOTATION_VERSION,
        "dataset_version": "v0.8.0", "rubric_version": RUBRIC_VERSION,
        "status": "TEMPLATE_UNBOUND", "case_count": 30,
        "case_ids": list(CALIBRATION_IDS),
        "review_policy": "Only independent human review may set HUMAN_APPROVED; Codex and LLM outputs remain DRAFT.",
        "created_at": None, "updated_at": None,
        "approval_policy": "MANUAL_HUMAN_REVIEW_REQUIRED; CODEX_AND_LLM_MUST_NOT_SELF_APPROVE",
    }
    rows = [HumanGenerationAnnotation(case_id=case_id).model_dump(mode="json") for case_id in CALIBRATION_IDS]
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "calibration.jsonl").write_text("".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ), encoding="utf-8")


def load_annotations(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
