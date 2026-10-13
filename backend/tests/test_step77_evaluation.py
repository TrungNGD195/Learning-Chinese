from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4
import shutil

import pytest
from pydantic import TypeAdapter, ValidationError

from app.ai.generation.schemas import (AssessmentGenerationRequest, MaterializedGenerationScope,
    StructuredAssessmentGenerationOutput, StructuredAssessmentGenerationProviderResult)
from app.ai.generation.service import AssessmentGenerationService, validate_and_map_output
from app.ai.grading.schemas import (ProviderGradingStatus, StructuredGradingOutput,
    StructuredGradingProviderResult)
from app.core.config import Settings
from app.evaluation.step77.artifacts import build_manifest, canonical_json, write_artifact
from app.evaluation.step77.contracts import (GenerationCase, GenerationQuestionAnnotation,
    GradingAnnotation, GradingCase, NormalizedState)
from app.evaluation.step77.dataset import (GENERATION_ANNOTATIONS, GENERATION_DATASET,
    GRADING_ANNOTATIONS, GRADING_DATASET, _all, read_jsonl, validate_step77_datasets)
from app.evaluation.step77.db_fixture import (cleanup_curriculum_fixture,
    cleanup_generation_assessments, dedicated_test_database_available, seed_curriculum_fixture)
from app.evaluation.step77.eligibility import official_eligibility
from app.evaluation.step77.generation import (DeterministicGenerationProvider,
    atomicity_after_failure, build_generation_summary, classify_invalid_generation_output,
    evaluate_generation_human_labels, execute_generation_case, generation_request_identity)
from app.evaluation.step77.grading import (DeterministicGradingProvider,
    build_grading_summary, execute_grading_case, normalize_result)
from app.evaluation.step77.replay import ProviderReplayRecord, load_replay, write_replay


def _offline_settings():
    return Settings(_env_file=None, app_env="test", debug=False,
                    test_database_url="postgresql+psycopg://step77.invalid/chinese_learning_test",
                    secret_key="step77-offline-test-signing-key-not-a-secret")


def _workspace_temp_path(request, *, directory: bool = False) -> Path:
    path = Path.cwd() / f".step77-test-{uuid4().hex}"
    if directory:
        path.mkdir()
        request.addfinalizer(lambda: shutil.rmtree(path, ignore_errors=True))
    else:
        request.addfinalizer(lambda: path.unlink(missing_ok=True))
    return path


def _identity_generation_config(identity: dict) -> dict:
    keys = ("temperature", "max_output_tokens", "reasoning_effort", "model_input_limit",
            "request_timeout_seconds", "max_transient_retries")
    return {key: identity[key] for key in keys if key in identity}


def _make_real_origin_artifact(request, *, track, run_id, case_id, request_sha256,
                               response, provider, model, generation_config,
                               prompt_version, prompt_sha256, schema_identity,
                               schema_version, provider_mode="REAL", manifest_overrides=None):
    from app.evaluation.step77.artifacts import canonical_json, digest
    directory = _workspace_temp_path(request, directory=True)
    response_hash = digest(canonical_json(response))
    case_identity = "case_id" if track == "grading" else "generation_case_id"
    row = {case_identity: case_id, "run_id": run_id, "provider_mode": provider_mode,
        "provider": provider, "model": model, "request_sha256": request_sha256,
        "provider_response_sha256": response_hash,
        "parsed_result_sha256": digest(canonical_json(response.get("output", response)))}
    cases_bytes = canonical_json(row) + b"\n"
    manifest = {"run_id": run_id, "track": track, "execution_mode": "OFFICIAL_RUNTIME",
        "provider_mode": provider_mode, "provider": provider, "model": model,
        "generation_config": generation_config, "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha256, "structured_schema_identity": schema_identity,
        "structured_schema_version": schema_version, "cases_artifact_sha256": digest(cases_bytes)}
    manifest.update(manifest_overrides or {})
    manifest_path = directory / "manifest.json"
    manifest_path.write_bytes(canonical_json(manifest) + b"\n")
    (directory / "cases.jsonl").write_bytes(cases_bytes)
    return manifest_path, digest(manifest_path.read_bytes()), response_hash


def test_frozen_datasets_and_annotations_have_exact_d108_counts():
    result = validate_step77_datasets()
    assert result["grading"] == {"total": 60, "development": 45, "holdout": 15,
                                  "annotations_draft": 60, "human_approved": 0}
    assert result["assessment_generation"]["total"] == 16
    assert result["assessment_generation"]["development"] == 12
    assert result["assessment_generation"]["holdout"] == 4
    assert result["assessment_generation"]["lesson_exercise"] == 8
    assert result["assessment_generation"]["periodic_test"] == 8
    assert result["assessment_generation"]["annotations_draft"] == 48
    assert result["assessment_generation"]["human_approved"] == 0


@pytest.mark.parametrize(("status", "score", "maximum", "expected"), [
    ("UNCERTAIN", None, 2, NormalizedState.UNCERTAIN),
    ("GRADED", 0, 2, NormalizedState.ZERO_CREDIT),
    ("GRADED", 1, 2, NormalizedState.PARTIAL_CREDIT),
    ("GRADED", 2, 2, NormalizedState.FULL_CREDIT),
])
def test_d106_normalization(status, score, maximum, expected):
    correct = (score == maximum) if status == "GRADED" else None
    assert normalize_result(status, score, maximum, correct) == expected


@pytest.mark.parametrize(("status", "score", "correct"), [
    ("GRADED", None, None), ("GRADED", -1, False), ("GRADED", 3, True),
    ("UNCERTAIN", 0, None), ("GRADED", 1, True),
])
def test_d106_rejects_impossible_or_d095_inconsistent_results(status, score, correct):
    with pytest.raises(ValueError):
        normalize_result(status, score, 2, correct)


def test_approved_human_grading_annotation_uses_the_same_d106_normalizer():
    case = GradingCase.model_validate(_all(GRADING_DATASET)[0])
    from app.evaluation.step77.grading import validate_human_annotation
    annotation = GradingAnnotation(case_id=case.case_id, expected_grading_status="GRADED",
        human_score=1, human_is_correct=False, normalized_state=NormalizedState.PARTIAL_CREDIT,
        review_status="HUMAN_APPROVED")
    validate_human_annotation(annotation, case)
    with pytest.raises(ValueError, match="D095_CORRECTNESS_INCONSISTENT"):
        normalize_result("GRADED", 1, 2, True)


def test_track_a_executes_production_grading_service_without_semantic_class_in_request():
    case = GradingCase.model_validate(_all(GRADING_DATASET)[0])
    annotation = GradingAnnotation.model_validate(read_jsonl(GRADING_ANNOTATIONS / "annotations.jsonl")[0])
    provider = DeterministicGradingProvider("CLEAR_CORRECT")
    row = asyncio.run(execute_grading_case(case, annotation, _offline_settings(),
                                           run_id="offline-test-run", provider=provider))
    assert row["technical_status"] == "SUCCESS"
    assert row["normalized_state"] == "FULL_CREDIT"
    assert provider.last_request is not None
    assert provider.last_request.question_type == case.question_type
    assert case.semantic_class.value not in provider.last_request.user_content


def test_track_a_technical_failure_is_not_uncertain_and_has_null_semantic_fields():
    class BrokenProvider:
        last_error_code = "AI_GRADING_TIMEOUT"
        async def grade(self, request):
            from app.ai.grading.errors import StructuredGradingProviderError
            raise StructuredGradingProviderError(self.last_error_code)
    case = GradingCase.model_validate(_all(GRADING_DATASET)[0])
    annotation = GradingAnnotation(case_id=case.case_id)
    row = asyncio.run(execute_grading_case(case, annotation, _offline_settings(),
                                           run_id="offline-test-run", provider=BrokenProvider()))
    assert row["technical_status"] == "TECHNICAL_FAILURE"
    assert row["technical_error_code"] == "AI_GRADING_TIMEOUT"
    assert row["grading_status"] is None and row["score"] is None and row["normalized_state"] is None


@pytest.mark.parametrize("error_code", [
    "AI_GRADING_TIMEOUT", "AI_GRADING_AUTHENTICATION_FAILED", "AI_GRADING_PROVIDER_UNAVAILABLE",
    "AI_GRADING_INVALID_RESPONSE", "AI_GRADING_SCHEMA_INVALID", "AI_GRADING_INPUT_LIMIT_EXCEEDED",
    "AI_GRADING_REQUEST_INVALID", "AI_GRADING_CUSTOM_TYPED_FAILURE",
])
def test_track_a_observer_preserves_typed_provider_failures_across_production_boundary(error_code):
    from app.ai.grading.errors import StructuredGradingProviderError
    class TypedFailure:
        mode = "REAL"
        provider_name = "openai"
        async def grade(self, request):
            raise StructuredGradingProviderError(error_code)
    case = GradingCase.model_validate(_all(GRADING_DATASET)[0])
    row = asyncio.run(execute_grading_case(case, GradingAnnotation(case_id=case.case_id),
        _offline_settings(), run_id="observer-run", provider=TypedFailure(), provider_mode="REAL"))
    assert row["provider_mode"] == "REAL"
    assert row["technical_status"] == "TECHNICAL_FAILURE"
    assert row["technical_error_code"] == error_code
    assert row["provider_diagnostics"]["error_code"] == error_code
    assert row["grading_status"] is None and row["score"] is None
    assert row["is_correct"] is None and row["normalized_state"] is None
    assert row["feedback"] is None


def test_track_a_observer_classifies_malformed_structured_response_without_semantic_fallback():
    class MalformedProvider:
        provider_name="openai"
        async def grade(self, request): return {"not": "a structured provider result"}
    case=GradingCase.model_validate(_all(GRADING_DATASET)[0])
    row=asyncio.run(execute_grading_case(case,GradingAnnotation(case_id=case.case_id),_offline_settings(),
        run_id="malformed-provider",provider=MalformedProvider()))
    assert row["technical_status"]=="TECHNICAL_FAILURE"
    assert row["technical_error_code"]=="AI_GRADING_INVALID_RESPONSE"
    assert row["grading_status"] is None and row["normalized_state"] is None


def test_track_a_observer_retains_safe_failure_metadata_and_normal_semantics():
    from app.ai.grading.errors import StructuredGradingProviderError
    class ObservedFailure:
        provider_name = "openai"
        last_error_code = "AI_GRADING_TIMEOUT"
        async def grade(self, request):
            raise StructuredGradingProviderError(self.last_error_code)
    case = GradingCase.model_validate(_all(GRADING_DATASET)[0])
    failed = asyncio.run(execute_grading_case(case, GradingAnnotation(case_id=case.case_id),
        _offline_settings(), run_id="observer-metadata", provider=ObservedFailure()))
    assert failed["provider_diagnostics"]["provider"] == "openai"
    assert failed["provider_diagnostics"]["latency_ms"] >= 0
    assert "exception" not in failed["provider_diagnostics"]
    uncertain = asyncio.run(execute_grading_case(case, GradingAnnotation(case_id=case.case_id),
        _offline_settings(), run_id="observer-uncertain",
        provider=DeterministicGradingProvider("EXPECTED_UNCERTAIN")))
    assert uncertain["technical_status"] == "SUCCESS"
    assert uncertain["grading_status"] == "UNCERTAIN"
    assert uncertain["score"] is None and uncertain["is_correct"] is None


def test_real_mode_grading_observation_does_not_require_provider_mode_or_last_result():
    class ProductionProtocolOnly:
        provider_name = "openai"
        async def grade(self, request):
            return StructuredGradingProviderResult(output=StructuredGradingOutput(
                grading_status=ProviderGradingStatus.GRADED, score=2, feedback="ok"),
                provider="openai", model=request.model, input_tokens=None, output_tokens=None,
                total_tokens=None, provider_preflight_input_tokens=0, latency_ms=5,
                attempt_count=1, provider_request_id=None)

    case = GradingCase.model_validate(_all(GRADING_DATASET)[0])
    provider = ProductionProtocolOnly()
    assert not hasattr(provider, "mode") and not hasattr(provider, "last_result")
    row = asyncio.run(execute_grading_case(case, GradingAnnotation(case_id=case.case_id),
        _offline_settings(), run_id="real-mode-observer", provider=provider, provider_mode="REAL"))
    assert row["provider_mode"] == "REAL"
    assert row["technical_status"] == "SUCCESS"
    assert row["provider_request_id"] is None
    assert row["provider_diagnostics"]["usage"] == {
        "input_tokens": None, "output_tokens": None, "total_tokens": None}


