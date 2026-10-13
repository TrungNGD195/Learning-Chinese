from __future__ import annotations

import json
import hashlib
from collections import Counter
from pathlib import Path

from .contracts import GenerationCase, GradingAnnotation, GradingCase, GenerationQuestionAnnotation

ROOT = Path(__file__).resolve().parents[4] / "evaluation"
GRADING_DATASET = ROOT / "datasets/ai_grading/v0.1.0"
GENERATION_DATASET = ROOT / "datasets/assessment_generation/v0.1.0"
GRADING_ANNOTATIONS = ROOT / "annotations/ai_grading/v0.1.0"
GENERATION_ANNOTATIONS = ROOT / "annotations/assessment_generation/v0.1.0"
SUPPORTED_QUESTION_TYPES = ("multiple_choice", "fill_blank", "matching", "reorder_sentence",
                             "translate_vi_zh", "translate_zh_vi", "sentence_writing")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def annotation_contract(track: str) -> tuple[str, str]:
    directory = GRADING_ANNOTATIONS if track == "grading" else GENERATION_ANNOTATIONS
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    versions = (manifest.get("annotation_version"), manifest.get("rubric_version"))
    if not all(isinstance(value, str) and value.strip() for value in versions):
        raise ValueError("STEP77_ANNOTATION_CONTRACT_INVALID")
    return versions


def _all(split_dir: Path) -> list[dict]:
    return read_jsonl(split_dir / "development.jsonl") + read_jsonl(split_dir / "holdout.jsonl")


def _fingerprint(row: dict, *, ignored: set[str]) -> str:
    payload = {key: value for key, value in row.items() if key not in ignored}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _assert_holdout_distinct(rows: list[dict], *, ignored: set[str], code: str) -> None:
    development = {_fingerprint(row, ignored=ignored) for row in rows if row.get("split") == "DEVELOPMENT"}
    holdout_rows = [row for row in rows if row.get("split") == "HOLDOUT"]
    holdout = [_fingerprint(row, ignored=ignored) for row in holdout_rows]
    if any(value in development for value in holdout) or len(set(holdout)) != len(holdout):
        raise ValueError(code)


def _assert_readable_utf8_sources(grading: list[dict], curriculum: dict) -> None:
    def check_text(value: object, *, source: str) -> None:
        if not isinstance(value, str):
            return
        suspicious = ("\ufffd", "Ã", "Â", "ä½", "å¥", "å†", "æ\u0090", "Táº", "CÃ")
        if any(marker in value for marker in suspicious):
            raise ValueError(f"STEP77_UTF8_CORRUPTION:{source}")
        if any(marker in value for marker in ("??", "D?ch", "ti?ng", "ch?o", "kh?e", "t?n l?")):
            raise ValueError(f"STEP77_UTF8_REPLACEMENT_QUESTION_MARK:{source}")

    for case in grading:
        for field in ("question_content", "reference_answer", "learner_answer"):
            value = case.get(field)
            check_text(value, source=f"grading:{case.get('case_id')}:{field}")
            if field != "learner_answer" and (
                not isinstance(value, str) or not any(ord(char) > 127 for char in value)
            ):
                raise ValueError(f"STEP77_FIXTURE_TEXT_NOT_READABLE:{case.get('case_id')}:{field}")
    for group in ("lessons", "vocabulary", "grammar"):
        for index, item in enumerate(curriculum.get(group, [])):
            for field, value in item.items():
                check_text(value, source=f"curriculum:{group}:{index}:{field}")
            educational_fields = {"lessons": ("title", "description"),
                "vocabulary": ("hanzi", "pinyin", "vietnamese_meaning", "example"),
                "grammar": ("structure", "explanation", "example")}[group]
            for field in educational_fields:
                value = item.get(field)
                if not isinstance(value, str) or not any(ord(char) > 127 for char in value):
                    raise ValueError(f"STEP77_CURRICULUM_TEXT_NOT_READABLE:{group}:{index}:{field}")


