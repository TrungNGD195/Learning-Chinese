from __future__ import annotations

import hashlib
from collections import Counter
from importlib.metadata import version as package_version
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from .annotations import ANNOTATION_ROOT, CALIBRATION_IDS, make_draft_packet, write_source_controlled_template
from .contracts import (
    DATASET_NAME, DATASET_SCHEMA_VERSION, DATASET_VERSION,
    ELIGIBLE_CASE_POLICY_VERSION, FIXED_EVIDENCE_POLICY_VERSION,
    FIXED_MEMORY_POLICY_VERSION, GENERATOR_MODEL, HUMAN_ANNOTATION_VERSION,
    JUDGE_MODEL, JUDGE_PROMPT_VERSION, RUBRIC_VERSION,
)
from app.ai.prompting.instructions import SYSTEM_INSTRUCTIONS

ROOT = Path(__file__).resolve().parents[4]
RUNS_ROOT = ROOT / "evaluation/runs"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def verify_stage_a_case_file_binding(manifest: dict, case_file_content: bytes) -> None:
    if hashlib.sha256(case_file_content).hexdigest() != manifest.get("cases_file_sha256"):
        raise ValueError("STEP74_STAGE_A_ARTIFACT_HASH_MISMATCH")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def build_manifest(*, run_id: str, evidence_resolver, generation_config, prompt_builder, token_counter,
                   run_status: str, started: datetime, rows: list[dict], runtime_smoke: dict) -> dict:
    try:
        import subprocess
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                capture_output=True, check=True).stdout.strip()
    except Exception:
        commit = None
    prompt_version = "production-system-instructions/sha256:" + hashlib.sha256(
        SYSTEM_INSTRUCTIONS.encode("utf-8")
    ).hexdigest()
    return {
        "run_id": run_id, "run_status": run_status,
        "execution_mode": "OFFICIAL_REAL_RUNTIME",
        "timestamp_started": started.isoformat(), "evaluation_step": "7.4",
        "dataset_name": DATASET_NAME, "dataset_version": DATASET_VERSION,
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "eligible_case_policy_version": ELIGIBLE_CASE_POLICY_VERSION,
        "eligible_case_count": len(rows),
        "development_case_count": sum(row.get("split") == "DEVELOPMENT" for row in rows),
        "holdout_case_count": sum(row.get("split") == "HOLDOUT" for row in rows),
        "included_bucket_counts": {
            "DEVELOPMENT": {"CURRENT_LESSON_ANSWERABLE": 16, "INTERNAL_KB_FALLBACK": 8,
                            "TRUSTED_EXTERNAL_FALLBACK": 4, "MULTI_TURN_CONTEXT": 8},
            "HOLDOUT": {"CURRENT_LESSON_ANSWERABLE": 4, "INTERNAL_KB_FALLBACK": 2,
                        "TRUSTED_EXTERNAL_FALLBACK": 1, "MULTI_TURN_CONTEXT": 2},
        },
        "excluded_buckets": ["NO_EVIDENCE_REFUSAL", "OUT_OF_DOMAIN_REFUSAL"],
        "code_commit": commit,
        "fixed_evidence_policy_version": FIXED_EVIDENCE_POLICY_VERSION,
        "internal_fixture_pack_version": "0.1.0",
        "internal_fixture_manifest_sha256": evidence_resolver.fixture_manifest_sha256,
        "internal_fixture_content_sha256": evidence_resolver.fixture_content_sha256,
        "trusted_external_registry_version": "0.1.0",
        "trusted_external_registry_sha256": evidence_resolver.external_manifest_sha256,
        "fixed_memory_policy_version": FIXED_MEMORY_POLICY_VERSION,
        "generator_provider": "openai", "generator_model": GENERATOR_MODEL,
        "generator_temperature": generation_config.temperature,
        "generator_max_output_tokens": generation_config.max_output_tokens,
        "generator_timeout_seconds": generation_config.request_timeout_seconds,
        "generator_max_transient_retries": generation_config.max_transient_retries,
        "generator_streaming": False, "generator_tools": [],
        "generator_identity": {
            "provider": "openai", "model": GENERATOR_MODEL,
            "temperature": generation_config.temperature,
            "max_output_tokens": generation_config.max_output_tokens,
            "reasoning_effort": generation_config.reasoning_effort,
            "model_input_limit": generation_config.model_input_limit,
            "timeout_seconds": generation_config.request_timeout_seconds,
            "max_transient_retries": generation_config.max_transient_retries,
            "streaming": False, "tools": [],
        },
        "generator_prompt_version_or_hash": prompt_version,
        "context_builder_version": "PromptContextBuilder",
        "token_counter_identity": f"{type(token_counter).__name__};tiktoken={package_version('tiktoken')}",
        "prompt_budget": {"model_input_limit": generation_config.model_input_limit,
                           "reserved_output_tokens": generation_config.max_output_tokens,
                           "serialization_overhead_tokens": 0},
        "judge_provider": "OpenAI API", "judge_api": "Responses API", "judge_model": JUDGE_MODEL,
        "judge_reasoning_effort": "none", "judge_temperature": 0,
        "judge_max_output_tokens": 1600, "judge_structured_output": True,
        "judge_tools": [], "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "judge_identity": {
            "provider": "OpenAI API", "api": "Responses API", "model": JUDGE_MODEL,
            "reasoning_effort": "none", "temperature": 0,
            "max_output_tokens": 1600, "structured_output": True, "tools": [],
        },
        "rubric_version": RUBRIC_VERSION,
        "human_annotation_version": HUMAN_ANNOTATION_VERSION,
        "human_calibration_case_count": 0,
        "human_calibration_case_ids": list(CALIBRATION_IDS),
        "human_calibration_packet_created": False,
        "human_calibration_packet_status": "NOT_CREATED",
        "human_calibration_draft_count": 0,
        "human_calibration_status": "NOT_CREATED",
        "technical_failure_policy_version": "generation-vs-judge-technical-failure/v1",
        "runtime_smoke": runtime_smoke,
        "runtime_api_calls": runtime_smoke["total_api_calls"] + sum(
            row.get("generator", {}).get("attempt_count") or 0 for row in rows
        ),
        "generator_success_count": sum(row.get("generator", {}).get("status") == "SUCCESS" for row in rows),
        "generator_technical_failure_count": sum(row.get("generator", {}).get("status") != "SUCCESS" for row in rows),
        "judge_success_count": 0,
        "judge_technical_failure_count": 0,
        "judge_not_run_count": len(rows),
        "judge_calibration_success_count": 0,
        "human_approved_count": 0,
        "case_counts_by_split": {split: sum(row["split"] == split for row in rows)
                                  for split in ("DEVELOPMENT", "HOLDOUT")},
        "case_counts_by_bucket": _bucket_counts(rows),
    }


