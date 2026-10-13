from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.ai.llm.schemas import GenerationConfig, LLMGenerationResult
from app.ai.llm.service import LLMGenerationService
from app.ai.prompting.builder import PromptContextBuilder
from app.core.config import Settings
from app.evaluation.step74.annotations import (
    ANNOTATION_ROOT,
    CALIBRATION_IDS,
    annotation_package_paths,
    answer_sha256,
    load_annotation_package,
    make_draft_packet,
    validate_annotation_manifest,
    validate_annotations,
    write_source_controlled_template,
)
from app.evaluation.step74 import annotations as annotation_module
from app.evaluation.step74.artifacts import (
    build_stage_a_summary, canonical_json, derive_stage_a_state,
    validate_artifact_metadata, write_jsonl,
    verify_stage_a_case_file_binding, write_stage_a,
)
from app.evaluation.step74.contracts import (
    CRITICAL_FAILURES,
    DATASET_NAME,
    DATASET_SCHEMA_VERSION,
    DATASET_VERSION,
    DIMENSIONS,
    ELIGIBLE_CASE_POLICY_VERSION,
    FIXED_EVIDENCE_POLICY_VERSION,
    FIXED_MEMORY_POLICY_VERSION,
    GENERATOR_MODEL,
    HUMAN_ANNOTATION_VERSION,
    JUDGE_MODEL,
    JUDGE_PROMPT_VERSION,
    RUBRIC_VERSION,
    AnnotationStatus,
    GenerationJudgeResult,
    HumanGenerationAnnotation,
    JudgeCallResult,
    JudgeTechnicalFailure,
)
from app.evaluation.step74.eligibility import (
    EXPECTED_SPLIT_BUCKETS,
    EXCLUDED_BUCKETS,
    select_eligible_cases,
)
from app.evaluation.step74.fixed_evidence import FixedEvidenceResolver
from app.evaluation.step74.judge import OpenAIResponsesGenerationJudge, judge_json_schema
from app.evaluation.step74.metrics import calibration_agreement, dimension_agreement
from app.evaluation.step74.prompt import FixedConversationMemoryFactory, ProductionPromptFactory
from app.evaluation.step74.runner import Step74Runner
from app.evaluation.step74.smoke import RuntimeSmokeEvidence
from app.evaluation.step74.rubrics import RUBRICS, rubrics_for_prompt


