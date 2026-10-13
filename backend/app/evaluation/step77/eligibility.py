from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from uuid import UUID


def _annotation_contract(track: str) -> tuple[str, str]:
    """Read frozen annotation identities from the source-controlled annotation manifest."""
    from .dataset import annotation_contract
    return annotation_contract(track)


def _settings_for_identity(identity: dict, *, track: str):
    """Build the production-shaped request settings from the frozen run identity."""
    from app.core.config import Settings
    config = identity.get("generation_config")
    required = {"temperature", "reasoning_effort", "model_input_limit",
                "request_timeout_seconds", "max_transient_retries"}
    token_key = "max_output_tokens"
    if not isinstance(config, dict) or not required.issubset(config) or token_key not in config:
        raise ValueError("STEP77_REQUEST_CONFIG_IDENTITY_INCOMPLETE")
    values = dict(app_env="test", debug=False,
        test_database_url="postgresql+psycopg://step77.invalid/chinese_learning_test",
        secret_key="step77-offline-identity-only", llm_provider=identity["provider"],
        llm_model=identity["model"], llm_temperature=config["temperature"],
        llm_reasoning_effort=config["reasoning_effort"],
        llm_model_input_limit=config["model_input_limit"],
        llm_request_timeout_seconds=config["request_timeout_seconds"],
        llm_max_transient_retries=config["max_transient_retries"])
    if track == "grading":
        values["llm_max_output_tokens"] = config[token_key]
    else:
        values["ai_generation_max_output_tokens"] = config[token_key]
    return Settings(_env_file=None, **values)


def _production_identity_valid(identity: dict, *, track: str) -> bool:
    from . import STEP77_EVALUATOR_VERSION
    from .artifacts import file_sha256
    backend_root = Path(__file__).resolve().parents[3]
    if track == "grading":
        from app.ai.grading.prompt import GRADING_PROMPT_VERSION
        prompt_path = backend_root / "app/ai/grading/prompt.py"
        schema_id = "app.ai.grading.schemas.StructuredGradingOutput/v1"
        agreement = {"primary_unit": "D-106/v1", "denominator": "D-107/v1"}
        if identity.get("agreement_policy_identity") != agreement:
            return False
    else:
        from app.ai.generation.prompt import ASSESSMENT_GENERATION_PROMPT_VERSION
        prompt_path = backend_root / "app/ai/generation/prompt.py"
        schema_id = "app.ai.generation.schemas.StructuredAssessmentGenerationOutput/v1"
        if identity.get("scope_domain_validator_identity") != "app.exercise.service.admin_validate_generated_question/v1":
            return False
    try:
        _settings_for_identity(identity, track=track)
    except (KeyError, TypeError, ValueError):
        return False
    expected_prompt_version = (GRADING_PROMPT_VERSION if track == "grading"
                               else ASSESSMENT_GENERATION_PROMPT_VERSION)
    return (identity.get("provider") == "openai"
            and identity.get("model") == "gpt-5.4-mini-2026-03-17"
            and identity.get("prompt_version") == expected_prompt_version
            and identity.get("prompt_sha256") == file_sha256(prompt_path)
            and identity.get("structured_schema_identity") == schema_id
            and identity.get("structured_schema_version") == "1.0.0"
            and identity.get("evaluator_version") == STEP77_EVALUATOR_VERSION)