def _bucket_counts(rows: list[dict]) -> dict:
    buckets: dict[str, dict[str, int]] = {}
    for row in rows:
        split, bucket = row["split"], row["bucket"]
        buckets.setdefault(split, {})[bucket] = buckets.setdefault(split, {}).get(bucket, 0) + 1
    return buckets


def build_stage_a_summary(run_id: str, rows: list[dict], *, identity: dict | None = None) -> dict:
    successes = sum(row["generator"]["status"] == "SUCCESS" for row in rows)
    failures = len(rows) - successes
    split_counts = {split: sum(row["split"] == split for row in rows) for split in ("DEVELOPMENT", "HOLDOUT")}
    summary = {
        "run_id": run_id, "run_status": identity.get("run_status") if identity else "OFFLINE_TEST_ONLY",
        "dataset_name": DATASET_NAME, "dataset_version": DATASET_VERSION,
        "dataset_schema_version": DATASET_SCHEMA_VERSION, "evaluation_step": "7.4",
        "eligible_case_policy_version": ELIGIBLE_CASE_POLICY_VERSION,
        "fixed_evidence_policy_version": FIXED_EVIDENCE_POLICY_VERSION,
        "fixed_memory_policy_version": FIXED_MEMORY_POLICY_VERSION,
        "rubric_version": RUBRIC_VERSION, "human_annotation_version": HUMAN_ANNOTATION_VERSION,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "eligible_case_count": len(rows),
        "case_counts_by_split": split_counts, "case_counts_by_bucket": _bucket_counts(rows),
        "generator_success_count": successes, "generator_technical_failure_count": failures,
        "generator_technical_success_rate": successes / len(rows) if rows else None,
        "judge_success_count": 0, "judge_technical_failure_count": 0, "judge_not_run_count": len(rows),
        "judge_technical_success_rate_on_generated_answers": None,
        "mean_score_by_dimension": None, "score_distribution_by_dimension": None,
        "cases_with_score_0_by_dimension": None, "metrics_by_split": None, "metrics_by_bucket": None,
        "claim_verdict_counts": None, "cases_with_unsupported_claims": None,
        "cases_with_contradicted_claims": None, "critical_failure_case_count": None,
        "critical_failure_rate_among_judged_cases": None, "critical_failure_counts_by_type": None,
        "generation_case_status_counts": dict(sorted(Counter(
            row["generation_case_status"] for row in rows
        ).items())),
        "human_calibration_case_count": 0, "human_calibration_packet_created": False,
        "human_calibration_packet_status": "NOT_CREATED", "human_calibration_draft_count": 0,
        "human_calibration_status": "NOT_CREATED", "human_approved_count": 0,
        "judge_calibration_success_count": 0,
        "human_judge_agreement_headline": None, "latency_ms_mean": _mean_latency(rows),
        "token_usage": {"input_tokens": _sum_usage(rows, "input_tokens"),
                        "output_tokens": _sum_usage(rows, "output_tokens"),
                        "total_tokens": _sum_usage(rows, "total_tokens")},
    }
    if identity:
        for key in ("execution_mode", "generator_model", "judge_model", "runtime_api_calls", "runtime_smoke",
                    "generator_identity", "judge_identity", "stage_a_started",
                    "human_calibration_case_count", "human_calibration_packet_created",
                    "human_calibration_packet_status", "human_calibration_draft_count",
                    "human_calibration_status", "human_approved_count", "human_annotation_version"):
            if key in identity:
                summary[key] = identity[key]
    else:
        summary["run_status"] = "OFFLINE_TEST_ONLY"
        summary["execution_mode"] = "OFFLINE_TEST"
        summary["runtime_api_calls"] = 0
    return summary