def test_generation_observer_supports_provider_protocol_without_evaluation_attributes():
    from app.evaluation.step77.generation import ObservingGenerationProvider
    output = StructuredAssessmentGenerationOutput.model_validate({"questions": [{
        "type": "multiple_choice", "prompt": "question", "source_refs": ["ref"],
        "options": [{"option_text": "a", "is_correct": True},
                    {"option_text": "b", "is_correct": False}]}]})
    result = StructuredAssessmentGenerationProviderResult(output=output, provider="openai", model="model",
        input_tokens=None, output_tokens=None, total_tokens=None, provider_preflight_input_tokens=0,
        latency_ms=7, attempt_count=1, provider_request_id=None)

    class ProductionProtocolOnly:
        async def generate(self, request):
            return result

    provider = ProductionProtocolOnly()
    assert not hasattr(provider, "mode") and not hasattr(provider, "last_result")
    observer = ObservingGenerationProvider(provider, provider_mode="REAL")
    observed = asyncio.run(observer.generate(type("Request", (), {"model": "model"})()))
    assert observed is result and observer.provider_mode == "REAL"
    assert observer.last_result is result
    assert observer.safe_metadata["provider_request_id"] is None
    assert observer.safe_metadata["usage"] == {
        "input_tokens": None, "output_tokens": None, "total_tokens": None}


def test_d107_excludes_draft_and_counts_approved_semantics_only():
    rows = [
        {"annotation_review_status": "DRAFT", "technical_status": "SUCCESS", "grading_status": "GRADED",
         "normalized_state": "FULL_CREDIT", "agreement": None, "false_confident": None, "over_abstention": None,
         "question_type": "translate_vi_zh", "semantic_class": "CLEAR_CORRECT"},
        {"annotation_review_status": "HUMAN_APPROVED", "technical_status": "SUCCESS", "grading_status": "UNCERTAIN",
         "normalized_state": "UNCERTAIN", "human_normalized_state": "UNCERTAIN", "agreement": True,
         "false_confident": False, "over_abstention": False,
         "question_type": "sentence_writing", "semantic_class": "AMBIGUOUS"},
        {"annotation_review_status": "HUMAN_APPROVED", "technical_status": "TECHNICAL_FAILURE", "grading_status": None,
         "normalized_state": None, "agreement": None, "false_confident": None, "over_abstention": None,
         "question_type": "translate_zh_vi", "semantic_class": "PARTIAL"},
    ]
    summary = build_grading_summary(rows)
    assert summary["semantic_denominator_count"] == 1
    assert summary["agreement_count"] == 1 and summary["agreement_rate"] == 1
    assert summary["technical_failure_count"] == 1
    assert summary["launch_target_status"] == "OFFLINE_NOT_OFFICIAL"


def test_d107_false_confidence_and_over_abstention_follow_exact_transitions():
    rows = [
        {"annotation_review_status": "HUMAN_APPROVED", "technical_status": "SUCCESS", "grading_status": "UNCERTAIN",
         "normalized_state": "UNCERTAIN", "human_normalized_state": "FULL_CREDIT", "agreement": False,
         "false_confident": False, "over_abstention": True, "question_type": "translate_vi_zh", "semantic_class": "CLEAR_CORRECT"},
        {"annotation_review_status": "HUMAN_APPROVED", "technical_status": "SUCCESS", "grading_status": "GRADED",
         "normalized_state": "ZERO_CREDIT", "human_normalized_state": "UNCERTAIN", "agreement": False,
         "false_confident": True, "over_abstention": False, "question_type": "translate_zh_vi", "semantic_class": "EXPECTED_UNCERTAIN"},
        {"annotation_review_status": "HUMAN_APPROVED", "technical_status": "SUCCESS", "grading_status": "GRADED",
         "normalized_state": "FULL_CREDIT", "human_normalized_state": "PARTIAL_CREDIT", "agreement": False,
         "false_confident": True, "over_abstention": False, "question_type": "sentence_writing", "semantic_class": "PARTIAL"},
    ]
    summary = build_grading_summary(rows)
    assert summary["semantic_denominator_count"] == 3
    assert summary["false_confident_count"] == 2
    assert summary["over_abstention_count"] == 1
    assert summary["model_uncertainty_count"] == 1


def test_d107_zero_denominator_is_null_and_offline_not_official():
    summary = build_grading_summary([])
    assert summary["semantic_denominator_count"] == 0
    assert summary["agreement_rate"] is None
    assert summary["launch_target_status"] == "OFFLINE_NOT_OFFICIAL"


def test_replay_identity_is_canonical_and_stale_config_is_rejected(request):
    identity = {"track": "grading", "model": "frozen-model", "temperature": 0.2}
    parsed = {"grading_status": "GRADED", "score": 2, "feedback": "ok"}
    request_hash = hashlib.sha256(canonical_json(identity)).hexdigest()
    origin, origin_sha, _ = _make_real_origin_artifact(request, track="grading", run_id="real-run",
        case_id="case-replay", request_sha256=request_hash, response=parsed, provider="openai",
        model="frozen-model", generation_config={"temperature": 0.2}, prompt_version="v1",
        prompt_sha256="a"*64, schema_identity="grading/v1", schema_version="1.0.0")
    record = ProviderReplayRecord.from_real_output(track="grading", request_sha256=request_hash,
        parsed_result=parsed, response=parsed, provider="openai", model="frozen-model",
        generation_config={"temperature": 0.2}, prompt_identity="v1", schema_identity="grading/v1",
        prompt_sha256="a"*64, schema_version="1.0.0", normalized_input={"answer": {"text": "你好"}},
        origin_run_id="real-run", origin_track="grading", origin_provider_mode="REAL",
        origin_case_id="case-replay", origin_artifact_path=str(origin), origin_artifact_sha256=origin_sha)
    path = Path.cwd() / ".step77-replay-test.json"
    try:
        write_replay(path, record)
        assert load_replay(path, expected_identity=identity).origin_run_id == "real-run"
        with pytest.raises(ValueError, match="STALE_REQUEST_IDENTITY"):
            load_replay(path, expected_identity={**identity, "temperature": 0.3})
    finally:
        path.unlink(missing_ok=True)


def _replay_record_fixture(request, *, origin_mode="REAL", manifest_overrides=None):
    from app.evaluation.step77.artifacts import digest, file_sha256
    identity = {"track": "grading", "model": "frozen-model", "temperature": 0.2}
    request_sha = digest(canonical_json(identity))
    response = {"status": "completed", "output": {"grading_status": "GRADED", "score": 2, "feedback": "ok"}}
    parsed = response["output"]
    origin, origin_sha, _ = _make_real_origin_artifact(request, track="grading", run_id="origin-run",
        case_id="origin-case", request_sha256=request_sha, response=response, provider="openai",
        model="frozen-model", generation_config={"temperature": 0.2}, prompt_version="prompt-v1",
        prompt_sha256="a"*64, schema_identity="grading/v1", schema_version="1.0.0",
        provider_mode=origin_mode, manifest_overrides=manifest_overrides)
    record = ProviderReplayRecord.from_real_output(track="grading", request_sha256=request_sha,
        parsed_result=parsed, response=response, provider="openai", model="frozen-model",
        generation_config={"temperature": 0.2}, prompt_identity="prompt-v1", prompt_version="prompt-v1",
        prompt_sha256="a"*64, schema_identity="grading/v1", schema_version="1.0.0",
        normalized_input={"answer": "x"}, origin_run_id="origin-run", origin_track="grading",
        origin_provider_mode="REAL", origin_case_id="origin-case", origin_artifact_path=str(origin),
        origin_artifact_sha256=origin_sha)
    return record, origin


def test_replay_requires_verifiable_real_origin_and_fails_closed_on_missing_or_altered_artifact(request):
    from app.evaluation.step77.replay import verify_real_origin_artifact
    from app.evaluation.step77.artifacts import digest
    fake, _ = _replay_record_fixture(request, origin_mode="FAKE")
    with pytest.raises(ValueError, match="ORIGIN_PROVENANCE_INVALID"):
        verify_real_origin_artifact(fake)
    missing, origin = _replay_record_fixture(request)
    origin.unlink()
    with pytest.raises(ValueError, match="ORIGIN_PROVENANCE_INVALID"):
        verify_real_origin_artifact(missing)
    altered, origin = _replay_record_fixture(request)
    origin.write_bytes(origin.read_bytes() + b" ")
    with pytest.raises(ValueError, match="ORIGIN_PROVENANCE_INVALID"):
        verify_real_origin_artifact(altered)
    altered_result, _ = _replay_record_fixture(request)
    changed_parsed = {**altered_result.parsed_result, "feedback": "not the REAL-origin result"}
    changed_parsed_hash = digest(canonical_json(changed_parsed))
    altered_result = altered_result.model_copy(update={"parsed_result": changed_parsed,
        "parsed_result_sha256": changed_parsed_hash})
    with pytest.raises(ValueError, match="ORIGIN_PROVENANCE_INVALID"):
        verify_real_origin_artifact(altered_result)


@pytest.mark.parametrize("mutation", ["request", "response", "run", "track", "provider",
    "model", "config", "prompt", "schema"])
def test_replay_origin_identity_and_hash_mismatches_fail_closed(request, mutation):
    from app.evaluation.step77.replay import verify_real_origin_artifact
    from app.evaluation.step77.artifacts import digest
    overrides = {}
    if mutation == "run": overrides["run_id"] = "another-run"
    if mutation == "track": overrides["track"] = "assessment_generation"
    if mutation == "provider": overrides["provider"] = "other-provider"
    if mutation == "model": overrides["model"] = "other-model"
    if mutation == "config": overrides["generation_config"] = {"temperature": 0.8}
    if mutation == "prompt": overrides["prompt_version"] = "other-prompt"
    if mutation == "schema": overrides["structured_schema_identity"] = "other-schema"
    record, origin = _replay_record_fixture(request, manifest_overrides=overrides)
    if mutation in {"request", "response"}:
        data = json.loads(origin.read_text(encoding="utf-8"))
        cases_path = origin.with_name("cases.jsonl")
        row = json.loads(cases_path.read_text(encoding="utf-8"))
        row["request_sha256" if mutation == "request" else "provider_response_sha256"] = "f"*64
        cases_path.write_bytes(canonical_json(row) + b"\n")
        data["cases_artifact_sha256"] = digest(cases_path.read_bytes())
        origin.write_bytes(canonical_json(data) + b"\n")
        record = record.model_copy(update={"origin_artifact_sha256": digest(origin.read_bytes())})
    elif overrides:
        record = record.model_copy(update={"origin_artifact_sha256": digest(origin.read_bytes())})
    with pytest.raises(ValueError, match="ORIGIN_PROVENANCE_INVALID"):
        verify_real_origin_artifact(record)


def test_fake_offline_artifacts_are_never_eligible():
    manifest = build_manifest(run_id="r1", track="grading", execution_mode="OFFLINE_TEST",
        provider_mode="FAKE", provider="test-only", model="frozen-model", dataset_version="v0.1.0",
        dataset_case_count=60, development_case_count=45, holdout_case_count=15,
        generation_config={}, prompt_version="v1", schema_version="v1",
        annotation_version="a1", rubric_version="r1")
    artifact_dir = Path.cwd()
    case_file, manifest_file, summary_file = (artifact_dir / "cases.jsonl",
        artifact_dir / "manifest.json", artifact_dir / "summary.json")
    assert not any(path.exists() for path in (case_file, manifest_file, summary_file))
    try:
        result = write_artifact(artifact_dir, manifest=manifest, rows=[{"case_id": "c1"}], summary={})
        persisted_cases = case_file.read_bytes()
        assert result["cases_sha256"] == hashlib.sha256(persisted_cases).hexdigest()
        saved = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert saved["cases_artifact_sha256"] == hashlib.sha256(persisted_cases).hexdigest()
        assert saved["official_eligible"] is False and saved["runtime_api_calls"] == 0
        assert saved["human_approved_count"] == 0
    finally:
        case_file.unlink(missing_ok=True)
        manifest_file.unlink(missing_ok=True)
        summary_file.unlink(missing_ok=True)
    with pytest.raises(ValueError, match="CANNOT_BE_OFFICIAL"):
        build_manifest(run_id="r2", track="grading", execution_mode="OFFLINE_TEST",
            provider_mode="FAKE", provider="test-only", model="m", dataset_version="v0.1.0",
            dataset_case_count=60, development_case_count=45, holdout_case_count=15,
            generation_config={}, prompt_version="v1", schema_version="v1",
            annotation_version="a1", rubric_version="r1", extra={"official_eligible": True})
    with pytest.raises(ValueError, match="CROSS_RUN_IDENTITY_MISMATCH"):
        write_artifact(Path.cwd(), manifest=manifest, rows=[{"run_id": "other"}], summary={})