def _assert_unique_jsonl_ids(paths: list[Path]) -> None:
    for path in paths:
        raw = path.read_bytes()
        try:
            raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError(f"STEP77_SOURCE_NOT_UTF8:{path.name}") from exc
        for line in raw.splitlines():
            if line:
                json.loads(line.decode("utf-8"))


def validate_step77_datasets() -> dict:
    grading_manifest = json.loads((GRADING_DATASET / "manifest.json").read_text(encoding="utf-8"))
    generation_manifest = json.loads((GENERATION_DATASET / "manifest.json").read_text(encoding="utf-8"))
    grading_annotation_manifest = json.loads((GRADING_ANNOTATIONS / "manifest.json").read_text(encoding="utf-8"))
    generation_annotation_manifest = json.loads((GENERATION_ANNOTATIONS / "manifest.json").read_text(encoding="utf-8"))
    if (grading_manifest.get("dataset_version") != "v0.1.0" or grading_manifest.get("total_cases") != 60
            or grading_manifest.get("development_cases") != 45 or grading_manifest.get("holdout_cases") != 15
            or grading_manifest.get("human_approved_annotations") != 0):
        raise ValueError("STEP77_GRADING_MANIFEST_INVALID")
    if (generation_manifest.get("dataset_version") != "v0.1.0" or generation_manifest.get("total_cases") != 16
            or generation_manifest.get("development_cases") != 12 or generation_manifest.get("holdout_cases") != 4
            or generation_manifest.get("lesson_exercise_cases") != 8
            or generation_manifest.get("periodic_test_cases") != 8
            or generation_manifest.get("human_approved_annotations") != 0):
        raise ValueError("STEP77_GENERATION_MANIFEST_INVALID")
    grading_versions = annotation_contract("grading")
    generation_versions = annotation_contract("generation")
    if (grading_annotation_manifest.get("human_approved_count") != 0
            or grading_annotation_manifest.get("annotation_count") != 60
            or grading_annotation_manifest.get("annotation_version") != grading_versions[0]
            or grading_annotation_manifest.get("rubric_version") != grading_versions[1]):
        raise ValueError("STEP77_GRADING_ANNOTATION_MANIFEST_INVALID")
    if (generation_annotation_manifest.get("human_approved_count") != 0
            or generation_annotation_manifest.get("annotation_count") != 48
            or generation_annotation_manifest.get("annotation_version") != generation_versions[0]
            or generation_annotation_manifest.get("rubric_version") != generation_versions[1]):
        raise ValueError("STEP77_GENERATION_ANNOTATION_MANIFEST_INVALID")
    grading = [GradingCase.model_validate(row) for row in _all(GRADING_DATASET)]
    generation = [GenerationCase.model_validate(row) for row in _all(GENERATION_DATASET)]
    grading_paths = [GRADING_DATASET / "development.jsonl", GRADING_DATASET / "holdout.jsonl"]
    generation_paths = [GENERATION_DATASET / "development.jsonl", GENERATION_DATASET / "holdout.jsonl"]
    _assert_unique_jsonl_ids(grading_paths + generation_paths + [
        GRADING_ANNOTATIONS / "annotations.jsonl", GENERATION_ANNOTATIONS / "questions.jsonl"])
    curriculum = json.loads((ROOT / "fixtures/assessment_generation/v0.1.0/curriculum.json").read_text(encoding="utf-8"))
    _assert_readable_utf8_sources([case.model_dump(mode="json") for case in grading], curriculum)
    grading_ids = [case.case_id for case in grading]
    if len(grading) != 60 or len(set(grading_ids)) != 60:
        raise ValueError("STEP77_GRADING_DATASET_COUNT_OR_ID_INVALID")
    _assert_holdout_distinct(_all(GRADING_DATASET),
        ignored={"case_id", "annotation_ref", "split", "review_status", "dataset_version", "schema_version"},
        code="STEP77_GRADING_HOLDOUT_LEAKAGE")
    grading_cells = Counter((case.question_type, case.semantic_class.value, case.split.value) for case in grading)
    for question_type in ("translate_vi_zh", "translate_zh_vi", "sentence_writing"):
        for semantic_class in ("CLEAR_CORRECT", "CLEAR_INCORRECT", "PARTIAL", "AMBIGUOUS", "EXPECTED_UNCERTAIN"):
            if grading_cells[(question_type, semantic_class, "DEVELOPMENT")] != 3 or grading_cells[(question_type, semantic_class, "HOLDOUT")] != 1:
                raise ValueError("STEP77_GRADING_DATASET_CELL_INVALID")
    for split, expected in (("DEVELOPMENT", 45), ("HOLDOUT", 15)):
        if sum(case.split.value == split for case in grading) != expected:
            raise ValueError("STEP77_GRADING_DATASET_SPLIT_INVALID")
    annotations = [GradingAnnotation.model_validate(row) for row in read_jsonl(GRADING_ANNOTATIONS / "annotations.jsonl")]
    if len(annotations) != 60 or {item.case_id for item in annotations} != set(grading_ids):
        raise ValueError("STEP77_GRADING_ANNOTATION_BINDING_INVALID")
    if any(item.review_status != "DRAFT" for item in annotations):
        raise ValueError("STEP77_GRADING_HUMAN_APPROVAL_FORBIDDEN")
    if any((item.annotation_version, item.rubric_version) != grading_versions for item in annotations):
        raise ValueError("STEP77_GRADING_ANNOTATION_VERSION_MISMATCH")
    generation_ids = [case.case_id for case in generation]
    if len(generation) != 16 or len(set(generation_ids)) != 16:
        raise ValueError("STEP77_GENERATION_DATASET_COUNT_OR_ID_INVALID")
    _assert_holdout_distinct(_all(GENERATION_DATASET),
        ignored={"case_id", "split", "dataset_version", "schema_version"},
        code="STEP77_GENERATION_HOLDOUT_LEAKAGE")
    if sum(case.split.value == "DEVELOPMENT" for case in generation) != 12 or sum(case.split.value == "HOLDOUT" for case in generation) != 4:
        raise ValueError("STEP77_GENERATION_DATASET_SPLIT_INVALID")
    if sum(case.generation_kind == "LESSON_EXERCISE" for case in generation) != 8 or sum(case.generation_kind == "PERIODIC_TEST" for case in generation) != 8:
        raise ValueError("STEP77_GENERATION_KIND_DISTRIBUTION_INVALID")
    types = {kind for case in generation for kind in case.allowed_question_types}
    difficulties = {case.difficulty for case in generation}
    if types != set(SUPPORTED_QUESTION_TYPES) or difficulties != {"EASY", "MEDIUM", "HARD"}:
        raise ValueError("STEP77_GENERATION_COVERAGE_INVALID")
    gen_annotations = [GenerationQuestionAnnotation.model_validate(row) for row in read_jsonl(GENERATION_ANNOTATIONS / "questions.jsonl")]
    if len(gen_annotations) != 48 or {(item.generation_case_id, item.question_index) for item in gen_annotations} != {(case.case_id, i) for case in generation for i in (1, 2, 3)}:
        raise ValueError("STEP77_GENERATION_ANNOTATION_BINDING_INVALID")
    if any(item.review_status != "DRAFT" for item in gen_annotations):
        raise ValueError("STEP77_GENERATION_HUMAN_APPROVAL_FORBIDDEN")
    if any((item.annotation_version, item.rubric_version) != generation_versions for item in gen_annotations):
        raise ValueError("STEP77_GENERATION_ANNOTATION_VERSION_MISMATCH")
    return {"grading": {"total": len(grading), "development": 45, "holdout": 15,
                         "annotations_draft": len(annotations), "human_approved": 0},
            "assessment_generation": {"total": len(generation), "development": 12, "holdout": 4,
                                       "lesson_exercise": 8, "periodic_test": 8,
                                       "annotations_draft": len(gen_annotations), "human_approved": 0,
                                       "supported_types": sorted(types), "difficulties": sorted(difficulties)}}