def _mean_latency(rows: list[dict]):
    values = [row["generator"].get("latency_ms") for row in rows if row["generator"].get("latency_ms") is not None]
    return sum(values) / len(values) if values else None


def _sum_usage(rows: list[dict], key: str):
    values = [row["generator"].get("token_usage", {}).get(key) for row in rows]
    values = [value for value in values if type(value) is int]
    return sum(values) if values else None


def derive_stage_a_state(*, official: bool, rows: list[dict], packet_count: int,
                         packet_creation_error: str | None = None) -> dict:
    """Derive terminal metadata only from the actual case and packet results."""
    successes = sum(row.get("generator", {}).get("status") == "SUCCESS" for row in rows)
    failures = len(rows) - successes
    complete_packet = packet_count == 30
    if not official:
        run_status = "OFFLINE_TEST_ONLY"
        packet_count = 0
        packet_status = "NOT_CREATED"
    elif complete_packet and failures == 0:
        run_status = "REVIEW_REQUIRED_HUMAN_CALIBRATION"
        packet_status = "DRAFT_CREATED"
    elif failures:
        run_status = "GENERATOR_TECHNICAL_FAILURES"
        packet_status = "INCOMPLETE" if packet_count else "NOT_CREATED"
    elif packet_count:
        run_status = "CALIBRATION_PACKET_INCOMPLETE"
        packet_status = "INCOMPLETE"
    else:
        run_status = "CALIBRATION_PACKET_CREATION_FAILED"
        packet_status = "NOT_CREATED"
    return {
        "run_status": run_status,
        "stage_a_started": official,
        "human_calibration_packet_created": packet_count > 0 and official,
        "human_calibration_packet_status": packet_status,
        "human_calibration_case_count": packet_count if official else 0,
        "human_calibration_draft_count": packet_count if official else 0,
        "human_calibration_status": (
            f"{packet_count} DRAFT; MANUAL REVIEW REQUIRED"
            if complete_packet and official and failures == 0
            else packet_status
        ),
        "human_approved_count": 0,
        "human_annotation_version": HUMAN_ANNOTATION_VERSION,
        "generator_success_count": successes,
        "generator_technical_failure_count": failures,
        "calibration_packet_creation_error": packet_creation_error,
    }


