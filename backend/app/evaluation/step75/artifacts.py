from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_offline_artifact_manifest(manifest: dict) -> None:
    if manifest.get("execution_mode") == "OFFLINE_TEST":
        if manifest.get("official_baseline_eligible") is not False:
            raise ValueError("OFFLINE_ARTIFACT_CANNOT_BE_OFFICIAL_BASELINE")
        if manifest.get("artifact_kind") == "OFFICIAL_RUNTIME":
            raise ValueError("OFFLINE_ARTIFACT_CANNOT_CLAIM_OFFICIAL_RUNTIME")
    if manifest.get("official_run_executed") is True:
        raise ValueError("OFFLINE_IMPLEMENTATION_CANNOT_RECORD_OFFICIAL_RUN")


def safe_case_for_artifact(result: dict) -> dict:
    """Reject secrets, raw vectors, and judge chain-of-thought before serialization."""
    raw = canonical_json(result).lower()
    banned = (b"api_key", b"secret_key", b"access_token", b"chain_of_thought", b"raw_vector")
    if any(term in raw for term in banned):
        raise ValueError("E2E_ARTIFACT_CONTAINS_PROHIBITED_FIELD")
    return result


def write_offline_manifest(path: Path, *, run_id: str, cases_sha256: str) -> None:
    manifest = {
        "run_id": run_id, "execution_mode": "OFFLINE_TEST",
        "artifact_kind": "OFFLINE_TEST", "official_baseline_eligible": False,
        "official_run_executed": False, "cases_artifact_sha256": cases_sha256,
        "dataset_version": "v0.8.0", "planned_official_executions": 84,
    }
    validate_offline_artifact_manifest(manifest)
    path.write_bytes(canonical_json(manifest) + b"\n")


def build_offline_manifest(*, run_id: str, started_at: str, cases_sha256: str,
                           fixture_hashes: dict, settings) -> dict:
    """Record frozen system identity without credentials or official-run claims."""
    import hashlib
    from app.ai.prompting.instructions import SYSTEM_INSTRUCTIONS
    system_hash = hashlib.sha256(SYSTEM_INSTRUCTIONS.encode("utf-8")).hexdigest()
    if settings.rag_min_rerank_score != -1.0815147161483765:
        raise ValueError("STEP75_FROZEN_RERANK_THRESHOLD_MISMATCH")
    if (settings.embedding_model_revision != "5617a9f61b028005a4858fdac845db406aefb181"
            or settings.reranker_model_revision != "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"):
        raise ValueError("STEP75_PINNED_MODEL_REVISION_MISMATCH")
    manifest = {
        "run_id": run_id, "run_status": "OFFLINE_TEST_ONLY", "execution_mode": "OFFLINE_TEST",
        "official_baseline_eligible": False, "operational_metrics_official": False,
        "timestamp_started": started_at, "timestamp_finalized": None, "evaluation_step": "7.5",
        "dataset_name": "lesson_chat_rag", "dataset_version": "v0.8.0",
        "dataset_schema_version": "1.0.0", "dataset_case_count": 60,
        "development_case_count": 48, "holdout_case_count": 12,
        "execution_plan_version": "step75-execution-plan/v1",
        "development_execution_count": 48, "holdout_execution_count": 36,
        "total_execution_count": 84, "fixture_hashes": fixture_hashes,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model_name,
        "embedding_revision": settings.embedding_model_revision,
        "embedding_profile": settings.embedding_input_version,
        "embedding_dimensions": 1024,
        "retrieval_candidate_k": settings.rag_retrieval_candidate_k,
        "retrieval_scope_policy_version": "lesson-chat-tier-scope/v1",
        "reranker_model": settings.reranker_model_name,
        "reranker_revision": settings.reranker_model_revision,
        "reranker_top_k": settings.reranker_top_k,
        "rag_min_rerank_score": settings.rag_min_rerank_score,
        "prompt_system_identity": "production-system-instructions",
        "prompt_system_sha256": system_hash,
        "context_builder_identity": "app.ai.prompting.builder.PromptContextBuilder",
        "memory_policy": "production-conversation-memory/v1",
        "memory_max_turns": settings.rag_memory_max_turns,
        "llm_mode": "DETERMINISTIC_FAKE", "llm_provider": "test-only",
        "llm_model": settings.llm_model,
        "llm_generation_config": {"temperature": settings.llm_temperature,
                                  "max_output_tokens": settings.llm_max_output_tokens,
                                  "reasoning_effort": settings.llm_reasoning_effort},
        "external_mode": "FIXTURE", "judge_mode": "DETERMINISTIC_FAKE",
        "external_provider_identity": "step75-reviewed-fixture/v0.1.0",
        "judge_provider": "test-only", "judge_api": "responses",
        "judge_model": "gpt-5.4-2026-03-05", "judge_reasoning_effort": "none",
        "judge_temperature": 0, "judge_max_output_tokens": 1600,
        "judge_prompt_version": "lesson-chat-e2e-judge/v1",
        "judge_schema_version": "1.0.0", "e2e_rubric_version": "lesson-chat-e2e-rubric/v1",
        "e2e_policy_version": "lesson-chat-e2e-policy/v1",
        "critical_failure_policy_version": "lesson-chat-e2e-critical/v1",
        "human_annotation_version": "lesson-chat-e2e-human/v0.1.0",
        "human_calibration_case_count_expected": 30, "human_approved_count": 0,
        "citation_validator_identity": "app.ai.citations.validator.CitationValidator",
        "cases_artifact_sha256": cases_sha256, "official_run_executed": False,
    }
    validate_offline_artifact_manifest(manifest)
    return manifest