def _generation_case():
    return next(GenerationCase.model_validate(row) for row in _all(GENERATION_DATASET)
                if row["generation_kind"] == "LESSON_EXERCISE")


def test_generation_service_and_production_validator_accept_deterministic_fake_output():
    from app.evaluation.step77.contracts import GenerationCase
    case = _generation_case()
    request = TypeAdapter(AssessmentGenerationRequest).validate_python({
        "type": case.generation_kind, "lesson_id": case.lesson_id, "question_count": 3,
        "allowed_types": case.allowed_question_types, "difficulty": case.difficulty,
        "title": case.title, "description": case.description, "pass_threshold": case.pass_threshold})
    ref = "vocab:00000000-0000-0000-0000-000000000001"
    scope = MaterializedGenerationScope(assessment_type="LESSON_EXERCISE", lesson_id=UUID(case.lesson_id),
        lesson_ids=(UUID(case.lesson_id),), vocabulary_ids=(), grammar_ids=(), title="t", description=None,
        pass_threshold=90, payload={"scope": {}, "vocabulary": [], "grammar": []},
        allowed_source_refs=frozenset({ref}))
    provider = DeterministicGenerationProvider(["multiple_choice", "fill_blank", "matching"])
    result = asyncio.run(AssessmentGenerationService(provider, _offline_settings()).generate(request, scope))
    from app.exercise.service import admin_validate_generated_question
    mapped = validate_and_map_output(result, request=request, scope=scope, domain_validator=admin_validate_generated_question)
    assert len(mapped) == 3
    assert {item["type"] for item in mapped} == {"multiple_choice", "fill_blank", "matching"}


def test_all_seven_production_generation_types_pass_the_production_domain_validator():
    from app.exercise.service import admin_validate_generated_question
    case = _generation_case()
    request = TypeAdapter(AssessmentGenerationRequest).validate_python({
        "type": case.generation_kind, "lesson_id": case.lesson_id, "question_count": 3,
        "allowed_types": case.allowed_question_types, "difficulty": case.difficulty})
    ref = "vocab:00000000-0000-0000-0000-000000000001"
    scope = MaterializedGenerationScope("LESSON_EXERCISE", UUID(case.lesson_id), (UUID(case.lesson_id),),
        (), (), "t", None, 90, {"scope": {}, "vocabulary": [], "grammar": []}, frozenset({ref}))
    covered = set()
    for kind in case.allowed_question_types:
        provider = DeterministicGenerationProvider([kind])
        result = asyncio.run(AssessmentGenerationService(provider, _offline_settings()).generate(request, scope))
        mapped = validate_and_map_output(result, request=request, scope=scope,
            domain_validator=admin_validate_generated_question)
        assert len(mapped) == 3
        covered.update(item["type"] for item in mapped)
    assert covered == set(case.allowed_question_types)


def test_generation_fake_source_reference_must_be_in_materialized_scope():
    from app.evaluation.step77.contracts import GenerationCase
    case = _generation_case()
    request = TypeAdapter(AssessmentGenerationRequest).validate_python({
        "type": case.generation_kind, "lesson_id": case.lesson_id, "question_count": 3,
        "allowed_types": case.allowed_question_types, "difficulty": case.difficulty})
    ref = "vocab:00000000-0000-0000-0000-000000000001"
    scope = MaterializedGenerationScope("LESSON_EXERCISE", UUID(case.lesson_id), (UUID(case.lesson_id),),
        (), (), "t", None, 90, {"scope": {}, "vocabulary": [], "grammar": []}, frozenset({ref}))
    provider = DeterministicGenerationProvider(["multiple_choice", "fill_blank", "matching"])
    result = asyncio.run(AssessmentGenerationService(provider, _offline_settings()).generate(request, scope))
    bad = StructuredAssessmentGenerationOutput.model_validate({"questions": [
        {"type": "fill_blank", "prompt": "x", "source_refs": ["grammar:00000000-0000-0000-0000-000000000002"],
         "reference_answer": "x"}] * 3})
    altered = type(result)(output=bad, provider=result.provider, model=result.model, input_tokens=None,
        output_tokens=None, total_tokens=None, provider_preflight_input_tokens=0, latency_ms=0,
        attempt_count=1, provider_request_id=None)
    from app.ai.generation.errors import AssessmentGenerationInvalidOutput
    from app.exercise.service import admin_validate_generated_question
    with pytest.raises(AssessmentGenerationInvalidOutput):
        validate_and_map_output(altered, request=request, scope=scope, domain_validator=admin_validate_generated_question)


def test_generation_production_validator_rejects_disallowed_type_and_malformed_schema():
    from app.ai.generation.errors import AssessmentGenerationInvalidOutput
    from app.exercise.service import admin_validate_generated_question
    case = _generation_case()
    request = TypeAdapter(AssessmentGenerationRequest).validate_python({
        "type": case.generation_kind, "lesson_id": case.lesson_id, "question_count": 3,
        "allowed_types": ["multiple_choice"], "difficulty": case.difficulty})
    ref = "vocab:00000000-0000-0000-0000-000000000001"
    scope = MaterializedGenerationScope("LESSON_EXERCISE", UUID(case.lesson_id), (UUID(case.lesson_id),),
        (), (), "t", None, 90, {"scope": {}, "vocabulary": [], "grammar": []}, frozenset({ref}))
    class DisallowedOutputProvider:
        async def generate(self, provider_request):
            output = StructuredAssessmentGenerationOutput.model_validate({"questions": [
                {"type": "fill_blank", "prompt": "x", "source_refs": [ref],
                 "reference_answer": "x"}] * 3})
            return StructuredAssessmentGenerationProviderResult(output=output, provider="test-only",
                model=provider_request.model, input_tokens=None, output_tokens=None, total_tokens=None,
                provider_preflight_input_tokens=0, latency_ms=0, attempt_count=1, provider_request_id=None)
    result = asyncio.run(AssessmentGenerationService(DisallowedOutputProvider(), _offline_settings()).generate(request, scope))
    with pytest.raises(AssessmentGenerationInvalidOutput):
        validate_and_map_output(result, request=request, scope=scope, domain_validator=admin_validate_generated_question)
    with pytest.raises(ValueError):
        StructuredAssessmentGenerationOutput.model_validate({"questions": [
            {"type": "multiple_choice", "prompt": "bad", "source_refs": [ref],
             "options": [{"option_text": "A", "is_correct": False}]}]})


def test_generation_case_rejects_question_count_other_than_three():
    row = dict(_all(GENERATION_DATASET)[0])
    row["question_count"] = 2
    with pytest.raises(ValueError, match="frozen generation settings"):
        GenerationCase.model_validate(row)


def test_invalid_generation_output_critical_mapping_is_deterministic():
    request = _trackb_generation_request(question_count=3, allowed_types=["multiple_choice"])
    output = _structured_output([_valid_fill_blank("vocab:outside")])
    result = _provider_result(output)
    classification = classify_invalid_generation_output(result, request, _generation_scope(),
        domain_validator=_domain_validator())
    assert classification == {
        "schema_valid": True,
        "requested_count_valid": False,
        "supported_question_types_valid": False,
        "source_refs_valid": False,
        "scope_adherent": False,
        "domain_validation_valid": None,
        "critical_failures": ["OUT_OF_SCOPE_GENERATION", "UNSUPPORTED_QUESTION_TYPE"],
    }


def _trackb_generation_request(*, question_count=3, allowed_types=None, generation_type="LESSON_EXERCISE"):
    body = {"type": generation_type, "question_count": question_count,
        "allowed_types": allowed_types or ["fill_blank"], "difficulty": "EASY"}
    if generation_type == "LESSON_EXERCISE":
        body["lesson_id"] = "00000000-0000-0000-0000-000000000010"
    else:
        body.update(lesson_ids=["00000000-0000-0000-0000-000000000010"],
                    vocabulary_ids=["00000000-0000-0000-0000-000000000011"], grammar_ids=[])
    return TypeAdapter(AssessmentGenerationRequest).validate_python(body)


def _generation_scope():
    from app.ai.generation.schemas import MaterializedGenerationScope
    lesson_id = UUID("00000000-0000-0000-0000-000000000010")
    return MaterializedGenerationScope("LESSON_EXERCISE", lesson_id, (lesson_id,), (), (),
        "Fixture lesson", None, 90, {}, frozenset({"vocab:allowed"}))


def _valid_fill_blank(source_ref="vocab:allowed"):
    return {"type": "fill_blank", "prompt": "Complete the word.", "source_refs": [source_ref],
            "reference_answer": "你好", "accepted_answers": []}


def _structured_output(questions):
    return StructuredAssessmentGenerationOutput.model_validate({"questions": questions})


def _provider_result(output):
    return StructuredAssessmentGenerationProviderResult(output=output, provider="test-only", model="offline",
        input_tokens=None, output_tokens=None, total_tokens=None, provider_preflight_input_tokens=0,
        latency_ms=0, attempt_count=1, provider_request_id=None)


def _domain_validator():
    from app.exercise.service import admin_validate_generated_question
    return admin_validate_generated_question


def test_trackb_real_production_request_valid_output_uses_question_count():
    request = _trackb_generation_request(question_count=3)
    assert type(request).__name__ == "LessonExerciseGenerationRequest"
    classification = classify_invalid_generation_output(
        _provider_result(_structured_output([_valid_fill_blank() for _ in range(3)])),
        request, _generation_scope(), domain_validator=_domain_validator())
    assert request.question_count == 3
    assert classification["schema_valid"] is True
    assert classification["requested_count_valid"] is True
    assert classification["critical_failures"] == []


def test_trackb_periodic_test_uses_real_production_request_contract():
    request = _trackb_generation_request(question_count=3, generation_type="PERIODIC_TEST")
    assert type(request).__name__ == "PeriodicTestGenerationRequest"
    assert request.question_count == 3
    assert request.lesson_ids and request.vocabulary_ids


def test_trackb_count_mismatch_is_not_a_schema_failure():
    request = _trackb_generation_request(question_count=3)
    classification = classify_invalid_generation_output(
        _provider_result(_structured_output([_valid_fill_blank() for _ in range(2)])),
        request, _generation_scope(), domain_validator=_domain_validator())
    assert classification["schema_valid"] is True
    assert classification["requested_count_valid"] is False
    assert "SCHEMA_INVALID" not in classification["critical_failures"]
    assert classification["critical_failures"] == []


def test_trackb_count_mismatch_remains_deterministic_failure_without_new_critical_enum():
    row = {"technical_ok": True, "critical_failures": [],
        "generation_case_status": "DETERMINISTIC_FAILURE", "generation_case_pass": False,
        "requested_count_valid": False, "persisted_question_count": 0}
    result = evaluate_generation_human_labels(row, [], run_id="offline")
    assert result["generation_case_status"] == "DETERMINISTIC_FAILURE"
    assert result["generation_case_pass"] is False
    assert result["critical_failures"] == []


def test_trackb_structural_schema_failure_is_schema_invalid():
    request = _trackb_generation_request(question_count=3)
    malformed_provider_payload = {"questions": [{"type": "fill_blank", "prompt": "missing required fields"}]}
    with pytest.raises(ValidationError):
        TypeAdapter(StructuredAssessmentGenerationOutput).validate_python(malformed_provider_payload)
    classification = classify_invalid_generation_output(None, request, _generation_scope())
    assert classification["schema_valid"] is False
    assert classification["critical_failures"] == ["SCHEMA_INVALID"]