def validate_artifact_metadata(manifest: dict, rows: list[dict], summary: dict, agreement: dict) -> None:
    shared = (
        "run_id", "dataset_name", "dataset_version", "dataset_schema_version", "evaluation_step",
        "eligible_case_policy_version", "fixed_evidence_policy_version", "fixed_memory_policy_version",
        "rubric_version", "human_annotation_version", "judge_prompt_version", "execution_mode",
        "generator_identity", "judge_identity",
    )
    expected_identity = {key: manifest.get(key) for key in shared}
    for artifact in (summary, agreement):
        if any(artifact.get(key) != value for key, value in expected_identity.items()):
            raise ValueError("STEP74_ARTIFACT_IDENTITY_MISMATCH")
    if len(rows) != 45 or len({row.get("case_id") for row in rows}) != 45:
        raise ValueError("STEP74_ARTIFACT_CASE_COUNT_MISMATCH")
    if any(any(row.get(key) != value for key, value in expected_identity.items()) for row in rows):
        raise ValueError("STEP74_CASE_ARTIFACT_IDENTITY_MISMATCH")
    run_status = manifest.get("run_status")
    execution_mode = manifest.get("execution_mode")
    if summary.get("run_status") != run_status or any(
        row.get("run_status") != run_status or row.get("execution_mode") != execution_mode for row in rows
    ):
        raise ValueError("STEP74_ARTIFACT_RUN_STATUS_MISMATCH")
    split_counts = {split: sum(row.get("split") == split for row in rows)
                    for split in ("DEVELOPMENT", "HOLDOUT")}
    success_count = sum(row.get("generator", {}).get("status") == "SUCCESS" for row in rows)
    failure_count = len(rows) - success_count
    if (summary.get("eligible_case_count") != len(rows)
            or summary.get("case_counts_by_split") != split_counts
            or manifest.get("eligible_case_count") != len(rows)
            or summary.get("generator_success_count") != success_count
            or summary.get("generator_technical_failure_count") != failure_count):
        raise ValueError("STEP74_ARTIFACT_COUNT_MISMATCH")
    if (manifest.get("case_counts_by_split") != split_counts
            or manifest.get("generator_success_count") != success_count
            or manifest.get("generator_technical_failure_count") != failure_count):
        raise ValueError("STEP74_MANIFEST_COUNT_MISMATCH")
    if summary.get("case_counts_by_bucket") != _bucket_counts(rows) or manifest.get("case_counts_by_bucket") != _bucket_counts(rows):
        raise ValueError("STEP74_ARTIFACT_BUCKET_COUNT_MISMATCH")
    if (summary.get("generator_model") != manifest.get("generator_model")
            or summary.get("judge_model") != manifest.get("judge_model")
            or summary.get("case_counts_by_split") != manifest.get("case_counts_by_split")
            or summary.get("case_counts_by_bucket") != manifest.get("case_counts_by_bucket")
            or agreement.get("eligible_case_count") != 45
            or agreement.get("case_counts_by_split") != split_counts
            or agreement.get("case_counts_by_bucket") != _bucket_counts(rows)):
        raise ValueError("STEP74_ARTIFACT_COUNT_OR_MODEL_IDENTITY_MISMATCH")
    for key in ("generator_success_count", "generator_technical_failure_count",
                "judge_success_count", "judge_technical_failure_count", "judge_not_run_count"):
        if agreement.get(key) != manifest.get(key) or summary.get(key) != manifest.get(key):
            raise ValueError("STEP74_ARTIFACT_TECHNICAL_COUNT_MISMATCH")
    for key in ("human_approved_count", "judge_calibration_success_count"):
        if agreement.get(key) != manifest.get(key) or summary.get(key) != manifest.get(key):
            raise ValueError("STEP74_ARTIFACT_CALIBRATION_COUNT_MISMATCH")
    for key in ("human_calibration_case_count", "human_calibration_packet_created",
                "human_calibration_packet_status", "human_calibration_draft_count",
                "human_calibration_status"):
        if agreement.get(key) != manifest.get(key) or summary.get(key) != manifest.get(key):
            raise ValueError("STEP74_ARTIFACT_CALIBRATION_PACKET_MISMATCH")
    selected = [row for row in rows if row.get("calibration", {}).get("in_human_subset") is True]
    packet_created = manifest.get("human_calibration_packet_created") is True
    packet_count = manifest.get("human_calibration_case_count")
    if len(selected) != 30 or type(packet_count) is not int or not 0 <= packet_count <= 30:
        raise ValueError("STEP74_CALIBRATION_PACKET_COUNT_MISMATCH")
    if packet_created != (packet_count > 0):
        raise ValueError("STEP74_CALIBRATION_PACKET_COUNT_MISMATCH")
    actual_drafts = sum(row.get("calibration", {}).get("human_review_status") == "DRAFT" for row in selected)
    actual_approved = sum(row.get("calibration", {}).get("human_review_status") == "HUMAN_APPROVED"
                          for row in selected)
    stage_b_complete = run_status == "STAGE_B_COMPLETE"
    if stage_b_complete:
        if (packet_count != 30 or manifest.get("human_calibration_draft_count") != 0
                or manifest.get("human_approved_count") != 30
                or actual_drafts != 0 or actual_approved != 30):
            raise ValueError("STEP74_STAGE_B_ANNOTATION_STATE_MISMATCH")
    elif (manifest.get("human_calibration_draft_count") != packet_count
          or manifest.get("human_calibration_draft_count") != actual_drafts
          or manifest.get("human_approved_count") != actual_approved):
        raise ValueError("STEP74_CASE_CALIBRATION_STATUS_MISMATCH")
    expected_packet_status = (
        "HUMAN_APPROVED" if stage_b_complete else
        "DRAFT_CREATED" if packet_created and packet_count == 30 else
        "INCOMPLETE" if packet_created else "NOT_CREATED"
    )
    expected_human_review_status = "HUMAN_APPROVED" if stage_b_complete else ("DRAFT" if packet_created else None)
    if any(row.get("calibration", {}).get("packet_status") != expected_packet_status
           or row.get("calibration", {}).get("annotation_version") != HUMAN_ANNOTATION_VERSION
           or row.get("calibration", {}).get("human_review_status") != expected_human_review_status
           for row in selected):
        raise ValueError("STEP74_CASE_CALIBRATION_PACKET_MISMATCH")
    if run_status == "REVIEW_REQUIRED_HUMAN_CALIBRATION":
        if (execution_mode != "OFFICIAL_REAL_RUNTIME" or run_status != "REVIEW_REQUIRED_HUMAN_CALIBRATION"
                or not packet_created or packet_count != 30 or success_count != len(rows)
                or manifest.get("human_calibration_draft_count") != 30
                or manifest.get("human_approved_count") != 0):
            raise ValueError("STEP74_INVALID_REVIEW_READY_STATUS")
    elif packet_created and packet_count == 30 and not stage_b_complete:
        raise ValueError("STEP74_COMPLETE_PACKET_WITHOUT_REVIEW_READY_STATUS")
    if not packet_created and packet_count != 0:
        raise ValueError("STEP74_PACKET_COUNT_WITHOUT_PACKET")
    if stage_b_complete and not packet_created:
        raise ValueError("STEP74_STAGE_B_ANNOTATION_STATE_MISMATCH")
    if execution_mode == "OFFLINE_TEST" and (
        run_status != "OFFLINE_TEST_ONLY" or packet_created or manifest.get("stage_a_started") is not False
    ):
        raise ValueError("STEP74_OFFLINE_ARTIFACT_CLAIMS_OFFICIAL_STAGE_A")
    if agreement.get("runtime_api_calls") != manifest.get("runtime_api_calls") \
            or summary.get("runtime_api_calls") != manifest.get("runtime_api_calls"):
        raise ValueError("STEP74_ARTIFACT_API_CALL_COUNT_MISMATCH")
    if (agreement.get("run_id") != manifest.get("run_id") or agreement.get("case_count_expected") != 30
            or agreement.get("run_status") != run_status
            or agreement.get("stage_a_started") != manifest.get("stage_a_started")):
        raise ValueError("STEP74_AGREEMENT_IDENTITY_MISMATCH")
    if agreement.get("human_calibration_case_count") != manifest.get("human_calibration_case_count"):
        raise ValueError("STEP74_CALIBRATION_COUNT_MISMATCH")
    if agreement.get("status") == "NOT_RUN_HUMAN_CALIBRATION_REQUIRED" and agreement.get("case_count_compared") != 0:
        raise ValueError("STEP74_STAGE_A_AGREEMENT_MUST_NOT_CLAIM_COMPARISONS")
    if manifest.get("run_status") != "STAGE_B_COMPLETE" and (
        agreement.get("status") == "COMPLETE_BASELINE_ONLY" or summary.get("run_status") == "STAGE_B_COMPLETE"
    ):
        raise ValueError("STEP74_STAGE_A_CANNOT_CLAIM_STAGE_B_FINALIZATION")


