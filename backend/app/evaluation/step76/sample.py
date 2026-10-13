from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifacts import write_comparison_artifacts
from .contracts import ComparisonRequest, ComparisonSide, LAYERS
from .loader import load_layer_artifact


def _write_run(root: Path, layer: str, run_id: str, *, candidate: bool) -> Path:
    """Write deterministic fixtures using the current upstream producer shapes."""
    output_root = root / "generation" if layer == "step74" else root
    output_root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"run_id": run_id, "evaluation_step": {"step73": "7.3", "step74": "7.4", "step75": "7.5"}[layer]}
    if layer == "step73":
        manifest.update({
            "dataset_version": "v0.8.0", "dataset_schema_version": "1.0.0",
            "dataset_splits": ["DEVELOPMENT", "HOLDOUT"], "code_commit": "fixture-base" if not candidate else "fixture-candidate",
            "embedding_model": "BAAI/bge-m3", "embedding_model_version": "pinned-test-revision",
            "chunking_version": "structure_aware/v1", "candidate_k": 20,
            "reranker_model": "BAAI/bge-reranker-v2-m3", "reranker_model_version": "pinned-test-revision",
            "reranker_top_k": 5, "reranker_config": {"input_version": "v1", "batch_size": 8},
            "retrieval_filter_config": {"CURRENT_LESSON": "scoped", "INTERNAL_KB": "approved-internal"},
            "RAG_EVIDENCE_CALIBRATION_MODE": True,
        })
        rows = [
            {"case_id": "fixture-dev-01", "bucket": "CURRENT_LESSON_ANSWERABLE", "split": "DEVELOPMENT", "case_scope_violation": False, "tier_attempts": []},
            {"case_id": "fixture-holdout-01", "bucket": "CURRENT_LESSON_ANSWERABLE", "split": "HOLDOUT", "case_scope_violation": False, "tier_attempts": []},
        ]
        metric = lambda value: {"semantic_recall20": value, "reranked_recall5": value, "reranked_precision5": value, "reranked_ndcg5": value}
        summary = {"run_id": run_id, "dataset_version": "v0.8.0", "metrics_overall": metric(.90 if not candidate else .91),
                   "metrics_by_split": {"DEVELOPMENT": metric(.90 if not candidate else .91), "HOLDOUT": metric(.90 if not candidate else .91)},
                   "metrics_by_bucket": {"CURRENT_LESSON_ANSWERABLE": metric(.90 if not candidate else .91)}, "cases_with_scope_violation": 0, "scope_violation_rate": 0.0}
    elif layer == "step74":
        manifest.update({"run_status": "OFFLINE_TEST_ONLY", "execution_mode": "OFFLINE_TEST",
                         "dataset_name": "lesson_chat_rag", "dataset_version": "v0.8.0", "dataset_schema_version": "1.0.0",
                         "eligible_case_policy_version": "step74-eligible/v1", "fixed_evidence_policy_version": "fixed-approved-evidence/v1",
                         "fixed_memory_policy_version": "fixed-memory/v1", "rubric_version": "lesson-chat-generation-rubric/v1",
                         "judge_prompt_version": "lesson-chat-generation-judge/v1", "human_annotation_version": "lesson-chat-generation-human/v0.1.0",
                         "technical_failure_policy_version": "generation-vs-judge-technical-failure/v1", "generator_model": "gpt-5.4-mini-2026-03-17",
                         "generator_identity": {"provider": "test-only", "model": "gpt-5.4-mini-2026-03-17"},
                         "generator_prompt_version_or_hash": "fixture-prompt-hash", "judge_model": "gpt-5.4-2026-03-05",
                         "judge_identity": {"provider": "test-only", "model": "gpt-5.4-2026-03-05"}, "human_approved_count": 0,
                         "runtime_api_calls": 0, "judge_calibration_success_count": 0})
        rows = [
            {"case_id": "fixture-dev-01", "bucket": "CURRENT_LESSON_ANSWERABLE", "split": "DEVELOPMENT", "dimension_scores": {"answer_correctness": 1.3}, "critical_failures": [], "judge": {"status": "SUCCESS"}},
            {"case_id": "fixture-holdout-01", "bucket": "CURRENT_LESSON_ANSWERABLE", "split": "HOLDOUT", "dimension_scores": {"answer_correctness": 1.3}, "critical_failures": [], "judge": {"status": "SUCCESS"}},
        ]
        dims = ("answer_correctness", "faithfulness_groundedness", "completeness", "language_quality", "learning_usefulness")
        means = {name: 1.1 if not candidate else 1.12 for name in dims}
        summary = {"run_id": run_id, "dataset_name": "lesson_chat_rag", "dataset_version": "v0.8.0",
                   "mean_score_by_dimension": means,
                   "metrics_by_split": {"DEVELOPMENT": {"mean_score_by_dimension": means}, "HOLDOUT": {"mean_score_by_dimension": means}},
                   "metrics_by_bucket": {"CURRENT_LESSON_ANSWERABLE": {"mean_score_by_dimension": means}}}
    else:
        manifest.update({"run_status": "OFFLINE_TEST_ONLY", "execution_mode": "OFFLINE_TEST", "official_baseline_eligible": False,
                         "official_run_executed": False, "dataset_name": "lesson_chat_rag", "dataset_version": "v0.8.0",
                         "dataset_schema_version": "1.0.0", "execution_plan_version": "step75-execution-plan/v1",
                         "retrieval_scope_policy_version": "lesson-chat-tier-scope/v1", "e2e_policy_version": "lesson-chat-e2e-policy/v1",
                         "critical_failure_policy_version": "lesson-chat-e2e-critical/v1", "human_annotation_version": "lesson-chat-e2e-human/v0.1.0",
                         "judge_prompt_version": "lesson-chat-e2e-judge/v1", "judge_schema_version": "1.0.0",
                         "e2e_rubric_version": "lesson-chat-e2e-rubric/v1", "prompt_system_identity": "production-system-instructions",
                         "prompt_system_sha256": "test-only", "rag_min_rerank_score": -1.0, "human_approved_count": 0,
                         "judge_model": "gpt-5.4-2026-03-05", "judge_reasoning_effort": "none",
                         "judge_temperature": 0, "judge_max_output_tokens": 1600})
        dev_pass = True if not candidate else True
        rows = [{"case_id": "fixture-dev-01", "bucket": "CURRENT_LESSON_ANSWERABLE", "split": "DEVELOPMENT", "repeat_index": 1,
                 "e2e_case_pass": dev_pass, "critical_failures": [], "technical_ok": True,
                 "trace": {"timings": {"total_latency_ms": 1100 if not candidate else 1080}}}]
        for index in (1, 2, 3):
            rows.append({"case_id": "fixture-holdout-01", "bucket": "CURRENT_LESSON_ANSWERABLE", "split": "HOLDOUT", "repeat_index": index,
                         "e2e_case_pass": True, "critical_failures": [], "technical_ok": True,
                         "trace": {"timings": {"total_latency_ms": 1100 if not candidate else 1080}}})
        summary = {"run_id": run_id, "e2e_case_pass_rate": 1.0, "overall_e2e_hard_validity_pass_rate": 1.0,
                   "technical_failure_rate": 0.0, "quality_rates_by_bucket": {"CURRENT_LESSON_ANSWERABLE": {"e2e_case_pass_rate": 1.0}},
                   "operational_latency_test_only": {"total_latency_ms": {"count": len(rows), "mean": 1100 if not candidate else 1080,
                                                                                "p50": 1100 if not candidate else 1080, "p95": 1100 if not candidate else 1080}},
                   "holdout_repeat_stability_test_only": {"fixture-holdout-01": {"execution_count": 3, "pass_count": 3}}}
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_root / "cases.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    return root


def generate_sample(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    fixture_root = root / "evaluation" / "fixtures" / "step76" / "v1"
    sides: dict[str, dict[str, Path]] = {"baseline": {}, "candidate": {}}
    for side, candidate in (("baseline", False), ("candidate", True)):
        for layer in LAYERS:
            run_id = f"step76-fixture-{side}-{layer}-v1"
            sides[side][layer] = _write_run(fixture_root / side / layer, layer, run_id, candidate=candidate)
    loaded = {side: {layer: load_layer_artifact(layer, directory) for layer, directory in paths.items()}
              for side, paths in sides.items()}
    request = ComparisonRequest("step76-test-comparison-v1",
                                ComparisonSide("step76-fixture-baseline-system-v1", loaded["baseline"]),
                                ComparisonSide("step76-fixture-candidate-system-v1", loaded["candidate"]),
                                "TEST_ONLY", "2026-10-12T00:00:00Z")
    return write_comparison_artifacts(request, root / "evaluation" / "regressions")