def test_trackb_disallowed_question_type_is_not_schema_invalid():
    request = _trackb_generation_request(question_count=3, allowed_types=["multiple_choice"])
    classification = classify_invalid_generation_output(
        _provider_result(_structured_output([_valid_fill_blank() for _ in range(3)])),
        request, _generation_scope(), domain_validator=_domain_validator())
    assert classification["schema_valid"] is True
    assert classification["supported_question_types_valid"] is False
    assert "UNSUPPORTED_QUESTION_TYPE" in classification["critical_failures"]
    assert "SCHEMA_INVALID" not in classification["critical_failures"]


def test_trackb_out_of_scope_source_is_not_schema_invalid():
    request = _trackb_generation_request(question_count=3)
    classification = classify_invalid_generation_output(
        _provider_result(_structured_output([_valid_fill_blank("vocab:not-selected") for _ in range(3)])),
        request, _generation_scope(), domain_validator=_domain_validator())
    assert classification["schema_valid"] is True
    assert classification["scope_adherent"] is False
    assert classification["source_refs_valid"] is False
    assert "OUT_OF_SCOPE_GENERATION" in classification["critical_failures"]
    assert "SCHEMA_INVALID" not in classification["critical_failures"]


def test_trackb_production_domain_failure_keeps_structural_schema_valid():
    request = _trackb_generation_request(question_count=3, allowed_types=["matching"])
    invalid_matching = {"type": "matching", "prompt": "Match items.", "source_refs": ["vocab:allowed"],
        "left_items": [{"id": "l1", "text": "A"}, {"id": "l2", "text": "B"}],
        "right_items": [{"id": "r1", "text": "One"}, {"id": "r2", "text": "Two"}],
        "correct_pairs": [{"left_id": "l1", "right_id": "r1"}, {"left_id": "l1", "right_id": "r2"}]}
    classification = classify_invalid_generation_output(
        _provider_result(_structured_output([invalid_matching for _ in range(3)])),
        request, _generation_scope(), domain_validator=_domain_validator())
    assert classification["schema_valid"] is True
    assert classification["domain_validation_valid"] is False
    assert "SCHEMA_INVALID" not in classification["critical_failures"]


def test_generation_request_identity_changes_with_case_or_model_settings():
    case = _generation_case()
    settings = _offline_settings()
    first, first_hash = generation_request_identity(case, settings)
    changed, changed_hash = generation_request_identity(case.model_copy(update={"difficulty": "HARD"}), settings)
    assert first_hash != changed_hash
    assert first["model"] == changed["model"]
    _, model_changed_hash = generation_request_identity(case, settings.model_copy(update={"llm_model": "changed-model"}))
    assert model_changed_hash != first_hash


def test_generation_scope_and_lifecycle_checks_are_explicit():
    from app.evaluation.step77.generation import draft_lifecycle_valid
    assert draft_lifecycle_valid("DRAFT") is True
    assert draft_lifecycle_valid("PUBLISHED") is False
    assert draft_lifecycle_valid("DRAFT", "published timestamp") is False
    assert atomicity_after_failure({"before"}, {"before"}) is True
    assert atomicity_after_failure({"before"}, {"before", "partial"}) is False


def test_persisted_generation_draft_normalizes_uuid_identities_before_hashing():
    from app.evaluation.step77.generation import normalize_persisted_draft

    assessment_id = UUID("f9ba6c99-261f-47e9-a9fa-cb024f104708")
    lesson_id = UUID("782d6c80-cfc3-4dd7-8ae9-4ab40d5dc67b")
    question_id = UUID("4685089c-444a-47ed-91d8-40b1dd657ed0")
    option_id = UUID("10857475-27e3-4fca-82d5-3f700f4a8699")
    persisted_draft = {
        "assessment": {"id": assessment_id, "lesson_id": lesson_id, "status": "DRAFT"},
        "questions": [{"id": question_id, "assessment_id": assessment_id,
            "points": 1.0, "options": [{"id": option_id, "question_id": question_id,
                "is_correct": True}]}],
    }

    normalized = normalize_persisted_draft(persisted_draft)
    assert normalized == {
        "assessment": {"id": str(assessment_id), "lesson_id": str(lesson_id), "status": "DRAFT"},
        "questions": [{"id": str(question_id), "assessment_id": str(assessment_id),
            "points": 1.0, "options": [{"id": str(option_id), "question_id": str(question_id),
                "is_correct": True}]}],
    }
    serialized = canonical_json(normalized)
    first_hash = hashlib.sha256(serialized).hexdigest()
    assert json.loads(serialized) == normalized
    assert hashlib.sha256(canonical_json(normalized)).hexdigest() == first_hash

    arbitrary = object()
    assert normalize_persisted_draft(arbitrary) is arbitrary
    with pytest.raises(TypeError):
        canonical_json(normalize_persisted_draft(arbitrary))


def test_generation_annotation_templates_are_unbound_and_draft():
    rows = read_jsonl(GENERATION_ANNOTATIONS / "questions.jsonl")
    assert len(rows) == 48
    assert all(row["review_status"] == "DRAFT" and row["step77_run_id"] is None
               and row["generated_question_sha256"] is None for row in rows)
    with pytest.raises(ValueError, match="exact output bindings"):
        GenerationQuestionAnnotation(generation_case_id="c", question_index=1,
            answer_reference_consistency="CONSISTENT", answerability="ANSWERABLE",
            review_status="HUMAN_APPROVED")


def test_generation_human_binding_rejects_stale_identity_and_defers_draft():
    row = {"technical_ok": True, "critical_failures": [], "persisted_question_count": 1,
        "generated_questions": [{"question_index": 1, "persisted_question_id": "q1", "question_sha256": "b"*64}],
        "generation_case_id": "case1", "execution_id": "exec1", "generated_draft_sha256": "a"*64,
        "materialized_scope_sha256": "c"*64, "generated_output_sha256": "d"*64,
        "human_review_complete": False, "generation_case_status": "DEFERRED_HUMAN_REVIEW",
        "generation_case_pass": None}
    draft = GenerationQuestionAnnotation(generation_case_id="case1", question_index=1)
    deferred = evaluate_generation_human_labels(row, [draft], run_id="run1")
    assert deferred["generation_case_pass"] is None
    bad = GenerationQuestionAnnotation(step77_run_id="wrong", generation_case_id="case1",
        execution_id="exec1", question_index=1, persisted_question_id="q1", generated_draft_sha256="a"*64,
        generated_question_sha256="b"*64, materialized_scope_sha256="c"*64,
        generation_output_sha256="d"*64, cases_artifact_sha256="e"*64,
        answer_reference_consistency="CONSISTENT", answerability="ANSWERABLE", review_status="HUMAN_APPROVED")
    with pytest.raises(ValueError, match="ARTIFACT_REQUIRED"):
        evaluate_generation_human_labels(row, [bad], run_id="run1")


def _bound_generation_review_fixture():
    from app.evaluation.step77.artifacts import canonical_json
    from app.evaluation.step77.generation import _recomputed_d109_bindings
    row = {"execution_id": "exec1", "step77_run_id": "run1", "generation_case_id": "case1",
        "split": "DEVELOPMENT", "generation_kind": "LESSON_EXERCISE", "difficulty": "EASY",
        "provider_mode": "FAKE", "request_sha256": "a" * 64,
        "materialized_scope_sha256": "", "provider_response_sha256": "", "generated_output_sha256": "",
        "generated_draft_sha256": "", "persisted_assessment_id": "assessment1",
        "persisted_assessment_status": "DRAFT", "persisted_question_count": 1,
        "technical_ok": True, "critical_failures": [],
        "generated_questions": [{"question_index": 1, "persisted_question_id": "q1",
            "question_type": "multiple_choice", "question_content": {"type": "multiple_choice", "prompt": "Q"},
            "question_sha256": ""}], "generation_case_id": "case1", "execution_id": "exec1",
        "source_refs_valid": True, "requested_count_valid": True, "draft_lifecycle_valid": True,
        "atomic_persistence_valid": True, "usage": None, "provider_request_id": None,
        "materialized_scope_content": {"lesson_ids": ["lesson1"]},
        "generated_draft_content": {"assessment": {"id": "assessment1"}, "questions": [{"id": "q1"}]},
        "generated_output_content": {"questions": [{"type": "multiple_choice"}]},
        "human_annotation_status": "DRAFT", "human_annotation_statuses": ["DRAFT"],
        "human_review_complete": False, "generation_case_status": "DEFERRED_HUMAN_REVIEW",
        "generation_case_pass": None}
    row["generated_questions"][0]["question_sha256"] = hashlib.sha256(
        canonical_json(row["generated_questions"][0]["question_content"])).hexdigest()
    row["generated_draft_sha256"] = hashlib.sha256(canonical_json(row["generated_draft_content"])).hexdigest()
    row["generated_output_sha256"] = hashlib.sha256(canonical_json(row["generated_output_content"])).hexdigest()
    row["materialized_scope_sha256"] = hashlib.sha256(canonical_json(row["materialized_scope_content"])).hexdigest()
    from app.evaluation.step77.artifacts import canonical_json
    artifact = canonical_json(row) + b"\n"
    hashes = _recomputed_d109_bindings(row, artifact)
    kwargs = dict(step77_run_id="run1", generation_case_id="case1", execution_id="exec1",
        question_index=1, persisted_question_id="q1", generated_draft_sha256=hashes[1],
        generated_question_sha256=hashes[0][1], materialized_scope_sha256=hashes[3],
        generation_output_sha256=hashes[2], cases_artifact_sha256=hashes[4],
        answer_reference_consistency="CONSISTENT", answerability="ANSWERABLE", review_status="HUMAN_APPROVED")
    return row, artifact, kwargs


def test_generation_d109_recomputed_binding_passes_and_semantic_fail_paths():
    row, artifact, kwargs = _bound_generation_review_fixture()
    passed = evaluate_generation_human_labels(row, [GenerationQuestionAnnotation(**kwargs)],
        run_id="run1", cases_artifact=artifact)
    assert passed["generation_case_status"] == "PASS" and passed["generation_case_pass"] is True
    failed = evaluate_generation_human_labels(row, [GenerationQuestionAnnotation(
        **{**kwargs, "answerability": "UNANSWERABLE"})], run_id="run1", cases_artifact=artifact)
    assert failed["generation_case_pass"] is False
    assert "UNANSWERABLE_QUESTION" in failed["critical_failures"]


def test_generation_d109_uses_current_execute_generation_case_content_projection():
    row, artifact, kwargs = _bound_generation_review_fixture()
    result = evaluate_generation_human_labels(row, [GenerationQuestionAnnotation(**kwargs)],
        run_id="run1", cases_artifact=artifact)
    assert result["generation_case_status"] == "PASS"


def test_generation_d109_review_status_enrichment_does_not_change_frozen_content_binding():
    from app.evaluation.step77.artifacts import canonical_json
    row, _, kwargs = _bound_generation_review_fixture()
    row["human_annotation_statuses"] = ["HUMAN_APPROVED"]
    artifact = canonical_json(row) + b"\n"
    kwargs["cases_artifact_sha256"] = hashlib.sha256(artifact).hexdigest()
    result = evaluate_generation_human_labels(row, [GenerationQuestionAnnotation(**kwargs)],
        run_id="run1", cases_artifact=artifact)
    assert result["generation_case_pass"] is True


@pytest.mark.parametrize("field", ["question_content", "generated_draft_content",
    "generated_output_content", "materialized_scope_content"])
