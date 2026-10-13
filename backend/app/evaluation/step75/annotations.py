from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import ANNOTATION_VERSION, RUBRIC_VERSION, HumanE2EAnnotation

ROOT = Path(__file__).resolve().parents[4]
ANNOTATION_ROOT = ROOT / "evaluation/annotations/lesson_chat_e2e/v0.1.0"
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


def canonical_sha256(value: object) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def execution_output_sha256(*, case_id: str, repeat_index: int, question: str,
                            generated_answer: str, selected_evidence: list[dict],
                            source_map: dict, validated_citations: list[dict],
                            sanitized_memory: dict | None) -> str:
    return canonical_sha256({"case_id": case_id, "repeat_index": repeat_index,
                             "question": question, "generated_answer": generated_answer,
                             "selected_evidence": selected_evidence, "source_map": source_map,
                             "validated_current_citations": validated_citations,
                             "sanitized_memory": sanitized_memory})


def validate_calibration_subset(cases: list[dict]) -> list[dict]:
    by_id = {row.get("case_id"): row for row in cases}
    if len(by_id) != len(cases) or set(CALIBRATION_IDS) - by_id.keys():
        raise ValueError("E2E_CALIBRATION_IDS_MISSING_OR_DUPLICATED")
    chosen = [by_id[case_id] for case_id in CALIBRATION_IDS]
    if any(row.get("split") != "DEVELOPMENT" or row.get("review_status") != "APPROVED"
           for row in chosen):
        raise ValueError("E2E_CALIBRATION_MUST_BE_APPROVED_DEVELOPMENT")
    return chosen


def validate_annotations(rows: list[dict], *, require_reviewed: bool = False) -> list[dict]:
    if len(rows) != 30 or {row.get("case_id") for row in rows} != set(CALIBRATION_IDS):
        raise ValueError("E2E_CALIBRATION_CASE_SET_MISMATCH")
    parsed = [HumanE2EAnnotation.model_validate(row) for row in rows]
    if require_reviewed and any(row.review_status.value == "DRAFT" for row in parsed):
        raise ValueError("REVIEW_REQUIRED")
    return [row.model_dump(mode="json") for row in parsed]


def validate_annotation_bindings(rows: list[dict], run_records: dict[str, dict], *,
                                 manifest: dict, cases_artifact_rows: list[dict],
                                 cases_artifact_sha256: str) -> list[dict]:
    """Fail closed if any reviewed annotation is stale or bound to changed output."""
    parsed = validate_annotations(rows, require_reviewed=True)
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("E2E_ANNOTATION_FROZEN_RUN_ID_MISSING")
    from .artifacts import canonical_json
    serialized_cases = b"".join(canonical_json(row) + b"\n" for row in cases_artifact_rows)
    actual_cases_hash = hashlib.sha256(serialized_cases).hexdigest()
    if (manifest.get("cases_artifact_sha256") != cases_artifact_sha256
            or actual_cases_hash != cases_artifact_sha256):
        raise ValueError("E2E_ANNOTATION_CASES_ARTIFACT_STALE")
    artifact_executions = {row.get("execution_id"): row for row in cases_artifact_rows
                           if isinstance(row, dict) and row.get("execution_id")}
    for row in parsed:
        if row.get("e2e_run_id") != run_id:
            raise ValueError("E2E_ANNOTATION_RUN_ID_MISMATCH")
        artifact_record = artifact_executions.get(row["execution_id"])
        if (artifact_record is None or artifact_record.get("case_id") != row["case_id"]
                or artifact_record.get("repeat_index") != row["repeat_index"]):
            raise ValueError("E2E_ANNOTATION_CASES_ARTIFACT_EXECUTION_MISMATCH")
        record = run_records.get(row["execution_id"])
        if (not record or record.get("case_id") != row["case_id"]
                or record.get("repeat_index") != row["repeat_index"]):
            raise ValueError("E2E_ANNOTATION_EXECUTION_BINDING_MISMATCH")
        artifact_trace = artifact_record.get("trace") or {}
        artifact_execution = {
            "question": (artifact_trace.get("conversation") or {}).get("current_question"),
            "generated_answer": (artifact_trace.get("generation") or {}).get("answer"),
            "source_map": (artifact_trace.get("prompt") or {}).get("source_map_snapshot"),
            "validated_citations": (artifact_trace.get("citation_validation") or {}).get("validated_citations"),
            "selected_evidence": artifact_trace.get("selected_evidence"),
            "sanitized_memory": (artifact_trace.get("memory") or {}).get("sanitized_context"),
        }
        if any(artifact_execution.get(key) != record.get(key) for key in artifact_execution):
            raise ValueError("E2E_ANNOTATION_CASES_ARTIFACT_EXECUTION_MISMATCH")
        if row["cases_artifact_sha256"] != cases_artifact_sha256:
            raise ValueError("E2E_ANNOTATION_CASES_ARTIFACT_STALE")
        expected_hashes = {
            "generated_answer_sha256": hashlib.sha256(
                record["generated_answer"].encode("utf-8")).hexdigest(),
            "source_map_sha256": canonical_sha256(record["source_map"]),
            "validated_citations_sha256": canonical_sha256(record["validated_citations"]),
            "evidence_snapshot_sha256": canonical_sha256(record["selected_evidence"]),
            "execution_output_sha256": execution_output_sha256(
                case_id=record["case_id"], repeat_index=1, question=record["question"],
                generated_answer=record["generated_answer"],
                selected_evidence=record["selected_evidence"], source_map=record["source_map"],
                validated_citations=record["validated_citations"],
                sanitized_memory=record.get("sanitized_memory")),
        }
        if any(row.get(field) != digest for field, digest in expected_hashes.items()):
            raise ValueError("E2E_ANNOTATION_RUNTIME_HASH_MISMATCH")
    return parsed


def write_unbound_draft_template(root: Path = ANNOTATION_ROOT) -> None:
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "annotation_name": "Lesson Chat End-to-End Human Calibration",
        "annotation_version": ANNOTATION_VERSION, "rubric_version": RUBRIC_VERSION,
        "dataset_version": "v0.8.0", "case_count": 30,
        "case_ids": list(CALIBRATION_IDS), "status": "TEMPLATE_UNBOUND",
        "review_policy": "Only an independent human may change review_status from DRAFT.",
        "binding_policy": "Run/output bindings are populated only from a later real frozen runtime run.",
        "human_approved_count": 0,
    }
    rows = [HumanE2EAnnotation(case_id=case_id).model_dump(mode="json")
            for case_id in CALIBRATION_IDS]
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "calibration.jsonl").write_text("".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
