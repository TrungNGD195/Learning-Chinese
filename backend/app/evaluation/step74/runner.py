from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.ai.llm.factory import get_llm_provider
from app.ai.llm.schemas import GenerationConfig
from app.ai.llm.serializer import LLMRequestSerializer
from app.ai.llm.service import LLMGenerationService
from app.ai.prompting.builder import PromptContextBuilder
from app.ai.prompting.token_counter import TiktokenTokenCounter
from app.core.config import Settings, get_settings

from .annotations import (CALIBRATION_IDS, answer_sha256, load_annotation_package,
                          validate_annotation_manifest, validate_annotations)
from .artifacts import (RUNS_ROOT, build_manifest, build_stage_a_summary, validate_artifact_metadata,
                        verify_stage_a_case_file_binding,
                        canonical_json, package_stage_a_review_zip, write_json, write_jsonl, write_stage_a)
from .contracts import (
    CRITICAL_FAILURES, DATASET_NAME, DATASET_SCHEMA_VERSION, DATASET_VERSION,
    ELIGIBLE_CASE_POLICY_VERSION, FIXED_EVIDENCE_POLICY_VERSION,
    FIXED_MEMORY_POLICY_VERSION, GENERATOR_MODEL, HUMAN_ANNOTATION_VERSION,
    JUDGE_MODEL, JUDGE_PROMPT_VERSION, RUBRIC_VERSION, JudgeCallResult,
    JudgeTechnicalFailure,
)
from .eligibility import select_eligible_cases
from .fixed_evidence import FixedEvidenceResolver
from .judge import OpenAIResponsesGenerationJudge
from .metrics import calibration_agreement
from .prompt import ProductionPromptFactory
from .smoke import RuntimeSmokeEvidence, run_real_smoke_gate