def _expected_case_binding(track: str, case, identity: dict) -> dict | None:
    """Recompute the execution identity from frozen dataset/config and fixture content."""
    try:
        settings = _settings_for_identity(identity, track=track)
        if track == "grading":
            from .grading import grading_request_identity
            expected_metadata = case.production_input_metadata
            return {"split": case.split.value, "question_type": case.question_type,
                    "semantic_class": case.semantic_class.value, "max_points": case.max_points,
                    "production_input_metadata": expected_metadata,
                    "request_sha256": grading_request_identity(case, settings)[1]}
        from .generation import generation_request_identity, scope_identity
        from .db_fixture import FIXTURE_LEVEL_ID, FIXTURE_PATH
        from app.ai.generation.schemas import (AssessmentGenerationRequest,
                                                MaterializedGenerationScope)
        from pydantic import TypeAdapter
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        lessons = {str(item["lesson_id"]): item for item in fixture["lessons"]}
        vocab = {str(item["id"]): item for item in fixture["vocabulary"]}
        grammar = {str(item["id"]): item for item in fixture["grammar"]}
        request_body = {"type": case.generation_kind, "question_count": case.question_count,
            "allowed_types": case.allowed_question_types, "difficulty": case.difficulty,
            "title": case.title, "description": case.description, "pass_threshold": case.pass_threshold}
        if case.generation_kind == "LESSON_EXERCISE":
            request_body["lesson_id"] = case.lesson_id
        else:
            request_body.update(lesson_ids=case.lesson_ids, vocabulary_ids=case.vocabulary_ids,
                                grammar_ids=case.grammar_ids)
        request = TypeAdapter(AssessmentGenerationRequest).validate_python(request_body)
        if case.generation_kind == "LESSON_EXERCISE":
            lesson = lessons[case.lesson_id]
            ld = {"id": case.lesson_id, "title": lesson["title"], "description": lesson["description"],
                  "lesson_number": lesson["lesson_number"], "hsk_level_id": str(FIXTURE_LEVEL_ID)}
            vrows = sorted((item for item in fixture["vocabulary"] if item["lesson_id"] == case.lesson_id),
                           key=lambda item: item["order_index"])
            grows = sorted((item for item in fixture["grammar"] if item["lesson_id"] == case.lesson_id),
                           key=lambda item: item["order_index"])
            vpayload = [{"source_ref": f"vocab:{item['id']}", "lesson": ld,
                **{key: item[key] for key in ("hanzi", "pinyin", "vietnamese_meaning", "part_of_speech")},
                "note": "Step 7.7 synthetic evaluation fixture", "example": item["example"],
                "order_index": item["order_index"]} for item in vrows]
            gpayload = [{"source_ref": f"grammar:{item['id']}", "lesson": ld,
                **{key: item[key] for key in ("name", "structure", "explanation", "usage")},
                "note": "Step 7.7 synthetic evaluation fixture", "example": item["example"],
                "order_index": item["order_index"]} for item in grows]
            payload = {"scope": {"lesson": ld}, "vocabulary": vpayload, "grammar": gpayload}
            allowed = frozenset(item["source_ref"] for item in vpayload + gpayload)
            lesson_ids = (case.lesson_id,)
            vocabulary_ids = tuple(item["id"] for item in vrows)
            grammar_ids = tuple(item["id"] for item in grows)
            assessment_type = case.generation_kind
        else:
            selected_lessons = sorted((lessons[item] for item in case.lesson_ids),
                                      key=lambda item: (item["lesson_number"], item["lesson_id"]))
            lesson_rows = [{"id": item["lesson_id"], "title": item["title"],
                "lesson_number": item["lesson_number"]} for item in selected_lessons]
            # Match production SQL ordering: lesson number/id, association order, entity id.
            rank = {row["lesson_id"]: (row["lesson_number"], row["lesson_id"]) for row in selected_lessons}
            vrows = sorted((item for item in fixture["vocabulary"] if item["id"] in case.vocabulary_ids
                            and item["lesson_id"] in rank), key=lambda item:(*rank[item["lesson_id"]], item["order_index"], item["id"]))
            grows = sorted((item for item in fixture["grammar"] if item["id"] in case.grammar_ids
                            and item["lesson_id"] in rank), key=lambda item:(*rank[item["lesson_id"]], item["order_index"], item["id"]))
            vp, gp = {}, {}
            for item in vrows:
                record = vp.setdefault(item["id"], {"source_ref":f"vocab:{item['id']}",
                    **{key:item[key] for key in ("hanzi","pinyin","vietnamese_meaning","part_of_speech")},
                    "lessons":[],"lesson_associations":[]})
                lesson=lessons[item["lesson_id"]]
                record["lessons"].append({"id":item["lesson_id"],"title":lesson["title"],"lesson_number":lesson["lesson_number"]})
                record["lesson_associations"].append({"note":"Step 7.7 synthetic evaluation fixture","example":item["example"],"order_index":item["order_index"]})
            for item in grows:
                record = gp.setdefault(item["id"], {"source_ref":f"grammar:{item['id']}",
                    **{key:item[key] for key in ("name","structure","explanation","usage")},
                    "lessons":[],"lesson_associations":[]})
                lesson=lessons[item["lesson_id"]]
                record["lessons"].append({"id":item["lesson_id"],"title":lesson["title"],"lesson_number":lesson["lesson_number"]})
                record["lesson_associations"].append({"note":"Step 7.7 synthetic evaluation fixture","example":item["example"],"order_index":item["order_index"]})
            if set(vp) != set(case.vocabulary_ids) or set(gp) != set(case.grammar_ids):
                return None
            payload={"scope":{"lessons":lesson_rows},"vocabulary":[vp[item] for item in case.vocabulary_ids],
                     "grammar":[gp[item] for item in case.grammar_ids]}
            allowed=frozenset([item["source_ref"] for item in payload["vocabulary"]+payload["grammar"]])
            lesson_ids=tuple(case.lesson_ids); vocabulary_ids=tuple(case.vocabulary_ids); grammar_ids=tuple(case.grammar_ids)
            assessment_type=case.generation_kind
        scope=MaterializedGenerationScope(assessment_type=assessment_type,
            lesson_id=request.lesson_id if case.generation_kind=="LESSON_EXERCISE" else None,
            lesson_ids=tuple(UUID(item) for item in lesson_ids),
            vocabulary_ids=tuple(UUID(item) for item in vocabulary_ids),
            grammar_ids=tuple(UUID(item) for item in grammar_ids),
            title=case.title or (f"AI Draft — {lessons[case.lesson_id]['title']}" if case.generation_kind=="LESSON_EXERCISE" else "AI Draft — Periodic Test"),
            description=case.description, pass_threshold=case.pass_threshold,
            payload=payload, allowed_source_refs=allowed)
        expected_scope={"identity":scope_identity(case),"payload":scope.payload,
                        "allowed_source_refs":sorted(scope.allowed_source_refs)}
        expected_scope_hash=hashlib.sha256(_canonical_json(expected_scope)).hexdigest()
        _, expected_request_hash=generation_request_identity(case,settings,request=request,scope=scope)
        return {"generation_kind": case.generation_kind, "split": case.split.value,
            "difficulty": case.difficulty, "question_count": case.question_count,
            "allowed_question_types": case.allowed_question_types, "lesson_id": case.lesson_id,
            "lesson_ids": case.lesson_ids, "vocabulary_ids": case.vocabulary_ids,
            "grammar_ids": case.grammar_ids, "fixture_scope_identity": case.fixture_scope_identity,
            "materialized_scope_content": expected_scope,
            "materialized_scope_sha256": expected_scope_hash,
            "request_sha256": expected_request_hash}
    except (KeyError, TypeError, ValueError, OSError):
        return None