def test_generation_d109_actual_frozen_content_mutation_invalidates_annotation(field):
    from app.evaluation.step77.artifacts import canonical_json
    row, _, kwargs = _bound_generation_review_fixture()
    if field == "question_content":
        row["generated_questions"][0][field]["prompt"] = "changed generated question"
    else:
        row[field]["changed"] = True
    row["generated_questions"][0]["question_sha256"] = hashlib.sha256(
        canonical_json(row["generated_questions"][0]["question_content"])).hexdigest()
    row["generated_draft_sha256"] = hashlib.sha256(canonical_json(row["generated_draft_content"])).hexdigest()
    row["generated_output_sha256"] = hashlib.sha256(canonical_json(row["generated_output_content"])).hexdigest()
    row["materialized_scope_sha256"] = hashlib.sha256(canonical_json(row["materialized_scope_content"])).hexdigest()
    with pytest.raises(ValueError, match="STALE_OR_WRONGLY_BOUND"):
        evaluate_generation_human_labels(row, [GenerationQuestionAnnotation(**kwargs)],
            run_id="run1", cases_artifact=canonical_json(row) + b"\n")


@pytest.mark.parametrize("field", ["question_content", "generated_draft_content",
    "materialized_scope_content", "generated_output_content"])
def test_generation_d109_content_change_after_annotation_fails_closed(field):
    from app.evaluation.step77.artifacts import canonical_json
    row, original_artifact, kwargs = _bound_generation_review_fixture()
    if field == "question_content":
        row["generated_questions"][0][field]["prompt"] = "changed"
    else:
        row[field]["changed"] = True
    row["generated_questions"][0]["question_sha256"] = hashlib.sha256(
        canonical_json(row["generated_questions"][0]["question_content"])).hexdigest()
    row["generated_draft_sha256"] = hashlib.sha256(canonical_json(row["generated_draft_content"])).hexdigest()
    row["generated_output_sha256"] = hashlib.sha256(canonical_json(row["generated_output_content"])).hexdigest()
    row["materialized_scope_sha256"] = hashlib.sha256(canonical_json(row["materialized_scope_content"])).hexdigest()
    changed_artifact = canonical_json(row) + b"\n"
    with pytest.raises(ValueError, match="STALE_OR_WRONGLY_BOUND|ARTIFACT_CONTENT_MISMATCH"):
        evaluate_generation_human_labels(row, [GenerationQuestionAnnotation(**kwargs)],
            run_id="run1", cases_artifact=changed_artifact)


def test_generation_d109_output_artifact_change_and_copied_fake_hash_fail_closed():
    from app.evaluation.step77.artifacts import canonical_json
    row, artifact, kwargs = _bound_generation_review_fixture()
    changed_artifact = artifact + canonical_json({"unrelated": "changed cases artifact"}) + b"\n"
    with pytest.raises(ValueError, match="STALE_OR_WRONGLY_BOUND|ARTIFACT_CONTENT_MISMATCH"):
        evaluate_generation_human_labels(row, [GenerationQuestionAnnotation(**kwargs)],
            run_id="run1", cases_artifact=changed_artifact)
    forged = dict(row)
    forged["generated_draft_content"] = {"different": "actual content"}
    copied = GenerationQuestionAnnotation(**kwargs)
    with pytest.raises(ValueError, match="CONTENT_MISMATCH"):
        evaluate_generation_human_labels(forged, [copied], run_id="run1", cases_artifact=artifact)


@pytest.mark.parametrize("byte_change", ["whitespace", "newline", "key_order"])
def test_generation_d109_binds_exact_persisted_cases_artifact_bytes(byte_change):
    from app.evaluation.step77.artifacts import canonical_json
    row, artifact, kwargs = _bound_generation_review_fixture()
    if byte_change == "whitespace":
        changed = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(", ", ": ")).encode("utf-8") + b"\n"
    elif byte_change == "newline":
        changed = artifact.rstrip(b"\n")
    else:
        changed = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    assert json.loads(changed) == row
    with pytest.raises(ValueError, match="STALE_OR_WRONGLY_BOUND"):
        evaluate_generation_human_labels(row, [GenerationQuestionAnnotation(**kwargs)],
            run_id="run1", cases_artifact=changed)


def test_generation_d109_actual_byte_hash_and_content_projection_are_separate():
    from app.evaluation.step77.artifacts import canonical_json, digest
    from app.evaluation.step77.generation import _projected_cases_artifact, _recomputed_d109_bindings
    row, artifact, kwargs = _bound_generation_review_fixture()
    hashes = _recomputed_d109_bindings(row, artifact)
    assert hashes[4] == digest(artifact)
    assert hashes[4] != digest(_projected_cases_artifact([row]))
    # A source DRAFT remains valid before it has any run/artifact binding.
    draft = GenerationQuestionAnnotation(generation_case_id="case1", question_index=1,
        review_status="DRAFT")
    assert evaluate_generation_human_labels(row, [draft], run_id="run1")["human_review_complete"] is False


def test_generation_summary_excludes_deferred_cases_from_boolean_pass_denominator():
    rows = [{"split": "DEVELOPMENT", "generation_kind": "LESSON_EXERCISE", "difficulty": "EASY",
             "generation_questions": [], "generated_questions": [], "technical_ok": True,
             "critical_failures": [], "human_annotation_status": "DRAFT", "human_review_complete": False,
             "generation_case_status": "DEFERRED_HUMAN_REVIEW", "generation_case_pass": None},
            {"split": "HOLDOUT", "generation_kind": "PERIODIC_TEST", "difficulty": "HARD",
             "generation_questions": [], "generated_questions": [], "technical_ok": True,
             "critical_failures": ["SCHEMA_INVALID"], "human_annotation_status": "DRAFT", "human_review_complete": False,
             "generation_case_status": "DETERMINISTIC_FAILURE", "generation_case_pass": False}]
    summary = build_generation_summary(rows)
    assert summary["generation_case_pass_rate"] == 0
    assert summary["deferred_human_review_case_count"] == 1


def test_official_eligibility_is_fail_closed_for_offline_fake():
    assert official_eligibility(execution_mode="OFFLINE_TEST", provider_mode="FAKE",
        production_identity_matches=True, dataset_valid=True, artifact_identity_valid=True,
        grading_human_approved_count=0, generation_annotations_exact_bound=False)[0] is False


def _track_a_official_fixture(approved_count=60):
    from app.evaluation.step77.artifacts import digest, file_sha256
    from app.evaluation.step77.eligibility import grading_official_eligibility
    cases = _all(GRADING_DATASET)
    dataset_files={name:(GRADING_DATASET/name).read_bytes() for name in ("manifest.json","development.jsonl","holdout.jsonl")}
    dataset_sha=digest(canonical_json({name:digest(data) for name,data in dataset_files.items()}))
    expected = {"dataset_version":"v0.1.0","dataset_schema_version":"1.0.0","dataset_sha256":dataset_sha,
        "provider": "openai", "model": "gpt-5.4-mini-2026-03-17", "generation_config": {
            "temperature": 0.2, "max_output_tokens": 800, "reasoning_effort": "none",
            "model_input_limit": 400000, "request_timeout_seconds": 60.0, "max_transient_retries": 1},
        "prompt_version": "v1", "prompt_sha256": file_sha256(Path(__file__).parents[1] / "app/ai/grading/prompt.py"),
        "structured_schema_identity": "app.ai.grading.schemas.StructuredGradingOutput/v1", "structured_schema_version": "1.0.0",
        "evaluator_version":"step77-offline/v1","agreement_policy_identity":{"primary_unit":"D-106/v1","denominator":"D-107/v1"},
        "annotation_version":"ai-grading-human/v0.1.0","rubric_version":"ai-grading-rubric/v1"}
    from app.evaluation.step77.eligibility import _settings_for_identity
    from app.evaluation.step77.contracts import GradingCase
    from app.evaluation.step77.grading import grading_request_identity
    settings = _settings_for_identity(expected, track="grading")
    executions = [{"case_id": case["case_id"], "provider_mode": "REAL", "provider": "openai",
        "model": expected["model"], "provider_request_id": f"req-{index}",
        "request_sha256": grading_request_identity(GradingCase.model_validate(case), settings)[1],
        "split": case["split"], "question_type": case["question_type"],
        "semantic_class": case["semantic_class"], "max_points": case["max_points"],
        "production_input_metadata": case["production_input_metadata"],
        "provider_response_sha256": f"{index+101:064x}", "parsed_result_sha256": f"{index+201:064x}",
        "technical_status": "SUCCESS"}
        for index, case in enumerate(cases)]
    annotations = []
    for index, case in enumerate(cases):
        approved = index < approved_count
        annotations.append({"case_id": case["case_id"],
            "annotation_version": "ai-grading-human/v0.1.0", "rubric_version": "ai-grading-rubric/v1",
            "expected_grading_status": "GRADED" if approved else None,
            "human_score": case["max_points"] if approved else None,
            "human_is_correct": True if approved else None,
            "normalized_state": "FULL_CREDIT" if approved else None,
            "review_status": "HUMAN_APPROVED" if approved else "DRAFT"})
    run_id="official-track-a"
    for row in executions: row["run_id"]=run_id
    artifact=b"".join(canonical_json(row)+b"\n" for row in executions)
    manifest={"run_id":run_id,"track":"grading","execution_mode":"OFFICIAL_RUNTIME","provider_mode":"REAL",
        "dataset_case_count":60,"development_case_count":45,"holdout_case_count":15,
        **expected,"cases_artifact_sha256":digest(artifact)}
    result=grading_official_eligibility(manifest=manifest,dataset_cases=cases,executions=executions,
        annotations=annotations,expected_identity=expected,cases_artifact=artifact,dataset_files=dataset_files)
    return result,(manifest,cases,executions,annotations,expected,artifact,dataset_files)


def test_track_a_official_eligibility_requires_exact_complete_60_case_coverage():
    from app.evaluation.step77.eligibility import grading_official_eligibility
    result, _ = _track_a_official_fixture()
    assert result == (True, "COMPLETE_TRACK_A_COVERAGE")
    for approvals in (0, 1, 59):
        assert _track_a_official_fixture(approvals)[0][0] is False


@pytest.mark.parametrize("mutation", ["wrong_request", "other_case_request", "question_type",
    "max_points", "production_input", "annotation_version", "rubric_version", "both_versions"])
def test_track_a_official_eligibility_recomputes_request_and_annotation_identity(mutation):
    from app.evaluation.step77.eligibility import grading_official_eligibility
    from app.evaluation.step77.artifacts import digest, file_sha256
    _,(manifest,cases,executions,annotations,expected,_,dataset_files)=_track_a_official_fixture()
    executions=[dict(row) for row in executions]; annotations=[dict(row) for row in annotations]
    if mutation == "wrong_request": executions[0]["request_sha256"]="f"*64
    elif mutation == "other_case_request": executions[0]["request_sha256"]=executions[-1]["request_sha256"]
    elif mutation == "question_type": executions[0]["question_type"]="sentence_writing"
    elif mutation == "max_points": executions[0]["max_points"]+=1
    elif mutation == "production_input": executions[0]["production_input_metadata"]={"answer_shape":{"text":"other"}}
    elif mutation == "annotation_version": annotations[0]["annotation_version"]="stale"
    elif mutation == "rubric_version": annotations[0]["rubric_version"]="stale"
    else:
        annotations[0]["annotation_version"]="stale"; annotations[0]["rubric_version"]="stale"
    artifact=b"".join(canonical_json(row)+b"\n" for row in executions)
    manifest={**manifest,"cases_artifact_sha256":digest(artifact)}
    result=grading_official_eligibility(manifest=manifest,dataset_cases=cases,executions=executions,
        annotations=annotations,expected_identity=expected,cases_artifact=artifact,dataset_files=dataset_files)
    assert result[0] is False, mutation


@pytest.mark.parametrize("request_id", ["req-present", None])
def test_track_a_official_eligibility_provider_request_id_is_optional(request_id):
    from app.evaluation.step77.eligibility import grading_official_eligibility
    from app.evaluation.step77.artifacts import digest
    _, (manifest,cases,executions,annotations,expected,_,dataset_files)=_track_a_official_fixture()
    executions=[dict(row, provider_request_id=request_id) for row in executions]
    artifact=b"".join(canonical_json(row)+b"\n" for row in executions)
    manifest={**manifest,"cases_artifact_sha256":digest(artifact)}
    assert grading_official_eligibility(manifest=manifest,dataset_cases=cases,executions=executions,
        annotations=annotations,expected_identity=expected,cases_artifact=artifact,
        dataset_files=dataset_files)==(True,"COMPLETE_TRACK_A_COVERAGE")