class Step74Runner:
    """Offline-testable harness; it never invokes retrieval, reranking, or fetch."""

    def __init__(self, *, settings: Settings | None = None, generation_service=None,
                 prompt_builder=None, token_counter=None, evidence_resolver=None, judge=None):
        self.settings = settings or get_settings()
        self.generation_config = GenerationConfig.from_settings(self.settings)
        if self.generation_config.model != GENERATOR_MODEL:
            raise ValueError("STEP74_GENERATOR_MODEL_MISMATCH")
        self.token_counter = token_counter or TiktokenTokenCounter()
        self.prompt_builder = prompt_builder or PromptContextBuilder(token_counter=self.token_counter)
        self.generation_service = generation_service or LLMGenerationService(
            get_llm_provider(), serializer=LLMRequestSerializer()
        )
        self.evidence_resolver = evidence_resolver or FixedEvidenceResolver()
        self.prompt_factory = ProductionPromptFactory(
            prompt_builder=self.prompt_builder,
            token_counter=self.token_counter,
            generation_config=self.generation_config,
            memory_max_turns=self.settings.rag_memory_max_turns,
        )
        self.judge = judge or OpenAIResponsesGenerationJudge(self.settings)

    async def generate_case(self, case: dict, *, run_id: str) -> dict:
        started = datetime.now(UTC)
        fixed = self.evidence_resolver.resolve_case(case)
        package_metadata = {}
        try:
            package, package_metadata = self.prompt_factory.build(case, fixed)
            result = await self.generation_service.generate(package, self.generation_config)
            if result.model != GENERATOR_MODEL or result.provider != "openai":
                raise RuntimeError("GENERATOR_PROVIDER_MODEL_MISMATCH")
            if not isinstance(result.text, str) or not result.text.strip():
                raise RuntimeError("EMPTY_GENERATOR_RESPONSE")
            answer = result.text
            return self._case_base(case, run_id, fixed, package_metadata) | {
                "generator": {
                    "status": "SUCCESS", "provider": result.provider, "model": result.model,
                    "temperature": self.generation_config.temperature,
                    "max_output_tokens": self.generation_config.max_output_tokens,
                    "attempt_count": result.attempt_count, "latency_ms": result.latency_ms,
                    "token_usage": {"input_tokens": result.input_tokens,
                                    "output_tokens": result.output_tokens,
                                    "total_tokens": result.total_tokens},
                    "provider_preflight_input_tokens": result.provider_preflight_input_tokens,
                    "provider_preflight_count": result.provider_preflight_count,
                    "error": None,
                },
                "generated_answer": answer,
                "generated_answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
                "judge": {"status": "NOT_RUN", "provider": "OpenAI API", "api": "Responses API",
                          "model": JUDGE_MODEL, "attempt_count": 0, "error": None},
                "dimension_scores": None, "claim_faithfulness": None,
                "critical_failures": [], "generation_case_status": "NOT_JUDGED",
                "generation_case_pass": None,
                "calibration": {"in_human_subset": case["case_id"] in CALIBRATION_IDS,
                                "human_review_status": "DRAFT" if case["case_id"] in CALIBRATION_IDS else None},
            }
        except Exception as exc:
            code = getattr(exc, "code", None)
            if not isinstance(code, str):
                code = str(exc) if str(exc) in {
                    "FIXED_EVIDENCE_CONTEXT_BUDGET_EXHAUSTED", "GENERATOR_PROVIDER_MODEL_MISMATCH",
                    "EMPTY_GENERATOR_RESPONSE",
                } else "GENERATION_TECHNICAL_FAILURE"
            return self._case_base(case, run_id, fixed, package_metadata) | {
                "generator": {"status": "TECHNICAL_FAILURE", "provider": "openai",
                              "model": GENERATOR_MODEL,
                              "temperature": self.generation_config.temperature,
                              "max_output_tokens": self.generation_config.max_output_tokens,
                              "attempt_count": getattr(exc, "attempt_count", None),
                              "latency_ms": getattr(exc, "latency_ms", None), "token_usage": None,
                              "error": {"code": code}},
                "generated_answer": None, "generated_answer_sha256": None,
                "judge": {"status": "NOT_RUN", "provider": "OpenAI API", "api": "Responses API",
                          "model": JUDGE_MODEL, "attempt_count": 0, "error": None},
                "dimension_scores": None, "claim_faithfulness": None,
                "critical_failures": [], "generation_case_status": "TECHNICAL_FAILURE",
                "generation_case_pass": None,
                "calibration": {"in_human_subset": case["case_id"] in CALIBRATION_IDS,
                                "human_review_status": "DRAFT" if case["case_id"] in CALIBRATION_IDS else None},
            }

    def _case_base(self, case: dict, run_id: str, fixed: list, package_metadata: dict) -> dict:
        evidence_ids = [evidence_id for item in fixed for evidence_id in item.evidence_ids]
        return {
            "case_id": case["case_id"], "run_id": run_id,
            "evaluation_step": "7.4", "dataset_name": DATASET_NAME,
            "execution_mode": getattr(self, "execution_mode", "OFFLINE_TEST"),
            "dataset_version": DATASET_VERSION, "dataset_schema_version": DATASET_SCHEMA_VERSION,
            "eligible_case_policy_version": ELIGIBLE_CASE_POLICY_VERSION,
            "fixed_evidence_policy_version": FIXED_EVIDENCE_POLICY_VERSION,
            "fixed_memory_policy_version": FIXED_MEMORY_POLICY_VERSION,
            "rubric_version": RUBRIC_VERSION,
            "human_annotation_version": HUMAN_ANNOTATION_VERSION,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "generator_identity": {"provider": "openai", "model": GENERATOR_MODEL,
                                   "temperature": self.generation_config.temperature,
                                   "max_output_tokens": self.generation_config.max_output_tokens,
                                   "reasoning_effort": self.generation_config.reasoning_effort,
                                   "model_input_limit": self.generation_config.model_input_limit,
                                   "timeout_seconds": self.generation_config.request_timeout_seconds,
                                   "max_transient_retries": self.generation_config.max_transient_retries,
                                   "streaming": False, "tools": []},
            "judge_identity": {"provider": "OpenAI API", "api": "Responses API",
                               "model": JUDGE_MODEL, "reasoning_effort": "none",
                               "temperature": 0, "max_output_tokens": 1600,
                               "structured_output": True, "tools": []},
            "split": case["split"], "bucket": case["bucket"], "question": case["question"],
            "expected_information": case["expected_information"],
            "reference_answer": case.get("reference_answer"),
            "fixed_evidence": [item.artifact() for item in fixed],
            "fixed_evidence_content_sha256": FixedEvidenceResolver.content_hash(fixed),
            "fixed_memory": package_metadata.get("fixed_memory"),
            "learning_context": package_metadata.get("learning_context"),
            "prompt_package_sha256": package_metadata.get("prompt_package_sha256"),
            "source_map_snapshot": package_metadata.get("source_map_snapshot"),
            "fixed_evidence_ids": evidence_ids,
            "fixed_evidence_score_semantics": "NOT_APPLICABLE_FIXED_EVIDENCE",
        }

    async def run_required_smokes(self) -> RuntimeSmokeEvidence:
        return await run_real_smoke_gate(self)

    async def run_stage_a(self, *, dataset_dir: Path | None = None, run_id: str | None = None) -> dict:
        from app.ai.llm.openai_provider import OpenAILLMProvider
        if not isinstance(self.generation_service.provider, OpenAILLMProvider):
            raise RuntimeError("OFFICIAL_STAGE_A_REQUIRES_PRODUCTION_LLM_PROVIDER")
        if self.settings.llm_model != GENERATOR_MODEL:
            raise RuntimeError("STEP74_GENERATOR_MODEL_MISMATCH")
        smoke = await self.run_required_smokes()
        if not isinstance(smoke, RuntimeSmokeEvidence):
            raise RuntimeError("STEP74_REAL_SMOKE_GATE_REQUIRED")
        smoke.validate()
        self.execution_mode = "OFFICIAL_REAL_RUNTIME"
        _, cases = select_eligible_cases(dataset_dir) if dataset_dir else select_eligible_cases()
        if len(cases) != 45:
            raise RuntimeError("STEP74_ELIGIBLE_COUNT_MISMATCH")
        run_id = run_id or "step74-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        started = datetime.now(UTC)
        run_dir = RUNS_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        rows = []
        for case in cases:
            rows.append(await self.generate_case(case, run_id=run_id))
        manifest = build_manifest(
            run_id=run_id, evidence_resolver=self.evidence_resolver,
            generation_config=self.generation_config, prompt_builder=self.prompt_builder,
            token_counter=self.token_counter,
            rows=rows, runtime_smoke=smoke.artifact(),
            run_status=("REVIEW_REQUIRED_HUMAN_CALIBRATION" if all(
                row["generator"]["status"] == "SUCCESS" for row in rows
            ) else "GENERATOR_TECHNICAL_FAILURES"),
            started=started,
        )
        generation = write_stage_a(run_id, run_dir, manifest, rows)
        zip_path, zip_sha256 = package_stage_a_review_zip(run_id, generation)
        result = {"run_id": run_id, "run_dir": str(run_dir), "generation_dir": str(generation),
                "review_zip": str(zip_path), "review_zip_sha256": zip_sha256,
                "eligible_case_count": len(rows), "generator_success_count": sum(r["generator"]["status"] == "SUCCESS" for r in rows),
                "generator_technical_failure_count": sum(r["generator"]["status"] != "SUCCESS" for r in rows),
                "human_calibration_case_count": manifest["human_calibration_case_count"],
                "human_calibration_packet_created": manifest["human_calibration_packet_created"],
                "human_approved_count": manifest["human_approved_count"],
                "status": "REVIEW_REQUIRED — HUMAN CALIBRATION" if all(r["generator"]["status"] == "SUCCESS" for r in rows) else "GENERATOR_TECHNICAL_FAILURES"}

        result["status"] = manifest["run_status"]
        return result

    @staticmethod
    def _validate_stage_a_identity(rows: list[dict], manifest: dict, run_id: str,
                                   *, allow_test_smoke: bool = False) -> None:
        if manifest.get("run_id") != run_id or manifest.get("evaluation_step") != "7.4":
            raise ValueError("STEP74_RUN_ID_MISMATCH")
        expected_identity = {
            "dataset_name": DATASET_NAME, "dataset_version": DATASET_VERSION,
            "dataset_schema_version": DATASET_SCHEMA_VERSION,
            "eligible_case_policy_version": ELIGIBLE_CASE_POLICY_VERSION,
            "fixed_evidence_policy_version": FIXED_EVIDENCE_POLICY_VERSION,
            "fixed_memory_policy_version": FIXED_MEMORY_POLICY_VERSION,
            "rubric_version": RUBRIC_VERSION,
            "human_annotation_version": HUMAN_ANNOTATION_VERSION,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
        }
        if any(manifest.get(key) != value for key, value in expected_identity.items()):
            raise ValueError("STEP74_RUN_IDENTITY_MISMATCH")
        generator_identity = manifest.get("generator_identity")
        if (manifest.get("generator_model") != GENERATOR_MODEL or not isinstance(generator_identity, dict)
                or generator_identity.get("provider") != "openai"
                or generator_identity.get("model") != GENERATOR_MODEL
                or generator_identity.get("temperature") != 0.2
                or generator_identity.get("max_output_tokens") != 800
                or generator_identity.get("reasoning_effort") != "none"
                or generator_identity.get("model_input_limit") != 400_000
                or generator_identity.get("streaming") is not False
                or generator_identity.get("tools") != []):
            raise ValueError("STEP74_GENERATOR_IDENTITY_MISMATCH")
        expected_judge_identity = {
            "provider": "OpenAI API", "api": "Responses API", "model": JUDGE_MODEL,
            "reasoning_effort": "none", "temperature": 0, "max_output_tokens": 1600,
            "structured_output": True, "tools": [],
        }
        if manifest.get("judge_model") != JUDGE_MODEL or manifest.get("judge_identity") != expected_judge_identity:
            raise ValueError("STEP74_JUDGE_IDENTITY_MISMATCH")
        smoke_data = manifest.get("runtime_smoke")
        if not isinstance(smoke_data, dict):
            raise ValueError("STEP74_REAL_SMOKE_GATE_REQUIRED")
        smoke = RuntimeSmokeEvidence(
            settings_preflight=smoke_data.get("settings_preflight"),
            generator_smoke=smoke_data.get("generator"),
            judge_smoke=smoke_data.get("judge"),
            source=smoke_data.get("source"),
        )
        smoke.validate(allow_test_fake=allow_test_smoke)
        expected_mode = "OFFLINE_TEST" if allow_test_smoke else "OFFICIAL_REAL_RUNTIME"
        if manifest.get("execution_mode") != expected_mode:
            raise ValueError("STEP74_RUNTIME_EXECUTION_MODE_MISMATCH")
        _, expected_cases = select_eligible_cases()
        expected = {case["case_id"]: (case["split"], case["bucket"]) for case in expected_cases}
        row_ids = [row.get("case_id") for row in rows]
        if len(rows) != 45 or len(set(row_ids)) != 45 or set(row_ids) != set(expected):
            raise ValueError("STEP74_STAGE_A_CASE_SET_MISMATCH")
        for row in rows:
            if row.get("run_id") != run_id or (row.get("split"), row.get("bucket")) != expected[row["case_id"]]:
                raise ValueError("STEP74_STAGE_A_CASE_IDENTITY_MISMATCH")
            if row.get("execution_mode") != expected_mode:
                raise ValueError("STEP74_CASE_EXECUTION_MODE_MISMATCH")
            if any(row.get(key) != value for key, value in expected_identity.items()):
                raise ValueError("STEP74_CASE_ARTIFACT_IDENTITY_MISMATCH")
            if row.get("generator_identity") != generator_identity or row.get("judge_identity") != expected_judge_identity:
                raise ValueError("STEP74_CASE_MODEL_IDENTITY_MISMATCH")
            answer = row.get("generated_answer")
            if not isinstance(answer, str) or not answer.strip() or row.get("generator", {}).get("status") != "SUCCESS":
                raise ValueError("HUMAN_CALIBRATION_STALE")
            if row.get("generated_answer_sha256") != answer_sha256(answer):
                raise ValueError("HUMAN_CALIBRATION_STALE")

    async def _resume_stage_b_rows(self, *, rows: list[dict], annotations: list[dict], run_id: str,
                                   manifest: dict) -> dict:
        self._validate_stage_a_identity(
            rows, manifest, run_id, allow_test_smoke=manifest.get("execution_mode") == "OFFLINE_TEST"
        )
        parsed = validate_annotations(annotations, rows, require_approved=True)
        judged: dict[str, dict] = {}
        outputs = []
        for source_row in rows:
            row = dict(source_row)
            case = {"case_id": row["case_id"], "question": row["question"],
                    "expected_information": row["expected_information"],
                    "reference_answer": row.get("reference_answer")}
            try:
                judge_call = await self.judge.evaluate(case, row["generated_answer"], row["fixed_evidence"])
                if isinstance(judge_call, JudgeCallResult):
                    result = judge_call.result
                    latency_ms = judge_call.latency_ms
                    token_usage = judge_call.token_usage
                    request_id = judge_call.request_id
                    attempt_count = judge_call.attempt_count
                else:
                    result, latency_ms, token_usage, request_id, attempt_count = judge_call, None, None, None, 1
                result.validate_evidence_ids(row["case_id"], set(row["fixed_evidence_ids"]))
                value = result.model_dump(mode="json")
                row.update({
                    "judge": {"status": "SUCCESS", "provider": "OpenAI API", "api": "Responses API",
                              "model": JUDGE_MODEL, "attempt_count": attempt_count,
                              "latency_ms": latency_ms, "request_id": request_id,
                              "token_usage": token_usage, "error": None},
                    "dimension_scores": {name: value["dimension_scores"][name]["score"]
                                         for name in value["dimension_scores"]},
                    "claim_faithfulness": value["claims"],
                    "critical_failures": value["critical_failures"],
                    "generation_case_status": "CRITICAL_FAILURE" if value["critical_failures"] else "BASELINE_SCORED",
                    "generation_case_pass": False if value["critical_failures"] else None,
                })
                if row["case_id"] in CALIBRATION_IDS:
                    judged[row["case_id"]] = {
                        "scores": row["dimension_scores"], "critical_failures": row["critical_failures"]
                    }
            except Exception as exc:
                code = exc.code if isinstance(exc, JudgeTechnicalFailure) else "JUDGE_TECHNICAL_FAILURE"
                row.update({
                    "judge": {"status": "TECHNICAL_FAILURE", "provider": "OpenAI API", "api": "Responses API",
                              "model": JUDGE_MODEL, "attempt_count": 1, "error": {"code": code}},
                    "dimension_scores": None, "claim_faithfulness": None,
                    "generation_case_status": "JUDGE_TECHNICAL_FAILURE", "generation_case_pass": None,
                })
            outputs.append(row)
        agreement = None
        if set(judged) == set(CALIBRATION_IDS) and len(judged) == 30:
            agreement = calibration_agreement(parsed, judged, run_id=run_id)
            stage_b_api_calls = sum(
                row.get("judge", {}).get("attempt_count") or 0 for row in outputs
                if row.get("judge", {}).get("status") != "NOT_RUN"
            )
            total_api_calls = manifest.get("runtime_api_calls", 0) + stage_b_api_calls
            agreement.update({
                "run_status": "STAGE_B_COMPLETE",
                "stage_a_started": True,
                "dataset_name": DATASET_NAME,
                "dataset_version": DATASET_VERSION,
                "dataset_schema_version": DATASET_SCHEMA_VERSION,
                "evaluation_step": "7.4",
                "eligible_case_policy_version": ELIGIBLE_CASE_POLICY_VERSION,
                "fixed_evidence_policy_version": FIXED_EVIDENCE_POLICY_VERSION,
                "fixed_memory_policy_version": FIXED_MEMORY_POLICY_VERSION,
                "human_annotation_version": HUMAN_ANNOTATION_VERSION,
                "rubric_version": RUBRIC_VERSION,
                "judge_prompt_version": JUDGE_PROMPT_VERSION,
                "execution_mode": manifest.get("execution_mode"),
                "eligible_case_count": manifest["eligible_case_count"],
                "case_counts_by_split": manifest["case_counts_by_split"],
                "case_counts_by_bucket": manifest["case_counts_by_bucket"],
                "generator_model": manifest["generator_model"],
                "judge_model": manifest["judge_model"],
                "generator_identity": manifest["generator_identity"],
                "judge_identity": manifest["judge_identity"],
                "human_calibration_case_count": 30,
                "human_calibration_packet_created": True,
                "human_calibration_packet_status": "HUMAN_APPROVED",
                "human_calibration_draft_count": 0,
                "human_calibration_status": "30 HUMAN_APPROVED; HASHES_VALIDATED",
                "human_approved_count": 30,
                "generator_success_count": manifest["generator_success_count"],
                "generator_technical_failure_count": manifest["generator_technical_failure_count"],
                "judge_success_count": sum(row["judge"]["status"] == "SUCCESS" for row in outputs),
                "judge_technical_failure_count": sum(row["judge"]["status"] == "TECHNICAL_FAILURE" for row in outputs),
                "judge_not_run_count": sum(row["judge"]["status"] == "NOT_RUN" for row in outputs),
                "judge_calibration_success_count": 30,
                "runtime_api_calls": total_api_calls,
                "status": "COMPLETE_BASELINE_ONLY",
            })
        return {"case_results": outputs, "agreement": agreement, "run_id": run_id,
                "status": "STAGE_B_COMPLETE" if agreement else "JUDGE_CALIBRATION_INCOMPLETE",
                "calibration_judge_success_count": len(judged),
                "calibration_case_count_expected": 30}

    async def resume_stage_b_from_run(self, run_id: str, *, run_dir: Path | None = None,
                                      annotation_file: Path | None = None) -> dict:
        if not run_id or run_id.strip() != run_id:
            raise ValueError("STEP74_RUN_ID_REQUIRED")
        run_dir = run_dir or RUNS_ROOT / run_id
        if run_dir.name != run_id or not run_dir.is_dir():
            raise ValueError("STEP74_RUN_ID_NOT_FOUND")
        generation = run_dir / "generation"
        manifest_path = generation / "manifest.json"
        cases_path = generation / "cases.jsonl"
        if not manifest_path.is_file() or not cases_path.is_file():
            raise ValueError("STEP74_STAGE_A_ARTIFACT_MISSING")
        summary_path = generation / "summary.json"
        agreement_path = generation / "calibration-agreement.json"
        if not summary_path.is_file() or not agreement_path.is_file():
            raise ValueError("STEP74_STAGE_A_ARTIFACT_MISSING")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("run_status") != "REVIEW_REQUIRED_HUMAN_CALIBRATION":
            raise ValueError("STEP74_RUN_NOT_RESUMABLE")
        if manifest.get("execution_mode") != "OFFICIAL_REAL_RUNTIME":
            raise ValueError("STEP74_OFFICIAL_STAGE_A_ARTIFACT_REQUIRED")
        stage_b_dir = generation / "stage-b"
        if stage_b_dir.exists():
            raise ValueError("STEP74_STAGE_B_ALREADY_FINALIZED")
        verify_stage_a_case_file_binding(manifest, cases_path.read_bytes())
        rows = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line]
        self._validate_stage_a_identity(rows, manifest, run_id)
        stage_a_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        stage_a_agreement = json.loads(agreement_path.read_text(encoding="utf-8"))
        validate_artifact_metadata(manifest, rows, stage_a_summary, stage_a_agreement)
        if manifest.get("human_calibration_case_ids") != list(CALIBRATION_IDS) \
                or manifest.get("human_calibration_case_count") != 30 \
                or manifest.get("human_approved_count") != 0:
            raise ValueError("STEP74_STAGE_A_CALIBRATION_BINDING_MISMATCH")
        annotation_manifest, annotations = load_annotation_package(annotation_file)
        validate_annotation_manifest(annotation_manifest, run_id=run_id)
        # Validate stale bindings before a judge request can be made.
        validate_annotations(annotations, rows, require_approved=True)
        before_hashes = {row["case_id"]: answer_sha256(row["generated_answer"]) for row in rows}
        result = await self._resume_stage_b_rows(rows=rows, annotations=annotations, run_id=run_id,
                                                 manifest=manifest)
        if result["agreement"] is None:
            return result
        updated_rows = result["case_results"]
        for row in updated_rows:
            row["run_status"] = "STAGE_B_COMPLETE"
            if row["case_id"] in CALIBRATION_IDS:
                row.setdefault("calibration", {}).update({
                    "human_review_status": "HUMAN_APPROVED",
                    "packet_status": "HUMAN_APPROVED",
                    "annotation_version": HUMAN_ANNOTATION_VERSION,
                })
        if any(answer_sha256(row["generated_answer"]) != before_hashes.get(row["case_id"])
               or row.get("generated_answer_sha256") != before_hashes.get(row["case_id"])
               for row in updated_rows):
            raise RuntimeError("Stage B attempted to modify a frozen generated answer")
        summary = build_stage_a_summary(run_id, updated_rows, identity=manifest)
        summary["run_status"] = "STAGE_B_COMPLETE"
        summary["human_calibration_packet_status"] = "HUMAN_APPROVED"
        summary["human_calibration_status"] = "30 HUMAN_APPROVED; HASHES_VALIDATED"
        summary["human_calibration_draft_count"] = 0
        summary["human_approved_count"] = 30
        summary["judge_success_count"] = sum(row["judge"]["status"] == "SUCCESS" for row in updated_rows)
        summary["judge_technical_failure_count"] = sum(row["judge"]["status"] == "TECHNICAL_FAILURE" for row in updated_rows)
        summary["judge_not_run_count"] = sum(row["judge"]["status"] == "NOT_RUN" for row in updated_rows)
        stage_b_api_calls = sum(
            row.get("judge", {}).get("attempt_count") or 0 for row in updated_rows
            if row.get("judge", {}).get("status") != "NOT_RUN"
        )
        summary["runtime_api_calls"] = manifest["runtime_api_calls"] + stage_b_api_calls
        summary["judge_technical_success_rate_on_generated_answers"] = (
            summary["judge_success_count"] / max(1, summary["judge_success_count"] + summary["judge_technical_failure_count"])
        )
        dimensions = [
            row["dimension_scores"] for row in updated_rows if row.get("dimension_scores") is not None
        ]
        names = list(dimensions[0]) if dimensions else []
        def score_metrics(group: list[dict]) -> dict:
            scored = [row["dimension_scores"] for row in group if row.get("dimension_scores") is not None]
            return {
                "case_count": len(group),
                "generator_success_count": sum(row["generator"]["status"] == "SUCCESS" for row in group),
                "judge_success_count": sum(row["judge"]["status"] == "SUCCESS" for row in group),
                "judge_technical_failure_count": sum(row["judge"]["status"] == "TECHNICAL_FAILURE" for row in group),
                "mean_score_by_dimension": {
                    name: sum(score[name] for score in scored) / len(scored) for name in names
                } if scored else None,
                "critical_failure_case_count": sum(bool(row.get("critical_failures")) for row in group),
            }
        summary["mean_score_by_dimension"] = {
            name: sum(scores[name] for scores in dimensions) / len(dimensions) for name in names
        } if dimensions else None
        summary["score_distribution_by_dimension"] = {
            name: {str(score): sum(scores[name] == score for scores in dimensions) for score in (0, 1, 2)}
            for name in names
        } if dimensions else None
        summary["cases_with_score_0_by_dimension"] = {
            name: sum(scores[name] == 0 for scores in dimensions) for name in names
        } if dimensions else None
        summary["metrics_by_split"] = {
            split: score_metrics([row for row in updated_rows if row["split"] == split])
            for split in ("DEVELOPMENT", "HOLDOUT")
        }
        summary["metrics_by_bucket"] = {
            bucket: score_metrics([row for row in updated_rows if row["bucket"] == bucket])
            for bucket in sorted({row["bucket"] for row in updated_rows})
        }
        successful_judges = [row for row in updated_rows if row["judge"]["status"] == "SUCCESS"]
        summary["critical_failure_rate_among_judged_cases"] = (
            sum(bool(row.get("critical_failures")) for row in successful_judges) / len(successful_judges)
            if successful_judges else None
        )
        verdict_counts = {verdict: 0 for verdict in ("SUPPORTED", "UNSUPPORTED", "CONTRADICTED")}
        for row in successful_judges:
            for claim in row.get("claim_faithfulness") or []:
                verdict_counts[claim["verdict"]] += 1
        summary["claim_verdict_counts"] = verdict_counts
        summary["cases_with_unsupported_claims"] = sum(
            any(claim["verdict"] == "UNSUPPORTED" for claim in (row.get("claim_faithfulness") or []))
            for row in successful_judges
        )
        summary["cases_with_contradicted_claims"] = sum(
            any(claim["verdict"] == "CONTRADICTED" for claim in (row.get("claim_faithfulness") or []))
            for row in successful_judges
        )
        summary["critical_failure_case_count"] = sum(bool(row.get("critical_failures")) for row in updated_rows)
        summary["critical_failure_counts_by_type"] = {
            code: sum(code in row.get("critical_failures", []) for row in updated_rows)
            for code in CRITICAL_FAILURES
        }
        summary["generation_case_status_counts"] = {
            status: sum(row.get("generation_case_status") == status for row in updated_rows)
            for status in sorted({row.get("generation_case_status") for row in updated_rows})
        }
        summary["human_approved_count"] = sum(row["review_status"] == "HUMAN_APPROVED" for row in annotations)
        summary["judge_calibration_success_count"] = result["calibration_judge_success_count"]
        judge_latencies = [row["judge"].get("latency_ms") for row in successful_judges
                           if row["judge"].get("latency_ms") is not None]
        summary["judge_latency_ms_mean"] = sum(judge_latencies) / len(judge_latencies) if judge_latencies else None
        summary["judge_token_usage"] = {
            name: sum(
                row["judge"].get("token_usage", {}).get(name) or 0
                for row in successful_judges
                if type(row["judge"].get("token_usage", {}).get(name)) is int
            ) or None
            for name in ("input_tokens", "output_tokens", "total_tokens")
        }
        agreement = result["agreement"]
        summary["human_judge_agreement_headline"] = {
            "macro_exact_agreement_rate": agreement["macro_exact_agreement_rate"],
            "overall_mean_absolute_score_difference": agreement["overall_mean_absolute_score_difference"],
            "agreement_gate": None,
        }
        stage_b_cases = ("".join(canonical_json(row) + "\n" for row in updated_rows)).encode("utf-8")
        stage_b_manifest = dict(manifest)
        stage_b_manifest.update({
            "run_status": "STAGE_B_COMPLETE",
            "human_calibration_packet_status": "HUMAN_APPROVED",
            "human_calibration_status": "30 HUMAN_APPROVED; HASHES_VALIDATED",
            "human_calibration_draft_count": 0,
            "timestamp_finalized": datetime.now(UTC).isoformat(),
            "human_approved_count": 30,
            "judge_calibration_success_count": 30,
            "judge_success_count": summary["judge_success_count"],
            "judge_technical_failure_count": summary["judge_technical_failure_count"],
            "judge_not_run_count": summary["judge_not_run_count"],
            "runtime_api_calls": summary["runtime_api_calls"],
            "cases_file_sha256": hashlib.sha256(stage_b_cases).hexdigest(),
            "stage_a_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "stage_a_cases_file_sha256": manifest["cases_file_sha256"],
        })
        validate_artifact_metadata(stage_b_manifest, updated_rows, summary, agreement)
        stage_b_dir.mkdir(parents=True, exist_ok=False)
        (stage_b_dir / "cases.jsonl").write_bytes(stage_b_cases)
        write_json(stage_b_dir / "summary.json", summary)
        write_json(stage_b_dir / "calibration-agreement.json", agreement)
        write_json(stage_b_dir / "manifest.json", stage_b_manifest)
        result["stage_b_dir"] = str(stage_b_dir)
        return result
