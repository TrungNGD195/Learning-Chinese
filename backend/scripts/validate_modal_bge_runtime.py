from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.ai.modal_bge.client import ModalBgeClient
from app.ai.modal_bge.schemas import (
    CONTRACT_VERSION, EMBEDDING_MODEL, EMBEDDING_REVISION, RERANKER_MODEL, RERANKER_REVISION,
)
from app.core.config import get_settings

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "docs/ai/evidence/modal-bge-validation"
STAGE_B_ENV = "STEP83_STAGE_B_AUTHORIZED"
PENDING_STATUS = "BILLING_AFTER_PENDING"
COMPLETE_STATUS = "COMPLETE_REAL_MEASUREMENTS"
PARITY_FAILED_STATUS = "PARITY_GATE_FAILED"
RERANK_PARITY_CANDIDATES = 20
RERANK_BATCH_SIZE = 8
EXPECTED_RUNTIME_VERSIONS = {
    "sentence-transformers": "6.1.0",
    "transformers": "5.18.0",
    "torch": "2.14.1",
}
_COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _number(value: Any, *, positive: bool, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        qualifier = "finite and positive" if positive else "finite and non-negative"
        raise ValueError(f"{label} must be {qualifier}")
    return result


def _nonempty(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\n" in value or "\r" in value:
        raise ValueError(f"{label} must be a non-empty single-line string")
    return value.strip()


def _timestamp(value: Any, *, label: str) -> datetime:
    raw = _nonempty(value, label=label)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from None
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def nearest_rank(values: list[float], percentile: float) -> float:
    if not values or not 0 < percentile <= 1:
        raise ValueError("A non-empty sample set and percentile in (0, 1] are required")
    ordered = sorted(_number(value, positive=True, label="sample") for value in values)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def _validate_latency_summary(row: Any, *, expected_warmups: int, label: str) -> None:
    if not isinstance(row, dict):
        raise ValueError(f"{label} evidence must be an object")
    if row.get("warmups") != expected_warmups:
        raise ValueError(f"{label} warmup count is invalid")
    samples = row.get("raw_samples_ms")
    if not isinstance(samples, list) or len(samples) != 30:
        raise ValueError(f"{label} must contain exactly 30 measured samples")
    if row.get("sample_count") != 30:
        raise ValueError(f"{label} sample_count must be 30")
    p50 = nearest_rank(samples, 0.5)
    p95 = nearest_rank(samples, 0.95)
    reported_p50 = _number(row.get("p50_ms"), positive=True, label=f"{label} p50")
    reported_p95 = _number(row.get("p95_ms"), positive=True, label=f"{label} p95")
    if not math.isclose(p50, reported_p50, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"{label} p50 does not match its raw samples")
    if not math.isclose(p95, reported_p95, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"{label} p95 does not match its raw samples")


def _runtime_provenance_verified(runtime: Any) -> bool:
    """Verify the runtime_info payload identifies the frozen deployed GPU/model stack."""
    if not isinstance(runtime, dict):
        return False
    if runtime.get("contract_version") != CONTRACT_VERSION:
        return False
    if (runtime.get("embedding_model_name"), runtime.get("embedding_model_revision"),
        runtime.get("reranker_model_name"), runtime.get("reranker_model_revision")) != (
        EMBEDDING_MODEL, EMBEDDING_REVISION, RERANKER_MODEL, RERANKER_REVISION
    ):
        return False
    if runtime.get("device") != "cuda":
        return False
    if not isinstance(runtime.get("gpu_name"), str) or not runtime["gpu_name"].strip():
        return False
    if not isinstance(runtime.get("cuda_version"), str) or not runtime["cuda_version"].strip():
        return False
    if not isinstance(runtime.get("torch_version"), str) or not runtime["torch_version"].strip():
        return False
    try:
        _number(runtime.get("gpu_total_vram_bytes"), positive=True, label="gpu_total_vram_bytes")
    except ValueError:
        return False
    versions = runtime.get("runtime_versions")
    return isinstance(versions, dict) and all(
        versions.get(package) == expected for package, expected in EXPECTED_RUNTIME_VERSIONS.items()
    )


def _validate_measurements(data: dict[str, Any]) -> None:
    required_strings = (
        "timestamp_utc", "modal_sdk_version", "modal_app_name", "modal_class_name",
        "gpu_name", "torch_version", "cuda_version",
    )
    for key in required_strings:
        _nonempty(data.get(key), label=key)
    _timestamp(data.get("timestamp_utc"), label="timestamp_utc")
    commit = _nonempty(data.get("git_commit"), label="git_commit")
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise ValueError("git_commit must be a hexadecimal commit identifier")
    if data.get("real_modal_runtime") is not True:
        raise ValueError("Only the real Modal execution path can provide real evidence")
    if data.get("runtime_provenance_verified") is not True:
        raise ValueError("Modal runtime provenance has not been verified")
    if data.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Unexpected Modal contract version")
    _number(data.get("gpu_total_vram_bytes"), positive=True, label="gpu_total_vram_bytes")

    versions = data.get("runtime_versions")
    if not isinstance(versions, dict):
        raise ValueError("runtime_versions must be an object")
    for package in ("sentence-transformers", "transformers", "torch"):
        _nonempty(versions.get(package), label=f"runtime_versions.{package}")

    for key, model, revision in (
        ("embedding", EMBEDDING_MODEL, EMBEDDING_REVISION),
        ("reranker", RERANKER_MODEL, RERANKER_REVISION),
    ):
        identity = data.get(key)
        if not isinstance(identity, dict):
            raise ValueError(f"{key} identity is required")
        if identity.get("model_name") != model or identity.get("model_revision") != revision:
            raise ValueError(f"{key} model identity mismatch")

    fixture = data.get("fixture_identity")
    if not isinstance(fixture, dict):
        raise ValueError("fixture_identity is required")
    _nonempty(fixture.get("name"), label="fixture_identity.name")
    if not isinstance(fixture.get("query"), str) or not fixture["query"].strip():
        raise ValueError("fixture query is required")
    if not isinstance(fixture.get("passages"), list) or len(fixture["passages"]) != RERANK_PARITY_CANDIDATES:
        raise ValueError("fixture must contain exactly 20 reranker candidates")

    _validate_latency_summary(data.get("warm_embedding_ms"), expected_warmups=5, label="warm embedding")
    _validate_latency_summary(data.get("warm_reranking_ms"), expected_warmups=3, label="warm reranking")
    _validate_latency_summary(data.get("combined_ms"), expected_warmups=3, label="combined workload")
    for label in ("warm_reranking_ms", "combined_ms"):
        summary = data[label]
        if (summary.get("candidate_count"), summary.get("batch_size"), summary.get("batch_count")) != (
            RERANK_PARITY_CANDIDATES, RERANK_BATCH_SIZE, 3
        ):
            raise ValueError(f"{label} must record all 20 candidates in 8/8/4 batches")

    cold = data.get("cold_initialization")
    if not isinstance(cold, dict):
        raise ValueError("cold initialization measurements are required")
    _number(cold.get("runtime_info_ms"), positive=True, label="cold initialization runtime_info_ms")

    vram = data.get("vram")
    if not isinstance(vram, dict):
        raise ValueError("VRAM evidence is required")
    allocated = _number(vram.get("allocated_bytes"), positive=False, label="vram.allocated_bytes")
    reserved = _number(vram.get("reserved_bytes"), positive=False, label="vram.reserved_bytes")
    max_allocated = _number(vram.get("max_allocated_bytes"), positive=False, label="vram.max_allocated_bytes")
    max_reserved = _number(vram.get("max_reserved_bytes"), positive=False, label="vram.max_reserved_bytes")
    if reserved < allocated or max_allocated < allocated or max_reserved < reserved or max_reserved < max_allocated:
        raise ValueError("VRAM counters are internally inconsistent")

    parity = data.get("parity")
    if not isinstance(parity, dict):
        raise ValueError("parity evidence is required")
    embedding_parity = parity.get("embedding")
    reranker_parity = parity.get("reranker")
    if not isinstance(embedding_parity, dict) or not isinstance(reranker_parity, dict):
        raise ValueError("embedding and reranker parity evidence are required")
    if (reranker_parity.get("candidate_count"), reranker_parity.get("batch_size"),
        reranker_parity.get("batch_count")) != (RERANK_PARITY_CANDIDATES, RERANK_BATCH_SIZE, 3):
        raise ValueError("Reranker parity must document all 20 candidates in 8/8/4 batches")
    if embedding_parity.get("dimension") != 1024 or embedding_parity.get("finite") is not True:
        raise ValueError("embedding parity result is incomplete")
    if embedding_parity.get("unit_norm") is not True:
        raise ValueError("embedding normalization parity is required")
    _number(embedding_parity.get("max_absolute_delta"), positive=False, label="embedding parity delta")
    _number(reranker_parity.get("max_absolute_delta"), positive=False, label="reranker parity delta")
    for name in ("local_raw_scores", "modal_raw_scores", "local_order", "modal_order",
                 "local_threshold_decisions", "modal_threshold_decisions"):
        value = reranker_parity.get(name)
        if not isinstance(value, list) or not value:
            raise ValueError(f"parity.{name} is required")
    local_scores = reranker_parity["local_raw_scores"]
    modal_scores = reranker_parity["modal_raw_scores"]
    local_order = reranker_parity["local_order"]
    modal_order = reranker_parity["modal_order"]
    local_decisions = reranker_parity["local_threshold_decisions"]
    modal_decisions = reranker_parity["modal_threshold_decisions"]
    if len(local_scores) != RERANK_PARITY_CANDIDATES or len(modal_scores) != RERANK_PARITY_CANDIDATES:
        raise ValueError("Reranker parity must compare all 20 candidates")
    if not all(math.isfinite(_number(score, positive=False, label="parity score"))
               for score in [*local_scores, *modal_scores]):
        raise ValueError("Reranker parity scores must be finite")
    if len(local_order) != len(local_scores) or len(modal_order) != len(modal_scores):
        raise ValueError("Reranker parity order is incomplete")
    if not all(isinstance(index, int) and not isinstance(index, bool)
               for index in [*local_order, *modal_order]):
        raise ValueError("Reranker parity order must contain integer indexes")
    expected_indexes = list(range(len(local_scores)))
    if sorted(local_order) != expected_indexes or sorted(modal_order) != expected_indexes:
        raise ValueError("Reranker parity order indexes are invalid")
    if not isinstance(reranker_parity.get("order_equal"), bool):
        raise ValueError("Reranker order comparison is required")
    if reranker_parity["order_equal"] != (local_order == modal_order):
        raise ValueError("Reranker order comparison does not match its evidence")
    if len(local_decisions) != len(local_scores) or len(modal_decisions) != len(modal_scores):
        raise ValueError("Threshold-decision comparison is incomplete")
    if not all(isinstance(decision, bool) for decision in [*local_decisions, *modal_decisions]):
        raise ValueError("Threshold decisions must be boolean values")
    _number(reranker_parity.get("threshold"), positive=False, label="parity threshold")
    if not isinstance(reranker_parity.get("threshold_decisions_equal"), bool):
        raise ValueError("Threshold-decision comparison is required")
    if reranker_parity["threshold_decisions_equal"] != (local_decisions == modal_decisions):
        raise ValueError("Threshold-decision comparison does not match its evidence")
    if reranker_parity["threshold_decisions_equal"] is not True:
        raise ValueError("PARITY_GATE_FAILED")

    pairs = data.get("concurrency_2_ms")
    if not isinstance(pairs, list) or len(pairs) != 10:
        raise ValueError("Concurrency evidence must contain exactly 10 measured pairs")
    for pair in pairs:
        if not isinstance(pair, dict):
            raise ValueError("Concurrency pair evidence must be an object")
        requests = pair.get("requests")
        if not isinstance(requests, list) or len(requests) != 2:
            raise ValueError("Each concurrency pair must contain exactly two requests")
        latencies = []
        for request in requests:
            if not isinstance(request, dict):
                raise ValueError("Concurrency request evidence must be an object")
            latency = _number(request.get("latency_ms"), positive=True, label="request latency_ms")
            execution = _number(request.get("execution_ms"), positive=True, label="request execution_ms")
            if latency < execution:
                raise ValueError("Common-arrival latency cannot be shorter than execution duration")
            latencies.append(latency)
        makespan = _number(pair.get("pair_makespan_ms"), positive=True, label="pair_makespan_ms")
        if not math.isclose(makespan, max(latencies), rel_tol=1e-6, abs_tol=1e-6):
            raise ValueError("Pair makespan must equal the latest common-arrival completion")


def validate_pending_measurement(data: dict[str, Any]) -> None:
    if data.get("status") != PENDING_STATUS:
        raise ValueError("Measurement artifact must be BILLING_AFTER_PENDING")
    _validate_measurements(data)
    billing = data.get("billing")
    if not isinstance(billing, dict):
        raise ValueError("Billing-before evidence is required")
    _nonempty(billing.get("before_reference"), label="billing.before_reference")
    _timestamp(billing.get("before_captured_at_utc"), label="billing.before_captured_at_utc")
    if billing.get("after_reference") not in (None, ""):
        raise ValueError("Pending artifact cannot contain finalized billing-after evidence")
    if billing.get("after_captured_at_utc") not in (None, ""):
        raise ValueError("Pending artifact cannot contain billing-after capture time")


def validate_real_result(data: dict[str, Any]) -> None:
    """Validate only canonical, complete Stage-B evidence after billing finalization."""
    if data.get("status") != COMPLETE_STATUS:
        raise ValueError("Only COMPLETE_REAL_MEASUREMENTS is canonical real evidence")
    _validate_measurements(data)
    billing = data.get("billing")
    if not isinstance(billing, dict):
        raise ValueError("Billing evidence is required")
    _nonempty(billing.get("before_reference"), label="billing.before_reference")
    _nonempty(billing.get("after_reference"), label="billing.after_reference")
    before_at = _timestamp(billing.get("before_captured_at_utc"), label="billing.before_captured_at_utc")
    after_at = _timestamp(billing.get("after_captured_at_utc"), label="billing.after_captured_at_utc")
    if after_at < before_at:
        raise ValueError("Billing-after capture must follow billing-before capture")


def finalize_real_result(data: dict[str, Any], *, billing_after_reference: str) -> dict[str, Any]:
    validate_pending_measurement(data)
    after = _nonempty(billing_after_reference, label="billing_after_reference")
    finalized = json.loads(json.dumps(data))
    finalized["billing"]["after_reference"] = after
    finalized["billing"]["after_captured_at_utc"] = datetime.now(UTC).isoformat()
    finalized["status"] = COMPLETE_STATUS
    validate_real_result(finalized)
    return finalized


async def measure_concurrency_pair(
    call: Callable[[], Awaitable[None]], *, clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Measure two requests from one common arrival, retaining client execution duration."""
    common_arrival = clock()
    release = asyncio.Event()

    async def request() -> dict[str, float]:
        await release.wait()
        actual_start = clock()
        await call()
        completion = clock()
        return {
            "latency_ms": (completion - common_arrival) * 1000,
            "execution_ms": (completion - actual_start) * 1000,
        }

    tasks = [asyncio.create_task(request()), asyncio.create_task(request())]
    await asyncio.sleep(0)
    release.set()
    requests = await asyncio.gather(*tasks)
    return {
        "requests": requests,
        "pair_makespan_ms": max(row["latency_ms"] for row in requests),
    }


def _ensure_stage_b_authorized() -> None:
    if os.environ.get(STAGE_B_ENV) != "true":
        raise RuntimeError("Stage B authorization is required")


async def run_real_validation(*, billing_before_reference: str) -> dict[str, Any]:
    """Run real parity/latency evidence after explicit Stage-B authorization and before billing capture."""
    _ensure_stage_b_authorized()
    before = _nonempty(billing_before_reference, label="billing_before_reference")
    billing_before_captured_at = datetime.now(UTC).isoformat()
    settings = get_settings()
    if settings.rag_min_rerank_score is None:
        raise RuntimeError("The frozen rerank threshold must be configured for parity checks")
    client = ModalBgeClient(settings)
    query = "你好 means hello; what does 你好 mean?"
    passages = [
        "你好 (nǐ hǎo) is a greeting meaning hello.",
        *[f"Deterministic passage {index}: 你好 is used to greet someone." for index in range(2, 21)],
    ]
    init_started = time.perf_counter()
    runtime = await client.invoke("runtime_info")
    cold_initialization_ms = (time.perf_counter() - init_started) * 1000
    if not isinstance(runtime, dict) or runtime.get("contract_version") != CONTRACT_VERSION:
        raise RuntimeError("Modal runtime contract verification failed")
    if (runtime.get("embedding_model_name"), runtime.get("embedding_model_revision"),
        runtime.get("reranker_model_name"), runtime.get("reranker_model_revision")) != (
        EMBEDDING_MODEL, EMBEDDING_REVISION, RERANKER_MODEL, RERANKER_REVISION
    ):
        raise RuntimeError("Modal runtime model identity mismatch")
    runtime_provenance_verified = _runtime_provenance_verified(runtime)
    real_modal_runtime = getattr(client, "real_modal_runtime", False) is True and runtime_provenance_verified

    local_settings = settings.model_copy(update={"embedding_provider": "local", "reranker_provider": "local"})
    from app.ai.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
    from app.ai.reranking.transformers_provider import TransformersRerankerProvider
    local_embedding = SentenceTransformerEmbeddingProvider(local_settings)
    local_reranker = TransformersRerankerProvider(local_settings)
    local_vector = await local_embedding.embed_query(query)
    local_pair_scores = []
    for offset in range(0, len(passages), RERANK_BATCH_SIZE):
        local_pair_scores.extend(await local_reranker.score(
            query, passages[offset:offset + RERANK_BATCH_SIZE],
        ))
    remote_embedding = await client.invoke("embed_query", query)
    await client.invoke("validate_rerank_inputs", query, passages)
    remote_pair_scores = []
    for offset in range(0, len(passages), RERANK_BATCH_SIZE):
        batch = passages[offset:offset + RERANK_BATCH_SIZE]
        remote_pair_scores.extend((await client.invoke("score_rerank", query, batch)).get("scores", []))
    remote_vector = remote_embedding.get("vector", [])
    if (len(local_vector) != 1024 or len(remote_vector) != 1024
        or len(local_pair_scores) != RERANK_PARITY_CANDIDATES):
        raise RuntimeError("Parity fixture returned an invalid output shape")
    if len(passages) != RERANK_PARITY_CANDIDATES or len(remote_pair_scores) != RERANK_PARITY_CANDIDATES:
        raise RuntimeError("Remote reranker returned an invalid score count")
    threshold = float(settings.rag_min_rerank_score)
    local_order = sorted(range(len(local_pair_scores)), key=lambda i: (-local_pair_scores[i], i))
    remote_order = sorted(range(len(remote_pair_scores)), key=lambda i: (-remote_pair_scores[i], i))
    local_decisions = [score >= threshold for score in local_pair_scores]
    remote_decisions = [score >= threshold for score in remote_pair_scores]
    threshold_equal = local_decisions == remote_decisions
    parity = {
        "embedding": {
            "max_absolute_delta": max(abs(a - b) for a, b in zip(local_vector, remote_vector, strict=True)),
            "dimension": len(remote_vector), "finite": all(math.isfinite(x) for x in remote_vector),
            "unit_norm": abs(math.sqrt(sum(x * x for x in remote_vector)) - 1.0) <= 1e-3,
        },
        "reranker": {
            "local_raw_scores": local_pair_scores, "modal_raw_scores": remote_pair_scores,
            "max_absolute_delta": max(abs(a - b) for a, b in zip(local_pair_scores, remote_pair_scores, strict=True)),
            "local_order": local_order, "modal_order": remote_order,
            "order_equal": local_order == remote_order,
            "local_threshold_decisions": local_decisions,
            "modal_threshold_decisions": remote_decisions,
            "candidate_count": RERANK_PARITY_CANDIDATES,
            "batch_size": RERANK_BATCH_SIZE,
            "batch_count": 3,
            "threshold_decisions_equal": threshold_equal,
            "threshold": threshold,
        },
    }
    common = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "modal_sdk_version": _package_version("modal"),
        "modal_app_name": settings.modal_bge_app_name,
        "modal_class_name": settings.modal_bge_class_name,
        "contract_version": CONTRACT_VERSION,
        "gpu_name": runtime.get("gpu_name"),
        "gpu_total_vram_bytes": runtime.get("gpu_total_vram_bytes"),
        "torch_version": runtime.get("torch_version"),
        "cuda_version": runtime.get("cuda_version"),
        "runtime_versions": runtime.get("runtime_versions"),
        "embedding": {"model_name": EMBEDDING_MODEL, "model_revision": EMBEDDING_REVISION},
        "reranker": {"model_name": RERANKER_MODEL, "model_revision": RERANKER_REVISION},
        "fixture_identity": {"name": "step83-deterministic-parity-v1", "query": query, "passages": passages},
        "parity": parity,
        "cold_initialization": {"runtime_info_ms": cold_initialization_ms},
        "billing": {
            "before_reference": before,
            "before_captured_at_utc": billing_before_captured_at,
            "after_reference": None,
            "after_captured_at_utc": None,
        },
        "real_modal_runtime": real_modal_runtime,
        "runtime_provenance_verified": runtime_provenance_verified,
    }
    if not threshold_equal:
        return {**common, "status": PARITY_FAILED_STATUS}

    async def embedding_call() -> None:
        result = await client.invoke("embed_query", query)
        if result.get("ok") is not True:
            raise RuntimeError("Modal embedding smoke call failed")

    async def rerank_call() -> None:
        await client.invoke("validate_rerank_inputs", query, passages)
        for offset in range(0, len(passages), RERANK_BATCH_SIZE):
            result = await client.invoke(
                "score_rerank", query, passages[offset:offset + RERANK_BATCH_SIZE],
            )
            if result.get("ok") is not True:
                raise RuntimeError("Modal reranking smoke call failed")

    async def combined_call() -> None:
        await embedding_call()
        await rerank_call()

    async def measure(call: Callable[[], Awaitable[None]], warmups: int, count: int) -> dict[str, Any]:
        for _ in range(warmups):
            await call()
        samples = []
        for _ in range(count):
            started = time.perf_counter()
            await call()
            samples.append((time.perf_counter() - started) * 1000)
        return {"raw_samples_ms": samples, "p50_ms": nearest_rank(samples, .50),
                "p95_ms": nearest_rank(samples, .95), "warmups": warmups, "sample_count": count}

    embedding_latency = await measure(embedding_call, 5, 30)
    reranker_latency = await measure(rerank_call, 3, 30)
    combined_latency = await measure(combined_call, 3, 30)
    reranker_latency.update({
        "candidate_count": RERANK_PARITY_CANDIDATES,
        "batch_size": RERANK_BATCH_SIZE,
        "batch_count": 3,
    })
    combined_latency.update({
        "candidate_count": RERANK_PARITY_CANDIDATES,
        "batch_size": RERANK_BATCH_SIZE,
        "batch_count": 3,
    })
    concurrency_pairs = []
    for _ in range(10):
        concurrency_pairs.append(await measure_concurrency_pair(combined_call))

    final_runtime = await client.invoke("runtime_info")
    final_runtime_provenance_verified = _runtime_provenance_verified(final_runtime)
    verified_provenance = runtime_provenance_verified and final_runtime_provenance_verified
    evidence = {
        **common,
        "status": PENDING_STATUS,
        "warm_embedding_ms": embedding_latency,
        "warm_reranking_ms": reranker_latency,
        "combined_ms": combined_latency,
        "concurrency_2_ms": concurrency_pairs,
        "gpu_name": final_runtime.get("gpu_name"),
        "gpu_total_vram_bytes": final_runtime.get("gpu_total_vram_bytes"),
        "torch_version": final_runtime.get("torch_version"),
        "cuda_version": final_runtime.get("cuda_version"),
        "runtime_versions": final_runtime.get("runtime_versions"),
        "runtime_provenance_verified": verified_provenance,
        "real_modal_runtime": getattr(client, "real_modal_runtime", False) is True and verified_provenance,
        "vram": {
            "allocated_bytes": final_runtime.get("vram_allocated_bytes"),
            "reserved_bytes": final_runtime.get("vram_reserved_bytes"),
            "max_allocated_bytes": final_runtime.get("vram_max_allocated_bytes"),
            "max_reserved_bytes": final_runtime.get("vram_max_reserved_bytes"),
        },
    }
    # A fully successful local fake can exercise the harness, but cannot be
    # promoted or finalized as real Modal evidence.
    if evidence["real_modal_runtime"]:
        validate_pending_measurement(evidence)
    return evidence


def _git_commit() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _package_version(package: str) -> str:
    from importlib.metadata import version
    return version(package)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Separately authorized Stage-B Modal BGE validation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Capture before-billing and measurements")
    run_parser.add_argument("--stage-b-authorized", action="store_true")
    run_parser.add_argument("--billing-before-reference", required=True)
    run_parser.add_argument("--output", type=Path, default=OUTPUT_DIR / "t4-validation-pending.json")
    finalize_parser = subparsers.add_parser("finalize", help="Attach after-billing evidence offline")
    finalize_parser.add_argument("--stage-b-authorized", action="store_true")
    finalize_parser.add_argument("--pending", type=Path, required=True)
    finalize_parser.add_argument("--billing-after-reference", required=True)
    finalize_parser.add_argument("--output", type=Path, default=OUTPUT_DIR / "t4-validation.json")
    args = parser.parse_args()
    if not args.stage_b_authorized:
        parser.error("Real Stage-B actions require --stage-b-authorized")
    if os.environ.get(STAGE_B_ENV) != "true":
        parser.error("Real Stage-B actions require explicit STEP83_STAGE_B_AUTHORIZED=true")

    if args.command == "run":
        result = asyncio.run(run_real_validation(billing_before_reference=args.billing_before_reference))
        _write_json(args.output, result)
        if result.get("status") == PARITY_FAILED_STATUS:
            parser.exit(2, "PARITY_GATE_FAILED; benchmark stopped and no complete evidence was written.\n")
        return

    pending = json.loads(args.pending.read_text(encoding="utf-8"))
    result = finalize_real_result(pending, billing_after_reference=args.billing_after_reference)
    _write_json(args.output, result)


if __name__ == "__main__":
    main()
