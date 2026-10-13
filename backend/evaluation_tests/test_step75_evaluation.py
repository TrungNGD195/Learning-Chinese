from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.evaluation.step75.annotations import (
    CALIBRATION_IDS, canonical_sha256, execution_output_sha256,
    validate_annotation_bindings, validate_annotations,
)
from app.evaluation.step75.artifacts import (
    build_summary, validate_offline_artifact_manifest,
)
from app.evaluation.step75.contracts import ActualBehavior, HumanE2EAnnotation
from app.evaluation.step75.citations import evaluate_citation_semantics
from app.evaluation.step75.evaluator import (
    assert_expectations_are_post_execution, derive_actual_behavior, evaluate_case,
)
from app.evaluation.step75.execution import invoke_learner_application_path
from app.evaluation.step75.execution import trace_actual_rag_result
from app.evaluation.step75.external_fixture import ReviewedExternalFixtureProvider
from app.evaluation.step75.judge import expected_request_identity
from app.evaluation.step75.planner import plan_executions


def _ood_case():
    return {"case_id": "ood-001", "split": "DEVELOPMENT", "bucket": "OUT_OF_DOMAIN_REFUSAL",
            "expected_tier": "NONE", "expected_behavior": "REFUSE_OUT_OF_DOMAIN",
            "expected_scope": {"scope_kind": "NONE"}}


def _trace(**updates):
    trace = {"execution_id": "e2e-test", "repeat_index": 1, "selected_tier": "NONE",
             "selected_evidence": [], "selected_evidence_gate_passed": False,
             "tiers_attempted": [], "semantic_no_evidence": False,
             "generation": {"called": False, "answer": None},
             "prompt": {"built": False},
             "citation_validation": {"valid": True, "validated_citations": []},
             "persistence": {"final_message_status": "COMPLETED", "error_code": None},
             "technical_error": None, "domain_guard": {"status": "NOT_PRESENT",
                                                         "out_of_domain_detected": False}}
    trace.update(updates)
    return trace


def test_ood_expected_actual_answer_fails_without_synthesizing_refusal():
    case = _ood_case()
    trace = _trace(selected_tier="CURRENT_LESSON", selected_evidence=[{"stable_locator": "x"}],
                   generation={"called": True, "answer": "answer"},
                   selected_evidence_gate_passed=True, prompt={"built": True})
    result = evaluate_case(case, trace, judge_completed=True)
    assert result["actual"]["behavior"] == "ANSWER"
    assert result["refusal_ok"] is False
    assert "OUT_OF_DOMAIN_ANSWER" in result["critical_failures"]
    assert result["e2e_case_pass"] is False


def _multi_turn_trace(**memory_updates):
    memory = {
        "applied": True, "production_path_ran": True, "builder_invocation_count": 1,
        "composition_applied": True, "generation_selected_turn_count": 2,
        "dropped_after_preflight": False, "selected_turn_count": 2,
        "historical_citation_markers_removed": True,
        "historical_citation_labels": ["[S1]"],
        "sanitized_context_sha256": "memory-hash",
        "sanitized_context": {"turns": [{"user_message_id": "u1"}, {"user_message_id": "u2"}]},
    }
    memory.update(memory_updates)
    return _trace(prompt={"built": True, "source_map_snapshot": {"S1": {}},
                          "context_blocks": [{"label": "S1"}]},
                  selected_evidence=[{"label": "S1"}], memory=memory,
                  judge_result={"context_adherence": {"material_violation": False,
                      "memory_used_as_evidence": False, "historical_citation_label_leak": False,
                      "current_evidence_overridden_by_history": False}})


def _multi_turn_case():
    return {"bucket": "MULTI_TURN_CONTEXT", "conversation_context": [
        {"user_text": "U1", "assistant_text": "A1"},
        {"user_text": "U2", "assistant_text": "A2"},
    ]}


def test_multi_turn_context_requires_actual_production_memory_application():
    from app.evaluation.step75.evaluator import _context_isolation_ok
    assert _context_isolation_ok(_multi_turn_trace(), _multi_turn_case()) is True
    missing_judgement = _multi_turn_trace()
    missing_judgement["judge_result"]["context_adherence"] = {}
    assert _context_isolation_ok(missing_judgement, _multi_turn_case()) is False


@pytest.mark.parametrize("memory_updates", [
    {"production_path_ran": False, "builder_invocation_count": 0},
    {"composition_applied": False},
    {"applied": False, "generation_selected_turn_count": 0},
    {"dropped_after_preflight": True, "applied": False, "generation_selected_turn_count": 0},
    {"selected_turn_count": 1, "generation_selected_turn_count": 1,
     "sanitized_context": {"turns": [{"user_message_id": "u1"}]}},
    {"sanitized_context_sha256": None},
])
def test_multi_turn_context_fails_when_memory_was_not_used_as_required(memory_updates):
    from app.evaluation.step75.evaluator import _context_isolation_ok
    assert _context_isolation_ok(_multi_turn_trace(**memory_updates), _multi_turn_case()) is False


def test_non_multi_turn_does_not_require_conversation_memory():
    from app.evaluation.step75.evaluator import _context_isolation_ok
    trace = _trace(prompt={"built": True, "source_map_snapshot": {}, "context_blocks": []},
                   memory={"applied": False}, judge_result={})
    assert _context_isolation_ok(trace, {"bucket": "CURRENT_LESSON_ANSWERABLE"}) is True


