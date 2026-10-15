"""Safe, offline-capable harness for Step 8.3 / D-004 BGE profiling.

The preflight path deliberately imports no model provider. Heavy modes check host
memory and the exact local cache revisions before constructing any provider.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import importlib.metadata
import inspect
import json
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
FIXTURE_ROOT = REPO_ROOT / "evaluation" / "fixtures" / "lesson_chat_rag" / "v0.1.0"
DATASET_ROOT = REPO_ROOT / "evaluation" / "datasets" / "lesson_chat_rag" / "v0"
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
SCENARIOS = (
    "baseline", "embedding-load", "reranker-load", "both-loaded", "warm-embedding",
    "warm-reranking", "concurrency-2", "ingestion-embedding",
)
REQUIRED_PROFILE_SCENARIOS = SCENARIOS
DEFAULT_MIN_AVAILABLE_RAM_GIB = 4.0  # profiler-machine guard only; not a hosting requirement
COLD_REPETITIONS = 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--scenario", choices=SCENARIOS)
    mode.add_argument("--aggregate", nargs="+", type=Path, metavar="SCENARIO_JSON")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-available-ram-gib", type=float, default=DEFAULT_MIN_AVAILABLE_RAM_GIB)
    parser.add_argument("--_child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.min_available_ram_gib < 0:
        parser.error("--min-available-ram-gib must be non-negative")
    if args.aggregate and not args.output:
        parser.error("--aggregate requires --output")
    return args


def derive_overlap_observed(start_a: float, complete_a: float, start_b: float, complete_b: float) -> bool:
    """Return whether measured execution intervals overlap (strict interval intersection)."""
    return max(start_a, start_b) < min(complete_a, complete_b)


def run_concurrency_pair(workload_a: Callable[[], Any], workload_b: Callable[[], Any], *, clock: Callable[[], float] = time.perf_counter,
                         wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict[str, Any]:
    """Schedule two synchronous production-shaped workloads at one asyncio arrival barrier.

    Sync work deliberately runs on the event loop. If A blocks it, B starts after A
    completes; timestamps expose that serialization instead of assuming overlap.
    """
    loop = asyncio.new_event_loop()
    started: dict[str, float] = {}
    completed: dict[str, float] = {}
    errors: dict[str, str | None] = {"a": None, "b": None}
    results: dict[str, Any] = {}
    release = asyncio.Event()
    arrival_timestamp = wall_clock().isoformat()
    arrival = clock()

    async def invoke(key: str, workload: Callable[[], Any]) -> None:
        await release.wait()
        started[key] = clock()
        try:
            value = workload()
            results[key] = await value if inspect.isawaitable(value) else value
        except Exception as exc:  # captured per request so the other arrival still runs
            errors[key] = type(exc).__name__
        finally:
            completed[key] = clock()

    async def pair() -> None:
        task_a = asyncio.create_task(invoke("a", workload_a))
        task_b = asyncio.create_task(invoke("b", workload_b))
        release.set()
        await asyncio.gather(task_a, task_b)

    try:
        loop.run_until_complete(pair())
    finally:
        loop.close()
    offsets = {key: ((started[key] - arrival) * 1000, (completed[key] - arrival) * 1000) for key in ("a", "b")}
    start_a, complete_a = offsets["a"]
    start_b, complete_b = offsets["b"]
    makespan = max(complete_a, complete_b)
    return {
        "common_arrival": arrival_timestamp,
        "request_a_start_offset_ms": start_a,
        "request_a_complete_offset_ms": complete_a,
        "request_a_execution_ms": complete_a - start_a,
        "request_a_latency_ms": complete_a,
        "request_b_start_offset_ms": start_b,
        "request_b_complete_offset_ms": complete_b,
        "request_b_execution_ms": complete_b - start_b,
        "request_b_latency_ms": complete_b,
        "pair_makespan_ms": makespan,
        "overlap_observed": derive_overlap_observed(start_a, complete_a, start_b, complete_b),
        "errors": errors,
        "results": results,
    }


def _child_command(scenario: str) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "--scenario", scenario, "--_child"]


def run_fresh_process_repetitions(scenario: str, *, runner: Callable[..., Any] = subprocess.run,
                                  count: int = COLD_REPETITIONS, test_only_fixture: bool = False) -> dict[str, Any]:
    """Run each model first-use measurement in an independent Python process."""
    if scenario not in {"embedding-load", "reranker-load"}:
        raise ValueError("fresh-process repetition is only valid for model load scenarios")
    raw: list[float] = []
    child_results = []
    steady_rss_samples: list[int] = []
    peak_rss_samples: list[int] = []
    env = os.environ.copy()
    env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    for repetition in range(count):
        completed = runner(_child_command(scenario), cwd=BACKEND_ROOT, capture_output=True, text=True, check=False, env=env)
        try:
            child = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            if completed.returncode != 0:
                raise RuntimeError(f"{scenario} fresh-process repetition {repetition + 1} failed with exit {completed.returncode}: {completed.stderr.strip()}") from exc
            raise
        if child.get("environment_gate") != "PASSED" or child.get("scenario_result", {}).get("status") != "MEASURED":
            return {"status": child.get("status", "ENVIRONMENT_GATE"), "reason": child.get("reason", "CHILD_MEASUREMENT_NOT_VALID"),
                    "scenario": scenario, "repetitions_completed": len(child_results), "child_result": child}
        if completed.returncode != 0:
            raise RuntimeError(f"{scenario} fresh-process repetition {repetition + 1} failed with exit {completed.returncode}: {completed.stderr.strip()}")
        child_measurement = child["scenario_result"]
        measurement = child_measurement.get("cold_first_use_ms")
        if not isinstance(measurement, (int, float)):
            raise ValueError(f"{scenario} child did not produce cold first-use timing")
        if test_only_fixture:
            if child.get("test_fixture_only") is not True or child.get("real_provider_measurement") is True:
                raise ValueError("test-only cold fixtures must be explicitly non-evidence")
        elif child.get("real_provider_measurement") is not True:
            raise ValueError(f"{scenario} child did not produce real cold first-use evidence")
        steady_rss = child_measurement.get("steady_rss_bytes")
        peak_rss = child_measurement.get("peak_rss_bytes")
        if not isinstance(steady_rss, int) or not isinstance(peak_rss, int):
            raise ValueError(f"{scenario} child did not produce steady and peak RSS evidence")
        raw.append(float(measurement))
        steady_rss_samples.append(steady_rss)
        peak_rss_samples.append(peak_rss)
        child_results.append(child)
    if len(raw) != count:
        raise ValueError(f"expected {count} cold repetitions, got {len(raw)}")
    return {"status": "TEST_FIXTURE_ONLY" if test_only_fixture else "MEASURED",
            "real_provider_measurement": not test_only_fixture, "fresh_process_repetitions": count, "raw_samples_ms": raw,
            "median_ms": statistics.median(raw), "steady_rss_samples_bytes": steady_rss_samples,
            "median_steady_rss_bytes": int(statistics.median(steady_rss_samples)),
            "peak_rss_samples_bytes": peak_rss_samples,
            "max_observed_peak_rss_bytes": max(peak_rss_samples), "sample_scenarios": child_results}


def _expected_model_settings(settings: Any, scenario: str) -> dict[str, Any] | None:
    checks = []
    if scenario in {"embedding-load", "both-loaded", "warm-embedding", "concurrency-2", "ingestion-embedding"}:
        checks.append(("embedding", settings.embedding_model_name, settings.embedding_model_revision, EMBEDDING_MODEL, EMBEDDING_REVISION))
    if scenario in {"reranker-load", "both-loaded", "warm-embedding", "warm-reranking", "concurrency-2"}:
        checks.append(("reranker", settings.reranker_model_name, settings.reranker_model_revision, RERANKER_MODEL, RERANKER_REVISION))
    for name, actual_model, actual_revision, expected_model, expected_revision in checks:
        if actual_model != expected_model or actual_revision != expected_revision:
            return {"status": "ENVIRONMENT_GATE", "reason": "MODEL_CONFIG_MISMATCH", "scenario": scenario,
                    "model": name, "expected": {"model": expected_model, "revision": expected_revision},
                    "actual": {"model": actual_model, "revision": actual_revision}}
    return None


def _psutil():
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError("psutil is required for RSS profiling; install backend dev dependencies") from exc
    return psutil


def memory_state() -> dict[str, int | None]:
    """Read host RAM without importing torch or constructing any model provider."""
    try:
        memory = _psutil().virtual_memory()
        return {"total_ram_bytes": int(memory.total), "available_ram_bytes": int(memory.available)}
    except (ImportError, RuntimeError):
        if os.name == "nt":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return {"total_ram_bytes": int(status.ullTotalPhys), "available_ram_bytes": int(status.ullAvailPhys)}
    return {"total_ram_bytes": None, "available_ram_bytes": None}


def resource_gate(scenario: str, *, available_ram_bytes: int | None, threshold_bytes: int) -> dict[str, Any] | None:
    if available_ram_bytes is None or available_ram_bytes < threshold_bytes:
        return {
            "status": "ENVIRONMENT_GATE",
            "reason": "INSUFFICIENT_AVAILABLE_RAM" if available_ram_bytes is not None else "RAM_STATE_UNAVAILABLE",
            "available_ram_bytes": available_ram_bytes,
            "configured_safety_threshold_bytes": threshold_bytes,
            "scenario": scenario,
        }
    return None


def nearest_rank_percentile(samples: Iterable[float], percentile: float) -> float:
    values = sorted(float(value) for value in samples)
    if not values or not 0 < percentile <= 100:
        raise ValueError("samples must be non-empty and percentile in (0, 100]")
    rank = max(1, int((percentile * len(values) + 99.999999) // 100))
    return values[rank - 1]


def aggregate_samples(samples: Iterable[float]) -> dict[str, Any]:
    values = [float(value) for value in samples]
    if not values:
        raise ValueError("at least one sample is required")
    return {
        "samples_ms": values,
        "count": len(values),
        "p50_ms": statistics.median(values),
        "p95_ms": nearest_rank_percentile(values, 95),
    }


def text_size_summary(texts: Iterable[str]) -> dict[str, Any]:
    values = list(texts)
    chars = [len(value) for value in values]
    utf8 = [len(value.encode("utf-8")) for value in values]
    def summary(sizes: list[int]) -> dict[str, int | float]:
        return {"min": min(sizes) if sizes else 0, "mean": round(statistics.mean(sizes), 2) if sizes else 0,
                "median": statistics.median(sizes) if sizes else 0, "max": max(sizes) if sizes else 0,
                "total": sum(sizes)}
    return {"characters": summary(chars), "utf8_bytes": summary(utf8)}


def steady_rss_summary(samples: list[int], *, window: int = 10) -> dict[str, int | float | None]:
    tail = samples[-window:]
    steady = int(statistics.median(tail)) if tail else None
    peak = max(samples) if samples else None
    baseline = samples[0] if samples else None
    return {
        "baseline_rss_bytes": baseline,
        "baseline_rss_mib": round(baseline / (1024 * 1024), 2) if baseline is not None else None,
        "steady_rss_bytes": steady,
        "steady_rss_mib": round(steady / (1024 * 1024), 2) if steady is not None else None,
        "peak_rss_bytes": peak,
        "peak_rss_mib": round(peak / (1024 * 1024), 2) if peak is not None else None,
        "steady_sample_count": len(tail),
        "steady_method": f"median of final {window} process RSS samples after 1 second settling interval",
    }


class RssSampler:
    """Sample process RSS with psutil; no tracemalloc substitution."""

    def __init__(self, interval_seconds: float = 0.05):
        if interval_seconds <= 0:
            raise ValueError("sampling interval must be positive")
        self.interval_seconds = interval_seconds
        self.samples: list[int] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        process = _psutil().Process(os.getpid())
        while not self._stop.is_set():
            self.samples.append(int(process.memory_info().rss))
            self._stop.wait(self.interval_seconds)

    def __enter__(self):
        process = _psutil().Process(os.getpid())
        self.samples.append(int(process.memory_info().rss))
        self._thread = threading.Thread(target=self._sample, name="bge-rss-sampler", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 4))

    @property
    def peak_rss_bytes(self) -> int | None:
        return max(self.samples) if self.samples else None


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _cache_snapshot(model_name: str, revision: str) -> dict[str, Any]:
    hub = Path(os.environ.get("HF_HUB_CACHE") or (Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"))
    model_dir = "models--" + model_name.replace("/", "--")
    repo_cache = hub / model_dir
    snapshot = repo_cache / "snapshots" / revision
    present = snapshot.is_dir()
    weight_files = ("model.safetensors", "pytorch_model.bin", "model.safetensors.index.json", "pytorch_model.bin.index.json")
    config_present = (snapshot / "config.json").is_file()
    weights_present = any((snapshot / file).is_file() for file in weight_files)
    return {
        "cache_root": str(hub),
        "model_cache_present": repo_cache.is_dir(),
        "exact_revision_present": present and config_present and weights_present,
        "revision": revision,
        "required_config_present": config_present,
        "model_weights_present": weights_present,
    }


def _runtime_capabilities() -> dict[str, Any]:
    result: dict[str, Any] = {"torch_available": False, "cuda_available": None, "cuda_devices": [], "mps_available": None}
    try:
        import torch
    except Exception as exc:  # preflight must still produce useful environment evidence
        result["torch_error_type"] = type(exc).__name__
        return result
    result.update({"torch_available": True, "torch_version": str(torch.__version__)})
    try:
        result["cuda_available"] = bool(torch.cuda.is_available())
        if result["cuda_available"]:
            result["cuda_devices"] = [
                {"index": i, "name": torch.cuda.get_device_name(i), "total_memory_bytes": int(torch.cuda.get_device_properties(i).total_memory)}
                for i in range(torch.cuda.device_count())
            ]
    except Exception as exc:
        result["cuda_probe_error_type"] = type(exc).__name__
    try:
        mps = getattr(getattr(torch, "backends", None), "mps", None)
        result["mps_available"] = bool(mps and mps.is_available())
    except Exception as exc:
        result["mps_probe_error_type"] = type(exc).__name__
    return result


def _cpu_model() -> str | None:
    model = platform.processor().strip()
    if model:
        return model
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            return None
    return None


def collect_preflight() -> dict[str, Any]:
    # Imports Settings only; provider constructors and model loaders are deliberately absent.
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.core.config import get_settings

    settings = get_settings()
    ram = memory_state()
    psutil_version = package_version("psutil")
    physical_cores = logical_cores = None
    try:
        ps = _psutil()
        physical_cores = ps.cpu_count(logical=False)
        logical_cores = ps.cpu_count(logical=True)
    except RuntimeError:
        logical_cores = os.cpu_count()
    commit = None
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    embedding_cache = _cache_snapshot(EMBEDDING_MODEL, EMBEDDING_REVISION)
    reranker_cache = _cache_snapshot(RERANKER_MODEL, RERANKER_REVISION)
    runtime = _runtime_capabilities()
    return {
        "schema_version": "step8.3-preflight/1.0",
        "status": "PREFLIGHT_ONLY",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "environment": {
            "os": platform.system(), "release": platform.release(), "architecture": platform.machine(),
            "platform": platform.platform(), "cpu_model": _cpu_model(), "physical_cores": physical_cores,
            "logical_cores": logical_cores, **ram, "python_version": platform.python_version(),
            "package_versions": {
                "sentence-transformers": package_version("sentence-transformers"),
                "transformers": package_version("transformers"), "torch": package_version("torch"),
                "numpy": package_version("numpy"), "psutil": psutil_version,
            },
        },
        "models": {
            "embedding": {
                "provider": "SentenceTransformerEmbeddingProvider", "model_name": settings.embedding_model_name,
                "revision": settings.embedding_model_revision, "requested_device": settings.embedding_device,
                "batch_size": settings.embedding_batch_size, "dimensions": 1024,
                "normalize_embeddings": settings.embedding_normalize, "input_version": settings.embedding_input_version,
                "loading": "lazy on first embed_documents/embed_query use", **embedding_cache,
            },
            "reranker": {
                "provider": "TransformersRerankerProvider", "model_name": settings.reranker_model_name,
                "revision": settings.reranker_model_revision, "requested_device": settings.reranker_device,
                "batch_size": settings.reranker_batch_size, "top_k": settings.reranker_top_k,
                "candidate_pool_size": settings.rag_retrieval_candidate_k, "input_version": settings.reranker_input_version,
                "loading": "lazy on first pair validation/scoring", **reranker_cache,
            },
        },
        "runtime_capability": runtime,
        "safety_guard": {
            "default_min_available_ram_gib": DEFAULT_MIN_AVAILABLE_RAM_GIB,
            "purpose": "benchmark-machine safety guard only; not a production or hosting requirement",
        },
        "model_loading_performed": False,
        "inference_performed": False,
        "network_access_performed": False,
        "database_or_provider_calls_performed": False,
    }


def load_fixture_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    blocks: list[dict[str, Any]] = []
    source_paths = []
    for source in manifest["sources"]:
        path = FIXTURE_ROOT / source["path"]
        source_data = json.loads(path.read_text(encoding="utf-8"))
        source_paths.append(path.relative_to(REPO_ROOT).as_posix())
        for block in source_data["blocks"]:
            blocks.append({**block, "_source": source_data, "_path": path.relative_to(REPO_ROOT).as_posix()})
    cases = []
    for split_file in ("development.jsonl", "holdout.jsonl"):
        path = DATASET_ROOT / split_file
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as stream:
            cases.extend(json.loads(line) for line in stream if line.strip())
    manifest["source_paths"] = source_paths
    return blocks, cases, manifest


def select_fixtures() -> dict[str, Any]:
    blocks, cases, fixture_manifest = load_fixture_data()
    locators = {block["stable_locator"] for block in blocks}
    eligible = sorted(
        (case for case in cases if case.get("review_status") == "APPROVED" and case.get("split") == "DEVELOPMENT"
         and case.get("bucket") in {"CURRENT_LESSON_ANSWERABLE", "INTERNAL_KB_FALLBACK"}),
        key=lambda case: case["case_id"],
    )[:10]
    if len(eligible) < 10:
        raise ValueError(f"expected 10 approved internal BGE DEVELOPMENT cases, found {len(eligible)}")
    selected_case_ids = [case["case_id"] for case in eligible]
    evidence_locators = []
    for case in eligible:
        for evidence in case.get("required_evidence", []):
            locator = evidence.get("stable_locator")
            if locator in locators and locator not in evidence_locators:
                evidence_locators.append(locator)
    by_locator = {block["stable_locator"]: block for block in blocks}
    chosen = [by_locator[locator] for locator in evidence_locators]
    chosen_ids = {block["stable_locator"] for block in chosen}
    for block in sorted(blocks, key=lambda item: item["stable_locator"]):
        if len(chosen) >= 20:
            break
        if block["stable_locator"] not in chosen_ids:
            chosen.append(block)
            chosen_ids.add(block["stable_locator"])
    rerank_blocks = chosen[:20]
    selected_queries = [case["question"] for case in eligible]
    passage_lengths = [len(_block_text(block)) for block in rerank_blocks]
    # Preserve all corpus inputs when fewer than the 64 target exist; never pad/duplicate.
    return {
        "fixture_pack_version": fixture_manifest["fixture_pack_version"],
        "dataset_version": "v0.8.0",
        "source_paths": fixture_manifest["source_paths"] + [
            (DATASET_ROOT / "development.jsonl").relative_to(REPO_ROOT).as_posix(),
            (DATASET_ROOT / "manifest.json").relative_to(REPO_ROOT).as_posix(),
        ],
        "selected_case_ids": selected_case_ids,
        "selected_cases": [
            {
                "case_id": case["case_id"], "bucket": case["bucket"],
                "required_evidence_locators": [
                    evidence["stable_locator"] for evidence in case.get("required_evidence", [])
                    if evidence.get("stable_locator") in locators
                ],
            }
            for case in eligible
        ],
        "selected_case_count": len(eligible),
        "selected_stable_locators": [block["stable_locator"] for block in rerank_blocks],
        "rerank_candidate_count": len(rerank_blocks),
        "ingestion_input_count": len(blocks),
        "ingestion_target_count": 64,
        "ingestion_input_limitation": "controlled accepted corpus contains fewer than 64 unique blocks" if len(blocks) < 64 else None,
        "unique_fixture_block_count": len(blocks),
        "query_text_characters": {"min": min(map(len, selected_queries)), "max": max(map(len, selected_queries)), "mean": round(statistics.mean(map(len, selected_queries)), 2)},
        "reranker_passage_text_characters": {"min": min(passage_lengths), "max": max(passage_lengths), "mean": round(statistics.mean(passage_lengths), 2)},
    }


def _block_text(block: dict[str, Any]) -> str:
    return json.dumps(block["content"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _provider_identity(provider: Any) -> dict[str, Any]:
    identity = asdict(provider.identity)
    if "model_version" in identity:
        identity["model_revision"] = identity.pop("model_version")
    return identity


def build_embedding_contexts(blocks: list[dict[str, Any]]):
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.ai.embeddings.schemas import EmbeddingChunkContext

    contexts = []
    for index, block in enumerate(sorted(blocks, key=lambda item: item["stable_locator"])):
        source = block["_source"]
        kind = source["source_kind"]
        is_lesson = kind == "LESSON"
        source_id = source["source_id"]
        source_uuid = uuid.uuid5(uuid.NAMESPACE_URL, source_id)
        stable_uuid = uuid.uuid5(uuid.NAMESPACE_URL, block["stable_locator"])
        contexts.append(EmbeddingChunkContext(
            chunk_id=stable_uuid, chunk_index=index, content=_block_text(block), content_type=block["content_type"],
            section=block["content_type"], document_title=None if is_lesson else source["title"],
            lesson_id=source_uuid if is_lesson else None, lesson_title=source.get("lesson_title"),
            hsk_level_number=source.get("hsk_level_number", 1), source_type="LESSON" if is_lesson else "DOCUMENT",
            source_document_id=None if is_lesson else source_uuid,
            source_lesson_id=source_uuid if is_lesson else None, chunk_lesson_id=source_uuid if is_lesson else None,
        ))
    return contexts


def build_rerank_candidates(blocks: list[dict[str, Any]]):
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.ai.retrieval.schemas import RetrievalCandidate

    candidates = []
    for rank, block in enumerate(blocks, start=1):
        source = block["_source"]
        lesson = source["source_kind"] == "LESSON"
        source_uuid = uuid.uuid5(uuid.NAMESPACE_URL, source["source_id"])
        candidates.append(RetrievalCandidate(
            rank=rank, chunk_id=uuid.uuid5(uuid.NAMESPACE_URL, block["stable_locator"]), chunk_index=rank - 1,
            content=_block_text(block), content_type=block["content_type"],
            knowledge_version_id=uuid.uuid5(uuid.NAMESPACE_URL, source["source_id"] + ":version:v1"),
            knowledge_source_id=source_uuid, source_type="LESSON" if lesson else "DOCUMENT",
            source_document_id=None if lesson else source_uuid, source_lesson_id=source_uuid if lesson else None,
            chunk_lesson_id=source_uuid if lesson else None,
            document_title=None if lesson else source["title"], lesson_title=source.get("lesson_title"),
            hsk_level_number=source.get("hsk_level_number", 1), page_number=None, section=block["content_type"],
            locator_metadata={"stable_locator": block["stable_locator"], "harness_fixture_identity": True},
            distance=1.0, retrieval_score=1.0 / rank,
        ))
    return candidates


def measure_concurrency_2(query_texts: list[str], candidates: list[Any], embed_query: Callable[[str], Any],
                          rerank: Callable[[str, list[Any]], Any], *, pair_runner: Callable[..., dict[str, Any]] = run_concurrency_pair) -> dict[str, Any]:
    if len(query_texts) < 2:
        raise ValueError("concurrency-2 requires at least two deterministic query fixtures")
    for index in range(2):
        query = query_texts[index % len(query_texts)]
        _run_sync(embed_query(query))
        _run_sync(rerank(query, candidates))
    pairs = []
    for index in range(10):
        query_a = query_texts[(2 * index) % len(query_texts)]
        query_b = query_texts[(2 * index + 1) % len(query_texts)]
        def request(query: str) -> Callable[[], Any]:
            async def run_request():
                await _await_maybe(embed_query(query))
                return await _await_maybe(rerank(query, candidates))
            return run_request
        pairs.append(pair_runner(request(query_a), request(query_b)))
    return {"warmup_workloads": 2, "pair_repetitions": 10, "arrivals_per_pair": 2, "pairs": pairs,
            "overlap_observed": any(pair["overlap_observed"] for pair in pairs)}


def measure_ingestion_embedding(blocks: list[dict[str, Any]], embed_documents: Callable[..., list[Any]], batch_size: int,
                                *, context_builder: Callable[[list[dict[str, Any]]], Any] | None = None,
                                formatter_factory: Callable[[], Any] | None = None,
                                clock: Callable[[], float] = time.perf_counter) -> dict[str, Any]:
    """Prepare and format first, warm up next, then time a complete unique input pass."""
    if context_builder is None:
        context_builder = build_embedding_contexts
    if formatter_factory is None:
        from app.ai.embeddings.formatter import EmbeddingInputFormatter
        formatter_factory = EmbeddingInputFormatter
    contexts = context_builder(blocks)
    formatter = formatter_factory()
    texts = [formatter.format(item) for item in contexts]
    sizes = [len(text.encode("utf-8")) for text in texts]
    warmup_texts = texts[:batch_size]
    warmup_batches = 0
    if warmup_texts:
        _run_sync(embed_documents(warmup_texts, batch_size=batch_size))
        warmup_batches = 1
    started = clock()
    vectors = []
    errors = []
    measured_batches = 0
    for offset in range(0, len(texts), batch_size):
        batch = texts[offset:offset + batch_size]
        try:
            vectors.extend(_run_sync(embed_documents(batch, batch_size=batch_size)))
            measured_batches += 1
        except Exception as exc:
            errors.append({"batch_index": measured_batches, "error_type": type(exc).__name__})
            break
    elapsed = clock() - started
    return {
        "status": "MEASURED" if not errors else "MEASUREMENT_FAILED", "input_count": len(texts),
        "total_chars": sum(map(len, texts)), "total_utf8_bytes": sum(sizes),
        "size_utf8_bytes": {"min": min(sizes) if sizes else 0, "mean": statistics.mean(sizes) if sizes else 0,
                            "max": max(sizes) if sizes else 0},
        "configured_batch_size": batch_size, "measured_batch_count": measured_batches,
        "warmup_batch_count": warmup_batches, "elapsed_seconds": elapsed,
        "chunks_per_second": len(texts) / elapsed if elapsed and not errors else None,
        "errors": errors, "vectors": vectors,
    }


def measure_both_loaded_workload(embedding_first_use: Callable[[], Any], reranker_first_use: Callable[[], Any],
                                 embed_query: Callable[[], Any], rerank: Callable[[], Any], *,
                                 clock: Callable[[], float] = time.perf_counter) -> dict[str, float]:
    embedding_started = clock(); _run_sync(embedding_first_use()); embedding_ms = (clock() - embedding_started) * 1000
    reranker_started = clock(); _run_sync(reranker_first_use()); reranker_ms = (clock() - reranker_started) * 1000
    warm_started = clock(); _run_sync(embed_query()); _run_sync(rerank()); warm_ms = (clock() - warm_started) * 1000
    return {"embedding_cold_first_use_ms": embedding_ms, "reranker_cold_first_use_ms": reranker_ms,
            "both_loaded_workload_ms": warm_ms}


def _run_sync(value):
    """Resolve the profiler's async provider boundary from its synchronous CLI harness."""
    return asyncio.run(value) if inspect.isawaitable(value) else value