@pytest.mark.parametrize("mutation", ["missing_dataset_case", "missing_execution", "duplicate_execution",
    "duplicate_annotation", "extra_annotation",
    "fake_provider", "offline", "bad_artifact_hash", "invalid_real_provenance",
    "missing_response_hash", "missing_parsed_result_hash"])
def test_track_a_official_eligibility_rejects_incomplete_or_untrusted_runs(mutation):
    from app.evaluation.step77.eligibility import grading_official_eligibility
    from app.evaluation.step77.artifacts import digest
    _, (manifest,cases,executions,annotations,expected,artifact,dataset_files)=_track_a_official_fixture()
    manifest=dict(manifest); executions=[dict(x) for x in executions]; annotations=[dict(x) for x in annotations]
    if mutation=="missing_dataset_case": cases.pop()
    elif mutation=="missing_execution": executions.pop()
    elif mutation=="duplicate_execution": executions.append(dict(executions[0]))
    elif mutation=="duplicate_annotation": annotations.append(dict(annotations[0]))
    elif mutation=="extra_annotation": annotations.append({**annotations[0],"case_id":"unrelated-case"})
    elif mutation=="fake_provider": manifest["provider_mode"]="FAKE"; [row.update(provider_mode="FAKE") for row in executions]
    elif mutation=="offline": manifest["execution_mode"]="OFFLINE_TEST"
    elif mutation=="bad_artifact_hash": manifest["cases_artifact_sha256"]="0"*64
    elif mutation=="invalid_real_provenance": executions[0]["request_sha256"]=""
    elif mutation=="missing_response_hash": executions[0]["provider_response_sha256"]=""
    elif mutation=="missing_parsed_result_hash": executions[0]["parsed_result_sha256"]=""
    # Mutated run content must be represented by the artifact being verified.
    if mutation in {"missing_execution","duplicate_execution","fake_provider","invalid_real_provenance",
                    "missing_response_hash","missing_parsed_result_hash"}:
        artifact=b"".join(canonical_json(row)+b"\n" for row in executions)
        manifest["cases_artifact_sha256"]=digest(artifact)
    result=grading_official_eligibility(manifest=manifest,dataset_cases=cases,executions=executions,
        annotations=annotations,expected_identity=expected,cases_artifact=artifact,dataset_files=dataset_files)
    assert result[0] is False, mutation


def _track_b_official_fixture():
    from app.evaluation.step77.artifacts import digest, file_sha256
    from app.evaluation.step77.eligibility import generation_official_eligibility
    cases=_all(GENERATION_DATASET); run_id="official-track-b"
    dataset_files={name:(GENERATION_DATASET/name).read_bytes() for name in ("manifest.json","development.jsonl","holdout.jsonl")}
    dataset_sha=digest(canonical_json({name:digest(data) for name,data in dataset_files.items()}))
    expected={"dataset_version":"v0.1.0","dataset_schema_version":"1.0.0","dataset_sha256":dataset_sha,
        "provider":"openai","model":"gpt-5.4-mini-2026-03-17","generation_config":{
            "temperature":0.2,"max_output_tokens":4000,"reasoning_effort":"none",
            "model_input_limit":400000,"request_timeout_seconds":60.0,"max_transient_retries":1},
        "prompt_version":"v1","prompt_sha256":file_sha256(Path(__file__).parents[1] / "app/ai/generation/prompt.py"),
        "structured_schema_identity":"app.ai.generation.schemas.StructuredAssessmentGenerationOutput/v1","structured_schema_version":"1.0.0",
        "evaluator_version":"step77-offline/v1","annotation_version":"assessment-generation-human/v0.1.0",
        "rubric_version":"assessment-generation-rubric/v1",
        "scope_domain_validator_identity":"app.exercise.service.admin_validate_generated_question/v1"}
    executions=[]; annotations=[]
    for ci,case in enumerate(cases):
        qrows=[]
        execution_id=f"execution-{ci}"; output={"questions":[]}
        draft={"assessment":{"id":f"assessment-{ci}"},"questions":[]}
        scope={"lesson_ids":case.get("lesson_ids") or [case.get("lesson_id")],"fixture_scope_identity":case["fixture_scope_identity"]}
        for index in range(1,4):
            content={"type":"multiple_choice","prompt":f"q-{case['case_id']}-{index}"}
            qrows.append({"question_index":index,"persisted_question_id":f"question-{ci}-{index}",
                "question_type":"multiple_choice","question_content":content,
                "question_sha256":hashlib.sha256(canonical_json(content)).hexdigest(),"source_refs":["fixture-ref"]})
            output["questions"].append(content); draft["questions"].append({"id":f"question-{ci}-{index}",**content})
        row={"step77_run_id":run_id,"generation_case_id":case["case_id"],"execution_id":execution_id,
            "split":case["split"],"generation_kind":case["generation_kind"],"difficulty":case["difficulty"],
            "provider_mode":"REAL","provider":"openai","model":expected["model"],
            "provider_request_id":f"gen-req-{ci}","request_sha256":f"{ci+1:064x}",
            "provider_response_sha256":hashlib.sha256(canonical_json(output)).hexdigest(),
            "parsed_result_sha256":hashlib.sha256(canonical_json(output)).hexdigest(),
            "technical_ok":True,"critical_failures":[],"persisted_question_count":3,
            "generated_questions":qrows,"generated_draft_content":draft,"generated_output_content":output,
            "materialized_scope_content":scope}
        row["generated_draft_sha256"]=hashlib.sha256(canonical_json(draft)).hexdigest()
        row["generated_output_sha256"]=hashlib.sha256(canonical_json(output)).hexdigest()
        row["materialized_scope_sha256"]=hashlib.sha256(canonical_json(scope)).hexdigest()
        from app.evaluation.step77.eligibility import _expected_case_binding
        from app.evaluation.step77.contracts import GenerationCase
        binding = _expected_case_binding("generation", GenerationCase.model_validate(case), expected)
        assert binding is not None
        row.update(binding)
        executions.append(row)
    artifact=b"".join(canonical_json(row)+b"\n" for row in executions)
    bound_cases_sha=digest(artifact)
    for row in executions:
        for question in row["generated_questions"]:
            annotations.append({"step77_run_id":run_id,"generation_case_id":row["generation_case_id"],
                "execution_id":row["execution_id"],"question_index":question["question_index"],
                "persisted_question_id":question["persisted_question_id"],
                "generated_draft_sha256":row["generated_draft_sha256"],
                "generated_question_sha256":question["question_sha256"],
                "materialized_scope_sha256":row["materialized_scope_sha256"],
                "generation_output_sha256":row["generated_output_sha256"],
                "cases_artifact_sha256":bound_cases_sha,"annotation_version":"assessment-generation-human/v0.1.0",
                "rubric_version":"assessment-generation-rubric/v1","answer_reference_consistency":"CONSISTENT",
                "answerability":"ANSWERABLE","review_status":"HUMAN_APPROVED"})
    manifest={"run_id":run_id,"track":"assessment_generation","execution_mode":"OFFICIAL_RUNTIME",
        "provider_mode":"REAL","dataset_case_count":16,"development_case_count":12,"holdout_case_count":4,
        "lesson_exercise_count":8,"periodic_test_count":8,"question_count_per_case":3,
        "production_supported_question_types":["fill_blank","matching","multiple_choice","reorder_sentence",
            "sentence_writing","translate_vi_zh","translate_zh_vi"],
        "difficulty_coverage":["EASY","MEDIUM","HARD"], **expected,
        "cases_artifact_sha256":digest(artifact)}
    result=generation_official_eligibility(manifest=manifest,dataset_cases=cases,executions=executions,
        annotations=annotations,expected_identity=expected,cases_artifact=artifact,dataset_files=dataset_files)
    return result,(manifest,cases,executions,annotations,expected,artifact,dataset_files)


def test_track_b_official_eligibility_requires_all_exact_d109_question_bindings():
    assert _track_b_official_fixture()[0] == (True,"COMPLETE_TRACK_B_D109_COVERAGE")


@pytest.mark.parametrize("mutation", ["wrong_request", "other_case_request", "wrong_scope_hash",
    "lesson_ids", "vocabulary_ids", "grammar_ids", "difficulty", "allowed_types", "question_count",
    "annotation_version", "rubric_version", "both_versions"])
def test_track_b_official_eligibility_recomputes_request_scope_and_annotation_identity(mutation):
    from app.evaluation.step77.eligibility import generation_official_eligibility
    from app.evaluation.step77.artifacts import digest
    _,(manifest,cases,executions,annotations,expected,_,dataset_files)=_track_b_official_fixture()
    executions=[dict(row) for row in executions]; annotations=[dict(row) for row in annotations]
    if mutation == "wrong_request": executions[0]["request_sha256"]="f"*64
    elif mutation == "other_case_request": executions[0]["request_sha256"]=executions[-1]["request_sha256"]
    elif mutation == "wrong_scope_hash": executions[0]["materialized_scope_sha256"]="f"*64
    elif mutation in {"lesson_ids","vocabulary_ids","grammar_ids"}:
        field=mutation; executions[0][field]=["00000000-0000-0000-0000-000000000000"]
    elif mutation == "difficulty": executions[0]["difficulty"]="HARD"
    elif mutation == "allowed_types": executions[0]["allowed_question_types"]=["sentence_writing"]
    elif mutation == "question_count": executions[0]["question_count"]=2
    elif mutation == "annotation_version": annotations[0]["annotation_version"]="stale"
    elif mutation == "rubric_version": annotations[0]["rubric_version"]="stale"
    else:
        annotations[0]["annotation_version"]="stale"; annotations[0]["rubric_version"]="stale"
    artifact=b"".join(canonical_json(row)+b"\n" for row in executions)
    manifest={**manifest,"cases_artifact_sha256":digest(artifact)}
    annotations=[{**row,"cases_artifact_sha256":digest(artifact)} for row in annotations]
    result=generation_official_eligibility(manifest=manifest,dataset_cases=cases,executions=executions,
        annotations=annotations,expected_identity=expected,cases_artifact=artifact,dataset_files=dataset_files)
    assert result[0] is False, mutation


@pytest.mark.parametrize("request_id", ["req-present", None])
def test_track_b_official_eligibility_provider_request_id_is_optional(request_id):
    from app.evaluation.step77.eligibility import generation_official_eligibility
    from app.evaluation.step77.artifacts import digest
    _,(manifest,cases,executions,annotations,expected,_,dataset_files)=_track_b_official_fixture()
    executions=[dict(row, provider_request_id=request_id) for row in executions]
    artifact=b"".join(canonical_json(row)+b"\n" for row in executions)
    manifest={**manifest,"cases_artifact_sha256":digest(artifact)}
    annotations=[{**row,"cases_artifact_sha256":digest(artifact)} for row in annotations]
    assert generation_official_eligibility(manifest=manifest,dataset_cases=cases,executions=executions,
        annotations=annotations,expected_identity=expected,cases_artifact=artifact,
        dataset_files=dataset_files)==(True,"COMPLETE_TRACK_B_D109_COVERAGE")


@pytest.mark.parametrize("mutation", ["missing_question", "duplicate_question", "stale_question",
    "stale_scope", "wrong_execution", "wrong_run", "missing_execution", "fake_provider", "offline",
    "invalid_real_provenance", "missing_response_hash", "missing_parsed_result_hash"])