@pytest.mark.parametrize(("text", "required", "sources", "expected_code"), [
    ("Answer [S0]", False, {}, "CITATION_FORMAT_INVALID"),
    ("Answer without a marker", True, {}, "CITATION_MISSING"),
    ("Answer [S2]", False, {"S1": "source"}, "CITATION_UNKNOWN_SOURCE"),
])
def test_real_citation_validator_failure_identity_is_preserved(text, required, sources, expected_code):
    from app.ai.citations.schemas import InternalCitationSource
    from app.ai.citations.validator import CitationValidator
    from app.evaluation.step75.evaluator import _critical_failures
    from app.evaluation.step75.observer import (
        CitationValidatorObserver, citation_validation_snapshot,
    )

    resolved_sources = {
        label: InternalCitationSource(label=label, chunk_id=uuid4(), source_type="LESSON", title="Fixture")
        for label in sources
    }
    observer = SimpleNamespace(citation_validation_attempted=False,
                               citation_validation_error_code=None,
                               citation_validation_latency_ms=0)
    validator = CitationValidatorObserver(CitationValidator(), observer)
    with pytest.raises(Exception) as error:
        validator.validate(text=text, sources=resolved_sources, citation_required=required)
    assert error.value.code == expected_code
    assert observer.citation_validation_attempted is True
    assert observer.citation_validation_error_code == expected_code
    assert citation_validation_snapshot(observer, [], valid=False)["error_code"] == expected_code
    trace = _trace(selected_tier="CURRENT_LESSON", generation={"called": True, "answer": text},
        selected_evidence_gate_passed=True, prompt={"built": True},
        citation_validation={"attempted": True, "valid": False, "error_code": expected_code,
                            "validated_citations": [], "cited_labels": []},
        persistence={"final_message_status": "FAILED", "error_code": None})
    assert derive_actual_behavior(trace) == ActualBehavior.ANSWER
    case = {"expected_behavior": "ANSWER"}
    criticals = _critical_failures(case, trace, ActualBehavior.ANSWER)
    if expected_code == "CITATION_MISSING":
        assert "REQUIRED_CITATION_MISSING" in criticals
    else:
        assert "FABRICATED_CITATION_OR_SOURCE" in criticals
    case = {"case_id": "citation-contract", "split": "DEVELOPMENT",
            "bucket": "CURRENT_LESSON_ANSWERABLE", "expected_tier": "CURRENT_LESSON",
            "expected_behavior": "ANSWER",
            "expected_scope": {"scope_kind": "CURRENT_LESSON", "lesson_locator": "lesson-1"},
            "required_evidence": [{"stable_locator": "loc-1", "requirement_id": "r1"}],
            "acceptable_evidence": []}
    trace.update(execution_id="citation-contract#r1", case_id="citation-contract", repeat_index=1,
        selected_evidence=[{"stable_locator": "loc-1", "lesson_locator": "lesson-1", "label": "S1"}],
        tiers_attempted=[{"tier": "CURRENT_LESSON", "attempt_index": 1,
            "scope_identity": "CURRENT_LESSON:lesson=lesson-1", "retrieval_status": "SUCCESS",
            "candidate_count": 1, "rerank_status": "SUCCESS", "reranked_evidence": [
                {"stable_locators": ["loc-1"], "rerank_score": 0.8}],
            "evidence_gate_threshold": 0.5, "evidence_gate_passed": True, "scope_violation": False}],
        prompt={"built": True, "source_map_snapshot": {"S1": {"source_kind": "INTERNAL_CHUNK"}},
                "context_blocks": [{"label": "S1"}]},
        persistence={"final_message_status": "FAILED", "error_code": None,
                     "message_citation_count": 0, "persisted_citations": []})
    result = evaluate_case(case, trace, judge_completed=True)
    assert result["citation_ok"] is False
    assert result["technical_ok"] is True
    assert result["e2e_case_pass"] is False


def test_unexpected_citation_validator_exception_is_technical_failure():
    from app.evaluation.step75.observer import CitationValidatorObserver
    observer = SimpleNamespace(citation_validation_attempted=False,
                               citation_validation_error_code=None,
                               citation_validation_latency_ms=0)
    class BrokenValidator:
        def validate(self, **kwargs):
            raise RuntimeError("injected validator infrastructure failure")
    with pytest.raises(RuntimeError):
        CitationValidatorObserver(BrokenValidator(), observer).validate(
            text="answer", sources={}, citation_required=True)
    assert observer.citation_validation_error_code == "CITATION_VALIDATION_FAILED"
    trace = _trace(selected_tier="CURRENT_LESSON", generation={"called": True},
        citation_validation={"attempted": True, "valid": False,
                             "error_code": observer.citation_validation_error_code},
        persistence={"final_message_status": "FAILED", "error_code": None})
    trace["technical_error"] = {"stage": "CITATION_VALIDATION", "code": "CITATION_VALIDATION_FAILED"}
    assert derive_actual_behavior(trace) == ActualBehavior.TECHNICAL_FAILURE
    result = evaluate_case(_ood_case(), trace)
    assert result["technical_ok"] is False
    assert result["e2e_case_pass"] is False


def test_production_latency_stops_at_response_before_readback_and_summary_uses_it():
    from app.evaluation.step75.observer import ProductionTraceObserver
    observer = object.__new__(ProductionTraceObserver)
    observer.started_at = 1.0
    observer.production_started_at = 10.0
    observer.production_response_at = 12.25
    readback_finished_at = 20.0
    assert observer.total_latency_ms == 2250
    assert observer.total_latency_ms != round((readback_finished_at - 10.0) * 1000)
    rows = [{"execution_id": f"latency-{i}", "case_id": f"case-{i}",
             "split": "DEVELOPMENT", "bucket": "CURRENT_LESSON_ANSWERABLE",
             "repeat_index": 1, "trace": {"timings": {"total_latency_ms": value}}}
            for i, value in enumerate((100, 200, 9000))]
    summary = build_summary(rows, run_id="latency-boundary-test")
    latency = summary["operational_latency_test_only"]["total_latency_ms"]
    assert latency["p50"] == 200
    assert latency["p95"] == pytest.approx(8120)


@pytest.mark.parametrize(("tier", "expected_actual"), [
    ("INTERNAL_KB", "FALLBACK_INTERNAL"), ("TRUSTED_EXTERNAL", "FALLBACK_EXTERNAL")])
def test_ood_expected_fallback_answers_are_out_of_domain_answers(tier, expected_actual):
    trace = _trace(selected_tier=tier, selected_evidence=[{"stable_locator": "x"}],
                   generation={"called": True, "answer": "answer"},
                   selected_evidence_gate_passed=True, prompt={"built": True})
    result = evaluate_case(_ood_case(), trace, judge_completed=True)
    assert result["actual"]["behavior"] == expected_actual
    assert result["refusal_ok"] is False
    assert "OUT_OF_DOMAIN_ANSWER" in result["critical_failures"]
    assert not result["e2e_case_pass"]


def test_ood_expected_generic_no_evidence_is_not_ood_refusal():
    case = _ood_case()
    trace = _trace(semantic_no_evidence=True, frozen_no_evidence_content="No evidence",
                   generation={"called": False, "answer": "No evidence"})
    result = evaluate_case(case, trace)
    assert result["actual"]["behavior"] == "REFUSE_NO_EVIDENCE"
    assert result["refusal_ok"] is False
    assert "OUT_OF_DOMAIN_ANSWER" not in result["critical_failures"]
    assert result["e2e_case_pass"] is False


def test_ood_expected_technical_failure_remains_technical_failure():
    case = _ood_case()
    trace = _trace(technical_error={"stage": "retrieval", "code": "RETRIEVAL_FAILED"})
    result = evaluate_case(case, trace)
    assert result["actual"]["behavior"] == "TECHNICAL_FAILURE"
    assert result["technical_ok"] is False
    assert result["refusal_ok"] is False
    assert result["e2e_case_pass"] is False


def test_expected_ood_never_creates_actual_ood_without_trace_signal():
    assert derive_actual_behavior(_trace()) != ActualBehavior.REFUSE_OUT_OF_DOMAIN
    domain_trace = _trace(domain_guard={"status": "REFUSED", "out_of_domain_detected": True},
                          semantic_no_evidence=True)
    assert derive_actual_behavior(domain_trace) == ActualBehavior.REFUSE_OUT_OF_DOMAIN


def test_production_no_evidence_result_trace_remains_generic_refusal():
    with pytest.raises(ValueError, match="E2E_FULL_PRODUCTION_TRACE_OBSERVER_AND_PERSISTENCE_REQUIRED"):
        trace_actual_rag_result(object(), execution_id="exec-1", case_id="ood-1",
                                repeat_index=1, assistant_status="COMPLETED",
                                current_question="question")
    assert derive_actual_behavior(_trace(semantic_no_evidence=True)) == ActualBehavior.REFUSE_NO_EVIDENCE


