from __future__ import annotations

import uuid
import subprocess
import json
from pathlib import Path

from app.ai.grading.prompt import GRADING_PROMPT_VERSION
from app.ai.generation.prompt import ASSESSMENT_GENERATION_PROMPT_VERSION
from app.core.config import Settings

from .artifacts import build_manifest, digest, file_sha256, write_artifact
from .contracts import GenerationQuestionAnnotation, GradingAnnotation, GenerationCase, GradingCase
from .dataset import (GENERATION_ANNOTATIONS, GENERATION_DATASET, GRADING_ANNOTATIONS,
                      GRADING_DATASET, _all, annotation_contract, read_jsonl, validate_step77_datasets)
from .db_fixture import (FIXTURE_PATH, cleanup_generation_assessments,
    cleanup_curriculum_fixture, seed_curriculum_fixture)
from .generation import build_generation_summary, execute_generation_case
from .grading import build_grading_summary, execute_grading_case

REPO_ROOT = Path(__file__).resolve().parents[4]


def _code_commit() -> str | None:
    if not (REPO_ROOT / ".git").exists():
        return None
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            check=True, capture_output=True, text=True, timeout=2)
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _dataset_sha256(*paths: Path) -> str:
    return digest(canonical_bytes({path.name: file_sha256(path) for path in paths}))


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


async def run_grading_offline(settings: Settings, *, run_id: str | None = None,
                              output_root: Path | None = None) -> dict:
    validate_step77_datasets()
    run_id = run_id or f"step77-grading-{uuid.uuid4()}"
    cases = [GradingCase.model_validate(row) for row in _all(GRADING_DATASET)]
    annotation_rows = [GradingAnnotation.model_validate(row) for row in read_jsonl(GRADING_ANNOTATIONS / "annotations.jsonl")]
    annotations = {item.case_id: item for item in annotation_rows}
    results = [await execute_grading_case(case, annotations[case.case_id], settings, run_id=run_id,
                                          provider_mode="FAKE")
               for case in cases]
    dataset_hash = _dataset_sha256(GRADING_DATASET / "manifest.json",
        GRADING_DATASET / "development.jsonl", GRADING_DATASET / "holdout.jsonl")
    prompt_path = REPO_ROOT / "backend/app/ai/grading/prompt.py"
    manifest = build_manifest(run_id=run_id, track="grading", execution_mode="OFFLINE_TEST",
        provider_mode="FAKE", provider=settings.llm_provider, model=settings.llm_model,
        dataset_version="v0.1.0", dataset_case_count=60, development_case_count=45,
        holdout_case_count=15, generation_config={"temperature": settings.llm_temperature,
        "max_output_tokens": settings.llm_max_output_tokens, "reasoning_effort": settings.llm_reasoning_effort,
        "model_input_limit": settings.llm_model_input_limit,
        "request_timeout_seconds": settings.llm_request_timeout_seconds,
        "max_transient_retries": settings.llm_max_transient_retries},
        prompt_version=GRADING_PROMPT_VERSION, schema_version="StructuredGradingOutput/v1",
        annotation_version=annotation_contract("grading")[0], rubric_version=annotation_contract("grading")[1],
        code_commit=_code_commit(), schema_identity="app.ai.grading.schemas.StructuredGradingOutput/v1",
        prompt_sha256=file_sha256(prompt_path), dataset_sha256=dataset_hash,
        extra={"agreement_policy_identity": {"primary_unit": "D-106/v1", "denominator": "D-107/v1"},
               "replay_provenance": None})
    directory = Path(output_root) / run_id / "grading" if output_root else REPO_ROOT / "evaluation/runs" / run_id / "grading"
    hashes = write_artifact(directory, manifest=manifest, rows=results, summary=build_grading_summary(results))
    return {"run_id": run_id, "directory": str(directory), "artifact_hashes": hashes,
            "executed": len(results), "human_approved": 0}