def test_track_b_official_eligibility_rejects_incomplete_or_stale_coverage(mutation):
    from app.evaluation.step77.eligibility import generation_official_eligibility
    from app.evaluation.step77.artifacts import digest
    _,(manifest,cases,executions,annotations,expected,artifact,dataset_files)=_track_b_official_fixture()
    manifest=dict(manifest); executions=[dict(x) for x in executions]; annotations=[dict(x) for x in annotations]
    if mutation=="missing_question": annotations.pop()
    elif mutation=="duplicate_question": annotations.append(dict(annotations[0]))
    elif mutation=="stale_question": annotations[0]["generated_question_sha256"]="0"*64
    elif mutation=="stale_scope": annotations[0]["materialized_scope_sha256"]="0"*64
    elif mutation=="wrong_execution": annotations[0]["execution_id"]="another-execution"
    elif mutation=="wrong_run": annotations[0]["step77_run_id"]="another-run"
    elif mutation=="missing_execution": executions.pop()
    elif mutation=="fake_provider": manifest["provider_mode"]="FAKE"; [row.update(provider_mode="FAKE") for row in executions]
    elif mutation=="offline": manifest["execution_mode"]="OFFLINE_TEST"
    elif mutation=="invalid_real_provenance": executions[0]["request_sha256"]=""
    elif mutation=="missing_response_hash": executions[0]["provider_response_sha256"]=""
    elif mutation=="missing_parsed_result_hash": executions[0]["parsed_result_sha256"]=""
    if mutation in {"missing_execution","fake_provider","invalid_real_provenance",
                    "missing_response_hash","missing_parsed_result_hash"}:
        artifact=b"".join(canonical_json(row)+b"\n" for row in executions)
        manifest["cases_artifact_sha256"]=digest(artifact)
    result=generation_official_eligibility(manifest=manifest,dataset_cases=cases,executions=executions,
        annotations=annotations,expected_identity=expected,cases_artifact=artifact,dataset_files=dataset_files)
    assert result[0] is False, mutation


def test_track_b_real_postgres_admin_generation_draft_and_atomic_failure():
    available, reason = asyncio.run(dedicated_test_database_available())
    if not available:
        pytest.skip(f"safe dedicated PostgreSQL unavailable: {reason}")
    from app.core.config import get_settings
    from app.database.models import Assessment, Question
    from app.database.session import SessionFactory
    from sqlalchemy import select
    from app.evaluation.step77.contracts import GenerationCase
    from app.evaluation.step77.db_fixture import _fixture_data
    from app.evaluation.step77.generation import execute_generation_case
    cases = [GenerationCase.model_validate(row) for row in _all(GENERATION_DATASET)]
    case = next(item for item in cases if item.generation_kind == "LESSON_EXERCISE")

    # Recover only prior Step-7.7 rows linked to this test's deterministic synthetic Lessons.
    fixture_lesson_ids = [UUID(row["lesson_id"]) for row in _fixture_data()["lessons"]]
    async def stale_fixture_assessment_ids():
        async with SessionFactory() as session:
            return (await session.execute(select(Assessment.id).where(
                Assessment.lesson_id.in_(fixture_lesson_ids)))).scalars().all()
    asyncio.run(cleanup_generation_assessments(asyncio.run(stale_fixture_assessment_ids())))
    asyncio.run(cleanup_curriculum_fixture())
    asyncio.run(seed_curriculum_fixture())
    ids = []
    try:
        async def linked_assessment_ids():
            async with SessionFactory() as session:
                return set((await session.execute(select(Assessment.id).where(
                    Assessment.lesson_id == case.lesson_id))).scalars().all())
        linked_before = asyncio.run(linked_assessment_ids())

        async def success():
            async with SessionFactory() as session:
                return await execute_generation_case(session, case, get_settings(), run_id="step77-db-test")
        result = asyncio.run(success())
        ids.extend(asyncio.run(linked_assessment_ids()) - linked_before)
        assert result["persisted_assessment_status"] == "DRAFT"
        assert result["persisted_question_count"] == 3
        assert result["draft_lifecycle_valid"] is True
        persisted_id = UUID(result["persisted_assessment_id"])
        if persisted_id not in ids:
            ids.append(persisted_id)

        async def fresh_database_read():
            async with SessionFactory() as session:
                assessment = await session.get(Assessment, ids[-1])
                question_count = (await session.execute(select(Question.id).where(
                    Question.assessment_id == ids[-1]))).scalars().all()
                return assessment, len(question_count)
        persisted_assessment, question_count = asyncio.run(fresh_database_read())
        assert persisted_assessment is not None
        assert persisted_assessment.status == "DRAFT"
        assert question_count == 3

        async def count_after_failure():
            async with SessionFactory() as session:
                before = (await session.execute(select(Assessment.id))).scalars().all()
                from app.ai.generation.errors import StructuredAssessmentGenerationProviderError, AI_GENERATION_PROVIDER_UNAVAILABLE
                class Broken:
                    async def generate(self, request):
                        raise StructuredAssessmentGenerationProviderError(AI_GENERATION_PROVIDER_UNAVAILABLE)
                failed = await execute_generation_case(session, case, get_settings(), run_id="step77-db-failure",
                    provider=Broken())
                after = (await session.execute(select(Assessment.id))).scalars().all()
                return failed, set(before), set(after)
        failed, before, after = asyncio.run(count_after_failure())
        assert failed["technical_ok"] is False
        assert after == before
    finally:
        asyncio.run(cleanup_generation_assessments(ids))
        asyncio.run(cleanup_curriculum_fixture())

    remaining_fixture_assessments = asyncio.run(linked_assessment_ids())
    assert not remaining_fixture_assessments


def test_step77_fixture_text_is_valid_utf8_and_rejects_mojibake_or_replacement_text(request):
    from app.evaluation.step77.dataset import _assert_readable_utf8_sources, _assert_unique_jsonl_ids

    validate_step77_datasets()
    corrupted = _workspace_temp_path(request)
    corrupted.write_bytes(b'{"text":"ok"}\n\xff')
    with pytest.raises(ValueError, match="SOURCE_NOT_UTF8"):
        _assert_unique_jsonl_ids([corrupted])
    with pytest.raises(ValueError, match="REPLACEMENT_QUESTION_MARK"):
        _assert_readable_utf8_sources([{"case_id": "broken", "question_content": "D?ch"}], {})
    with pytest.raises(ValueError, match="UTF8_CORRUPTION"):
        _assert_readable_utf8_sources([{"case_id": "broken", "question_content": "Xin chÃ o"}], {})


@pytest.mark.parametrize("track", ["grading", "assessment_generation"])
def test_step77_holdout_duplicate_and_id_only_leakage_are_rejected(track):
    from app.evaluation.step77.dataset import _assert_holdout_distinct

    root = GRADING_DATASET if track == "grading" else GENERATION_DATASET
    rows = _all(root)
    development = next(row for row in rows if row["split"] == "DEVELOPMENT")
    holdout = next(row for row in rows if row["split"] == "HOLDOUT")
    duplicate = {**development, "case_id": holdout["case_id"], "split": "HOLDOUT"}
    with pytest.raises(ValueError, match="HOLDOUT_LEAKAGE"):
        _assert_holdout_distinct([*rows, duplicate],
            ignored={"case_id", "annotation_ref", "split", "review_status", "dataset_version", "schema_version"},
            code="STEP77_GRADING_HOLDOUT_LEAKAGE")


def test_track_a_production_grading_service_replay_provider_yields_normalized_result(request):
    from app.evaluation.step77.replay import ReplayGradingProvider
    from app.evaluation.step77.grading import grading_request_identity

    case = GradingCase.model_validate(_all(GRADING_DATASET)[0])
    settings = _offline_settings().model_copy(update={"llm_provider": "openai"})
    identity, request_sha = grading_request_identity(case, settings)
    parsed = {"grading_status": "GRADED", "score": case.max_points, "feedback": "Replayed response."}
    response = {"status": "completed", "output": parsed}
    config = _identity_generation_config(identity)
    origin, origin_sha, _ = _make_real_origin_artifact(request, track="grading", run_id="fixture-real-origin",
        case_id=case.case_id, request_sha256=request_sha, response=response, provider="openai",
        model=settings.llm_model, generation_config=config, prompt_version=identity["prompt_identity"],
        prompt_sha256=identity["prompt_sha256"], schema_identity=identity["structured_schema_identity"],
        schema_version=identity["structured_schema_version"])
    record = ProviderReplayRecord.from_real_output(track="grading", request_sha256=request_sha,
        parsed_result=parsed, response=response, provider="openai",
        model=settings.llm_model, generation_config=config,
        prompt_identity=identity["prompt_identity"], prompt_version=identity["prompt_identity"],
        prompt_sha256=identity["prompt_sha256"], schema_identity=identity["structured_schema_identity"],
        schema_version=identity["structured_schema_version"], normalized_input=identity["normalized_production_input"],
        origin_run_id="fixture-real-origin", origin_track="grading", origin_provider_mode="REAL",
        origin_case_id=case.case_id, origin_artifact_path=str(origin), origin_artifact_sha256=origin_sha,
        metadata={"status": "completed", "api_key": "never-persist"},
        finish_status_metadata={"finish_reason": "stop"}, input_tokens=12, output_tokens=5,
        total_tokens=17, latency_ms=31, provider_request_id="req-safe-id")
    path = _workspace_temp_path(request)
    write_replay(path, record)
    provider = ReplayGradingProvider(path)
    result = asyncio.run(execute_grading_case(case, GradingAnnotation(case_id=case.case_id), settings,
                                              run_id="replay-run", provider=provider, provider_mode="REPLAY"))
    assert result["provider_mode"] == "REPLAY"
    assert result["technical_status"] == "SUCCESS"
    assert result["normalized_state"] == "FULL_CREDIT"
    assert result["replay_origin"] == {"execution_mode": "REAL", "run_id": "fixture-real-origin"}
    assert provider.record.input_tokens == 12 and provider.record.provider_request_id == "req-safe-id"
    serialized = path.read_text(encoding="utf-8")
    assert "never-persist" not in serialized and "api_key" not in serialized


@pytest.mark.parametrize(("track", "identity_field"), [
    ("grading", "case_id"), ("assessment_generation", "generation_case_id")])
def test_real_replay_origin_uses_track_specific_case_identity_and_parsed_hash(
        request, track, identity_field):
    from app.evaluation.step77.replay import verify_real_origin_artifact
    from app.evaluation.step77.artifacts import digest

    parsed = ({"grading_status": "GRADED", "score": 2, "feedback": "ok"}
              if track == "grading" else {"questions": [{"type": "multiple_choice"}]})
    response = {"status": "completed", "output": parsed}
    origin, origin_sha, _ = _make_real_origin_artifact(request, track=track, run_id="origin-track-aware",
        case_id="track-case", request_sha256="a" * 64, response=response, provider="openai",
        model="frozen-model", generation_config={"temperature": 0.2}, prompt_version="prompt-v1",
        prompt_sha256="b" * 64, schema_identity=f"{track}-schema", schema_version="1.0.0")
    record = ProviderReplayRecord.from_real_output(track=track, request_sha256="a" * 64,
        parsed_result=parsed, response=response, provider="openai", model="frozen-model",
        generation_config={"temperature": 0.2}, prompt_identity="prompt-v1", prompt_sha256="b" * 64,
        schema_identity=f"{track}-schema", schema_version="1.0.0", normalized_input={"input": "frozen"},
        origin_run_id="origin-track-aware", origin_track=track, origin_provider_mode="REAL",
        origin_case_id="track-case", origin_artifact_path=str(origin), origin_artifact_sha256=origin_sha)
    verify_real_origin_artifact(record)

    wrong_case = record.model_copy(update={"origin_case_id": "wrong-case"})
    with pytest.raises(ValueError, match="ORIGIN_PROVENANCE_INVALID"):
        verify_real_origin_artifact(wrong_case)
    wrong_parsed_hash = record.model_copy(update={"parsed_result_sha256": "0" * 64})
    with pytest.raises(ValueError, match="ORIGIN_PROVENANCE_INVALID"):
        verify_real_origin_artifact(wrong_parsed_hash)