def _case_request_matches(track: str, case, row: dict, identity: dict) -> bool:
    binding = _expected_case_binding(track, case, identity)
    return binding is not None and all(row.get(key) == value for key, value in binding.items())


def _canonical_json(value: object) -> bytes:
    from .artifacts import canonical_json
    return canonical_json(value)


def _artifact_rows(rows: list[dict]) -> bytes:
    from .artifacts import canonical_json
    return b"".join(canonical_json(row) + b"\n" for row in rows)


def _manifest_and_artifact_valid(manifest: dict, artifact: bytes, rows: list[dict]) -> bool:
    from .artifacts import digest
    return (manifest.get("cases_artifact_sha256") == digest(artifact)
            and artifact == _artifact_rows(rows))


def _identity_matches(manifest: dict, expected_identity: dict) -> bool:
    return all(manifest.get(key) == value for key, value in expected_identity.items())


def _dataset_files_valid(dataset_cases: list[dict], dataset_files: dict[str, bytes], manifest: dict) -> bool:
    from .artifacts import canonical_json, digest
    required = {"manifest.json", "development.jsonl", "holdout.jsonl"}
    if set(dataset_files) != required: return False
    try:
        source_manifest = json.loads(dataset_files["manifest.json"].decode("utf-8", errors="strict"))
        source_cases = [json.loads(line) for name in ("development.jsonl", "holdout.jsonl")
                        for line in dataset_files[name].decode("utf-8", errors="strict").splitlines() if line.strip()]
        source_hash = digest(canonical_json({name: digest(data) for name, data in dataset_files.items()}))
        return (source_cases == dataset_cases and source_hash == manifest.get("dataset_sha256")
                and source_hash == source_manifest.get("dataset_sha256", source_hash)
                and source_manifest.get("total_cases") == len(dataset_cases))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return False