async def _await_maybe(value):
    return await value if inspect.isawaitable(value) else value


def _provider_workload(scenario: str, selected: dict[str, Any]) -> dict[str, Any]:
    """Execute only after memory/cache guard; uses normal provider/service paths."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.core.config import get_settings

    settings = get_settings()
    if scenario == "baseline":
        # Match the frozen baseline: normal config/provider modules imported, no model forced resident.
        from app.ai.embeddings.provider import get_embedding_provider  # noqa: F401
        from app.ai.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider  # noqa: F401
        from app.ai.reranking.provider import get_reranker_provider  # noqa: F401
        from app.ai.reranking.transformers_provider import TransformersRerankerProvider  # noqa: F401
        sampler = RssSampler()
        with sampler:
            time.sleep(1.0)
            return {"scenario": scenario, "status": "MEASURED", "baseline_definition": "fresh process after Settings and normal embedding/reranking provider modules are imported, before model construction or inference", **steady_rss_summary(sampler.samples)}
    blocks, _cases, _manifest = load_fixture_data()
    selected_locators = set(selected["selected_stable_locators"])
    rerank_blocks = [block for block in blocks if block["stable_locator"] in selected_locators]
    queries = []
    with (DATASET_ROOT / "development.jsonl").open(encoding="utf-8") as stream:
        queries = [json.loads(line) for line in stream if line.strip() and json.loads(line).get("case_id") in selected["selected_case_ids"]]
    query_texts = [case["question"] for case in queries]
    started = time.perf_counter()
    with RssSampler() as sampler:
        if scenario in {"embedding-load", "both-loaded", "warm-embedding", "concurrency-2", "ingestion-embedding"}:
            from app.ai.embeddings.provider import get_embedding_provider
            embedding = get_embedding_provider()
            if scenario == "ingestion-embedding":
                measured = measure_ingestion_embedding(
                    blocks, embedding.embed_documents, settings.embedding_batch_size,
                )
                time.sleep(1.0)
                vectors = measured.pop("vectors")
                return {"scenario": scenario, **measured, "provider_identity": _provider_identity(embedding),
                        "resolved_device": embedding.device, "dimensions": len(vectors[0]) if vectors else None,
                        **steady_rss_summary(sampler.samples)}
            if scenario == "embedding-load":
                sample_started = time.perf_counter(); _run_sync(embedding.embed_query(query_texts[0])); elapsed = time.perf_counter() - sample_started
                time.sleep(1.0)
                return {"scenario": scenario, "status": "MEASURED", "cold_first_use_ms": elapsed * 1000, "provider_identity": _provider_identity(embedding), "resolved_device": embedding.device, **steady_rss_summary(sampler.samples)}
            if scenario == "warm-embedding":
                for query in query_texts[:5]: _run_sync(embedding.embed_query(query))
                samples = []
                for i in range(30):
                    started = time.perf_counter(); _run_sync(embedding.embed_query(query_texts[i % len(query_texts)])); samples.append((time.perf_counter() - started) * 1000)
                time.sleep(1.0)
                return {"scenario": scenario, "status": "MEASURED", "warmups": 5, "query_count": len(query_texts),
                        "query_size": text_size_summary(query_texts), "latency": aggregate_samples(samples),
                        "provider_identity": _provider_identity(embedding), "resolved_device": embedding.device,
                        **steady_rss_summary(sampler.samples)}
            if scenario == "concurrency-2":
                pass  # keep embedding resident; exercise reranker below before timing
        if scenario in {"reranker-load", "both-loaded", "warm-reranking", "concurrency-2"}:
            from app.ai.reranking.service import RerankingService
            from app.ai.reranking.provider import get_reranker_provider
            reranker = get_reranker_provider()
            service = RerankingService(provider=reranker, settings=settings)
            candidates = build_rerank_candidates(rerank_blocks)
            if scenario == "reranker-load":
                sample_started = time.perf_counter(); _run_sync(service.rerank(query_texts[0], candidates)); elapsed = time.perf_counter()-sample_started
                time.sleep(1.0)
                return {"scenario": scenario, "status": "MEASURED", "cold_first_use_ms": elapsed*1000, "candidate_count": len(candidates), "provider_identity": _provider_identity(reranker), "resolved_device": reranker.device, **steady_rss_summary(sampler.samples)}
            if scenario == "warm-reranking":
                for query in query_texts[:3]: _run_sync(service.rerank(query, candidates))
                samples = []
                for i in range(30):
                    sample_started=time.perf_counter(); _run_sync(service.rerank(query_texts[i % len(query_texts)], candidates)); samples.append((time.perf_counter()-sample_started)*1000)
                time.sleep(1.0)
                passage_texts = [candidate.content for candidate in candidates]
                return {"scenario": scenario, "status": "MEASURED", "warmups": 3, "candidate_count": len(candidates),
                        "query_size": text_size_summary(query_texts), "passage_size": text_size_summary(passage_texts),
                        "configured_batch_size": settings.reranker_batch_size,
                        "measured_batch_count": (len(candidates) + settings.reranker_batch_size - 1) // settings.reranker_batch_size,
                        "error_count": 0, "latency": aggregate_samples(samples),
                        "provider_identity": _provider_identity(reranker), "resolved_device": reranker.device,
                        **steady_rss_summary(sampler.samples)}
        if scenario == "both-loaded":
            # Keep model first-use observations distinct from warm application-like latency.
            from app.ai.embeddings.provider import get_embedding_provider
            embedding_provider = get_embedding_provider()
            query = query_texts[0]
            warm_query = query_texts[1 % len(query_texts)]
            measured = measure_both_loaded_workload(
                    lambda: _run_sync(embedding_provider.embed_query(query)), lambda: _run_sync(service.rerank(query, candidates)),
                    lambda: _run_sync(embedding_provider.embed_query(warm_query)), lambda: _run_sync(service.rerank(warm_query, candidates)),
            )
            time.sleep(1.0)
            return {"scenario": scenario, "status": "MEASURED", **measured,
                    "embedding_identity": _provider_identity(embedding_provider), "reranker_identity": _provider_identity(reranker),
                    "embedding_device": embedding_provider.device, "reranker_device": reranker.device,
                    "resident_together": True, **steady_rss_summary(sampler.samples)}
        if scenario == "concurrency-2":
            def measured_pair(request_a, request_b):
                sample_start = len(sampler.samples)
                pair_result = run_concurrency_pair(request_a, request_b)
                pair_samples = sampler.samples[sample_start:]
                pair_result["peak_rss_bytes"] = max(pair_samples) if pair_samples else int(_psutil().Process(os.getpid()).memory_info().rss)
                return pair_result
            measured = measure_concurrency_2(query_texts, candidates, embedding.embed_query, service.rerank,
                                             pair_runner=measured_pair)
            for pair in measured["pairs"]:
                pair.pop("results", None)
            time.sleep(1.0)
            return {"scenario": scenario, "status": "MEASURED", **measured,
                    "execution_model": "two asyncio-scheduled same-loop tasks invoking current synchronous providers; no thread-pool optimization",
                    "embedding_identity": _provider_identity(embedding), "reranker_identity": _provider_identity(reranker),
                    "embedding_device": embedding.device, "reranker_device": reranker.device,
                    **steady_rss_summary(sampler.samples)}
    raise ValueError(f"unsupported scenario {scenario}")


def run_scenario(scenario: str, *, min_available_ram_gib: float = DEFAULT_MIN_AVAILABLE_RAM_GIB,
                 workload: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
                 child: bool = False) -> dict[str, Any]:
    # Baseline is intentionally safe without the heavy-model memory gate.
    ram = memory_state()
    threshold = int(min_available_ram_gib * (1024 ** 3))
    if scenario != "baseline":
        gate = resource_gate(scenario, available_ram_bytes=ram["available_ram_bytes"], threshold_bytes=threshold)
        if gate:
            return gate
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.core.config import get_settings
    settings = get_settings()
    mismatch = _expected_model_settings(settings, scenario)
    if mismatch:
        return mismatch
    required_models = set()
    if scenario in {"embedding-load", "both-loaded", "warm-embedding", "concurrency-2", "ingestion-embedding"}:
        required_models.add("embedding")
    if scenario in {"reranker-load", "both-loaded", "warm-reranking", "concurrency-2"}:
        required_models.add("reranker")
    cache = {
        "embedding": _cache_snapshot(EMBEDDING_MODEL, EMBEDDING_REVISION) if "embedding" in required_models else None,
        "reranker": _cache_snapshot(RERANKER_MODEL, RERANKER_REVISION) if "reranker" in required_models else None,
    }
    if any(cache[name] is not None and not cache[name]["exact_revision_present"] for name in required_models):
        return {"status": "ENVIRONMENT_GATE", "reason": "MODEL_CACHE_MISSING", "scenario": scenario,
                "model_cache": cache, "available_ram_bytes": ram["available_ram_bytes"],
                "configured_safety_threshold_bytes": threshold}
    context = collect_profile_context()
    selected = select_fixtures() if scenario != "baseline" else {}
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        os.environ[name] = "1"
    real_execution = workload is None
    if scenario in {"embedding-load", "reranker-load"} and not child and real_execution:
        result = run_fresh_process_repetitions(scenario)
    else:
        result = (workload or _provider_workload)(scenario, selected)
    if result.get("status") == "ENVIRONMENT_GATE":
        return {**result, "scenario": scenario}
    return {"schema_version": "step8.3-profile/1.0", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            **context, "scenario": scenario, "scenario_result": result, "fixture_manifest": selected,
            "real_provider_measurement": real_execution,
            "parameters": {"min_available_ram_gib_safety_guard": min_available_ram_gib,
                           "rss_sampling_interval_ms": 50, "warm_embedding_warmups": 5,
                           "warm_embedding_samples": 30, "warm_reranking_warmups": 3,
                           "warm_reranking_samples": 30, "reranker_candidate_count": 20,
                           "concurrency_pair_repetitions": 10, "ingestion_embedding_target_inputs": 64},
            "memory": {key: value for key, value in result.items() if "rss" in key},
            "environment_gate": "PASSED", "available_ram_bytes_before_provider_construction": ram["available_ram_bytes"],
            "configured_safety_threshold_bytes": threshold, "offline_environment": {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}}


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def collect_profile_context() -> dict[str, Any]:
    """Collect scenario metadata after the RAM gate but before provider construction."""
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.core.config import get_settings

    settings = get_settings()
    ram = memory_state()
    try:
        ps = _psutil()
        physical_cores, logical_cores = ps.cpu_count(logical=False), ps.cpu_count(logical=True)
    except RuntimeError:
        physical_cores, logical_cores = None, os.cpu_count()
    return {
        "git_commit": _git_commit(),
        "environment": {
            "os": platform.system(), "release": platform.release(), "architecture": platform.machine(),
            "platform": platform.platform(), "cpu_model": _cpu_model(), "physical_cores": physical_cores,
            "logical_cores": logical_cores, **ram, "python_version": platform.python_version(),
            "package_versions": {name: package_version(name) for name in
                                  ("sentence-transformers", "transformers", "torch", "numpy", "psutil")},
        },
        "models": {
            "embedding": {
                "provider": "SentenceTransformerEmbeddingProvider", "model_name": settings.embedding_model_name,
                "revision": settings.embedding_model_revision, "requested_device": settings.embedding_device,
                "batch_size": settings.embedding_batch_size, "dimensions": 1024,
                "normalize_embeddings": settings.embedding_normalize, "input_version": settings.embedding_input_version,
                "loading": "lazy on first embed_documents/embed_query use",
            },
            "reranker": {
                "provider": "TransformersRerankerProvider", "model_name": settings.reranker_model_name,
                "revision": settings.reranker_model_revision, "requested_device": settings.reranker_device,
                "batch_size": settings.reranker_batch_size, "top_k": settings.reranker_top_k,
                "candidate_pool_size": settings.rag_retrieval_candidate_k, "input_version": settings.reranker_input_version,
                "loading": "lazy on first pair validation/scoring",
            },
        },
    }


def _write_json(path: Path | None, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(serialized, end="")
        return
    destination = path if path.is_absolute() else REPO_ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialized, encoding="utf-8")
    print(json.dumps({"status": payload.get("status", payload.get("environment_gate", "UNKNOWN")), "output": str(destination)}))


def _read_profile_input(path: Path) -> dict[str, Any]:
    source = path if path.is_absolute() else REPO_ROOT / path
    return json.loads(source.read_text(encoding="utf-8"))


def _canonical_memory_sections(baseline: dict[str, Any], embedding_load: dict[str, Any],
                              reranker_load: dict[str, Any], both_loaded: dict[str, Any]) -> dict[str, Any]:
    """Project scenario RSS into the four explicit canonical memory sections."""
    for name, result, required in (
        ("baseline", baseline, ("baseline_rss_bytes", "steady_rss_bytes")),
        ("both-loaded", both_loaded, ("steady_rss_bytes", "peak_rss_bytes")),
    ):
        if any(not isinstance(result.get(field), int) for field in required):
            raise ValueError(f"{name} is missing required memory measurements")
    return {
        "baseline": {key: baseline[key] for key in ("baseline_rss_bytes", "steady_rss_bytes", "peak_rss_bytes")
                     if baseline.get(key) is not None},
        "embedding_only": {"steady_rss_samples_bytes": embedding_load["steady_rss_samples_bytes"],
                           "median_steady_rss_bytes": embedding_load["median_steady_rss_bytes"],
                           "peak_rss_samples_bytes": embedding_load["peak_rss_samples_bytes"],
                           "max_observed_peak_rss_bytes": embedding_load["max_observed_peak_rss_bytes"]},
        "reranker_only": {"steady_rss_samples_bytes": reranker_load["steady_rss_samples_bytes"],
                          "median_steady_rss_bytes": reranker_load["median_steady_rss_bytes"],
                          "peak_rss_samples_bytes": reranker_load["peak_rss_samples_bytes"],
                          "max_observed_peak_rss_bytes": reranker_load["max_observed_peak_rss_bytes"]},
        "both_loaded": {key: both_loaded[key] for key in ("steady_rss_bytes", "peak_rss_bytes")},
    }


def aggregate_profile(input_paths: list[Path]) -> dict[str, Any]:
    """Create canonical D-004 evidence only from complete real scenario outputs."""
    evidence: dict[str, dict[str, Any]] = {}
    for path in input_paths:
        item = _read_profile_input(path)
        scenario = item.get("scenario")
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario evidence: {path}")
        if scenario in evidence:
            raise ValueError(f"duplicate scenario evidence: {scenario}")
        if item.get("real_provider_measurement") is not True or item.get("environment_gate") != "PASSED":
            raise ValueError(f"{scenario} is not marked as a real provider measurement")
        result = item.get("scenario_result")
        if not isinstance(result, dict) or result.get("status") != "MEASURED":
            raise ValueError(f"{scenario} does not contain a complete measured result")
        evidence[scenario] = item
    missing = set(REQUIRED_PROFILE_SCENARIOS) - set(evidence)
    if missing:
        raise ValueError(f"missing required scenario evidence: {', '.join(sorted(missing))}")

    for scenario in ("embedding-load", "reranker-load"):
        result = evidence[scenario]["scenario_result"]
        if (result.get("fresh_process_repetitions") != 3 or len(result.get("raw_samples_ms", [])) != 3
                or len(result.get("sample_scenarios", [])) != 3):
            raise ValueError(f"{scenario} must contain exactly three fresh-process samples")
        if (len(result.get("steady_rss_samples_bytes", [])) != 3
                or len(result.get("peak_rss_samples_bytes", [])) != 3
                or result.get("median_steady_rss_bytes") is None
                or result.get("max_observed_peak_rss_bytes") is None):
            raise ValueError(f"{scenario} must preserve all three steady and peak RSS samples")
        if (result["median_steady_rss_bytes"] != int(statistics.median(result["steady_rss_samples_bytes"]))
                or result["max_observed_peak_rss_bytes"] != max(result["peak_rss_samples_bytes"])):
            raise ValueError(f"{scenario} cold memory summary does not match its raw RSS samples")
        for index, child in enumerate(result["sample_scenarios"]):
            child_result = child.get("scenario_result", {})
            if (child.get("real_provider_measurement") is not True
                    or child_result.get("cold_first_use_ms") != result["raw_samples_ms"][index]
                    or child_result.get("steady_rss_bytes") != result["steady_rss_samples_bytes"][index]
                    or child_result.get("peak_rss_bytes") != result["peak_rss_samples_bytes"][index]):
                raise ValueError(f"{scenario} raw child timing/RSS does not match the parent summary")
    concurrency = evidence["concurrency-2"]["scenario_result"]
    if concurrency.get("pair_repetitions") != 10 or concurrency.get("arrivals_per_pair") != 2 or len(concurrency.get("pairs", [])) != 10:
        raise ValueError("concurrency-2 evidence must contain 10 measured pairs of two arrivals")
    for pair in concurrency["pairs"]:
        for request in ("a", "b"):
            start = pair.get(f"request_{request}_start_offset_ms")
            complete = pair.get(f"request_{request}_complete_offset_ms")
            execution = pair.get(f"request_{request}_execution_ms")
            latency = pair.get(f"request_{request}_latency_ms")
            if None in (start, complete, execution, latency) or execution != complete - start or latency != complete:
                raise ValueError("concurrency-2 latency/execution timestamps are incomplete or inconsistent")
        if pair.get("pair_makespan_ms") != max(pair["request_a_complete_offset_ms"], pair["request_b_complete_offset_ms"]):
            raise ValueError("concurrency-2 pair makespan is inconsistent with completion timestamps")
        overlap = derive_overlap_observed(pair["request_a_start_offset_ms"], pair["request_a_complete_offset_ms"],
                                          pair["request_b_start_offset_ms"], pair["request_b_complete_offset_ms"])
        if pair.get("overlap_observed") is not overlap or not isinstance(pair.get("errors"), dict):
            raise ValueError("concurrency-2 overlap/errors are missing or not derived from timestamps")
    ingestion = evidence["ingestion-embedding"]["scenario_result"]
    if ingestion.get("errors") or ingestion.get("input_count", 0) <= 0:
        raise ValueError("ingestion embedding evidence is incomplete or contains errors")
    warm_embedding = evidence["warm-embedding"]["scenario_result"]
    warm_reranking = evidence["warm-reranking"]["scenario_result"]
    if warm_embedding.get("latency", {}).get("count") != 30 or warm_reranking.get("latency", {}).get("count") != 30:
        raise ValueError("warm latency scenarios must each contain 30 measured samples")

    baseline = evidence["baseline"]
    baseline_result = baseline["scenario_result"]
    both_loaded = evidence["both-loaded"]["scenario_result"]
    embedding_load = evidence["embedding-load"]["scenario_result"]
    reranker_load = evidence["reranker-load"]["scenario_result"]
    memory_sections = _canonical_memory_sections(baseline_result, embedding_load, reranker_load, both_loaded)
    context = baseline
    results = {name.replace("-", "_"): item["scenario_result"] for name, item in evidence.items()}
    models = context.get("models", {})
    if models.get("embedding", {}).get("model_name") != EMBEDDING_MODEL or models.get("embedding", {}).get("revision") != EMBEDDING_REVISION:
        raise ValueError("embedding identity does not match the frozen D-004 subject")
    if models.get("reranker", {}).get("model_name") != RERANKER_MODEL or models.get("reranker", {}).get("revision") != RERANKER_REVISION:
        raise ValueError("reranker identity does not match the frozen D-004 subject")
    return {
        "schema_version": "step8.3-d004-profile/1.0",
        "status": "COMPLETE_REAL_MEASUREMENTS",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": context.get("git_commit"),
        "environment": context.get("environment"),
        "models": models,
        "fixture_manifest": evidence["warm-embedding"].get("fixture_manifest"),
        "parameters": {name: item.get("parameters") for name, item in evidence.items()},
        "memory": memory_sections,
        "cold_load": {"embedding": results["embedding_load"], "reranker": results["reranker_load"]},
        "warm_embedding": results["warm_embedding"],
        "warm_reranking": results["warm_reranking"],
        "both_loaded_workload": results["both_loaded"],
        "concurrency_2": results["concurrency_2"],
        "ingestion_embedding": results["ingestion_embedding"],
        "baseline": results["baseline"],
        "limitations": ["environment-specific per-process measurements", "RSS does not include all accelerator VRAM",
                         "no production provider, deployment, worker, or hosting decision is made"],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.aggregate:
        profile = aggregate_profile(args.aggregate)
        _write_json(args.output, profile)
        return 0
    if args.preflight:
        result = collect_preflight()
        minimum = int(args.min_available_ram_gib * (1024 ** 3))
        gate = resource_gate("all-real-model-scenarios", available_ram_bytes=result["environment"]["available_ram_bytes"], threshold_bytes=minimum)
        result["benchmark_gate"] = gate or {"status": "READY", "scenario": "all-real-model-scenarios", "available_ram_bytes": result["environment"]["available_ram_bytes"], "configured_safety_threshold_bytes": minimum}
        _write_json(args.output, result)
        return 0
    result = run_scenario(args.scenario, min_available_ram_gib=args.min_available_ram_gib, child=args._child)
    _write_json(args.output, result)
    return 0 if result.get("environment_gate") == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