def test_track_a_replay_identity_mismatch_fails_closed_as_stale(request):
    from app.evaluation.step77.replay import ReplayGradingProvider
    from app.evaluation.step77.grading import grading_request_identity

    case = GradingCase.model_validate(_all(GRADING_DATASET)[0])
    settings = _offline_settings()
    identity, request_sha = grading_request_identity(case, settings)
    parsed = {"grading_status": "GRADED", "score": case.max_points, "feedback": "Replay."}
    config = _identity_generation_config(identity)
    origin, origin_sha, _ = _make_real_origin_artifact(request, track="grading", run_id="fixture-real-origin",
        case_id=case.case_id, request_sha256=request_sha, response=parsed, provider=settings.llm_provider,
        model=settings.llm_model, generation_config=config, prompt_version=identity["prompt_identity"],
        prompt_sha256=identity["prompt_sha256"], schema_identity=identity["structured_schema_identity"],
        schema_version=identity["structured_schema_version"])
    record = ProviderReplayRecord.from_real_output(track="grading", request_sha256=request_sha,
        parsed_result=parsed, response=parsed, provider=settings.llm_provider, model=settings.llm_model,
        generation_config=config, prompt_identity=identity["prompt_identity"], prompt_sha256=identity["prompt_sha256"],
        schema_identity=identity["structured_schema_identity"], schema_version=identity["structured_schema_version"],
        normalized_input=identity["normalized_production_input"], origin_run_id="fixture-real-origin",
        origin_track="grading", origin_provider_mode="REAL", origin_case_id=case.case_id,
        origin_artifact_path=str(origin), origin_artifact_sha256=origin_sha)
    path=_workspace_temp_path(request); write_replay(path,record)
    changed=settings.model_copy(update={"llm_model":"changed-model"})
    result=asyncio.run(execute_grading_case(case,GradingAnnotation(case_id=case.case_id),changed,
        run_id="stale-run",provider=ReplayGradingProvider(path,provider=changed.llm_provider),
        provider_mode="REPLAY"))
    assert result["technical_status"] == "TECHNICAL_FAILURE"
    assert result["technical_error_code"] == "STEP77_REPLAY_STALE_REQUEST_IDENTITY"
    assert result["grading_status"] is None and result["normalized_state"] is None


def test_track_b_production_generation_service_replay_provider_and_domain_validator(request):
    from app.exercise.service import admin_validate_generated_question
    from app.evaluation.step77.generation import generation_provider_request_identity, execute_generation_replay_case
    from app.evaluation.step77.replay import ReplayGenerationProvider

    case = _generation_case()
    settings = _offline_settings().model_copy(update={"llm_provider": "openai"})
    generation_request = TypeAdapter(AssessmentGenerationRequest).validate_python({
        "type": case.generation_kind, "lesson_id": case.lesson_id, "question_count": 3,
        "allowed_types": case.allowed_question_types, "difficulty": case.difficulty})
    ref = "vocab:00000000-0000-0000-0000-000000000001"
    scope = MaterializedGenerationScope("LESSON_EXERCISE", UUID(case.lesson_id), (UUID(case.lesson_id),),
        (), (), "Review", None, 90, {"scope": {}, "vocabulary": [], "grammar": []}, frozenset({ref}))
    capture = DeterministicGenerationProvider(["multiple_choice", "fill_blank", "matching"])
    captured_result = asyncio.run(AssessmentGenerationService(capture, settings).generate(generation_request, scope))
    provider_request = capture.last_request
    identity, request_sha = generation_provider_request_identity(provider_request, provider="openai")
    case_identity, case_request_sha = generation_request_identity(case, settings,
        request=generation_request, scope=scope)
    assert case_identity == identity and case_request_sha == request_sha
    parsed = captured_result.output.model_dump(mode="json")
    response = {"status":"completed","output":parsed}
    config = _identity_generation_config(identity)
    origin, origin_sha, _ = _make_real_origin_artifact(request, track="assessment_generation",
        run_id="fixture-real-generation-origin", case_id=case.case_id, request_sha256=request_sha,
        response=response, provider="openai", model=provider_request.model, generation_config=config,
        prompt_version=identity["prompt_identity"], prompt_sha256=identity["prompt_sha256"],
        schema_identity=identity["structured_schema_identity"], schema_version=identity["structured_schema_version"])
    record = ProviderReplayRecord.from_real_output(track="assessment_generation", request_sha256=request_sha,
        parsed_result=parsed, response=response, provider="openai",
        model=provider_request.model, generation_config=config,
        prompt_identity=identity["prompt_identity"], prompt_version=identity["prompt_identity"],
        prompt_sha256=identity["prompt_sha256"], schema_identity=identity["structured_schema_identity"],
        schema_version=identity["structured_schema_version"], normalized_input=identity["normalized_production_input"],
        origin_run_id="fixture-real-generation-origin", origin_track="assessment_generation",
        origin_provider_mode="REAL", origin_case_id=case.case_id,
        origin_artifact_path=str(origin), origin_artifact_sha256=origin_sha, metadata={"status":"completed"},
        finish_status_metadata={"finish_reason":"stop"}, input_tokens=20, output_tokens=30,
        total_tokens=50, latency_ms=42, provider_request_id="req-generation-safe")
    path=_workspace_temp_path(request); write_replay(path,record)
    replay=ReplayGenerationProvider(path)
    evaluation_result=asyncio.run(execute_generation_replay_case(case=case,request=generation_request,
        scope=scope,settings=settings,provider=replay,run_id="step77-replay-test",
        domain_validator=admin_validate_generated_question))
    assert evaluation_result["technical_ok"] is True, evaluation_result["technical_error_code"]
    assert replay.mode == "REPLAY" and replay.record.origin_run_id == "fixture-real-generation-origin"
    assert evaluation_result["provider_mode"] == "REPLAY"
    assert evaluation_result["generated_question_count"] == 3
    assert evaluation_result["generation_case_status"] == "DEFERRED_HUMAN_REVIEW"
    assert evaluation_result["replay_origin"]["run_id"] == "fixture-real-generation-origin"
    assert all(item["question_type"] in case.allowed_question_types
               for item in evaluation_result["generated_questions"])


def test_generation_summary_counts_only_boolean_finalizations_and_all_annotation_states():
    from app.evaluation.step77.generation import build_generation_summary

    rows = [
        {"split":"DEVELOPMENT","generation_kind":"LESSON_EXERCISE","difficulty":"EASY",
         "generation_questions":[],"generated_questions":[],"technical_ok":True,"critical_failures":[],
         "human_annotation_statuses":["HUMAN_APPROVED"]*3,"human_review_complete":True,
         "generation_case_status":"PASS","generation_case_pass":True},
        {"split":"DEVELOPMENT","generation_kind":"PERIODIC_TEST","difficulty":"MEDIUM",
         "generation_questions":[],"generated_questions":[],"technical_ok":False,"critical_failures":[],
         "human_annotation_statuses":["DRAFT","NEEDS_ADJUDICATION","HUMAN_APPROVED"],"human_review_complete":False,
         "generation_case_status":"TECHNICAL_FAILURE","generation_case_pass":False},
        {"split":"HOLDOUT","generation_kind":"PERIODIC_TEST","difficulty":"HARD",
         "generation_questions":[],"generated_questions":[],"technical_ok":True,"critical_failures":[],
         "human_annotation_statuses":["DRAFT"]*3,"human_review_complete":False,
         "generation_case_status":"DEFERRED_HUMAN_REVIEW","generation_case_pass":None},
    ]
    summary=build_generation_summary(rows)
    assert summary["technical_failure_count"] == 1 and summary["technical_failure_rate"] == pytest.approx(1/3)
    assert summary["generation_case_status_counts"]["DEFERRED_HUMAN_REVIEW"] == 1
    assert summary["generation_case_pass_count"] == 1 and summary["generation_case_fail_count"] == 1
    assert summary["generation_case_pass_rate"] == pytest.approx(1/2)
    assert summary["human_annotation_counts"] == {"DRAFT":4,"NEEDS_ADJUDICATION":1,"HUMAN_APPROVED":4}
    assert summary["human_review_complete_case_count"] == 1
    assert summary["deferred_human_review_case_count"] == 1


def test_step77_all_cli_track_writes_one_shared_run_identity(request, monkeypatch):
    from app.evaluation.step77 import cli
    from app.evaluation.step77.artifacts import write_artifact

    settings = _offline_settings()
    output_root = _workspace_temp_path(request, directory=True)
    async def fake_track(track, *, run_id, output_root):
        directory = Path(output_root) / run_id / track
        manifest = {"run_id":run_id,"track":track,"execution_mode":"OFFLINE_TEST",
            "provider_mode":"FAKE","provider":"test-only","model":"offline",
            "official_eligible":False,"runtime_api_calls":0,"human_approved_count":0}
        write_artifact(directory,manifest=manifest,rows=[{"run_id":run_id,"track":track}],summary={"planned_case_count":1})
        return {"run_id":run_id,"directory":str(directory)}
    async def fake_grading(settings_arg, **kwargs): return await fake_track("grading", **kwargs)
    async def fake_generation(settings_arg, **kwargs): return await fake_track("assessment_generation", **kwargs)
    monkeypatch.setattr(cli,"run_grading_offline",fake_grading)
    monkeypatch.setattr(cli,"run_generation_offline",fake_generation)
    monkeypatch.setattr(cli,"get_settings",lambda:settings)
    result=asyncio.run(cli._run("all",None,output_root))
    run_ids={item["run_id"] for item in result.values()}
    assert len(run_ids)==1
    run_id=run_ids.pop()
    for track in ("grading","assessment_generation"):
        directory=output_root/run_id/track
        for name in ("manifest.json","cases.jsonl","summary.json"):
            content=(directory/name).read_text(encoding="utf-8")
            if name.endswith(".jsonl"):
                assert json.loads(content)["run_id"]==run_id
            else:
                assert json.loads(content)["run_id"]==run_id


def test_offline_runner_manifest_contains_reproducibility_identities(request):
    from app.evaluation.step77.runner import run_grading_offline

    output_root = _workspace_temp_path(request, directory=True)
    result=asyncio.run(run_grading_offline(_offline_settings(),run_id="step77-manifest-test",output_root=output_root))
    manifest=json.loads((Path(result["directory"])/"manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"]=="step77-manifest-test" and manifest["track"]=="grading"
    assert manifest["dataset_case_count"]==60 and manifest["development_case_count"]==45 and manifest["holdout_case_count"]==15
    assert manifest["code_commit"] is None
    assert manifest["dataset_sha256"] and manifest["prompt_sha256"] and manifest["structured_schema_identity"]
    assert manifest["agreement_policy_identity"]=={"primary_unit":"D-106/v1","denominator":"D-107/v1"}
    assert manifest["runtime_api_calls"]==0 and manifest["official_eligible"] is False


def test_generation_runner_manifest_contains_frozen_reproducibility_identities(request, monkeypatch):
    from app.evaluation.step77 import runner
    import app.database.session as database_session

    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
    class SessionFactoryFake:
        def __call__(self): return Session()
    async def no_op(*args, **kwargs): return None
    async def fake_execute(session, case, settings, *, run_id, **kwargs):
        return {"step77_run_id":run_id,"generation_case_id":case.case_id,
            "split":case.split.value,"generation_kind":case.generation_kind,
            "difficulty":case.difficulty,"technical_ok":True,"critical_failures":[],
            "generation_questions":[],"generated_questions":[],"human_annotation_status":"DRAFT",
            "human_annotation_statuses":["DRAFT"]*3,"human_review_complete":False,
            "generation_case_status":"DEFERRED_HUMAN_REVIEW","generation_case_pass":None}
    monkeypatch.setattr(runner,"seed_curriculum_fixture",no_op)
    monkeypatch.setattr(runner,"cleanup_generation_assessments",no_op)
    monkeypatch.setattr(runner,"cleanup_curriculum_fixture",no_op)
    monkeypatch.setattr(runner,"execute_generation_case",fake_execute)
    monkeypatch.setattr(database_session,"SessionFactory",SessionFactoryFake())
    output_root=_workspace_temp_path(request,directory=True)
    result=asyncio.run(runner.run_generation_offline(_offline_settings(),run_id="step77-generation-manifest-test",output_root=output_root))
    manifest=json.loads((Path(result["directory"])/"manifest.json").read_text(encoding="utf-8"))
    assert (manifest["dataset_case_count"],manifest["development_case_count"],manifest["holdout_case_count"])==(16,12,4)
    assert (manifest["lesson_exercise_count"],manifest["periodic_test_count"],manifest["question_count_per_case"])==(8,8,3)
    assert len(manifest["production_supported_question_types"])==7
    assert set(manifest["difficulty_coverage"])=={"EASY","MEDIUM","HARD"}
    assert manifest["materialized_scope_fixture_id"]=="step77-curriculum-fixture/v0.1.0"
    assert manifest["materialized_scope_fixture_sha256"] and manifest["scope_domain_validator_identity"]
    assert manifest["dataset_sha256"] and manifest["prompt_sha256"] and manifest["structured_schema_identity"]
    assert manifest["code_commit"] is None and manifest["runtime_api_calls"]==0