def write_stage_a(run_id: str, run_dir: Path, manifest: dict, rows: list[dict], *,
                  annotation_root: Path = ANNOTATION_ROOT) -> Path:
    if len(rows) != 45 or len({row["case_id"] for row in rows}) != 45:
        raise ValueError("Stage A artifacts require exactly 45 unique eligible cases")
    official = manifest.get("execution_mode") == "OFFICIAL_REAL_RUNTIME"
    packet: list[dict] = []
    packet_error: str | None = None
    if official:
        prior_annotations = annotation_root / "calibration.jsonl"
        if prior_annotations.is_file():
            prior_rows = [json.loads(line) for line in prior_annotations.read_text(encoding="utf-8").splitlines() if line]
            if any(row.get("review_status") == "HUMAN_APPROVED" for row in prior_rows):
                raise ValueError("HUMAN_CALIBRATION_STALE")
        if all(row.get("generator", {}).get("status") == "SUCCESS" for row in rows):
            try:
                packet = make_draft_packet(rows, run_id=run_id)
            except ValueError:
                packet_error = "CALIBRATION_PACKET_BINDING_FAILED"
            if packet:
                source_manifest = {
                    "annotation_name": "Lesson Chat Generation Human Calibration",
                    "annotation_version": HUMAN_ANNOTATION_VERSION,
                    "dataset_version": DATASET_VERSION, "rubric_version": RUBRIC_VERSION,
                    "status": "DRAFT_HUMAN_CALIBRATION", "generation_run_id": run_id,
                    "case_count": 30, "case_ids": list(CALIBRATION_IDS),
                    "review_policy": "Only independent human review may set HUMAN_APPROVED; Codex and LLM outputs remain DRAFT.",
                    "created_at": datetime.now(UTC).isoformat(), "updated_at": datetime.now(UTC).isoformat(),
                    "approval_policy": "MANUAL_HUMAN_REVIEW_REQUIRED; CODEX_AND_LLM_MUST_NOT_SELF_APPROVE",
                }
                write_json(annotation_root / "manifest.json", source_manifest)
                write_jsonl(annotation_root / "calibration.jsonl", packet)
        else:
            packet_error = "GENERATOR_RESULTS_INCOMPLETE"
    state = derive_stage_a_state(official=official, rows=rows, packet_count=len(packet),
                                 packet_creation_error=packet_error)
    packet_created = state["human_calibration_packet_created"]
    run_status = state["run_status"]
    packet_status = state["human_calibration_packet_status"]
    packet_status_label = state["human_calibration_status"]
    for row in rows:
        row["run_status"] = run_status
        row["execution_mode"] = manifest.get("execution_mode")
        row.setdefault("calibration", {})
        row["calibration"].update({
            "in_human_subset": row.get("case_id") in CALIBRATION_IDS,
            "human_review_status": "DRAFT" if row.get("case_id") in CALIBRATION_IDS and packet_created else None,
            "packet_status": packet_status if row.get("case_id") in CALIBRATION_IDS else None,
            "annotation_version": HUMAN_ANNOTATION_VERSION,
        })
    manifest.update(state | {
        "eligible_case_count": len(rows),
        "case_counts_by_split": {split: sum(row.get("split") == split for row in rows)
                                  for split in ("DEVELOPMENT", "HOLDOUT")},
        "case_counts_by_bucket": _bucket_counts(rows),
    })
    if not official:
        manifest["runtime_api_calls"] = 0
        manifest["runtime_smoke"] = {"status": "NOT_RUN_OFFLINE_TEST", "source": "OFFLINE_TEST", "api_calls": 0}
    generation = run_dir / "generation"
    generation.mkdir(parents=True, exist_ok=False)
    write_jsonl(generation / "cases.jsonl", rows)
    manifest["cases_file_sha256"] = hashlib.sha256((generation / "cases.jsonl").read_bytes()).hexdigest()
    write_json(generation / "manifest.json", manifest)
    write_json(generation / "summary.json", build_stage_a_summary(run_id, rows, identity=manifest))
    agreement = {
        "agreement_artifact_version": "1.0.0", "run_id": run_id,
        "run_status": run_status,
        "stage_a_started": manifest["stage_a_started"],
        "dataset_name": DATASET_NAME, "dataset_version": DATASET_VERSION,
        "dataset_schema_version": DATASET_SCHEMA_VERSION, "evaluation_step": "7.4",
        "eligible_case_policy_version": ELIGIBLE_CASE_POLICY_VERSION,
        "fixed_evidence_policy_version": FIXED_EVIDENCE_POLICY_VERSION,
        "fixed_memory_policy_version": FIXED_MEMORY_POLICY_VERSION,
        "human_annotation_version": HUMAN_ANNOTATION_VERSION,
        "rubric_version": RUBRIC_VERSION, "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "case_count_expected": 30, "case_count_compared": 0,
        "human_calibration_case_count": manifest["human_calibration_case_count"],
        "human_calibration_packet_created": packet_created,
        "human_calibration_packet_status": packet_status,
        "human_calibration_draft_count": manifest["human_calibration_draft_count"],
        "human_calibration_status": packet_status_label,
        "human_approved_count": 0,
        "runtime_api_calls": manifest["runtime_api_calls"],
        "generator_success_count": manifest["generator_success_count"],
        "generator_technical_failure_count": manifest["generator_technical_failure_count"],
        "judge_success_count": 0, "judge_technical_failure_count": 0,
        "judge_not_run_count": len(rows), "judge_calibration_success_count": 0,
        "eligible_case_count": 45,
        "case_counts_by_split": manifest["case_counts_by_split"],
        "case_counts_by_bucket": manifest["case_counts_by_bucket"],
        "generator_model": manifest["generator_model"], "judge_model": manifest["judge_model"],
        "generator_identity": manifest["generator_identity"], "judge_identity": manifest["judge_identity"],
        "per_dimension": None, "macro_exact_agreement_rate": None,
        "overall_mean_absolute_score_difference": None,
        "critical_failure_set_exact_agreement_rate": None,
        "human_critical_failure_case_count": None, "judge_critical_failure_case_count": None,
        "agreement_gate": None, "status": "NOT_RUN_HUMAN_CALIBRATION_REQUIRED",
        "execution_mode": manifest["execution_mode"],
    }
    write_json(generation / "calibration-agreement.json", agreement)
    if packet_created:
        write_jsonl(generation / "calibration.jsonl", packet)
    summary = json.loads((generation / "summary.json").read_text(encoding="utf-8"))
    validate_artifact_metadata(manifest, rows, summary, agreement)
    return generation


def package_review_zip(output: Path, files: list[Path], *, root: Path = ROOT) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, path.relative_to(root).as_posix())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return digest


def package_stage_a_review_zip(run_id: str, generation_dir: Path) -> tuple[Path, str]:
    paths = [generation_dir / name for name in
             ("manifest.json", "cases.jsonl", "summary.json", "calibration-agreement.json", "calibration.jsonl")]
    paths = [path for path in paths if path.is_file()]
    paths.extend(path for path in (ANNOTATION_ROOT / "manifest.json", ANNOTATION_ROOT / "calibration.jsonl")
                 if path.is_file())
    output = ROOT / "tmp" / f"step-7.4-{run_id}-stage-a-review.zip"
    digest = package_review_zip(output, paths)
    return output, digest