class Counter:
    def count(self, text: str) -> int:
        return max(1, len(text) // 4)


class LargeEvidenceCounter(Counter):
    def count(self, text: str) -> int:
        if "Type: VOCABULARY" in text or "Type: GRAMMAR" in text:
            return 500_000
        return super().count(text)


@pytest.fixture
def workspace_tmp_path(request):
    path = ROOT / "tmp" / ".step74-test-data" / request.node.name / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    yield path


def settings(**overrides):
    values = {
        "llm_model": GENERATOR_MODEL, "llm_temperature": 0.2,
        "llm_max_output_tokens": 800, "llm_reasoning_effort": "none",
        "llm_model_input_limit": 400_000, "llm_request_timeout_seconds": 60,
        "llm_max_transient_retries": 1, "rag_memory_max_turns": 3,
        "llm_api_key": None,
    }
    values.update(overrides)
    return Settings.model_construct(**values)


def valid_judge_payload(case_id: str, evidence_id: str) -> dict:
    return {
        "schema_version": "1.0.0", "case_id": case_id,
        "dimension_scores": {name: {"score": 2, "rationale": "Supported by the supplied case."}
                             for name in DIMENSIONS},
        "claims": [{"claim_id": "C1", "claim_text": "A material teaching claim.",
                    "verdict": "SUPPORTED", "supporting_evidence_ids": [evidence_id],
                    "concise_rationale": "The fixed evidence supports it."}],
        "critical_failures": [], "concise_overall_rationale": "Concise evaluation rationale.",
    }


def offline_smoke_evidence() -> RuntimeSmokeEvidence:
    return RuntimeSmokeEvidence(
        settings_preflight="PASS",
        source="TEST_FAKE",
        generator_smoke={"status": "PASS", "provider": "openai", "model": GENERATOR_MODEL,
                         "config": {"model": GENERATOR_MODEL, "temperature": 0.2,
                                    "max_output_tokens": 800, "reasoning_effort": "none", "tools": []},
                         "api_calls": 1},
        judge_smoke={"status": "PASS", "provider": "OpenAI API", "api": "Responses API",
                     "model": JUDGE_MODEL, "reasoning_effort": "none", "temperature": 0,
                     "max_output_tokens": 1600, "structured_output": True, "tools": [], "api_calls": 1},
    )


def fake_stage_a_manifest(run_id: str, rows: list[dict]) -> dict:
    generator_identity = {
        "provider": "openai", "model": GENERATOR_MODEL, "temperature": 0.2,
        "max_output_tokens": 800, "reasoning_effort": "none", "model_input_limit": 400_000,
        "timeout_seconds": 60, "max_transient_retries": 1, "streaming": False, "tools": [],
    }
    judge_identity = {"provider": "OpenAI API", "api": "Responses API", "model": JUDGE_MODEL,
                      "reasoning_effort": "none", "temperature": 0, "max_output_tokens": 1600,
                      "structured_output": True, "tools": []}
    return {
        "run_id": run_id, "run_status": "OFFLINE_TEST_ONLY",
        "execution_mode": "OFFLINE_TEST",
        "evaluation_step": "7.4", "dataset_name": DATASET_NAME,
        "dataset_version": DATASET_VERSION, "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "eligible_case_policy_version": ELIGIBLE_CASE_POLICY_VERSION,
        "fixed_evidence_policy_version": FIXED_EVIDENCE_POLICY_VERSION,
        "fixed_memory_policy_version": FIXED_MEMORY_POLICY_VERSION,
        "rubric_version": RUBRIC_VERSION, "human_annotation_version": HUMAN_ANNOTATION_VERSION,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "generator_model": GENERATOR_MODEL, "judge_model": JUDGE_MODEL,
        "generator_identity": generator_identity, "judge_identity": judge_identity,
        "eligible_case_count": len(rows),
        "runtime_api_calls": 2,
        "stage_a_started": False,
        "human_calibration_case_count": 0, "human_calibration_packet_created": False,
        "human_calibration_packet_status": "NOT_CREATED", "human_calibration_draft_count": 0,
        "human_calibration_status": "NOT_CREATED", "human_annotation_version": HUMAN_ANNOTATION_VERSION,
        "human_approved_count": 0,
        "generator_success_count": sum(row.get("generator", {}).get("status") == "SUCCESS" for row in rows),
        "generator_technical_failure_count": sum(row.get("generator", {}).get("status") != "SUCCESS" for row in rows),
        "judge_success_count": sum(row.get("judge", {}).get("status") == "SUCCESS" for row in rows),
        "judge_technical_failure_count": sum(row.get("judge", {}).get("status") == "TECHNICAL_FAILURE" for row in rows),
        "judge_not_run_count": sum(row.get("judge", {}).get("status") == "NOT_RUN" for row in rows),
        "judge_calibration_success_count": 0,
        "case_counts_by_split": {split: sum(row["split"] == split for row in rows)
                                  for split in ("DEVELOPMENT", "HOLDOUT")},
        "case_counts_by_bucket": {
            split: {bucket: sum(row["split"] == split and row["bucket"] == bucket for row in rows)
                    for bucket in sorted({row["bucket"] for row in rows if row["split"] == split})}
            for split in ("DEVELOPMENT", "HOLDOUT")
        },
        "runtime_smoke": offline_smoke_evidence().artifact(allow_test_fake=True),
    }


def fake_stage_a_rows(run_id: str) -> list[dict]:
    _, cases = select_eligible_cases()
    identity = {
        "evaluation_step": "7.4", "dataset_name": DATASET_NAME,
        "dataset_version": DATASET_VERSION, "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "eligible_case_policy_version": ELIGIBLE_CASE_POLICY_VERSION,
        "fixed_evidence_policy_version": FIXED_EVIDENCE_POLICY_VERSION,
        "fixed_memory_policy_version": FIXED_MEMORY_POLICY_VERSION,
        "rubric_version": RUBRIC_VERSION, "human_annotation_version": HUMAN_ANNOTATION_VERSION,
        "judge_prompt_version": JUDGE_PROMPT_VERSION, "execution_mode": "OFFLINE_TEST",
        "generator_identity": {
            "provider": "openai", "model": GENERATOR_MODEL, "temperature": 0.2,
            "max_output_tokens": 800, "reasoning_effort": "none", "model_input_limit": 400_000,
            "timeout_seconds": 60, "max_transient_retries": 1, "streaming": False, "tools": [],
        },
        "judge_identity": {"provider": "OpenAI API", "api": "Responses API", "model": JUDGE_MODEL,
                            "reasoning_effort": "none", "temperature": 0, "max_output_tokens": 1600,
                            "structured_output": True, "tools": []},
    }
    return [{
        **identity, "run_id": run_id, "run_status": "OFFLINE_TEST_ONLY", "case_id": case["case_id"],
        "split": case["split"], "bucket": case["bucket"],
        "question": case["question"], "expected_information": case["expected_information"],
        "fixed_evidence_ids": ["e1"],
        "fixed_evidence": [{"evidence_ids": ["e1"], "llm_visible_content": "A fixed reviewed evidence block."}],
        "generated_answer": "Frozen generated answer for " + case["case_id"],
        "generated_answer_sha256": answer_sha256("Frozen generated answer for " + case["case_id"]),
        "generator": {"status": "SUCCESS", "provider": "openai", "model": GENERATOR_MODEL},
        "judge": {"status": "NOT_RUN"}, "dimension_scores": None,
        "claim_faithfulness": None, "critical_failures": [],
        "generation_case_status": "NOT_JUDGED", "generation_case_pass": None,
        "calibration": {"in_human_subset": case["case_id"] in CALIBRATION_IDS,
                        "human_review_status": None,
                        "packet_status": "NOT_CREATED" if case["case_id"] in CALIBRATION_IDS else None,
                        "annotation_version": HUMAN_ANNOTATION_VERSION},
    } for case in cases]


def approved_annotations_for(rows: list[dict], run_id: str) -> list[dict]:
    drafts = make_draft_packet(rows, run_id=run_id)
    return [row | {
        "review_status": AnnotationStatus.HUMAN_APPROVED.value,
        "scores": {name: 1 for name in DIMENSIONS},
        "claim_faithfulness": [{"claim_id": "C1", "claim_text": "Reviewed claim.",
            "verdict": "SUPPORTED", "supporting_evidence_ids": ["e1"],
            "concise_note": "Supported by the reviewed fixed evidence."}],
    } for row in drafts]


def test_eligibility_is_exact_45_36_9_and_excludes_refusals():
    _, cases = select_eligible_cases()
    assert len(cases) == 45
    assert sum(row["split"] == "DEVELOPMENT" for row in cases) == 36
    assert sum(row["split"] == "HOLDOUT" for row in cases) == 9
    assert not ({row["bucket"] for row in cases} & EXCLUDED_BUCKETS)
    for split, expected in EXPECTED_SPLIT_BUCKETS.items():
        actual = {bucket: sum(row["split"] == split and row["bucket"] == bucket for row in cases)
                  for bucket in expected}
        assert actual == expected


def test_five_frozen_rubrics_are_independent_with_all_three_levels():
    assert tuple(RUBRICS) == DIMENSIONS
    for rubric in RUBRICS.values():
        assert set(rubric) == {"ground_truth", "0", "1", "2"}
        assert all(isinstance(rubric[str(score)], str) and rubric[str(score)] for score in (0, 1, 2))
    prompt_rubrics = rubrics_for_prompt()
    assert prompt_rubrics["rubric_version"] == "lesson-chat-generation-rubric/v1"
    assert set(prompt_rubrics["critical_failures"]) == set(CRITICAL_FAILURES)


def test_eligible_order_is_stable_and_multiturn_is_included():
    _, cases = select_eligible_cases()
    assert cases == sorted(cases, key=lambda row: (row["split"], row["case_id"]))
    assert sum(row["bucket"] == "MULTI_TURN_CONTEXT" for row in cases) == 10


def test_fixed_evidence_resolves_exact_internal_and_external_sources_without_network():
    _, cases = select_eligible_cases()
    resolver = FixedEvidenceResolver()
    internal = next(row for row in cases if row["bucket"] == "CURRENT_LESSON_ANSWERABLE")
    evidence = resolver.resolve_case(internal)
    assert evidence[0].stable_locator == internal["required_evidence"][0]["stable_locator"]
    assert evidence[0].evidence_ids == (internal["required_evidence"][0]["evidence_id"],)
    assert evidence[0].content_sha256 == hashlib.sha256(evidence[0].content.encode()).hexdigest()
    external = next(row for row in cases if row["bucket"] == "TRUSTED_EXTERNAL_FALLBACK")
    ext = resolver.resolve_case(external)[0]
    assert ext.source_id.startswith("external.")
    assert ext.external.url.startswith("https://")
    assert "reviewed_claims" not in ext.llm_visible_content
    assert resolver.external_manifest["runtime_external_retrieval_implemented"] is False


def test_prompt_context_builder_receives_fixed_candidates_and_preserves_source_map():
    _, cases = select_eligible_cases()
    case = next(row for row in cases if row["bucket"] == "CURRENT_LESSON_ANSWERABLE")
    resolver = FixedEvidenceResolver()
    fixed = resolver.resolve_case(case)
    counter = Counter()
    factory = ProductionPromptFactory(
        prompt_builder=PromptContextBuilder(token_counter=counter), token_counter=counter,
        generation_config=GenerationConfig(),
    )
    package, metadata = factory.build(case, fixed)
    assert len(package.context_blocks) == len(fixed)
    assert package.context_blocks[0].source_label == "S1"
    assert "S1" in package.source_map
    assert package.source_map["S1"].locator_metadata["stable_locator"] == fixed[0].stable_locator
    assert fixed[0].candidate.locator_metadata["score_semantics"] == "NOT_APPLICABLE_FIXED_EVIDENCE"
    assert metadata["prompt_package_sha256"]


def test_fixed_external_evidence_uses_production_context_builder_and_registry_claims():
    _, cases = select_eligible_cases()
    case = next(row for row in cases if row["bucket"] == "TRUSTED_EXTERNAL_FALLBACK")
    resolver = FixedEvidenceResolver()
    fixed = resolver.resolve_case(case)
    counter = Counter()
    package, _ = ProductionPromptFactory(
        prompt_builder=PromptContextBuilder(token_counter=counter), token_counter=counter,
        generation_config=GenerationConfig(),
    ).build(case, fixed)
    assert package.context_blocks[0].source_label == "S1"
    assert package.source_map["S1"].url == fixed[0].external.url
    assert package.context_blocks[0].text


def test_fixed_evidence_budget_exhaustion_is_normalized():
    _, cases = select_eligible_cases()
    case = next(row for row in cases if row["bucket"] == "CURRENT_LESSON_ANSWERABLE")
    resolver = FixedEvidenceResolver()
    counter = LargeEvidenceCounter()
    factory = ProductionPromptFactory(
        prompt_builder=PromptContextBuilder(token_counter=counter), token_counter=counter,
        generation_config=GenerationConfig(),
    )
    with pytest.raises(RuntimeError, match="FIXED_EVIDENCE_CONTEXT_BUDGET_EXHAUSTED"):
        factory.build(case, resolver.resolve_case(case))


def test_fixed_multiturn_memory_stays_separate_from_evidence_and_keeps_order():
    _, cases = select_eligible_cases()
    case = next(row for row in cases if row["bucket"] == "MULTI_TURN_CONTEXT")
    resolver = FixedEvidenceResolver()
    fixed = resolver.resolve_case(case)
    counter = Counter()
    package, metadata = ProductionPromptFactory(
        prompt_builder=PromptContextBuilder(token_counter=counter), token_counter=counter,
        generation_config=GenerationConfig(),
    ).build(case, fixed)
    memory = package.conversation_memory
    assert memory and memory.status == "APPLIED"
    assert memory.turns[0].user_text == case["conversation_context"][0]["user_text"]
    assert len(package.context_blocks) == len(fixed)
    assert all(turn.user_message_id not in package.selected_chunk_ids for turn in memory.turns)
    assert metadata["fixed_memory"]["selected_turn_count"] == memory.selected_turn_count
    assert "S" not in "".join(turn.user_text for turn in memory.turns)


def test_fixed_memory_reuses_production_assistant_citation_sanitization():
    memory = FixedConversationMemoryFactory(Counter(), max_turns=3).build([
        {"user_text": "Explain that again", "assistant_text": "This prior reply cited [S1]."},
        {"user_text": "Another prior question", "assistant_text": "[S2]"},
    ], token_budget=100)
    assert memory.selected_turn_count == 1
    assert memory.omitted_turn_count == 1
    assert memory.turns[0].assistant_text == "This prior reply cited ."


class CapturingProvider:
    def __init__(self, *, text="A supported answer.", failure=None):
        self.request = None
        self.text = text
        self.failure = failure

    async def generate(self, request):
        self.request = request
        if self.failure:
            raise self.failure
        return LLMGenerationResult(
            text=self.text, provider="openai", model=GENERATOR_MODEL,
            input_tokens=23, output_tokens=7, total_tokens=30,
            provider_preflight_input_tokens=23, latency_ms=12, attempt_count=1,
            provider_request_id=None,
        )


def test_generation_uses_existing_llm_generation_service_serializer_provider_seam():
    _, cases = select_eligible_cases()
    case = next(row for row in cases if row["bucket"] == "CURRENT_LESSON_ANSWERABLE")
    provider = CapturingProvider()
    service = LLMGenerationService(provider)
    runner = Step74Runner(settings=settings(), generation_service=service, token_counter=Counter())
    result = asyncio.run(runner.generate_case(case, run_id="offline-test"))
    assert result["generator"]["status"] == "SUCCESS"
    assert provider.request.model == GENERATOR_MODEL
    assert provider.request.temperature == 0.2
    assert provider.request.max_output_tokens == 800
    assert provider.request.historical_messages == ()
    assert result["generated_answer_sha256"] == answer_sha256(result["generated_answer"])
    assert result["judge"]["status"] == "NOT_RUN"


def test_generation_technical_failure_and_blank_answer_have_no_semantic_scores():
    _, cases = select_eligible_cases()
    case = next(row for row in cases if row["bucket"] == "CURRENT_LESSON_ANSWERABLE")
    failure_runner = Step74Runner(
        settings=settings(), generation_service=LLMGenerationService(CapturingProvider(failure=RuntimeError("transport"))),
        token_counter=Counter(),
    )
    failed = asyncio.run(failure_runner.generate_case(case, run_id="failure"))
    assert failed["generator"]["status"] == "TECHNICAL_FAILURE"
    assert failed["dimension_scores"] is None and failed["judge"]["status"] == "NOT_RUN"
    blank_runner = Step74Runner(
        settings=settings(), generation_service=LLMGenerationService(CapturingProvider(text="  ")),
        token_counter=Counter(),
    )
    blank = asyncio.run(blank_runner.generate_case(case, run_id="blank"))
    assert blank["generator"]["error"]["code"] == "EMPTY_GENERATOR_RESPONSE"
    assert blank["generated_answer"] is None and blank["dimension_scores"] is None


def test_generator_preflight_rejects_production_model_change():
    with pytest.raises(Exception):
        Step74Runner(settings=settings(llm_model="other-model"), generation_service=object(), token_counter=Counter())


class FakeResponses:
    def __init__(self, payload, *, model=JUDGE_MODEL):
        self.payload = payload
        self.model = model
        self.kwargs = None
        self.responses = self

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(status="completed", model=self.model, output_text=json.dumps(self.payload),
                               usage=SimpleNamespace(input_tokens=20, output_tokens=10, total_tokens=30),
                               _request_id="safe-request-id")


def test_d100_judge_config_structured_schema_and_evidence_validation():
    _, cases = select_eligible_cases()
    case = next(row for row in cases if row["bucket"] == "CURRENT_LESSON_ANSWERABLE")
    fixed = FixedEvidenceResolver().resolve_case(case)[0].artifact()
    evidence_id = fixed["evidence_ids"][0]
    client = FakeResponses(valid_judge_payload(case["case_id"], evidence_id))
    judge = OpenAIResponsesGenerationJudge(settings=settings(), client=client)
    call = asyncio.run(judge.evaluate(case, "A supported answer.", [fixed]))
    assert isinstance(call, JudgeCallResult)
    assert call.result.case_id == case["case_id"]
    assert call.result.dimension_scores.answer_correctness.score == 2
    assert call.result.claims[0].supporting_evidence_ids == [evidence_id]
    kwargs = client.kwargs
    assert kwargs["model"] == JUDGE_MODEL
    assert kwargs["reasoning"] == {"effort": "none"}
    assert kwargs["temperature"] == 0 and kwargs["max_output_tokens"] == 1600
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["text"]["format"]["strict"] is True
    assert "tools" not in kwargs
    assert set(judge_json_schema()["properties"]["dimension_scores"]["required"]) == set(DIMENSIONS)


def test_d100_judge_missing_credential_is_normalized_without_sdk_call():
    judge = OpenAIResponsesGenerationJudge(settings=settings(llm_api_key=None))
    with pytest.raises(JudgeTechnicalFailure, match="JUDGE_PROVIDER_NOT_CONFIGURED"):
        judge._get_client()


def test_d100_judge_rejects_returned_model_identity_mismatch():
    _, cases = select_eligible_cases()
    case = next(row for row in cases if row["bucket"] == "CURRENT_LESSON_ANSWERABLE")
    fixed = FixedEvidenceResolver().resolve_case(case)[0].artifact()
    client = FakeResponses(valid_judge_payload(case["case_id"], fixed["evidence_ids"][0]), model="other-model")
    judge = OpenAIResponsesGenerationJudge(settings=settings(), client=client)
    with pytest.raises(JudgeTechnicalFailure, match="JUDGE_MODEL_IDENTITY_MISMATCH"):
        asyncio.run(judge.evaluate(case, "A supported answer.", [fixed]))


def test_judge_rejects_unknown_claim_evidence_and_wrong_case_or_critical_failure():
    payload = valid_judge_payload("case", "e1")
    result = GenerationJudgeResult.model_validate(payload)
    with pytest.raises(ValueError, match="unknown fixed evidence"):
        result.validate_evidence_ids("case", set())
    with pytest.raises(ValueError, match="case_id"):
        result.validate_evidence_ids("another", {"e1"})
    payload["critical_failures"] = ["FABRICATED_CITATION_OR_SOURCE"]
    with pytest.raises(ValueError):
        GenerationJudgeResult.model_validate(payload)
    assert set(CRITICAL_FAILURES) == {
        "SERIOUS_FACTUAL_ERROR", "UNSUPPORTED_CONFIDENT_CLAIM", "CONTRADICTED_BY_EVIDENCE"
    }


def test_judge_rejects_cross_field_faithfulness_and_critical_failure_contradictions():
    payload = valid_judge_payload("case", "e1")
    payload["claims"][0]["verdict"] = "CONTRADICTED"
    with pytest.raises(ValueError, match="contradicted claims"):
        GenerationJudgeResult.model_validate(payload)
    payload["critical_failures"] = ["CONTRADICTED_BY_EVIDENCE"]
    payload["dimension_scores"]["faithfulness_groundedness"]["score"] = 0
    assert GenerationJudgeResult.model_validate(payload)
    payload["claims"][0]["verdict"] = "SUPPORTED"
    with pytest.raises(ValueError, match="requires a contradicted claim"):
        GenerationJudgeResult.model_validate(payload)

    payload = valid_judge_payload("case", "e1")
    payload["claims"][0]["verdict"] = "UNSUPPORTED"
    payload["critical_failures"] = ["UNSUPPORTED_CONFIDENT_CLAIM"]
    with pytest.raises(ValueError, match="unsupported-confident"):
        GenerationJudgeResult.model_validate(payload)
    payload["dimension_scores"]["faithfulness_groundedness"]["score"] = 1
    assert GenerationJudgeResult.model_validate(payload)

    payload["critical_failures"] = []
    payload["dimension_scores"]["faithfulness_groundedness"]["score"] = 2
    with pytest.raises(ValueError, match="faithfulness 2"):
        GenerationJudgeResult.model_validate(payload)

    payload = valid_judge_payload("case", "e1")
    payload["claims"][0]["claim_id"] = "claim-one"
    with pytest.raises(ValueError):
        GenerationJudgeResult.model_validate(payload)
    payload = valid_judge_payload("case", "e1")
    payload["critical_failures"] = ["SERIOUS_FACTUAL_ERROR"]
    with pytest.raises(ValueError, match="correctness score 0"):
        GenerationJudgeResult.model_validate(payload)


def test_real_smoke_gate_requires_exact_passed_provider_and_request_identity():
    evidence = offline_smoke_evidence()
    evidence.validate(allow_test_fake=True)
    with pytest.raises(RuntimeError, match="REAL_SMOKE_GATE_REQUIRED"):
        evidence.validate()
    with pytest.raises(RuntimeError, match="REAL_SMOKE_GATE_REQUIRED"):
        RuntimeSmokeEvidence("PASS", evidence.generator_smoke, evidence.judge_smoke,
                             source="FAKE_TEST_RESULT").validate()
    with pytest.raises(RuntimeError, match="JUDGE_SMOKE_REQUIRED|IDENTITY_MISMATCH"):
        RuntimeSmokeEvidence("PASS", evidence.generator_smoke,
                             evidence.judge_smoke | {"max_output_tokens": 800}).validate()


def test_settings_smoke_preflight_rejects_missing_credential_without_exposing_value():
    from app.evaluation.step74.smoke import validate_settings_preflight

    config = GenerationConfig.from_settings(settings())
    with pytest.raises(RuntimeError, match="CREDENTIAL_UNAVAILABLE"):
        validate_settings_preflight(settings(app_env="test", debug=False, llm_api_key=None), config)


def test_human_calibration_exact_subset_draft_gate_and_stale_hash():
    _, cases = select_eligible_cases()
    chosen = {row["case_id"]: row for row in cases}
    rows = [{"case_id": case_id, "run_id": "run", "split": "DEVELOPMENT",
             "fixed_evidence_ids": ["e1"], "generator": {"status": "SUCCESS"},
             "generated_answer": "answer " + case_id,
             "generated_answer_sha256": answer_sha256("answer " + case_id)} for case_id in CALIBRATION_IDS]
    draft = make_draft_packet(rows, run_id="run")
    assert len(draft) == 30 and all(row["review_status"] == "DRAFT" for row in draft)
    assert all(row["scores"] is None for row in draft)
    with pytest.raises(ValueError, match="REVIEW_REQUIRED"):
        validate_annotations(draft, rows, require_approved=True)
    approved = [row | {"review_status": "HUMAN_APPROVED",
                       "scores": {name: 2 for name in DIMENSIONS},
                       "claim_faithfulness": [{"claim_id": "C1", "claim_text": "Reviewed claim.",
                           "verdict": "SUPPORTED", "supporting_evidence_ids": ["e1"],
                           "concise_note": "The cited fixture block supports it."}]} for row in draft]
    validate_annotations(approved, rows, require_approved=True)
    stale_rows = [row | {"generated_answer_sha256": "0" * 64} if row["case_id"] == CALIBRATION_IDS[0] else row for row in rows]
    with pytest.raises(ValueError, match="HUMAN_CALIBRATION_STALE"):
        validate_annotations(approved, stale_rows, require_approved=True)
    changed_answer_kept_old_metadata = [
        row | {"generated_answer": "modified after stage A"}
        if row["case_id"] == CALIBRATION_IDS[0] else row for row in rows
    ]
    with pytest.raises(ValueError, match="HUMAN_CALIBRATION_STALE"):
        validate_annotations(approved, changed_answer_kept_old_metadata, require_approved=True)
    assert len(chosen) == 45


def test_human_approved_cross_field_consistency_matches_frozen_rubric():
    run_id = "human-cross-field"
    rows = fake_stage_a_rows(run_id)
    approved = approved_annotations_for(rows, run_id)
    assert HumanGenerationAnnotation.model_validate(approved[0]).review_status == AnnotationStatus.HUMAN_APPROVED

    contradicted = approved[0] | {
        "scores": approved[0]["scores"] | {"faithfulness_groundedness": 0},
        "claim_faithfulness": [approved[0]["claim_faithfulness"][0] | {"verdict": "CONTRADICTED"}],
        "critical_failures": ["CONTRADICTED_BY_EVIDENCE"],
    }
    HumanGenerationAnnotation.model_validate(contradicted)

    wrong_contradiction_score = contradicted | {
        "scores": contradicted["scores"] | {"faithfulness_groundedness": 1}
    }
    with pytest.raises(ValueError, match="contradicted claims"):
        HumanGenerationAnnotation.model_validate(wrong_contradiction_score)

    orphan_contradiction_flag = approved[0] | {"critical_failures": ["CONTRADICTED_BY_EVIDENCE"]}
    with pytest.raises(ValueError, match="requires a contradicted claim"):
        HumanGenerationAnnotation.model_validate(orphan_contradiction_flag)

    orphan_unsupported_flag = approved[0] | {"critical_failures": ["UNSUPPORTED_CONFIDENT_CLAIM"]}
    with pytest.raises(ValueError, match="unsupported-confident"):
        HumanGenerationAnnotation.model_validate(orphan_unsupported_flag)

    for verdict in ("UNSUPPORTED", "CONTRADICTED"):
        inconsistent_full_faithfulness = approved[0] | {
            "scores": approved[0]["scores"] | {"faithfulness_groundedness": 2},
            "claim_faithfulness": [approved[0]["claim_faithfulness"][0] | {"verdict": verdict}]
        }
        with pytest.raises(ValueError):
            HumanGenerationAnnotation.model_validate(inconsistent_full_faithfulness)

    wrong_factual_error_score = approved[0] | {"critical_failures": ["SERIOUS_FACTUAL_ERROR"]}
    with pytest.raises(ValueError, match="correctness score 0"):
        HumanGenerationAnnotation.model_validate(wrong_factual_error_score)


def test_stage_b_defaults_to_canonical_source_and_rejects_run_local_draft_substitution(workspace_tmp_path, monkeypatch):
    assert annotation_package_paths() == (ANNOTATION_ROOT / "manifest.json", ANNOTATION_ROOT / "calibration.jsonl")
    canonical_root = workspace_tmp_path / "canonical" / "v0.1.0"
    write_source_controlled_template(canonical_root)
    monkeypatch.setattr(annotation_module, "ANNOTATION_ROOT", canonical_root)
    assert annotation_package_paths() == (canonical_root / "manifest.json", canonical_root / "calibration.jsonl")

    run_id = "canonical-annotation-source"
    rows = fake_stage_a_rows(run_id)
    drafts = make_draft_packet(rows, run_id=run_id)
    source_manifest = json.loads((canonical_root / "manifest.json").read_text(encoding="utf-8"))
    source_manifest.update({"status": "DRAFT_HUMAN_CALIBRATION", "generation_run_id": run_id})
    (canonical_root / "manifest.json").write_text(json.dumps(source_manifest), encoding="utf-8")
    write_jsonl(canonical_root / "calibration.jsonl", drafts)

    run_local = workspace_tmp_path / "run" / "generation" / "calibration.jsonl"
    run_local.parent.mkdir(parents=True, exist_ok=True)
    tempting_but_untrusted = approved_annotations_for(rows, run_id)
    write_jsonl(run_local, tempting_but_untrusted)

    loaded_manifest, loaded_rows = load_annotation_package()
    validate_annotation_manifest(loaded_manifest, run_id=run_id)
    with pytest.raises(ValueError, match="REVIEW_REQUIRED"):
        validate_annotations(loaded_rows, rows, require_approved=True)
    assert all(row["review_status"] == "DRAFT" for row in loaded_rows)
    assert all(row["review_status"] == "HUMAN_APPROVED" for row in tempting_but_untrusted)


def test_canonical_human_approved_package_and_manifest_bindings_are_validated(workspace_tmp_path, monkeypatch):
    canonical_root = workspace_tmp_path / "annotations" / "v0.1.0"
    write_source_controlled_template(canonical_root)
    monkeypatch.setattr(annotation_module, "ANNOTATION_ROOT", canonical_root)
    run_id = "canonical-approved-package"
    rows = fake_stage_a_rows(run_id)
    manifest = json.loads((canonical_root / "manifest.json").read_text(encoding="utf-8"))
    manifest.update({"status": "DRAFT_HUMAN_CALIBRATION", "generation_run_id": run_id})
    (canonical_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    approved = approved_annotations_for(rows, run_id)
    write_jsonl(canonical_root / "calibration.jsonl", approved)

    loaded_manifest, loaded_rows = load_annotation_package()
    validate_annotation_manifest(loaded_manifest, run_id=run_id)
    assert len(validate_annotations(loaded_rows, rows, require_approved=True)) == 30

    with pytest.raises(ValueError, match="VERSION_MISMATCH"):
        validate_annotation_manifest(manifest | {"annotation_version": "wrong"}, run_id=run_id)
    with pytest.raises(ValueError, match="RUN_ID_MISMATCH"):
        validate_annotation_manifest(manifest, run_id="another-run")


def test_human_approval_fails_closed_on_versions_claim_evidence_and_duplicate_rows():
    rows = [{"case_id": case_id, "run_id": "run", "split": "DEVELOPMENT",
             "fixed_evidence_ids": ["e1"], "generator": {"status": "SUCCESS"},
             "generated_answer": "answer " + case_id,
             "generated_answer_sha256": answer_sha256("answer " + case_id)} for case_id in CALIBRATION_IDS]
    approved = approved_annotations_for(rows, "run")
    wrong_version = [row | {"annotation_version": "v9.9.9"} if row["case_id"] == CALIBRATION_IDS[0] else row
                     for row in approved]
    with pytest.raises(ValueError, match="VERSION_MISMATCH"):
        validate_annotations(wrong_version, rows, require_approved=True)
    unknown_claim_evidence = [row | {"claim_faithfulness": [row["claim_faithfulness"][0] |
        {"supporting_evidence_ids": ["outside-case-evidence"]}]} if row["case_id"] == CALIBRATION_IDS[0] else row
        for row in approved]
    with pytest.raises(ValueError, match="not supplied"):
        validate_annotations(unknown_claim_evidence, rows, require_approved=True)
    with pytest.raises(ValueError, match="duplicate/missing"):
        validate_annotations(approved + [approved[0]], rows, require_approved=True)
    with pytest.raises(ValueError):
        validate_annotations(approved, rows + [rows[0]], require_approved=True)


def test_source_controlled_calibration_template_has_exact_ids_and_no_human_labels():
    annotation_root = ROOT / "evaluation/annotations/lesson_chat_generation/v0.1.0"
    manifest = json.loads((annotation_root / "manifest.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (annotation_root / "calibration.jsonl").read_text(encoding="utf-8").splitlines()]
    assert manifest["status"] == "TEMPLATE_UNBOUND"
    assert manifest["case_ids"] == list(CALIBRATION_IDS)
    assert [row["case_id"] for row in rows] == list(CALIBRATION_IDS)
    assert all(row["review_status"] == "DRAFT" and row["scores"] is None for row in rows)
    assert manifest["annotation_version"] == HUMAN_ANNOTATION_VERSION
    assert all(row["annotation_version"] == HUMAN_ANNOTATION_VERSION for row in rows)
    assert all(row["generation_run_id"] is None and row["generated_answer_sha256"] is None for row in rows)
    assert sum(row["review_status"] == "HUMAN_APPROVED" for row in rows) == 0


def test_agreement_metrics_are_deterministic_and_have_no_threshold():
    stats = dimension_agreement([(0, 0), (1, 2), (2, 2)])
    assert stats["exact_agreement_rate"] == pytest.approx(2 / 3)
    assert stats["mean_absolute_score_difference"] == pytest.approx(1 / 3)
    assert stats["confusion_matrix"] == [[1, 0, 0], [0, 0, 1], [0, 0, 1]]
    assert "agreement_gate" not in stats
    humans = [{"case_id": case_id, "scores": {name: 1 for name in DIMENSIONS},
               "critical_failures": []} for case_id in CALIBRATION_IDS]
    judges = {row["case_id"]: {"scores": row["scores"], "critical_failures": []} for row in humans}
    agreement = calibration_agreement(humans, judges, run_id="r")
    assert agreement["case_count_compared"] == 30
    assert agreement["macro_exact_agreement_rate"] == 1
    assert agreement["agreement_gate"] is None


@pytest.mark.parametrize("case_ids", [
    CALIBRATION_IDS[:-1],
    (*CALIBRATION_IDS, "unexpected-calibration-case"),
])
def test_agreement_refuses_incomplete_or_extra_calibration_coverage(case_ids):
    humans = [{"case_id": case_id, "scores": {name: 1 for name in DIMENSIONS},
               "critical_failures": []} for case_id in case_ids]
    judges = {case_id: {"scores": {name: 1 for name in DIMENSIONS}, "critical_failures": []}
              for case_id in case_ids}
    with pytest.raises(ValueError, match="exactly 30"):
        calibration_agreement(humans, judges, run_id="incomplete")


def test_stage_b_fake_judge_preserves_answer_on_judge_failure_and_scores_only_successes():
    _, cases = select_eligible_cases()
    fail_case_id = "current-hsk1-l01-002"

    class FakeJudge:
        async def evaluate(self, case, generated_answer, evidence):
            assert "scores" not in case and "review_status" not in case
            if case["case_id"] == fail_case_id:
                raise JudgeTechnicalFailure("JUDGE_PROVIDER_FAILURE")
            evidence_id = evidence[0]["evidence_ids"][0]
            payload = valid_judge_payload(case["case_id"], evidence_id)
            if case["case_id"] == CALIBRATION_IDS[0]:
                payload["dimension_scores"]["answer_correctness"]["score"] = 0
                payload["dimension_scores"]["faithfulness_groundedness"]["score"] = 1
                payload["dimension_scores"]["completeness"]["score"] = 1
                payload["dimension_scores"]["learning_usefulness"]["score"] = 1
                payload["critical_failures"] = ["SERIOUS_FACTUAL_ERROR"]
            result = GenerationJudgeResult.model_validate(payload)
            return JudgeCallResult(result, latency_ms=3, token_usage={"input_tokens": 4})

    provider = CapturingProvider()
    runner = Step74Runner(settings=settings(), generation_service=LLMGenerationService(provider),
                          token_counter=Counter(), judge=FakeJudge())

    async def generate_all():
        return [await runner.generate_case(case, run_id="stageb-offline") for case in cases]

    rows = asyncio.run(generate_all())
    drafts = make_draft_packet(rows, run_id="stageb-offline")
    by_id = {row["case_id"]: row for row in rows}
    annotations = [row | {"review_status": AnnotationStatus.HUMAN_APPROVED.value,
                          "scores": {name: 2 for name in DIMENSIONS},
                          "claim_faithfulness": [{"claim_id": "C1", "claim_text": "Reviewed claim.",
                              "verdict": "SUPPORTED", "supporting_evidence_ids": by_id[row["case_id"]]["fixed_evidence_ids"][:1],
                              "concise_note": "Supported by reviewed evidence."}]}
                   for row in drafts]
    manifest = fake_stage_a_manifest("stageb-offline", rows)
    result = asyncio.run(runner._resume_stage_b_rows(rows=rows, annotations=annotations,
                                                      run_id="stageb-offline", manifest=manifest))
    failed = next(row for row in result["case_results"] if row["case_id"] == fail_case_id)
    succeeded = next(row for row in result["case_results"]
                     if row["case_id"] not in {fail_case_id, CALIBRATION_IDS[0]})
    assert failed["judge"]["status"] == "TECHNICAL_FAILURE"
    assert failed["generated_answer"] and failed["generated_answer_sha256"]
    assert failed["dimension_scores"] is None and failed["generation_case_status"] == "JUDGE_TECHNICAL_FAILURE"
    assert succeeded["judge"]["status"] == "SUCCESS"
    assert succeeded["generation_case_status"] == "BASELINE_SCORED"
    assert succeeded["generation_case_pass"] is None
    critical = next(row for row in result["case_results"] if row["case_id"] == CALIBRATION_IDS[0])
    assert critical["generation_case_status"] == "CRITICAL_FAILURE"
    assert critical["generation_case_pass"] is False
    assert critical["critical_failures"] == ["SERIOUS_FACTUAL_ERROR"]
    assert result["agreement"] is not None and result["agreement"]["case_count_compared"] == 30


def test_stage_b_resume_reuses_frozen_answers_and_never_calls_generator():
    class CountingJudge:
        def __init__(self):
            self.calls = []

        async def evaluate(self, case, generated_answer, evidence):
            assert "scores" not in case and "review_status" not in case
            self.calls.append((case["case_id"], generated_answer))
            result = GenerationJudgeResult.model_validate(
                valid_judge_payload(case["case_id"], evidence[0]["evidence_ids"][0])
            )
            return JudgeCallResult(result, latency_ms=1)

    run_id = "offline-resume-no-regeneration"
    rows = fake_stage_a_rows(run_id)
    annotations = approved_annotations_for(rows, run_id)
    manifest = fake_stage_a_manifest(run_id, rows)
    provider = CapturingProvider()
    judge = CountingJudge()
    runner = Step74Runner(settings=settings(), generation_service=LLMGenerationService(provider),
                          token_counter=Counter(), judge=judge)
    original_answers = {row["case_id"]: row["generated_answer"] for row in rows}
    result = asyncio.run(runner._resume_stage_b_rows(rows=rows, annotations=annotations,
                                                      run_id=run_id, manifest=manifest))
    assert result["status"] == "STAGE_B_COMPLETE"
    assert result["calibration_judge_success_count"] == 30
    assert provider.request is None
    assert len(judge.calls) == 45
    assert {row["case_id"]: row["generated_answer"] for row in result["case_results"]} == original_answers


def test_stage_b_incomplete_calibration_does_not_finalize_agreement():
    class OneCalibrationFailure:
        async def evaluate(self, case, generated_answer, evidence):
            if case["case_id"] == CALIBRATION_IDS[-1]:
                raise JudgeTechnicalFailure("JUDGE_PROVIDER_FAILURE")
            return GenerationJudgeResult.model_validate(
                valid_judge_payload(case["case_id"], evidence[0]["evidence_ids"][0])
            )

    run_id = "offline-resume-29-of-30"
    rows = fake_stage_a_rows(run_id)
    result = asyncio.run(Step74Runner(
        settings=settings(), generation_service=LLMGenerationService(CapturingProvider()),
        token_counter=Counter(), judge=OneCalibrationFailure(),
    )._resume_stage_b_rows(rows=rows, annotations=approved_annotations_for(rows, run_id),
                           run_id=run_id, manifest=fake_stage_a_manifest(run_id, rows)))
    assert result["calibration_judge_success_count"] == 29
    assert result["agreement"] is None
    assert result["status"] == "JUDGE_CALIBRATION_INCOMPLETE"


def test_stage_b_wrong_run_or_stale_answer_fails_before_judge():
    class NeverJudge:
        calls = 0

        async def evaluate(self, *args):
            self.calls += 1
            raise AssertionError("judge must not run before binding validation")

    run_id = "offline-stale-check"
    rows = fake_stage_a_rows(run_id)
    annotations = approved_annotations_for(rows, run_id)
    judge = NeverJudge()
    runner = Step74Runner(settings=settings(), generation_service=LLMGenerationService(CapturingProvider()),
                          token_counter=Counter(), judge=judge)
    manifest = fake_stage_a_manifest(run_id, rows)
    with pytest.raises(ValueError, match="RUN_ID_MISMATCH"):
        asyncio.run(runner._resume_stage_b_rows(rows=rows, annotations=annotations,
                                                run_id="wrong-run", manifest=manifest))
    changed = [row | {"generated_answer": "tampered answer"}
               if row["case_id"] == CALIBRATION_IDS[0] else row for row in rows]
    with pytest.raises(ValueError, match="HUMAN_CALIBRATION_STALE"):
        asyncio.run(runner._resume_stage_b_rows(rows=changed, annotations=annotations,
                                                run_id=run_id, manifest=manifest))
    assert judge.calls == 0


def test_resume_stage_b_from_run_rejects_missing_or_wrong_run_id_without_generator():
    runner = Step74Runner(settings=settings(), generation_service=LLMGenerationService(CapturingProvider()),
                          token_counter=Counter(), judge=SimpleNamespace())
    with pytest.raises(ValueError, match="RUN_ID_REQUIRED"):
        asyncio.run(runner.resume_stage_b_from_run(""))
    with pytest.raises(ValueError, match="RUN_ID_NOT_FOUND"):
        asyncio.run(runner.resume_stage_b_from_run("no-such-frozen-run"))


def test_public_stage_b_resume_writes_validated_artifacts_from_temp_filesystem(workspace_tmp_path, monkeypatch):
    from app.evaluation.step74.annotations import write_source_controlled_template
    from app.evaluation.step74.artifacts import validate_artifact_metadata
    from app.evaluation.step74 import smoke as smoke_module

    # This filesystem fixture stands in for a previously completed Stage A. Permit its
    # explicitly TEST_FAKE smoke evidence while leaving the rest of the resume path intact.
    original_smoke_validate = smoke_module.RuntimeSmokeEvidence.validate

    def validate_fixture_smoke(self, *, allow_test_fake=False):
        return original_smoke_validate(self, allow_test_fake=True)

    monkeypatch.setattr(smoke_module.RuntimeSmokeEvidence, "validate", validate_fixture_smoke)

    run_id = "stage-b-public-resume-fixture"
    run_dir = workspace_tmp_path / run_id
    rows = fake_stage_a_rows(run_id)
    for row in rows:
        row["execution_mode"] = "OFFICIAL_REAL_RUNTIME"
    manifest = fake_stage_a_manifest(run_id, rows) | {
        "execution_mode": "OFFICIAL_REAL_RUNTIME",
        "run_status": "REVIEW_REQUIRED_HUMAN_CALIBRATION",
        "human_calibration_case_ids": list(CALIBRATION_IDS),
    }
    draft_root = workspace_tmp_path / "stage-a-draft-package"
    write_source_controlled_template(draft_root)
    generation_dir = write_stage_a(run_id, run_dir, manifest, rows, annotation_root=draft_root)
    stage_a_manifest = json.loads((generation_dir / "manifest.json").read_text(encoding="utf-8"))
    stage_a_cases_bytes = (generation_dir / "cases.jsonl").read_bytes()
    stage_a_rows = [json.loads(line) for line in stage_a_cases_bytes.decode("utf-8").splitlines()]
    original_answer_hashes = {row["case_id"]: row["generated_answer_sha256"] for row in stage_a_rows}

    approved_root = workspace_tmp_path / "canonical-compatible-approved-fixture"
    write_source_controlled_template(approved_root)
    approved_manifest = {
        "annotation_version": HUMAN_ANNOTATION_VERSION, "rubric_version": RUBRIC_VERSION,
        "dataset_version": DATASET_VERSION, "case_ids": list(CALIBRATION_IDS), "case_count": 30,
        "generation_run_id": run_id,
    }
    approved_annotations = approved_annotations_for(stage_a_rows, run_id)
    (approved_root / "manifest.json").write_text(
        json.dumps(approved_manifest, ensure_ascii=False), encoding="utf-8",
    )
    (approved_root / "calibration.jsonl").write_text("".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in approved_annotations
    ), encoding="utf-8")

    class FakeJudge:
        def __init__(self):
            self.calls = []

        async def evaluate(self, case, generated_answer, evidence):
            self.calls.append(case["case_id"])
            return JudgeCallResult(GenerationJudgeResult.model_validate(
                valid_judge_payload(case["case_id"], evidence[0]["evidence_ids"][0])
            ), latency_ms=1, token_usage={})

    class NeverGenerator:
        calls = 0

        async def generate(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("Stage-B resume must not regenerate Stage-A answers")

    judge = FakeJudge()
    generator = NeverGenerator()
    runner = Step74Runner(settings=settings(), generation_service=generator,
                          token_counter=Counter(), judge=judge)
    result = asyncio.run(runner.resume_stage_b_from_run(
        run_id, run_dir=run_dir, annotation_file=approved_root / "calibration.jsonl",
    ))

    assert result["status"] == "STAGE_B_COMPLETE"
    assert generator.calls == 0
    assert result["calibration_case_count_expected"] == 30
    assert result["calibration_judge_success_count"] == 30
    assert len([case_id for case_id in judge.calls if case_id in set(CALIBRATION_IDS)]) == 30
    assert {case_id for case_id in judge.calls if case_id in set(CALIBRATION_IDS)} == set(CALIBRATION_IDS)
    stage_b_dir = generation_dir / "stage-b"
    assert {path.name for path in stage_b_dir.iterdir()} == {
        "manifest.json", "cases.jsonl", "summary.json", "calibration-agreement.json",
    }
    final_manifest = json.loads((stage_b_dir / "manifest.json").read_text(encoding="utf-8"))
    final_rows = [json.loads(line) for line in (stage_b_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    final_summary = json.loads((stage_b_dir / "summary.json").read_text(encoding="utf-8"))
    agreement = json.loads((stage_b_dir / "calibration-agreement.json").read_text(encoding="utf-8"))
    assert final_manifest["run_status"] == "STAGE_B_COMPLETE"
    assert final_manifest["human_calibration_case_count"] == 30
    assert final_manifest["human_calibration_draft_count"] == 0
    assert final_manifest["human_approved_count"] == 30
    assert {row["case_id"] for row in approved_annotations} == set(CALIBRATION_IDS)
    assert final_manifest["stage_a_cases_file_sha256"] == stage_a_manifest["cases_file_sha256"]
    assert {row["case_id"]: row["generated_answer_sha256"] for row in final_rows} == original_answer_hashes
    assert sum(row["calibration"].get("human_review_status") == "HUMAN_APPROVED" for row in final_rows) == 30
    validate_artifact_metadata(final_manifest, final_rows, final_summary, agreement)

    bad_manifest = final_manifest | {"human_calibration_draft_count": 30}
    bad_summary = final_summary | {"human_calibration_draft_count": 30}
    bad_agreement = agreement | {"human_calibration_draft_count": 30}
    with pytest.raises(ValueError, match="STAGE_B_ANNOTATION_STATE_MISMATCH"):
        validate_artifact_metadata(bad_manifest, final_rows, bad_summary, bad_agreement)


def test_stage_a_fails_closed_before_artifacts_when_smoke_gate_not_passed():
    from app.ai.llm.openai_provider import OpenAILLMProvider

    production_provider_instance = object.__new__(OpenAILLMProvider)
    runner = Step74Runner(
        settings=settings(), generation_service=SimpleNamespace(provider=production_provider_instance),
        token_counter=Counter(),
    )

    async def fake_failed_smokes():
        return RuntimeSmokeEvidence(
            settings_preflight="PASS", source="TEST_FAKE",
            generator_smoke={"status": "FAILED", "provider": "openai", "model": GENERATOR_MODEL,
                             "config": {}, "api_calls": 0},
            judge_smoke={},
        )

    runner.run_required_smokes = fake_failed_smokes
    with pytest.raises(RuntimeError, match="REAL_SMOKE_GATE_REQUIRED|GENERATOR_SMOKE_REQUIRED"):
        asyncio.run(runner.run_stage_a(run_id="offline-smoke-gate-test"))
    assert not (ROOT / "evaluation/runs/offline-smoke-gate-test").exists()


def test_artifact_metadata_cross_checks_run_identity_counts_and_stage_a_status():
    run_id = "offline-artifact-consistency"
    rows = fake_stage_a_rows(run_id)
    manifest = fake_stage_a_manifest(run_id, rows)
    manifest.update({
        "eligible_case_count": 45,
        "case_counts_by_split": {split: sum(row["split"] == split for row in rows)
                                  for split in ("DEVELOPMENT", "HOLDOUT")},
        "case_counts_by_bucket": {
            split: {bucket: sum(row["split"] == split and row["bucket"] == bucket for row in rows)
                    for bucket in sorted({row["bucket"] for row in rows if row["split"] == split})}
            for split in ("DEVELOPMENT", "HOLDOUT")
        },
    })
    summary = build_stage_a_summary(run_id, rows, identity=manifest)
    agreement = {key: manifest[key] for key in (
        "run_id", "dataset_name", "dataset_version", "dataset_schema_version", "evaluation_step",
        "eligible_case_policy_version", "fixed_evidence_policy_version", "fixed_memory_policy_version",
        "rubric_version", "human_annotation_version", "judge_prompt_version", "execution_mode", "run_status",
        "stage_a_started",
        "generator_identity", "judge_identity", "generator_model", "judge_model",
        "eligible_case_count", "case_counts_by_split", "case_counts_by_bucket",
        "human_calibration_case_count", "human_calibration_packet_created",
        "human_calibration_packet_status", "human_calibration_draft_count", "human_calibration_status",
        "human_approved_count", "generator_success_count",
        "generator_technical_failure_count", "judge_success_count", "judge_technical_failure_count",
        "judge_not_run_count", "judge_calibration_success_count",
        "runtime_api_calls",
    )}
    agreement.update({"case_count_expected": 30, "case_count_compared": 0,
                      "status": "NOT_RUN_HUMAN_CALIBRATION_REQUIRED"})
    validate_artifact_metadata(manifest, rows, summary, agreement)
    with pytest.raises(ValueError, match="IDENTITY_MISMATCH"):
        validate_artifact_metadata(manifest, rows, summary | {"run_id": "other-run"}, agreement)
    with pytest.raises(ValueError, match="RUN_STATUS_MISMATCH|CANNOT_CLAIM_STAGE_B"):
        validate_artifact_metadata(manifest, rows, summary | {"run_status": "STAGE_B_COMPLETE"},
                                   agreement | {"status": "COMPLETE_BASELINE_ONLY", "case_count_compared": 30})
    with pytest.raises(ValueError, match="CALIBRATION_PACKET_MISMATCH"):
        validate_artifact_metadata(
            manifest, rows, summary | {"human_calibration_packet_status": "DRAFT_CREATED"}, agreement,
        )


def test_stage_a_metadata_is_derived_from_actual_results_and_packet_creation():
    rows = fake_stage_a_rows("metadata-state")
    complete = derive_stage_a_state(official=True, rows=rows, packet_count=30)
    assert complete["run_status"] == "REVIEW_REQUIRED_HUMAN_CALIBRATION"
    assert complete["stage_a_started"] is True
    assert complete["generator_success_count"] == 45
    assert complete["generator_technical_failure_count"] == 0
    assert complete["human_calibration_packet_created"] is True
    assert complete["human_calibration_case_count"] == 30
    assert complete["human_calibration_draft_count"] == 30
    assert complete["human_approved_count"] == 0
    complete_summary = build_stage_a_summary(
        "metadata-state", rows,
        identity=complete | {"execution_mode": "OFFICIAL_REAL_RUNTIME", "generator_model": GENERATOR_MODEL,
                            "judge_model": JUDGE_MODEL},
    )
    assert complete_summary["run_status"] == "REVIEW_REQUIRED_HUMAN_CALIBRATION"
    assert complete_summary["generator_success_count"] == 45
    assert complete_summary["generator_technical_failure_count"] == 0
    assert complete_summary["human_calibration_packet_created"] is True
    assert complete_summary["human_calibration_case_count"] == 30
    assert complete_summary["human_calibration_draft_count"] == 30
    assert complete_summary["human_approved_count"] == 0
    assert complete_summary["generation_case_status_counts"] == {"NOT_JUDGED": 45}

    failed_rows = [row | {"generator": {"status": "TECHNICAL_FAILURE"},
                          "generation_case_status": "TECHNICAL_FAILURE"}
                   if row["case_id"] == rows[0]["case_id"] else row for row in rows]
    failed = derive_stage_a_state(official=True, rows=failed_rows, packet_count=0)
    assert failed["run_status"] == "GENERATOR_TECHNICAL_FAILURES"
    assert failed["generator_success_count"] == 44
    assert failed["generator_technical_failure_count"] == 1
    assert failed["human_calibration_packet_created"] is False
    assert failed["human_calibration_status"] == "NOT_CREATED"
    failed_summary = build_stage_a_summary(
        "metadata-state", failed_rows,
        identity=failed | {"execution_mode": "OFFICIAL_REAL_RUNTIME", "generator_model": GENERATOR_MODEL,
                          "judge_model": JUDGE_MODEL},
    )
    assert failed_summary["generator_success_count"] == 44
    assert failed_summary["generator_technical_failure_count"] == 1
    assert failed_summary["human_calibration_packet_created"] is False
    assert failed_summary["run_status"] == "GENERATOR_TECHNICAL_FAILURES"
    assert failed_summary["generation_case_status_counts"] == {"NOT_JUDGED": 44, "TECHNICAL_FAILURE": 1}

    absent = derive_stage_a_state(official=True, rows=rows, packet_count=0)
    assert absent["run_status"] == "CALIBRATION_PACKET_CREATION_FAILED"
    assert absent["human_calibration_packet_created"] is False
    assert absent["human_calibration_case_count"] == 0

    partial = derive_stage_a_state(official=True, rows=rows, packet_count=29)
    assert partial["run_status"] == "CALIBRATION_PACKET_INCOMPLETE"
    assert partial["human_calibration_packet_created"] is True
    assert partial["human_calibration_packet_status"] == "INCOMPLETE"
    assert partial["human_calibration_case_count"] == 29

    offline = derive_stage_a_state(official=False, rows=rows, packet_count=30)
    assert offline["run_status"] == "OFFLINE_TEST_ONLY"
    assert offline["stage_a_started"] is False
    assert offline["human_calibration_packet_created"] is False
    assert offline["human_calibration_case_count"] == 0


def test_offline_stage_a_writer_does_not_create_or_claim_human_packet(workspace_tmp_path):
    from app.evaluation.step74.annotations import write_source_controlled_template

    annotation_root = workspace_tmp_path / "annotations" / "v0.1.0"
    write_source_controlled_template(annotation_root)
    before_manifest = (annotation_root / "manifest.json").read_bytes()
    before_rows = (annotation_root / "calibration.jsonl").read_bytes()
    run_id = "offline-stage-a-metadata"
    rows = fake_stage_a_rows(run_id)
    manifest = fake_stage_a_manifest(run_id, rows)
    generation = write_stage_a(run_id, workspace_tmp_path / "run", manifest, rows, annotation_root=annotation_root)

    written_manifest = json.loads((generation / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((generation / "summary.json").read_text(encoding="utf-8"))
    assert written_manifest["execution_mode"] == "OFFLINE_TEST"
    assert written_manifest["run_status"] == summary["run_status"] == "OFFLINE_TEST_ONLY"
    assert written_manifest["stage_a_started"] is False
    assert written_manifest["generator_success_count"] == summary["generator_success_count"] == 45
    assert written_manifest["generator_technical_failure_count"] == summary["generator_technical_failure_count"] == 0
    assert written_manifest["human_calibration_packet_created"] is False
    assert written_manifest["human_calibration_case_count"] == 0
    assert written_manifest["human_calibration_status"] == "NOT_CREATED"
    assert written_manifest["runtime_api_calls"] == summary["runtime_api_calls"] == 0
    assert written_manifest["runtime_smoke"]["status"] == "NOT_RUN_OFFLINE_TEST"
    assert not (generation / "calibration.jsonl").exists()
    assert (annotation_root / "manifest.json").read_bytes() == before_manifest
    assert (annotation_root / "calibration.jsonl").read_bytes() == before_rows


def test_stage_a_case_file_binding_detects_tampered_artifact_bytes():
    content = b'{"case_id":"frozen"}\n'
    manifest = {"cases_file_sha256": hashlib.sha256(content).hexdigest()}
    verify_stage_a_case_file_binding(manifest, content)
    with pytest.raises(ValueError, match="ARTIFACT_HASH_MISMATCH"):
        verify_stage_a_case_file_binding(manifest, content + b'{"case_id":"changed"}\n')


def test_official_stage_a_refuses_mock_provider_and_artifacts_are_deterministic_in_memory():
    _, cases = select_eligible_cases()
    fake_service = SimpleNamespace(provider=object())
    runner = Step74Runner(settings=settings(), generation_service=fake_service, token_counter=Counter())
    with pytest.raises(RuntimeError, match="PRODUCTION_LLM_PROVIDER"):
        asyncio.run(runner.run_stage_a(run_id="should-not-write"))
    run_id = "test-artifact-run"
    rows = []
    for case in cases:
        answer = "offline test output " + case["case_id"]
        rows.append({"run_id": run_id, "case_id": case["case_id"], "split": case["split"],
                     "bucket": case["bucket"], "generator": {"status": "SUCCESS", "latency_ms": 1,
                     "token_usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}},
                     "generated_answer": answer, "generated_answer_sha256": answer_sha256(answer),
                     "judge": {"status": "NOT_RUN"}, "critical_failures": [],
                     "generation_case_status": "NOT_JUDGED"})
    packet = make_draft_packet(rows, run_id=run_id)
    summary = build_stage_a_summary(run_id, rows)
    encoded_a = canonical_json({"manifest": {"run_id": run_id}, "rows": rows, "packet": packet})
    encoded_b = canonical_json({"manifest": {"run_id": run_id}, "rows": rows, "packet": packet})
    assert len(packet) == 30 and all(row["review_status"] == "DRAFT" for row in packet)
    assert sum(row["review_status"] == "HUMAN_APPROVED" for row in packet) == 0
    assert summary["eligible_case_count"] == 45 and summary["human_approved_count"] == 0
    assert summary["judge_not_run_count"] == 45 and summary["run_status"] == "OFFLINE_TEST_ONLY"
    assert encoded_a == encoded_b
    assert "API_KEY" not in encoded_a and "chain_of_thought" not in encoded_a.lower()