def _rate(rows: list[dict], field: str) -> float | None:
    return sum(bool(row.get(field)) for row in rows) / len(rows) if rows else None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def _dimension_rows(rows: list[dict]) -> dict:
    fields = ("answer_correctness", "faithfulness_groundedness", "completeness",
              "language_quality", "learning_usefulness")
    result = {}
    for field in fields:
        scores = []
        for row in rows:
            value = (row.get("generation_dimension_scores") or {}).get(field)
            score = value.get("score") if isinstance(value, dict) else value
            if type(score) is int and score in (0, 1, 2):
                scores.append(score)
        result[field] = {"count": len(scores), "distribution": {str(n): scores.count(n) for n in (0, 1, 2)},
                         "mean": sum(scores) / len(scores) if scores else None}
    return result


def build_summary(rows: list[dict], *, run_id: str, planned_count: int = 84) -> dict:
    root = Path(__file__).resolve().parents[4]
    dataset_root = root / "evaluation/datasets/lesson_chat_rag/v0"
    planned_cases = [json.loads(line) for filename in ("development.jsonl", "holdout.jsonl")
                     for line in (dataset_root / filename).read_text(encoding="utf-8").splitlines() if line]
    from .planner import plan_executions
    planned_rows = plan_executions(planned_cases)
    if len(planned_rows) != planned_count:
        raise ValueError("E2E_SUMMARY_PLANNED_COUNT_MISMATCH")
    by_split_bucket = Counter((row["split"], row["bucket"]) for row in rows)
    planned_by_split_bucket = Counter((row["split"], row["bucket"]) for row in planned_rows)
    dimensions = ("retrieval_ok", "generation_ok", "citation_correctness_ok",
                  "citation_coverage_ok", "context_ok", "fallback_ok", "refusal_ok", "technical_ok")
    by_bucket = {}
    for bucket in sorted({row["bucket"] for row in rows}):
        subset = [row for row in rows if row["bucket"] == bucket]
        by_bucket[bucket] = {"executed_count": len(subset), "e2e_case_pass_rate": _rate(subset, "e2e_case_pass"),
                             **{name: _rate(subset, name) for name in dimensions}}
    critical_types = Counter(name for row in rows for name in row.get("critical_failures", []))
    critical_executions = sum(bool(row.get("critical_failures")) for row in rows)
    latency_fields = ("total_latency_ms", "retrieval_latency_ms", "rerank_latency_ms", "llm_latency_ms",
                      "context_build_duration_ms", "evaluation_only_persistence_readback_latency_ms",
                      "citation_validation_latency_ms", "citation_finalization_latency_ms",
                      "evaluation_only_citation_finalization_diagnostic_latency_ms")
    latency = {}
    for field in latency_fields:
        values = [float(row.get("trace", {}).get("timings", {}).get(field)) for row in rows
                  if isinstance(row.get("trace", {}).get("timings", {}).get(field), (int, float))]
        latency[field] = {"count": len(values), "mean": sum(values) / len(values) if values else None,
                          "p50": _percentile(values, .5), "p95": _percentile(values, .95)}
    token_fields = ("input_tokens", "output_tokens", "total_tokens")
    token_usage = {}
    for field in token_fields:
        values = [row["trace"]["generation"]["token_usage"].get(field) for row in rows
                  if isinstance(row.get("trace", {}).get("generation", {}).get("token_usage"), dict)
                  and type(row["trace"]["generation"]["token_usage"].get(field)) is int]
        token_usage[field] = {"count": len(values), "sum": sum(values),
                              "mean": sum(values) / len(values) if values else None}
    holdout = {}
    holdout_cases = sorted({row["case_id"] for row in rows if row["split"] == "HOLDOUT"})
    for case_id in holdout_cases:
        subset = sorted((row for row in rows if row["case_id"] == case_id), key=lambda row: row["repeat_index"])
        score_rows = [row for row in subset if row.get("generation_dimension_scores")]
        variances = {}
        for name, score in _dimension_rows(score_rows).items():
            vals = [((row.get("generation_dimension_scores") or {}).get(name) or {}).get("score")
                    for row in score_rows]
            vals = [value for value in vals if type(value) is int]
            variances[name] = (sum((value - sum(vals) / len(vals)) ** 2 for value in vals) / len(vals)
                               if vals else None)
        holdout[case_id] = {
            "execution_count": len(subset), "expected_execution_count": 3,
            "pass_count": sum(bool(row.get("e2e_case_pass")) for row in subset),
            "pass_rate": _rate(subset, "e2e_case_pass"),
            "critical_failure_repeat_count": sum(bool(row.get("critical_failures")) for row in subset),
            "critical_failure_types_by_repeat": [
                {"repeat_index": row["repeat_index"], "types": list(row.get("critical_failures", []))}
                for row in subset],
            "generation_dimension_variance": variances,
        }
    result = {name: _rate(rows, name) for name in dimensions}
    result.update({"run_id": run_id, "execution_mode": "OFFLINE_TEST",
                   "metrics_classification": "TEST_ONLY_NOT_PRODUCTION_BASELINE",
                   "operational_metrics_official": False,
                   "planned_execution_count": planned_count,
                   "total_planned_execution_count": planned_count,
                   "executed_count": len(rows), "total_executed_execution_count": len(rows),
                   "overall_e2e_hard_validity_pass_rate": _rate(rows, "e2e_case_pass"),
                   "e2e_case_pass_rate": _rate(rows, "e2e_case_pass"),
                   "case_counts_by_split": {split: len({r["case_id"] for r in rows if r["split"] == split})
                                             for split in ("DEVELOPMENT", "HOLDOUT")},
                   "planned_case_counts_by_split": {split: len({r["case_id"] for r in planned_cases
                                               if r["split"] == split}) for split in ("DEVELOPMENT", "HOLDOUT")},
                   "planned_execution_counts_by_split": {split: sum(r["split"] == split for r in planned_rows)
                                                          for split in ("DEVELOPMENT", "HOLDOUT")},
                   "execution_counts_by_split": {split: sum(r["split"] == split for r in rows)
                                                  for split in ("DEVELOPMENT", "HOLDOUT")},
                   "planned_execution_counts_by_bucket": {bucket: sum(r["bucket"] == bucket
                       for r in planned_rows) for bucket in sorted({r["bucket"] for r in planned_rows})},
                   "planned_execution_counts_by_split_bucket": {
                       f"{split}:{bucket}": count for (split, bucket), count
                       in sorted(planned_by_split_bucket.items())},
                   "counts_by_bucket": {bucket: sum(r["bucket"] == bucket for r in rows)
                                        for bucket in sorted({r["bucket"] for r in rows})},
                   "counts_by_split_bucket": {f"{split}:{bucket}": count
                                               for (split, bucket), count in sorted(by_split_bucket.items())},
                   "pass_rate_by_bucket": {bucket: values["e2e_case_pass_rate"]
                                           for bucket, values in by_bucket.items()},
                   "quality_rates_by_bucket": by_bucket,
                   "technical_failure_rate": (sum(not bool(row.get("technical_ok")) for row in rows) / len(rows)
                                              if rows else None),
                   "critical_failures": {"total_count": sum(len(row.get("critical_failures", [])) for row in rows),
                                         "execution_count": critical_executions,
                                         "rate": critical_executions / len(rows) if rows else None,
                                         "counts_by_type": dict(sorted(critical_types.items()))},
                   "generation_quality": _dimension_rows([row for row in rows
                       if row.get("generation_applicable") and row.get("generation_dimension_scores")]),
                   "operational_latency_test_only": latency,
                   "token_usage_test_only": token_usage,
                   "holdout_repeat_stability_test_only": holdout,
                   "human_approved_count": 0, "official_baseline_eligible": False})
    return result


def write_offline_artifacts(directory: Path, *, manifest: dict, rows: list[dict]) -> None:
    """Write only to a caller-owned temporary directory in deterministic test mode."""
    validate_offline_artifact_manifest(manifest)
    if manifest.get("execution_mode") != "OFFLINE_TEST":
        raise ValueError("OFFLINE_WRITER_REQUIRES_OFFLINE_TEST_MODE")
    directory.mkdir(parents=True, exist_ok=True)
    safe_rows = [safe_case_for_artifact(row) for row in rows]
    cases = b"".join(canonical_json(row) + b"\n" for row in safe_rows)
    (directory / "cases.jsonl").write_bytes(cases)
    frozen_manifest = {**manifest, "cases_artifact_sha256": sha256(cases),
                       "executed_count": len(safe_rows)}
    (directory / "manifest.json").write_bytes(canonical_json(frozen_manifest) + b"\n")
    (directory / "summary.json").write_bytes(canonical_json(
        build_summary(safe_rows, run_id=manifest["run_id"])) + b"\n")