def grading_official_eligibility(*, manifest: dict, dataset_cases: list[dict],
                                 executions: list[dict], annotations: list[dict],
                                 expected_identity: dict, cases_artifact: bytes,
                                 dataset_files: dict[str, bytes]) -> tuple[bool, str]:
    """Prove complete Track-A benchmark coverage; never authorizes execution."""
    from .contracts import GradingAnnotation, GradingCase
    from .grading import validate_human_annotation
    required_identity = {"dataset_version", "dataset_schema_version", "dataset_sha256", "provider", "model",
        "generation_config", "prompt_version", "prompt_sha256", "structured_schema_identity",
        "structured_schema_version", "evaluator_version", "agreement_policy_identity",
        "annotation_version", "rubric_version"}
    if not required_identity.issubset(expected_identity): return False, "EXPECTED_IDENTITY_INCOMPLETE"
    try:
        frozen_annotation_version, frozen_rubric_version = _annotation_contract("grading")
    except (OSError, ValueError, json.JSONDecodeError):
        return False, "ANNOTATION_CONTRACT_INVALID"
    if (expected_identity.get("annotation_version") != frozen_annotation_version
            or expected_identity.get("rubric_version") != frozen_rubric_version):
        return False, "ANNOTATION_CONTRACT_IDENTITY_MISMATCH"
    if not _production_identity_valid(expected_identity, track="grading"):
        return False, "FROZEN_PRODUCTION_IDENTITY_MISMATCH"
    if manifest.get("execution_mode") != "OFFICIAL_RUNTIME": return False, "OFFICIAL_RUNTIME_REQUIRED"
    if manifest.get("provider_mode") != "REAL": return False, "REAL_PROVIDER_REQUIRED"
    if not _identity_matches(manifest, expected_identity): return False, "PRODUCTION_IDENTITY_MISMATCH"
    if not _dataset_files_valid(dataset_cases, dataset_files, manifest): return False, "DATASET_ARTIFACT_INVALID"
    cases = [GradingCase.model_validate(row).model_dump(mode="json") for row in dataset_cases]
    ids = [row["case_id"] for row in cases]
    if (len(ids) != 60 or len(set(ids)) != 60 or any(row.get("dataset_version") != "v0.1.0" for row in dataset_cases)
            or manifest.get("dataset_version") != "v0.1.0" or manifest.get("dataset_schema_version") != "1.0.0"
            or manifest.get("dataset_case_count") != 60
            or manifest.get("development_case_count") != 45 or manifest.get("holdout_case_count") != 15):
        return False, "DATASET_CASE_COVERAGE_INVALID"
    if Counter(row["split"] for row in cases) != {"DEVELOPMENT": 45, "HOLDOUT": 15}:
        return False, "DATASET_SPLIT_INVALID"
    matrix = Counter((row["question_type"], row["semantic_class"], row["split"]) for row in cases)
    if len(matrix) != 30 or any(matrix[(qt, sc, split)] != expected
        for qt in ("translate_vi_zh", "translate_zh_vi", "sentence_writing")
        for sc in ("CLEAR_CORRECT", "CLEAR_INCORRECT", "PARTIAL", "AMBIGUOUS", "EXPECTED_UNCERTAIN")
        for split, expected in (("DEVELOPMENT", 3), ("HOLDOUT", 1))):
        return False, "DATASET_MATRIX_INVALID"
    execution_ids = [row.get("case_id") for row in executions]
    if len(execution_ids) != 60 or len(set(execution_ids)) != 60 or set(execution_ids) != set(ids):
        return False, "EXECUTION_CASE_COVERAGE_INVALID"
    case_by_id = {row["case_id"]: GradingCase.model_validate(row) for row in dataset_cases}
    try:
        for row in executions:
            case = case_by_id[row["case_id"]]
            if (row.get("run_id") != manifest.get("run_id") or row.get("provider_mode") != "REAL"
                or row.get("provider") != manifest.get("provider")
                or row.get("model") != manifest.get("model")
                or row.get("technical_status") not in {"SUCCESS", "TECHNICAL_FAILURE"}
                or (row.get("technical_status") == "SUCCESS"
                    and (not row.get("provider_response_sha256") or not row.get("parsed_result_sha256")))
                or not _case_request_matches("grading", case, row, manifest)):
                return False, "EXECUTION_REQUEST_BINDING_INVALID"
    except (ValueError, TypeError, KeyError):
        return False, "EXECUTION_REQUEST_BINDING_INVALID"
    if not _manifest_and_artifact_valid(manifest, cases_artifact, executions):
        return False, "ARTIFACT_IDENTITY_INVALID"
    annotation_ids = [item.get("case_id") for item in annotations]
    if len(annotation_ids) != 60 or len(set(annotation_ids)) != 60 or set(annotation_ids) != set(ids):
        return False, "ANNOTATION_CASE_COVERAGE_INVALID"
    try:
        for raw in annotations:
            item = GradingAnnotation.model_validate(raw)
            if (item.annotation_version != frozen_annotation_version
                    or item.rubric_version != frozen_rubric_version):
                return False, "ANNOTATION_VERSION_MISMATCH"
            if item.review_status != "HUMAN_APPROVED": return False, "HUMAN_APPROVAL_COVERAGE_INCOMPLETE"
            validate_human_annotation(item, case_by_id[item.case_id])
    except (ValueError, KeyError):
        return False, "ANNOTATION_CONTENT_INVALID"
    return True, "COMPLETE_TRACK_A_COVERAGE"