def test_expected_labels_are_post_execution_and_not_passed_to_application_path():
    async def submit(**kwargs):
        assert set(kwargs) == {"user_id", "conversation_id", "content"}
        return kwargs

    import asyncio
    result = asyncio.run(invoke_learner_application_path(
        submit, user_id="u", conversation_id="c", current_question="question"))
    assert result["content"] == "question"
    with pytest.raises(ValueError, match="EXPECTED_LABELS_MUST_NOT_ENTER_EXECUTION_TRACE"):
        assert_expectations_are_post_execution(_ood_case(), {"expected_behavior": "REFUSE_OUT_OF_DOMAIN"})


def test_step73_required_requirement_groups_all_must_be_satisfied():
    case = {"required_evidence": [
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "a", "requirement_id": "r1", "evidence_id": "e1"},
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "a-alt", "requirement_id": "r1", "evidence_id": "e1-alt"},
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "b", "requirement_id": "r2", "evidence_id": "e2"}],
        "acceptable_evidence": []}
    from app.evaluation.step75.evaluator import _selected_evidence_satisfies_step73
    assert not _selected_evidence_satisfies_step73(case, [{"stable_locator": "a"}])
    assert _selected_evidence_satisfies_step73(case, [{"stable_locator": "a"}, {"stable_locator": "b"}])
    assert _selected_evidence_satisfies_step73(case, [{"stable_locator": "a-alt"}, {"stable_locator": "b"}])


def test_unbound_draft_template_allowed_but_reviewed_requires_run_bindings():
    row = HumanE2EAnnotation(case_id=CALIBRATION_IDS[0])
    assert row.review_status.value == "DRAFT"
    with pytest.raises(ValidationError):
        HumanE2EAnnotation(case_id=CALIBRATION_IDS[0], review_status="HUMAN_APPROVED")


def test_annotation_template_has_exact_frozen_subset_and_no_approval():
    rows = [HumanE2EAnnotation(case_id=case_id).model_dump(mode="json") for case_id in CALIBRATION_IDS]
    checked = validate_annotations(rows)
    assert len(checked) == 30
    assert all(row["review_status"] == "DRAFT" for row in checked)
    assert sum(row["review_status"] == "HUMAN_APPROVED" for row in checked) == 0
    assert all(row["e2e_run_id"] is None and row["execution_output_sha256"] is None for row in checked)


