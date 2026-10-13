from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .artifacts import canonical_json, digest

_SAFE_METADATA_KEYS = frozenset({
    "status", "finish_reason", "response_status", "service_tier", "system_fingerprint",
    "attempt_count", "input_tokens", "output_tokens", "total_tokens", "latency_ms",
})


def sanitize_provider_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Keep a small provider diagnostic allowlist; discard unknown or sensitive fields."""
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items()
            if key in _SAFE_METADATA_KEYS and isinstance(value, (str, int, float, bool, type(None)))}


def origin_case_identity_field(track: str) -> str:
    """Map each frozen artifact track to its actual case identity field."""
    fields = {"grading": "case_id", "assessment_generation": "generation_case_id"}
    try:
        return fields[track]
    except KeyError:
        raise ValueError("STEP77_REPLAY_ORIGIN_PROVENANCE_INVALID") from None


class ProviderReplayRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    replay_schema_version: str = "1.1.0"
    track: str
    request_sha256: str
    response_sha256: str
    parsed_result_sha256: str
    provider: str
    model: str
    generation_config: dict[str, Any]
    prompt_identity: str
    prompt_version: str
    prompt_sha256: str
    structured_schema_identity: str
    structured_schema_version: str
    normalized_input_sha256: str
    sanitized_provider_metadata: dict[str, Any] = Field(default_factory=dict)
    parsed_result: dict[str, Any]
    finish_status_metadata: dict[str, Any] = Field(default_factory=dict)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    provider_request_id: str | None = None
    origin_execution_mode: str
    origin_run_id: str | None = None
    origin_track: str
    origin_provider_mode: str
    origin_case_id: str
    origin_artifact_path: str
    origin_artifact_sha256: str
    created_at: str | None = None

    @classmethod
    def from_real_output(cls, *, track: str, request_sha256: str, parsed_result: dict,
                         response: dict, provider: str, model: str, generation_config: dict,
                         prompt_identity: str, schema_identity: str, normalized_input: dict,
                         origin_run_id: str, prompt_version: str | None = None,
                         prompt_sha256: str | None = None, schema_version: str = "1.0.0",
                         metadata: dict | None = None, finish_status_metadata: dict | None = None,
                         input_tokens: int | None = None, output_tokens: int | None = None,
                         total_tokens: int | None = None, latency_ms: int | None = None,
                         origin_track: str, origin_provider_mode: str, origin_case_id: str,
                         origin_artifact_path: str, origin_artifact_sha256: str,
                         provider_request_id: str | None = None, created_at: str | None = None):
        sanitized = sanitize_provider_metadata(metadata)
        finish_status = sanitize_provider_metadata(finish_status_metadata)
        return cls(track=track, request_sha256=request_sha256,
            response_sha256=digest(canonical_json(response)),
            parsed_result_sha256=digest(canonical_json(parsed_result)), provider=provider, model=model,
            generation_config=generation_config, prompt_identity=prompt_identity,
            prompt_version=prompt_version or prompt_identity, prompt_sha256=prompt_sha256 or "unavailable",
            structured_schema_identity=schema_identity, structured_schema_version=schema_version,
            normalized_input_sha256=digest(canonical_json(normalized_input)),
            sanitized_provider_metadata=sanitized, parsed_result=parsed_result,
            finish_status_metadata=finish_status, input_tokens=input_tokens, output_tokens=output_tokens,
            total_tokens=total_tokens, latency_ms=latency_ms,
            provider_request_id=provider_request_id, origin_execution_mode="REAL",
            origin_run_id=origin_run_id, origin_track=origin_track,
            origin_provider_mode=origin_provider_mode, origin_case_id=origin_case_id,
            origin_artifact_path=origin_artifact_path, origin_artifact_sha256=origin_artifact_sha256,
            created_at=created_at or datetime.now(UTC).isoformat())


def verify_real_origin_artifact(record: ProviderReplayRecord) -> None:
    """Verify REAL provenance against an immutable official-run manifest and cases artifact."""
    try:
        manifest_path = Path(record.origin_artifact_path)
        raw_manifest = manifest_path.read_bytes()
        if digest(raw_manifest) != record.origin_artifact_sha256:
            raise ValueError
        manifest = json.loads(raw_manifest.decode("utf-8", errors="strict"))
        cases_path = manifest_path.with_name("cases.jsonl")
        raw_cases = cases_path.read_bytes()
        if digest(raw_cases) != manifest.get("cases_artifact_sha256"):
            raise ValueError
        rows = [json.loads(line) for line in raw_cases.decode("utf-8", errors="strict").splitlines() if line.strip()]
        case_identity_field = origin_case_identity_field(record.origin_track)
        matching = [row for row in rows if row.get(case_identity_field) == record.origin_case_id]
        if len(matching) != 1:
            raise ValueError
        row = matching[0]
        expected_config = record.generation_config
        checks = (
            manifest.get("execution_mode") == "OFFICIAL_RUNTIME",
            manifest.get("provider_mode") == "REAL" == record.origin_provider_mode,
            manifest.get("run_id") == record.origin_run_id,
            manifest.get("track") == record.origin_track == record.track,
            manifest.get("provider") == record.provider,
            manifest.get("model") == record.model,
            manifest.get("generation_config") == expected_config,
            manifest.get("prompt_version") == record.prompt_version,
            manifest.get("prompt_identity", manifest.get("prompt_version")) == record.prompt_identity,
            manifest.get("prompt_sha256") == record.prompt_sha256,
            manifest.get("structured_schema_identity") == record.structured_schema_identity,
            manifest.get("structured_schema_version") == record.structured_schema_version,
            row.get("provider_mode") == "REAL",
            row.get(case_identity_field) == record.origin_case_id,
            row.get("request_sha256") == record.request_sha256,
            row.get("provider_response_sha256") == record.response_sha256,
            row.get("parsed_result_sha256") == record.parsed_result_sha256,
            row.get("provider") == record.provider,
            row.get("model") == record.model,
        )
        if not all(checks):
            raise ValueError
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        raise ValueError("STEP77_REPLAY_ORIGIN_PROVENANCE_INVALID") from None


def write_replay(path: Path, record: ProviderReplayRecord) -> None:
    if record.origin_execution_mode != "REAL" or not record.origin_run_id:
        raise ValueError("STEP77_REPLAY_REQUIRES_REAL_ORIGIN")
    verify_real_origin_artifact(record)
    from .artifacts import _check_safe
    _check_safe(record.model_dump(mode="json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(record.model_dump(mode="json")) + b"\n")


def load_replay(path: Path, *, expected_identity: dict) -> ProviderReplayRecord:
    record = ProviderReplayRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
    expected_sha = digest(canonical_json(expected_identity))
    if record.request_sha256 != expected_sha:
        raise ValueError("STEP77_REPLAY_STALE_REQUEST_IDENTITY")
    identity_fields = {
        "track": "track", "provider": "provider", "model": "model",
        "prompt_identity": "prompt_identity", "prompt_sha256": "prompt_sha256",
        "structured_schema_identity": "structured_schema_identity",
        "structured_schema_version": "structured_schema_version",
    }
    for identity_key, record_key in identity_fields.items():
        if identity_key in expected_identity and getattr(record, record_key) != expected_identity[identity_key]:
            raise ValueError("STEP77_REPLAY_STALE_REQUEST_IDENTITY")
    if "normalized_production_input" in expected_identity and record.normalized_input_sha256 != digest(
        canonical_json(expected_identity["normalized_production_input"])
    ):
        raise ValueError("STEP77_REPLAY_STALE_REQUEST_IDENTITY")
    config_keys = ("temperature", "max_output_tokens", "reasoning_effort", "model_input_limit",
                   "request_timeout_seconds", "max_transient_retries")
    expected_config = {key: expected_identity[key] for key in config_keys if key in expected_identity}
    if expected_config and record.generation_config != expected_config:
        raise ValueError("STEP77_REPLAY_STALE_REQUEST_IDENTITY")
    if record.origin_execution_mode != "REAL" or not record.origin_run_id:
        raise ValueError("STEP77_REPLAY_ORIGIN_NOT_REAL")
    if digest(canonical_json(record.parsed_result)) != record.parsed_result_sha256:
        raise ValueError("STEP77_REPLAY_RESPONSE_HASH_MISMATCH")
    if not record.provider or not record.model or not record.prompt_sha256:
        raise ValueError("STEP77_REPLAY_IDENTITY_INCOMPLETE")
    verify_real_origin_artifact(record)
    return record


class ReplayGradingProvider:
    """Replay a real provider result through production grading parsing/normalization."""
    mode = "REPLAY"

    def __init__(self, path: Path, *, provider: str = "openai"):
        self.path = path
        self.provider_name = provider
        self.last_result = None
        self.record: ProviderReplayRecord | None = None
        self.last_error_code: str | None = None

    async def grade(self, request):
        from app.ai.grading.schemas import StructuredGradingOutput, StructuredGradingProviderResult
        from app.evaluation.step77.grading import grading_provider_request_identity

        identity, _ = grading_provider_request_identity(request, provider=self.provider_name)
        try:
            record = load_replay(self.path, expected_identity=identity)
            if record.track != "grading" or record.provider != self.provider_name or record.model != request.model:
                raise ValueError("STEP77_REPLAY_STALE_REQUEST_IDENTITY")
        except (ValueError, OSError):
            self.last_error_code = "STEP77_REPLAY_STALE_REQUEST_IDENTITY"
            raise
        output = StructuredGradingOutput.model_validate(record.parsed_result)
        self.last_result = StructuredGradingProviderResult(output=output, provider=record.provider,
            model=record.model, input_tokens=record.input_tokens, output_tokens=record.output_tokens,
            total_tokens=record.total_tokens, provider_preflight_input_tokens=0,
            latency_ms=record.latency_ms or 0,
            attempt_count=int(record.sanitized_provider_metadata.get("attempt_count", 1)),
            provider_request_id=record.provider_request_id)
        self.record = record
        return self.last_result


class ReplayGenerationProvider:
    """Replay structured generation through the production generation service and validators."""
    mode = "REPLAY"

    def __init__(self, path: Path, *, provider: str = "openai"):
        self.path = path
        self.provider_name = provider
        self.last_result = None
        self.record: ProviderReplayRecord | None = None
        self.last_error_code: str | None = None

    async def generate(self, request):
        from app.ai.generation.schemas import StructuredAssessmentGenerationOutput, StructuredAssessmentGenerationProviderResult
        from app.evaluation.step77.generation import generation_provider_request_identity

        identity, _ = generation_provider_request_identity(request, provider=self.provider_name)
        try:
            record = load_replay(self.path, expected_identity=identity)
            if record.track != "assessment_generation" or record.provider != self.provider_name or record.model != request.model:
                raise ValueError("STEP77_REPLAY_STALE_REQUEST_IDENTITY")
        except (ValueError, OSError):
            self.last_error_code = "STEP77_REPLAY_STALE_REQUEST_IDENTITY"
            raise
        output = StructuredAssessmentGenerationOutput.model_validate(record.parsed_result)
        self.last_result = StructuredAssessmentGenerationProviderResult(output=output, provider=record.provider,
            model=record.model, input_tokens=record.input_tokens, output_tokens=record.output_tokens,
            total_tokens=record.total_tokens, provider_preflight_input_tokens=0,
            latency_ms=record.latency_ms or 0,
            attempt_count=int(record.sanitized_provider_metadata.get("attempt_count", 1)),
            provider_request_id=record.provider_request_id)
        self.record = record
        return self.last_result