async def run_generation_offline(settings: Settings, *, run_id: str | None = None,
                                 output_root: Path | None = None) -> dict:
    validate_step77_datasets()
    run_id = run_id or f"step77-generation-{uuid.uuid4()}"
    await seed_curriculum_fixture()
    from app.database.session import SessionFactory
    cases = [GenerationCase.model_validate(row) for row in _all(GENERATION_DATASET)]
    annotation_rows = read_jsonl(GENERATION_ANNOTATIONS / "questions.jsonl")
    annotation_states: dict[str, list[str]] = {}
    for annotation in annotation_rows:
        annotation_states.setdefault(annotation["generation_case_id"], []).append(annotation["review_status"])
    results = []
    assessment_ids = []
    try:
        for case in cases:
            async with SessionFactory() as session:
                row = await execute_generation_case(session, case, settings, run_id=run_id,
                    human_annotation_statuses=annotation_states.get(case.case_id, []), provider_mode="FAKE")
            results.append(row)
            if row.get("persisted_assessment_id"):
                from uuid import UUID
                assessment_ids.append(UUID(row["persisted_assessment_id"]))
    finally:
        await cleanup_generation_assessments(assessment_ids)
        await cleanup_curriculum_fixture()
    supported = sorted({kind for case in cases for kind in case.allowed_question_types})
    dataset_hash = _dataset_sha256(GENERATION_DATASET / "manifest.json",
        GENERATION_DATASET / "development.jsonl", GENERATION_DATASET / "holdout.jsonl")
    prompt_path = REPO_ROOT / "backend/app/ai/generation/prompt.py"
    curriculum_fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    manifest = build_manifest(run_id=run_id, track="assessment_generation", execution_mode="OFFLINE_TEST",
        provider_mode="FAKE", provider=settings.llm_provider, model=settings.llm_model,
        dataset_version="v0.1.0", dataset_case_count=16, development_case_count=12,
        holdout_case_count=4, generation_config={"temperature": settings.llm_temperature,
        "max_output_tokens": settings.ai_generation_max_output_tokens,
        "reasoning_effort": settings.llm_reasoning_effort,
        "model_input_limit": settings.llm_model_input_limit,
        "request_timeout_seconds": settings.llm_request_timeout_seconds,
        "max_transient_retries": settings.llm_max_transient_retries},
        prompt_version=ASSESSMENT_GENERATION_PROMPT_VERSION, schema_version="StructuredAssessmentGenerationOutput/v1",
        annotation_version=annotation_contract("generation")[0], rubric_version=annotation_contract("generation")[1],
        code_commit=_code_commit(), schema_identity="app.ai.generation.schemas.StructuredAssessmentGenerationOutput/v1",
        prompt_sha256=file_sha256(prompt_path), dataset_sha256=dataset_hash,
        extra={"lesson_exercise_count": 8, "periodic_test_count": 8, "question_count_per_case": 3,
               "production_supported_question_types": supported,
               "difficulty_coverage": ["EASY", "MEDIUM", "HARD"],
               "materialized_scope_fixture_id": curriculum_fixture.get("fixture_id"),
               "materialized_scope_fixture_sha256": file_sha256(FIXTURE_PATH),
               "scope_domain_validator_identity": "app.exercise.service.admin_validate_generated_question/v1",
               "replay_provenance": None})
    directory = Path(output_root) / run_id / "assessment_generation" if output_root else REPO_ROOT / "evaluation/runs" / run_id / "assessment_generation"
    hashes = write_artifact(directory, manifest=manifest, rows=results, summary=build_generation_summary(results))
    return {"run_id": run_id, "directory": str(directory), "artifact_hashes": hashes,
            "executed": len(results), "human_approved": 0}


def offline_settings() -> Settings:
    return Settings(_env_file=None, app_env="test", debug=False,
                    test_database_url="postgresql+psycopg://step77.invalid/chinese_learning_test",
                    secret_key="step77-offline-test-signing-key-not-a-secret")