def test_reviewed_annotation_rejects_stale_output_hash():
    records = {}
    rows = []
    cases_hash = "a" * 64
    for index, case_id in enumerate(CALIBRATION_IDS):
        execution_id = f"exec-{index}"
        record = {"case_id": case_id, "repeat_index": 1, "question": "q",
                  "generated_answer": "answer", "selected_evidence": [], "source_map": {},
                  "validated_citations": [], "sanitized_memory": None}
        records[execution_id] = record
        rows.append(HumanE2EAnnotation(
            case_id=case_id, repeat_index=1, e2e_run_id="run-1", execution_id=execution_id,
            generated_answer_sha256=__import__("hashlib").sha256(b"answer").hexdigest(),
            source_map_sha256=canonical_sha256({}),
            validated_citations_sha256=canonical_sha256([]),
            evidence_snapshot_sha256=canonical_sha256([]),
            execution_output_sha256=execution_output_sha256(
                case_id=case_id, repeat_index=1, question="q", generated_answer="answer",
                selected_evidence=[], source_map={}, validated_citations=[], sanitized_memory=None),
            cases_artifact_sha256=cases_hash, review_status="NEEDS_ADJUDICATION",
        ).model_dump(mode="json"))
    artifact_rows = [_annotation_artifact_row(key, value) for key, value in records.items()]
    cases_hash = _cases_artifact_hash(artifact_rows)
    for row in rows:
        row["cases_artifact_sha256"] = cases_hash
    manifest = {"run_id": "run-1", "cases_artifact_sha256": cases_hash}
    validate_annotation_bindings(rows, records, manifest=manifest,
                                 cases_artifact_rows=artifact_rows,
                                 cases_artifact_sha256=cases_hash)
    rows[0]["generated_answer_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="E2E_ANNOTATION_RUNTIME_HASH_MISMATCH"):
        validate_annotation_bindings(rows, records, manifest=manifest,
                                     cases_artifact_rows=artifact_rows,
                                     cases_artifact_sha256=cases_hash)


def _annotation_artifact_row(execution_id, value):
    return {"execution_id": execution_id, "case_id": value["case_id"],
            "repeat_index": value["repeat_index"], "trace": {
                "conversation": {"current_question": value["question"]},
                "generation": {"answer": value["generated_answer"]},
                "prompt": {"source_map_snapshot": value["source_map"]},
                "citation_validation": {"validated_citations": value["validated_citations"]},
                "selected_evidence": value["selected_evidence"],
                "memory": {"sanitized_context": value["sanitized_memory"]}}}


def _cases_artifact_hash(rows):
    import hashlib
    from app.evaluation.step75.artifacts import canonical_json
    return hashlib.sha256(b"".join(canonical_json(row) + b"\n" for row in rows)).hexdigest()


def _reviewed_annotation_fixture():
    import hashlib
    cases_hash = "a" * 64
    records, rows = {}, []
    for index, case_id in enumerate(CALIBRATION_IDS):
        execution_id = f"exec-{index}"
        record = {"case_id": case_id, "repeat_index": 1, "question": "q",
                  "generated_answer": "answer", "selected_evidence": [], "source_map": {},
                  "validated_citations": [], "sanitized_memory": None}
        records[execution_id] = record
        rows.append(HumanE2EAnnotation(
            case_id=case_id, repeat_index=1, e2e_run_id="run-1", execution_id=execution_id,
            generated_answer_sha256=hashlib.sha256(b"answer").hexdigest(),
            source_map_sha256=canonical_sha256({}),
            validated_citations_sha256=canonical_sha256([]),
            evidence_snapshot_sha256=canonical_sha256([]),
            execution_output_sha256=execution_output_sha256(
                case_id=case_id, repeat_index=1, question="q", generated_answer="answer",
                selected_evidence=[], source_map={}, validated_citations=[], sanitized_memory=None),
            cases_artifact_sha256=cases_hash, review_status="NEEDS_ADJUDICATION",
        ).model_dump(mode="json"))
    artifact_rows = [_annotation_artifact_row(key, value) for key, value in records.items()]
    cases_hash = _cases_artifact_hash(artifact_rows)
    for row in rows:
        row["cases_artifact_sha256"] = cases_hash
    return rows, records, artifact_rows, {"run_id": "run-1", "cases_artifact_sha256": cases_hash}, cases_hash


def test_annotation_binding_rejects_wrong_run_even_when_hashes_match():
    rows, records, artifact_rows, manifest, digest = _reviewed_annotation_fixture()
    rows[0]["e2e_run_id"] = "other-run"
    with pytest.raises(ValueError, match="E2E_ANNOTATION_RUN_ID_MISMATCH"):
        validate_annotation_bindings(rows, records, manifest=manifest,
                                     cases_artifact_rows=artifact_rows, cases_artifact_sha256=digest)


def test_annotation_binding_rejects_unknown_execution_id():
    rows, records, artifact_rows, manifest, digest = _reviewed_annotation_fixture()
    rows[0]["execution_id"] = "missing-execution"
    with pytest.raises(ValueError, match="E2E_ANNOTATION_CASES_ARTIFACT_EXECUTION_MISMATCH"):
        validate_annotation_bindings(rows, records, manifest=manifest,
                                     cases_artifact_rows=artifact_rows, cases_artifact_sha256=digest)


def test_annotation_binding_rejects_case_repeat_mismatch_and_stale_cases_artifact():
    rows, records, artifact_rows, manifest, digest = _reviewed_annotation_fixture()
    artifact_rows[0]["repeat_index"] = 2
    digest = _cases_artifact_hash(artifact_rows)
    manifest["cases_artifact_sha256"] = digest
    with pytest.raises(ValueError, match="E2E_ANNOTATION_CASES_ARTIFACT_EXECUTION_MISMATCH"):
        validate_annotation_bindings(rows, records, manifest=manifest,
                                     cases_artifact_rows=artifact_rows, cases_artifact_sha256=digest)
    artifact_rows[0]["repeat_index"] = 1
    with pytest.raises(ValueError, match="E2E_ANNOTATION_CASES_ARTIFACT_STALE"):
        validate_annotation_bindings(rows, records, manifest=manifest,
                                     cases_artifact_rows=artifact_rows, cases_artifact_sha256="b" * 64)


def test_annotation_binding_rejects_case_mismatch_and_stale_artifact_content():
    rows, records, artifact_rows, manifest, digest = _reviewed_annotation_fixture()
    artifact_rows[0]["case_id"] = "different-case"
    changed_digest = _cases_artifact_hash(artifact_rows)
    manifest["cases_artifact_sha256"] = changed_digest
    with pytest.raises(ValueError, match="E2E_ANNOTATION_CASES_ARTIFACT_EXECUTION_MISMATCH"):
        validate_annotation_bindings(rows, records, manifest=manifest,
                                     cases_artifact_rows=artifact_rows, cases_artifact_sha256=changed_digest)
    # Same declared file digest cannot make changed execution content valid.
    rows, records, changed_artifact, manifest, digest = _reviewed_annotation_fixture()
    changed_artifact[0]["trace"]["generation"]["answer"] = "stale output"
    changed_digest = _cases_artifact_hash(changed_artifact)
    manifest["cases_artifact_sha256"] = changed_digest
    with pytest.raises(ValueError, match="E2E_ANNOTATION_CASES_ARTIFACT_EXECUTION_MISMATCH"):
        validate_annotation_bindings(rows, records, manifest=manifest,
                                     cases_artifact_rows=changed_artifact, cases_artifact_sha256=changed_digest)


def test_d104_judge_request_configuration_is_frozen_and_step75_specific():
    assert expected_request_identity() == {"api": "responses", "model": "gpt-5.4-2026-03-05",
        "reasoning_effort": "none", "temperature": 0, "max_output_tokens": 1600,
        "structured_output": True, "tools": []}


def test_citation_correctness_and_coverage_are_separate_and_current_only():
    current = {"S1": {"source_kind": "INTERNAL_CHUNK", "source_id": "chunk-1",
                       "chunk_id": "chunk-1", "url": None}}
    supported = evaluate_citation_semantics(
        claims=[{"requires_grounding": True, "cited_labels": ["S1"], "supporting_labels": ["S1"]}],
        current_citation_labels={"S1"}, source_map=current,
        persisted_citations=[{"label": "S1", "source_kind": "INTERNAL_CHUNK",
                              "source_id": "chunk-1", "chunk_id": "chunk-1", "url": None}])
    assert supported["citation_correctness_ok"] is True
    assert supported["citation_coverage_ok"] is True
    unsupported = evaluate_citation_semantics(
        claims=[{"requires_grounding": True, "cited_labels": ["S1"], "supporting_labels": []}],
        current_citation_labels={"S1"}, source_map=current, persisted_citations=[])
    assert unsupported["citation_correctness_ok"] is False
    assert unsupported["citation_coverage_ok"] is False
    assert "REQUIRED_CITATION_MISSING" in unsupported["critical_failures"]


def test_offline_artifact_cannot_claim_official_baseline():
    with pytest.raises(ValueError, match="OFFLINE_ARTIFACT_CANNOT_BE_OFFICIAL_BASELINE"):
        validate_offline_artifact_manifest({"execution_mode": "OFFLINE_TEST",
                                            "official_baseline_eligible": True})


def test_offline_summary_derives_counts_from_actual_rows():
    row = {"execution_id": "e1", "case_id": "c1", "split": "DEVELOPMENT",
           "bucket": "CURRENT_LESSON_ANSWERABLE", "repeat_index": 1,
           "retrieval_ok": True, "generation_ok": True, "citation_correctness_ok": True,
           "citation_coverage_ok": True, "citation_ok": True, "context_ok": True,
           "fallback_ok": True, "refusal_ok": True, "technical_ok": True,
           "critical_failures": [], "e2e_case_pass": True}
    manifest = {"run_id": "offline-test", "execution_mode": "OFFLINE_TEST",
                "artifact_kind": "OFFLINE_TEST", "official_baseline_eligible": False,
                "official_run_executed": False}
    validate_offline_artifact_manifest(manifest)
    summary = build_summary([row], run_id="offline-test")
    assert manifest["official_baseline_eligible"] is False
    assert summary["execution_mode"] == "OFFLINE_TEST"
    assert summary["executed_count"] == 1
    assert summary["e2e_case_pass_rate"] == 1.0
    assert summary["planned_execution_count"] == 84
    assert summary["operational_metrics_official"] is False
    assert summary["metrics_classification"] == "TEST_ONLY_NOT_PRODUCTION_BASELINE"


def test_offline_summary_aggregates_critical_quality_latency_tokens_and_holdout_repeats():
    rows = []
    for repeat, passed in ((1, True), (2, False), (3, True)):
        rows.append({"execution_id": f"c1#r{repeat}", "case_id": "c1", "split": "HOLDOUT",
                     "bucket": "CURRENT_LESSON_ANSWERABLE", "repeat_index": repeat,
                     "retrieval_ok": passed, "generation_ok": passed,
                     "citation_correctness_ok": passed, "citation_coverage_ok": True,
                     "context_ok": True, "fallback_ok": True, "refusal_ok": True,
                     "technical_ok": True, "critical_failures": [] if passed else ["REQUIRED_CITATION_MISSING"],
                     "e2e_case_pass": passed, "generation_applicable": True,
                     "generation_dimension_scores": {"answer_correctness": {"score": repeat - 1}},
                     "trace": {"timings": {"total_latency_ms": repeat * 10},
                               "generation": {"token_usage": {"input_tokens": repeat,
                                  "output_tokens": 2, "total_tokens": repeat + 2}}}})
    summary = build_summary(rows, run_id="offline-summary")
    assert summary["counts_by_bucket"]["CURRENT_LESSON_ANSWERABLE"] == 3
    assert summary["quality_rates_by_bucket"]["CURRENT_LESSON_ANSWERABLE"]["generation_ok"] == 2 / 3
    assert summary["critical_failures"]["counts_by_type"] == {"REQUIRED_CITATION_MISSING": 1}
    assert summary["generation_quality"]["answer_correctness"]["distribution"] == {"0": 1, "1": 1, "2": 1}
    assert summary["operational_latency_test_only"]["total_latency_ms"]["p50"] == 20
    assert summary["token_usage_test_only"]["input_tokens"]["sum"] == 6
    assert summary["holdout_repeat_stability_test_only"]["c1"]["execution_count"] == 3
    assert summary["holdout_repeat_stability_test_only"]["c1"]["critical_failure_repeat_count"] == 1
    assert summary["holdout_repeat_stability_test_only"]["c1"]["generation_dimension_variance"][
        "answer_correctness"] == 2 / 3


def test_critical_failures_derive_from_runtime_tier_scores_and_transitions():
    from app.evaluation.step75.evaluator import _critical_failures
    case = _ood_case()
    current = {"tier": "CURRENT_LESSON", "attempt_index": 1,
               "retrieval_status": "SUCCESS", "rerank_status": "SUCCESS",
               "reranked_evidence": [{"rerank_score": 0.9}], "evidence_gate_threshold": 0.5,
               "evidence_gate_passed": True}
    internal = {"tier": "INTERNAL_KB", "attempt_index": 2,
                "retrieval_status": "SUCCESS", "rerank_status": "SUCCESS",
                "reranked_evidence": [], "evidence_gate_threshold": 0.5,
                "evidence_gate_passed": False}
    trace = _trace(selected_tier="INTERNAL_KB", selected_evidence_gate_passed=False,
                   tiers_attempted=[current, internal], generation={"called": True},
                   prompt={"built": True})
    failures = _critical_failures(case, trace, ActualBehavior.FALLBACK_INTERNAL)
    assert "TIER_FALLBACK_POLICY_VIOLATION" in failures


def test_confident_answer_after_runtime_gate_failure_is_critical():
    from app.evaluation.step75.evaluator import _critical_failures
    case = {"expected_behavior": "ANSWER"}
    trace = _trace(selected_tier="CURRENT_LESSON", generation={"called": True},
                   tiers_attempted=[{"tier": "CURRENT_LESSON", "attempt_index": 1,
                     "retrieval_status": "SUCCESS", "rerank_status": "SUCCESS",
                     "reranked_evidence": [{"rerank_score": 0.1}],
                     "evidence_gate_threshold": 0.5, "evidence_gate_passed": False}])
    assert "CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE" in _critical_failures(
        case, trace, ActualBehavior.ANSWER)


def test_technical_failure_continuing_as_no_evidence_is_critical():
    from app.evaluation.step75.evaluator import _critical_failures
    case = {"expected_behavior": "REFUSE_NO_EVIDENCE"}
    trace = _trace(semantic_no_evidence=True,
                   tiers_attempted=[{"tier": "CURRENT_LESSON", "attempt_index": 1,
                                     "retrieval_status": "TECHNICAL_FAILURE",
                                     "rerank_status": "NOT_APPLICABLE"}],
                   generation={"called": False}, persistence={"final_message_status": "COMPLETED"})
    assert "TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE" in _critical_failures(
        case, trace, ActualBehavior.TECHNICAL_FAILURE)


def test_judge_protocol_result_propagates_dimensions_claims_citations_and_context():
    from app.evaluation.step75.contracts import DIMENSIONS, E2EJudgeResult, ClaimVerdict
    case = {"case_id": "case-1", "split": "DEVELOPMENT", "bucket": "CURRENT_LESSON_ANSWERABLE",
            "expected_tier": "CURRENT_LESSON", "expected_behavior": "ANSWER",
            "expected_scope": {"scope_kind": "CURRENT_LESSON", "lesson_locator": "lesson-1"},
            "required_evidence": [{"stable_locator": "fixture:lesson:block", "source_kind": "INTERNAL_CHUNK",
                                   "evidence_id": "e1", "requirement_id": "r1"}],
            "acceptable_evidence": []}
    source = {"source_kind": "INTERNAL_CHUNK", "source_id": "chunk-1", "chunk_id": "chunk-1", "url": None}
    scores = {name: {"score": 2, "rationale": "supported"} for name in DIMENSIONS}
    judge = E2EJudgeResult.model_validate({"schema_version": "1.0.0", "case_id": "case-1", "repeat_index": 1,
        "generation_dimension_scores": scores,
        "claims": [{"claim_id": "C1", "claim_text": "Supported fact", "requires_grounding": True,
                    "cited_labels": ["S1"], "supporting_labels": ["S1"], "verdict": ClaimVerdict.SUPPORTED,
                    "concise_rationale": "source supports claim"}],
        "context_adherence": {"material_violation": False, "memory_used_as_evidence": False,
            "historical_citation_label_leak": False, "current_evidence_overridden_by_history": False,
            "concise_rationale": "memory was contextual"},
        "semantic_critical_failures": [], "concise_overall_rationale": "supported"}).model_dump(mode="json")
    trace = _trace(execution_id="case-1#r1", case_id="case-1", repeat_index=1,
        selected_tier="CURRENT_LESSON", selected_evidence_gate_passed=True,
        selected_evidence=[{"stable_locator": "fixture:lesson:block", "lesson_locator": "lesson-1",
                            "label": "S1", "source_kind": "INTERNAL_CHUNK", "source_id": "chunk-1",
                            "chunk_id": "chunk-1"}],
        tiers_attempted=[{"tier": "CURRENT_LESSON", "attempt_index": 1,
            "retrieval_status": "SUCCESS", "candidate_count": 1, "semantic_candidates": [],
            "rerank_status": "SUCCESS", "reranked_evidence": [{"rerank_score": -0.5}],
            "evidence_gate_threshold": -1.0, "evidence_gate_passed": True, "scope_violation": False}],
        generation={"called": True, "answer": "answer", "error_code": None},
        prompt={"built": True, "source_map_snapshot": {"S1": source}, "context_blocks": []},
        citation_validation={"attempted": True, "valid": True, "cited_labels": ["S1"],
            "validated_citations": [{"label": "S1"}]},
        persistence={"final_message_status": "COMPLETED", "message_citation_count": 1,
            "persisted_citations": [{"label": "S1", **source}]},
        judge_result=judge)
    result = evaluate_case(case, trace, judge_completed=True)
    assert result["generation_dimension_scores"] == scores
    assert result["semantic_claims"] == judge["claims"]
    assert result["citation_correctness_ok"] is True
    assert result["citation_coverage_ok"] is True
    assert result["context_ok"] is True
    assert result["generation_ok"] is True
    assert result["e2e_case_pass"] is True
    trace["judge_result"]["context_adherence"]["material_violation"] = True
    trace["judge_result"]["context_adherence"]["memory_used_as_evidence"] = True
    assert evaluate_case(case, trace, judge_completed=True)["context_ok"] is False


def test_semantic_critical_failure_maps_to_generation_ok_only_per_d103():
    from app.evaluation.step75.contracts import DIMENSIONS, E2EJudgeResult
    case = {"case_id": "case-1", "split": "DEVELOPMENT", "bucket": "CURRENT_LESSON_ANSWERABLE",
            "expected_tier": "CURRENT_LESSON", "expected_behavior": "ANSWER",
            "expected_scope": {"scope_kind": "CURRENT_LESSON", "lesson_locator": "lesson-1"},
            "required_evidence": [{"stable_locator": "loc-a", "requirement_id": "r1"}],
            "acceptable_evidence": []}
    scores = {name: {"score": 1, "rationale": "test"} for name in DIMENSIONS}
    scores["answer_correctness"] = {"score": 0, "rationale": "serious fact error"}
    judge = E2EJudgeResult.model_validate({"schema_version": "1.0.0", "case_id": "case-1", "repeat_index": 1,
        "generation_dimension_scores": scores, "claims": [],
        "context_adherence": {"material_violation": False, "memory_used_as_evidence": False,
            "historical_citation_label_leak": False, "current_evidence_overridden_by_history": False,
            "concise_rationale": "no context issue"},
        "semantic_critical_failures": ["SERIOUS_FACTUAL_ERROR"], "concise_overall_rationale": "failure"}).model_dump(mode="json")
    trace = _trace(execution_id="case-1#r1", case_id="case-1", repeat_index=1,
        selected_tier="CURRENT_LESSON", selected_evidence_gate_passed=True,
        selected_evidence=[{"stable_locator": "loc-a", "lesson_locator": "lesson-1", "label": "S1"}],
        tiers_attempted=[{"tier": "CURRENT_LESSON", "attempt_index": 1, "retrieval_status": "SUCCESS",
            "rerank_status": "SUCCESS", "reranked_evidence": [{"rerank_score": 1.0}],
            "evidence_gate_threshold": 0.5, "evidence_gate_passed": True}],
        generation={"called": True, "answer": "wrong"}, prompt={"built": True,
        "source_map_snapshot": {"S1": {"source_kind": "INTERNAL_CHUNK", "source_id": "chunk-1",
                                         "chunk_id": "chunk-1", "url": None}},
        "context_blocks": []}, citation_validation={"attempted": True, "valid": True,
        "cited_labels": [], "validated_citations": []}, persistence={"final_message_status": "COMPLETED",
        "message_citation_count": 0, "persisted_citations": []}, judge_result=judge)
    result = evaluate_case(case, trace, judge_completed=True)
    assert result["generation_ok"] is False
    assert result["citation_correctness_ok"] is True
    assert result["citation_coverage_ok"] is True
    assert "SERIOUS_FACTUAL_ERROR" in result["critical_failures"]
    assert result["e2e_case_pass"] is False
    judge["semantic_critical_failures"] = ["REQUIRED_CITATION_MISSING"]
    citation_only = evaluate_case(case, trace, judge_completed=True)
    assert citation_only["generation_ok"] is True
    assert citation_only["e2e_case_pass"] is False


def test_external_fixture_uses_actual_query_and_preserves_reviewed_provenance():
    import asyncio
    provider = ReviewedExternalFixtureProvider()
    candidates = asyncio.run(provider.search("basic comparison bi adjective", 10))
    assert candidates
    provenance = provider.provenance_for_url(candidates[0].url)
    assert provenance and provenance["source_id"]
    assert provenance["url"] == candidates[0].url


def _external_cases():
    root = Path(__file__).resolve().parents[2]
    rows = []
    for filename in ("development.jsonl", "holdout.jsonl"):
        rows.extend(json.loads(line) for line in
                    (root / "evaluation/datasets/lesson_chat_rag/v0" / filename)
                    .read_text(encoding="utf-8").splitlines() if line)
    return [row for row in rows if row["bucket"] == "TRUSTED_EXTERNAL_FALLBACK"]


def test_all_five_trusted_external_required_urls_satisfy_exact_evidence_identity():
    cases = _external_cases()
    assert len(cases) == 5
    from app.evaluation.step75.evaluator import _selected_evidence_satisfies_step73
    for case in cases:
        required_url = case["required_evidence"][0]["url"]
        assert _selected_evidence_satisfies_step73(case, [{
            "source_kind": "EXTERNAL_URL", "url": required_url,
        }]), case["case_id"]
        assert not _selected_evidence_satisfies_step73(case, [{
            "source_kind": "EXTERNAL_URL", "url": "https://wrong.example/source",
        }]), case["case_id"]


def test_external_multiple_required_semantics_all_need_matching_urls():
    case = {"required_evidence": [
        {"source_kind": "EXTERNAL_URL", "url": "https://trusted.example/a", "requirement_id": "r1"},
        {"source_kind": "EXTERNAL_URL", "url": "https://trusted.example/b", "requirement_id": "r2"}],
        "acceptable_evidence": []}
    from app.evaluation.step75.evaluator import _selected_evidence_satisfies_step73
    assert not _selected_evidence_satisfies_step73(case, [
        {"source_kind": "EXTERNAL_URL", "url": "https://trusted.example/a"}])
    assert _selected_evidence_satisfies_step73(case, [
        {"source_kind": "EXTERNAL_URL", "url": "https://trusted.example/a"},
        {"source_kind": "EXTERNAL_URL", "url": "https://trusted.example/b"}])


def test_expected_bucket_labels_do_not_select_external_runtime_execution():
    async def submit(**kwargs):
        assert set(kwargs) == {"user_id", "conversation_id", "content"}
        assert "expected_tier" not in kwargs and "expected_behavior" not in kwargs
        return kwargs
    import asyncio
    result = asyncio.run(invoke_learner_application_path(
        submit, user_id="u", conversation_id="c", current_question="question"))
    assert result["content"] == "question"


def test_below_threshold_selected_evidence_does_not_pass_gate():
    case = {"case_id": "current-1", "split": "DEVELOPMENT", "bucket": "CURRENT_LESSON_ANSWERABLE",
            "expected_tier": "CURRENT_LESSON", "expected_behavior": "ANSWER",
            "expected_scope": {"scope_kind": "CURRENT_LESSON", "lesson_locator": "lesson-a"},
            "required_evidence": [{"source_kind": "INTERNAL_CHUNK", "stable_locator": "loc-a",
                                   "requirement_id": "r1", "evidence_id": "e1"}],
            "acceptable_evidence": []}
    trace = _trace(selected_tier="CURRENT_LESSON", selected_evidence_gate_passed=False,
                   selected_evidence=[{"stable_locator": "loc-a", "lesson_locator": "lesson-a",
                                       "rerank_score": -1.2}],
                   tiers_attempted=[{"tier": "CURRENT_LESSON", "attempt_index": 1,
                                     "scope_identity": "CURRENT_LESSON:lesson=x",
                                     "retrieval_status": "SUCCESS", "candidate_count": 1,
                                     "semantic_candidates": [], "rerank_status": "SUCCESS",
                                     "reranked_evidence": [{"rerank_score": -1.2}],
                                     "max_rerank_score": -1.2, "evidence_gate_threshold": -1.0815,
                                     "evidence_gate_passed": False, "scope_violation": False}])
    trace["generation"] = {"called": True, "answer": "answer"}
    trace["prompt"] = {"built": True, "source_map_snapshot": {}, "context_blocks": []}
    result = evaluate_case(case, trace, judge_completed=True)
    assert result["retrieval_ok"] is False
    assert result["e2e_case_pass"] is False


def test_actual_usable_higher_tier_makes_fallback_policy_fail():
    case = {"case_id": "fallback-1", "split": "DEVELOPMENT", "bucket": "INTERNAL_KB_FALLBACK",
            "expected_tier": "INTERNAL_KB", "expected_behavior": "FALLBACK_INTERNAL",
            "expected_scope": {"scope_kind": "INTERNAL_KB"},
            "required_evidence": [{"source_kind": "INTERNAL_CHUNK", "stable_locator": "loc-kb",
                                   "requirement_id": "r1", "evidence_id": "e1"}],
            "acceptable_evidence": []}
    trace = _trace(selected_tier="INTERNAL_KB", selected_evidence_gate_passed=True,
                   selected_evidence=[{"stable_locator": "loc-kb", "source_kind": "INTERNAL_CHUNK"}],
                   tiers_attempted=[
                       {"tier": "CURRENT_LESSON", "attempt_index": 1, "scope_identity": "lesson",
                        "retrieval_status": "SUCCESS", "candidate_count": 1, "semantic_candidates": [],
                        "rerank_status": "SUCCESS", "reranked_evidence": [{"rerank_score": 0.1}],
                        "max_rerank_score": 0.1, "evidence_gate_threshold": -1.0,
                        "evidence_gate_passed": True, "usable_higher_priority_evidence": True,
                        "scope_violation": False},
                       {"tier": "INTERNAL_KB", "attempt_index": 2, "scope_identity": "internal",
                        "retrieval_status": "SUCCESS", "candidate_count": 1, "semantic_candidates": [],
                        "rerank_status": "SUCCESS", "reranked_evidence": [{"rerank_score": 0.1}],
                        "max_rerank_score": 0.1, "evidence_gate_threshold": -1.0,
                        "evidence_gate_passed": True, "scope_violation": False}])
    trace["generation"] = {"called": True, "answer": "answer"}
    trace["prompt"] = {"built": True, "source_map_snapshot": {}, "context_blocks": []}
    result = evaluate_case(case, trace, judge_completed=True)
    assert result["fallback_ok"] is False
    assert result["e2e_case_pass"] is False


def test_prompt_source_map_keeps_uncited_context_source():
    from types import SimpleNamespace
    from app.evaluation.step75.observer import _source_map_snapshot
    package = SimpleNamespace(source_map={
        "S1": SimpleNamespace(chunk_id="chunk-1", url=None, title="one", source_type="LESSON"),
        "S2": SimpleNamespace(chunk_id="chunk-2", url=None, title="two", source_type="LESSON")},
        context_blocks=())
    snapshot = _source_map_snapshot(package)
    cited_labels = {"S1"}
    assert set(snapshot) == {"S1", "S2"}
    assert cited_labels == {"S1"}
    result = evaluate_citation_semantics(
        claims=[{"requires_grounding": True, "cited_labels": ["S1"], "supporting_labels": ["S1"]}],
        current_citation_labels={"S1"}, source_map=snapshot,
        persisted_citations=[{"label": "S1", "source_kind": "INTERNAL_CHUNK",
                              "source_id": "chunk-1", "chunk_id": "chunk-1", "url": None}])
    assert result["citation_correctness_ok"] is True


def test_memory_sanitization_is_verified_against_original_and_actual_memory():
    from types import SimpleNamespace
    from app.evaluation.step75.observer import historical_marker_sanitization_was_observed
    from app.ai.memory.sanitizer import sanitize_historical_assistant_text
    assistant_id = uuid4()
    original = "Earlier answer [S1]"
    turn = SimpleNamespace(assistant_message_id=assistant_id,
                           assistant_text=sanitize_historical_assistant_text(original))
    assert historical_marker_sanitization_was_observed({assistant_id: original}, [turn])
    leaked = SimpleNamespace(assistant_message_id=assistant_id, assistant_text=original)
    assert not historical_marker_sanitization_was_observed({assistant_id: original}, [leaked])


def test_persisted_citation_provenance_mismatch_is_detected():
    result = evaluate_citation_semantics(
        claims=[], current_citation_labels={"S1"},
        source_map={"S1": {"source_kind": "INTERNAL_CHUNK", "source_id": "chunk-current",
                            "chunk_id": "chunk-current", "url": None}},
        persisted_citations=[{"label": "S1", "source_kind": "INTERNAL_CHUNK",
                              "source_id": "different-chunk", "chunk_id": "different-chunk", "url": None}])
    assert result["citation_correctness_ok"] is False
    assert "CITATION_PROVENANCE_MISMATCH" in result["critical_failures"]


def test_required_citation_failure_does_not_fail_semantic_generation_dimension():
    case = {"case_id": "citation-1", "split": "DEVELOPMENT", "bucket": "CURRENT_LESSON_ANSWERABLE",
            "expected_tier": "CURRENT_LESSON", "expected_behavior": "ANSWER",
            "expected_scope": {"scope_kind": "CURRENT_LESSON", "lesson_locator": "lesson-a"},
            "required_evidence": [{"source_kind": "INTERNAL_CHUNK", "stable_locator": "loc-a",
                                   "requirement_id": "r1", "evidence_id": "e1"}],
            "acceptable_evidence": []}
    trace = _trace(selected_tier="CURRENT_LESSON", selected_evidence_gate_passed=True,
                   selected_evidence=[{"stable_locator": "loc-a", "lesson_locator": "lesson-a"}],
                   generation={"called": True, "answer": "factually faithful"},
                   prompt={"built": True, "source_map_snapshot": {"S1": {
                       "source_kind": "INTERNAL_CHUNK", "source_id": "chunk-a",
                       "chunk_id": "chunk-a", "url": None}}, "context_blocks": []},
                   citation_validation={"attempted": True, "valid": True,
                                        "cited_labels": [], "validated_citations": []},
                   persistence={"final_message_status": "COMPLETED", "message_citation_count": 0,
                                "message_retrieval_count": 1, "persisted_citations": []},
                   judge_result={"semantic_critical_failures": ["REQUIRED_CITATION_MISSING"],
                                 "claims": [{"requires_grounding": True, "cited_labels": [],
                                             "supporting_labels": []}]})
    result = evaluate_case(case, trace, judge_completed=True)
    assert result["generation_ok"] is True
    assert result["citation_ok"] is False
    assert "REQUIRED_CITATION_MISSING" in result["critical_failures"]
    assert result["e2e_case_pass"] is False


def test_observer_captures_real_orchestrator_per_tier_rerank_gate_facts(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://offline:offline@localhost:5432/offline")
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.ai.rag.orchestrator import RagOrchestrator
    from app.ai.rag.schemas import RagInternalTier
    from app.ai.retrieval.schemas import RetrievalCandidate
    from app.ai.reranking.schemas import RerankedCandidate, RerankResult
    from app.evaluation.step75.observer import ProductionTraceObserver

    chunk_id, source_id, version_id = uuid4(), uuid4(), uuid4()
    candidate = RetrievalCandidate(
        rank=1, chunk_id=chunk_id, chunk_index=0, content="fixture evidence", content_type="GRAMMAR",
        knowledge_version_id=version_id, knowledge_source_id=source_id, source_type="LESSON",
        source_document_id=None, source_lesson_id=uuid4(), chunk_lesson_id=None,
        document_title=None, lesson_title="Lesson", hsk_level_number=1, page_number=None,
        section=None, locator_metadata=None, distance=0.1, retrieval_score=0.9)
    scored = RerankedCandidate(**candidate.__dict__, rerank_score=-0.5, rerank_rank=1)

    class SessionContext:
        async def __aenter__(self): return object()
        async def __aexit__(self, *args): return False
    class Retrieval:
        async def retrieve(self, query, *, retrieval_filter): return (candidate,)
    class Reranker:
        def rerank(self, query, candidates): return RerankResult((scored,), (scored,))
    class External:
        provider = None
        async def search(self, query): return ()
    class ExternalRerank:
        def rerank(self, query, candidates): return SimpleNamespace(scored_candidates=(), eligible_top_candidates=())
    class Prompt:
        def build(self, *args, **kwargs): raise AssertionError
        def build_from_evidence(self, *args, **kwargs): raise AssertionError
    class Generation:
        provider = None
    settings = SimpleNamespace(rag_min_rerank_score=-1.0815147161483765,
                               external_retrieval_allowed_domains=("www.open.edu",))
    orchestrator = object.__new__(RagOrchestrator)
    orchestrator.settings = settings
    orchestrator.session_factory = SessionContext
    orchestrator.retrieval_factory = lambda session: Retrieval()
    orchestrator.reranker = Reranker()
    orchestrator.external_retrieval_service = External()
    orchestrator.external_reranking_service = ExternalRerank()
    orchestrator.prompt_builder = Prompt()
    orchestrator.generation_service = Generation()
    orchestrator._score_tier = RagOrchestrator._score_tier.__get__(orchestrator, RagOrchestrator)
    observer = ProductionTraceObserver(orchestrator, evidence_metadata_by_chunk_id={
        str(chunk_id): {"source_kind": "LESSON", "source_id": "fixture.lesson", "stable_locators": ["fixture:lesson:block"]}})

    async def run():
        await orchestrator._score_tier("query", candidate.source_lesson_id, RagInternalTier.CURRENT_LESSON)
    try:
        asyncio.run(run())
        attempt = observer.tier_trace([RagInternalTier.CURRENT_LESSON])[0]
        assert attempt["retrieval_status"] == "SUCCESS"
        assert attempt["candidate_count"] == 1
        assert attempt["semantic_candidates"][0]["stable_locators"] == ["fixture:lesson:block"]
        assert attempt["rerank_status"] == "SUCCESS"
        assert attempt["reranked_evidence"][0]["rerank_score"] == -0.5
        assert attempt["evidence_gate_threshold"] == -1.0815147161483765
        assert attempt["evidence_gate_passed"] is True
        assert attempt["retrieval_latency_ms"] is not None
        assert attempt["rerank_latency_ms"] is not None
        from app.ai.citations.schemas import ValidatedCitation
        from app.ai.rag.schemas import RagRunResult, RagRunStatus, RagTierUsed, RetrievalTraceEntry
        source_entry = SimpleNamespace(chunk_id=chunk_id, url=None, title="Lesson",
                                       source_type="LESSON", source_document_id=None,
                                       source_lesson_id=candidate.source_lesson_id,
                                       page_number=None, section=None, locator_metadata=None)
        block = SimpleNamespace(source_label="S1", text="fixture evidence", candidate=scored,
                                url=None, domain=None, title="Lesson", rerank_score=-0.5)
        observer.record_package(SimpleNamespace(
            source_map={"S1": source_entry}, context_blocks=(block,), user_query="query",
            system_instructions="instructions", learning_context=None,
            selected_chunk_ids=(chunk_id,), omitted_chunk_ids=(), conversation_memory=None))
        citation = ValidatedCitation(label="S1", source_kind="INTERNAL_CHUNK", title="Lesson",
                                     chunk_id=chunk_id, source_type="LESSON")
        rag_result = RagRunResult(
            assistant_message_id=uuid4(), status=RagRunStatus.GROUNDED_ANSWER,
            assistant_content="Answer [S1]", tiers_attempted=(RagTierUsed.CURRENT_LESSON,),
            tier_used=RagTierUsed.CURRENT_LESSON, current_lesson_candidate_count=1,
            current_lesson_scored_count=1, internal_kb_candidate_count=0,
            internal_kb_scored_count=0, selected_context_count=1, memory_selected_turn_count=0,
            retrieval_trace=(RetrievalTraceEntry(chunk_id, 1, 0.9, -0.5),),
            validated_citations=(citation,))
        persisted = {"final_message_status": "COMPLETED", "message_retrieval_count": 1,
                     "message_citation_count": 1, "persisted_citations": [{
                         "label": "S1", "source_kind": "INTERNAL_CHUNK", "source_id": str(chunk_id),
                         "chunk_id": str(chunk_id), "url": None}], "persisted_retrievals": []}
        trace = trace_actual_rag_result(
            rag_result, execution_id="exec-trace", case_id="case-trace", repeat_index=1,
            assistant_status="COMPLETED", current_question="query", conversation_id="conv", current_user_message_id="user",
            current_user_sequence_number=2, observer=observer, persisted=persisted,
            lesson_id=str(candidate.source_lesson_id))
        assert trace["tiers_attempted"][0]["evidence_gate_threshold"] == -1.0815147161483765
        assert set(trace["prompt"]["source_map_snapshot"]) == {"S1"}
        assert trace["persistence"]["message_retrieval_count"] == 1
    finally:
        observer.restore()
        get_settings.cache_clear()


def test_official_plan_is_84_executions_from_60_approved_cases():
    root = Path(__file__).resolve().parents[2]
    cases = []
    for split, name in (("DEVELOPMENT", "development.jsonl"), ("HOLDOUT", "holdout.jsonl")):
        cases.extend(json.loads(line) for line in (root / "evaluation/datasets/lesson_chat_rag/v0" / name)
                     .read_text(encoding="utf-8").splitlines() if line)
    plan = plan_executions(cases)
    assert len(plan) == 84
    assert sum(row["split"] == "DEVELOPMENT" for row in plan) == 48
    assert sum(row["split"] == "HOLDOUT" for row in plan) == 36
    assert all(row["repeat_index"] == 1 for row in plan if row["split"] == "DEVELOPMENT")