def generation_official_eligibility(*, manifest: dict, dataset_cases: list[dict],
                                    executions: list[dict], annotations: list[dict],
                                    expected_identity: dict, cases_artifact: bytes,
                                    dataset_files: dict[str, bytes]) -> tuple[bool, str]:
    """Prove exact D-109 question coverage from actual output/scope/artifact content."""
    from .contracts import GenerationCase, GenerationQuestionAnnotation
    from .generation import evaluate_generation_human_labels
    required_identity = {"dataset_version", "dataset_schema_version", "dataset_sha256", "provider", "model",
        "generation_config", "prompt_version", "prompt_sha256", "structured_schema_identity",
        "structured_schema_version", "evaluator_version", "annotation_version", "rubric_version",
        "scope_domain_validator_identity"}
    if not required_identity.issubset(expected_identity): return False, "EXPECTED_IDENTITY_INCOMPLETE"
    try:
        frozen_annotation_version, frozen_rubric_version = _annotation_contract("generation")
    except (OSError, ValueError, json.JSONDecodeError):
        return False, "ANNOTATION_CONTRACT_INVALID"
    if (expected_identity.get("annotation_version") != frozen_annotation_version
            or expected_identity.get("rubric_version") != frozen_rubric_version):
        return False, "ANNOTATION_CONTRACT_IDENTITY_MISMATCH"
    if not _production_identity_valid(expected_identity, track="generation"):
        return False, "FROZEN_PRODUCTION_IDENTITY_MISMATCH"
    if manifest.get("execution_mode") != "OFFICIAL_RUNTIME": return False, "OFFICIAL_RUNTIME_REQUIRED"
    if manifest.get("provider_mode") != "REAL": return False, "REAL_PROVIDER_REQUIRED"
    if not _identity_matches(manifest, expected_identity): return False, "PRODUCTION_IDENTITY_MISMATCH"
    if not _dataset_files_valid(dataset_cases, dataset_files, manifest): return False, "DATASET_ARTIFACT_INVALID"
    cases = [GenerationCase.model_validate(row) for row in dataset_cases]
    ids = [case.case_id for case in cases]
    if (len(ids) != 16 or len(set(ids)) != 16
            or any(case.dataset_version != "v0.1.0" for case in cases)
            or manifest.get("dataset_version") != "v0.1.0" or manifest.get("dataset_schema_version") != "1.0.0"):
        return False, "DATASET_CASE_COVERAGE_INVALID"
    if (Counter(case.split.value for case in cases) != {"DEVELOPMENT": 12, "HOLDOUT": 4}
            or sum(case.generation_kind == "LESSON_EXERCISE" for case in cases) != 8
            or sum(case.generation_kind == "PERIODIC_TEST" for case in cases) != 8
            or any(case.question_count != 3 for case in cases)
            or manifest.get("dataset_case_count") != 16 or manifest.get("development_case_count") != 12
            or manifest.get("holdout_case_count") != 4 or manifest.get("lesson_exercise_count") != 8
            or manifest.get("periodic_test_count") != 8 or manifest.get("question_count_per_case") != 3):
        return False, "DATASET_D108_CONTRACT_INVALID"
    supported = {kind for case in cases for kind in case.allowed_question_types}
    difficulties = {case.difficulty for case in cases}
    if (supported != {"multiple_choice", "fill_blank", "matching", "reorder_sentence",
                      "translate_vi_zh", "translate_zh_vi", "sentence_writing"}
            or difficulties != {"EASY", "MEDIUM", "HARD"}
            or manifest.get("production_supported_question_types") != sorted(supported)
            or manifest.get("difficulty_coverage") != ["EASY", "MEDIUM", "HARD"]):
        return False, "DATASET_COVERAGE_INVALID"
    execution_ids = [row.get("generation_case_id") for row in executions]
    if len(execution_ids) != 16 or len(set(execution_ids)) != 16 or set(execution_ids) != set(ids):
        return False, "EXECUTION_CASE_COVERAGE_INVALID"
    if not _manifest_and_artifact_valid(manifest, cases_artifact, executions):
        return False, "ARTIFACT_IDENTITY_INVALID"
    case_by_id = {case.case_id: case for case in cases}
    for row in executions:
        case = case_by_id[row["generation_case_id"]]
        if (row.get("provider_mode") != "REAL" or row.get("provider") != manifest.get("provider")
                or row.get("model") != manifest.get("model")
                or (row.get("technical_ok") and (not row.get("provider_response_sha256")
                                                    or not row.get("parsed_result_sha256")))
                or row.get("step77_run_id") != manifest.get("run_id")
                or row.get("technical_ok") not in {True, False}
                or not _case_request_matches("generation", case, row, manifest)):
            return False, "EXECUTION_REQUEST_BINDING_INVALID"
    expected_keys: set[tuple[str, int]] = set()
    by_case: dict[str, list[dict]] = {}
    for row in executions:
        case_id = row["generation_case_id"]
        questions = row.get("generated_questions") or []
        if row["technical_ok"]:
            if len(questions) != 3: return False, "GENERATED_QUESTION_COVERAGE_INVALID"
            for question in questions:
                expected_keys.add((case_id, question.get("question_index")))
        elif questions:
            return False, "FAILED_EXECUTION_HAS_GENERATED_QUESTIONS"
        by_case[case_id] = []
    actual_keys = []
    try:
        parsed = [GenerationQuestionAnnotation.model_validate(item) for item in annotations]
        for annotation in parsed:
            if (annotation.annotation_version != frozen_annotation_version
                    or annotation.rubric_version != frozen_rubric_version):
                return False, "ANNOTATION_VERSION_MISMATCH"
            key = (annotation.generation_case_id, annotation.question_index)
            actual_keys.append(key)
            if annotation.generation_case_id not in by_case:
                return False, "ANNOTATION_CASE_COVERAGE_INVALID"
            by_case[annotation.generation_case_id].append(annotation)
        if len(actual_keys) != len(set(actual_keys)) or set(actual_keys) != expected_keys:
            return False, "ANNOTATION_QUESTION_COVERAGE_INVALID"
        for case_id, items in by_case.items():
            if not items: continue
            if any(item.review_status != "HUMAN_APPROVED" for item in items):
                return False, "HUMAN_APPROVAL_COVERAGE_INCOMPLETE"
            row = next(row for row in executions if row["generation_case_id"] == case_id)
            evaluated = evaluate_generation_human_labels(row, items, run_id=manifest["run_id"],
                                                          cases_artifact=cases_artifact)
            if not evaluated.get("human_review_complete"):
                return False, "D109_BINDING_INVALID"
    except (ValueError, KeyError, TypeError):
        return False, "D109_BINDING_INVALID"
    return True, "COMPLETE_TRACK_B_D109_COVERAGE"


def official_eligibility(*, execution_mode: str, provider_mode: str,
                         production_identity_matches: bool, dataset_valid: bool,
                         artifact_identity_valid: bool, grading_human_approved_count: int,
                         generation_annotations_exact_bound: bool) -> tuple[bool, str]:
    """Deprecated coarse gate: booleans/counts cannot prove full case coverage."""
    return False, "EXPLICIT_TRACK_COVERAGE_REQUIRED"
