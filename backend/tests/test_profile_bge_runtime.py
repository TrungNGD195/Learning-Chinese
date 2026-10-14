from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "profile_bge_runtime.py"
SPEC = importlib.util.spec_from_file_location("profile_bge_runtime", SCRIPT)
profiler = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = profiler
SPEC.loader.exec_module(profiler)


def test_cli_parsing_preflight_and_safety_threshold():
    args = profiler.parse_args(["--preflight", "--min-available-ram-gib", "2.5"])
    assert args.preflight is True
    assert args.min_available_ram_gib == 2.5
    assert profiler.parse_args(["--scenario", "warm-embedding"]).scenario == "warm-embedding"
    aggregate_args = profiler.parse_args(["--aggregate", "a.json", "b.json", "--output", "profile.json"])
    assert [path.name for path in aggregate_args.aggregate] == ["a.json", "b.json"]
    assert aggregate_args.output.name == "profile.json"
    with pytest.raises(SystemExit):
        profiler.parse_args(["--scenario", "warm-embedding", "--min-available-ram-gib", "-1"])


def test_memory_guard_precedes_fake_provider_construction(monkeypatch):
    events = []
    monkeypatch.setattr(profiler, "memory_state", lambda: {"total_ram_bytes": 10, "available_ram_bytes": 4})

    def fake_workload(scenario, selection):
        events.append("provider_construction")
        return {"scenario": scenario, "status": "FAKE_TEST_ONLY"}

    result = profiler.run_scenario("embedding-load", min_available_ram_gib=1, workload=fake_workload)
    assert result["reason"] == "INSUFFICIENT_AVAILABLE_RAM"
    assert result["scenario"] == "embedding-load"
    assert result["available_ram_bytes"] == 4
    assert result["configured_safety_threshold_bytes"] == 1024**3
    assert events == []
    assert not any(key.endswith("ms") or "rss" in key for key in result)


def test_low_memory_scenario_has_no_measurement_fields(monkeypatch):
    monkeypatch.setattr(profiler, "memory_state", lambda: {"total_ram_bytes": 100, "available_ram_bytes": 9})
    result = profiler.run_scenario("reranker-load", min_available_ram_gib=1, workload=lambda *_: pytest.fail("must gate"))
    assert result == {
        "status": "ENVIRONMENT_GATE", "reason": "INSUFFICIENT_AVAILABLE_RAM",
        "available_ram_bytes": 9, "configured_safety_threshold_bytes": 1024**3,
        "scenario": "reranker-load",
    }
    assert "first_use_ms" not in result and "peak_rss_bytes" not in result


def test_missing_exact_cache_stops_before_provider_workload(monkeypatch):
    monkeypatch.setattr(profiler, "memory_state", lambda: {"total_ram_bytes": 10**12, "available_ram_bytes": 10**12})
    monkeypatch.setattr(profiler, "_cache_snapshot", lambda _name, revision: {"exact_revision_present": False, "revision": revision})
    result = profiler.run_scenario("embedding-load", workload=lambda *_: pytest.fail("cache gate must precede provider"))
    assert result["status"] == "ENVIRONMENT_GATE"
    assert result["reason"] == "MODEL_CACHE_MISSING"
    assert result["scenario"] == "embedding-load"
    assert result["model_cache"]["embedding"]["exact_revision_present"] is False
    assert result["model_cache"]["reranker"] is None
    assert "latency" not in result and "rss" not in result


def test_nearest_rank_percentile_and_sample_aggregation():
    assert profiler.nearest_rank_percentile([8, 1, 3, 2, 4, 5, 6, 7, 9, 10], 50) == 5
    assert profiler.nearest_rank_percentile([8, 1, 3, 2, 4, 5, 6, 7, 9, 10], 95) == 10
    assert profiler.aggregate_samples([1, 2, 3, 4])["p50_ms"] == 2.5
    rss = profiler.steady_rss_summary([1, 2, 3, 4], window=2)
    assert rss["baseline_rss_bytes"] == 1
    assert rss["steady_rss_bytes"] == 3
    assert rss["peak_rss_bytes"] == 4
    with pytest.raises(ValueError):
        profiler.nearest_rank_percentile([], 95)


def test_exact_cache_revision_detection_without_loading(monkeypatch):
    tmp_path = Path(__file__).parent / ".step83-cache-test"
    model = tmp_path / "models--BAAI--bge-m3" / "snapshots" / profiler.EMBEDDING_REVISION
    weights = model / "model.safetensors"
    config = model / "config.json"
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    model.mkdir(parents=True)
    try:
        config.write_text("{}", encoding="utf-8")
        weights.write_bytes(b"fixture-marker")
        result = profiler._cache_snapshot(profiler.EMBEDDING_MODEL, profiler.EMBEDDING_REVISION)
        assert result["model_cache_present"] is True
        assert result["exact_revision_present"] is True
        assert result["revision"] == profiler.EMBEDDING_REVISION
        missing = profiler._cache_snapshot(profiler.RERANKER_MODEL, profiler.RERANKER_REVISION)
        assert missing["model_cache_present"] is False
        assert missing["exact_revision_present"] is False
    finally:
        weights.unlink(missing_ok=True)
        config.unlink(missing_ok=True)
        model.rmdir()
        model.parent.rmdir()
        model.parent.parent.rmdir()
        tmp_path.rmdir()


def test_cuda_capability_uses_torch_runtime_checks(monkeypatch):
    calls = []
    cuda = types.SimpleNamespace(
        is_available=lambda: calls.append("cuda") or True,
        device_count=lambda: 1,
        get_device_name=lambda index: "fixture CUDA device",
        get_device_properties=lambda index: types.SimpleNamespace(total_memory=1234),
    )
    torch = types.SimpleNamespace(__version__="test", cuda=cuda,
                                  backends=types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: False)))
    monkeypatch.setitem(sys.modules, "torch", torch)
    result = profiler._runtime_capabilities()
    assert calls == ["cuda"]
    assert result["cuda_available"] is True
    assert result["cuda_devices"] == [{"index": 0, "name": "fixture CUDA device", "total_memory_bytes": 1234}]
    assert result["mps_available"] is False


def test_fixture_selection_is_deterministic_and_uses_unique_real_locators():
    first = profiler.select_fixtures()
    second = profiler.select_fixtures()
    assert first == second
    assert first["dataset_version"] == "v0.8.0"
    assert first["selected_case_count"] == 10
    assert first["selected_case_ids"] == sorted(first["selected_case_ids"])
    assert first["rerank_candidate_count"] == 20
    assert len(set(first["selected_stable_locators"])) == 20
    assert first["ingestion_input_count"] == first["unique_fixture_block_count"]
    assert first["ingestion_input_count"] < first["ingestion_target_count"]
    assert all(row["required_evidence_locators"] for row in first["selected_cases"])


def test_fixture_formatting_uses_unique_repo_content_without_padding():
    from app.ai.embeddings.formatter import EmbeddingInputFormatter

    blocks, _cases, _manifest = profiler.load_fixture_data()
    contexts = profiler.build_embedding_contexts(blocks)
    formatted = [EmbeddingInputFormatter().format(context) for context in contexts]
    candidates = profiler.build_rerank_candidates(sorted(
        blocks, key=lambda block: block["stable_locator"]
    )[:20])
    passages = [candidate.content for candidate in candidates]
    assert len(contexts) == 26
    assert len(set(formatted)) == len(formatted)
    assert len(candidates) == 20
    assert len({candidate.locator_metadata["stable_locator"] for candidate in candidates}) == 20
    assert len(set(passages)) == 20
    assert all(formatted_text.strip() for formatted_text in formatted)
    assert all(passages)


def test_json_evidence_serialization_is_reproducible():
    target = Path(__file__).parent / ".step83-serialization-test.json"
    payload = {"schema_version": "test", "model_loading_performed": False, "message": "中文"}
    try:
        profiler._write_json(target, payload)
        assert json.loads(target.read_text(encoding="utf-8")) == payload
        assert "中文" in target.read_text(encoding="utf-8")
    finally:
        target.unlink(missing_ok=True)


def test_preflight_does_not_import_provider_modules(monkeypatch):
    # collect_preflight only asks Settings/config, runtime capability, metadata and cache helpers.
    monkeypatch.setattr(profiler, "memory_state", lambda: {"total_ram_bytes": 1000, "available_ram_bytes": 100})
    monkeypatch.setattr(profiler, "_runtime_capabilities", lambda: {"torch_available": False, "cuda_available": None, "cuda_devices": [], "mps_available": None})
    monkeypatch.setattr(profiler, "_cache_snapshot", lambda name, revision: {"model_cache_present": False, "exact_revision_present": False, "revision": revision})
    monkeypatch.setattr(profiler, "package_version", lambda name: "test-version" if name != "psutil" else None)
    monkeypatch.setattr(profiler.subprocess, "run", lambda *a, **k: types.SimpleNamespace(stdout="commit\n"))
    # Use valid test settings without printing or copying any secret values.
    from app.core.config import Settings
    settings = Settings(app_env="test", debug=False, test_database_url="postgresql+psycopg://test:test@localhost/testdb", secret_key="test-only")
    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
    forbidden = {"app.ai.embeddings.sentence_transformer_provider", "app.ai.reranking.transformers_provider"}
    for module_name in forbidden:
        monkeypatch.delitem(sys.modules, module_name, raising=False)
    monkeypatch.setattr(profiler, "_cpu_model", lambda: "test cpu")
    result = profiler.collect_preflight()
    assert result["model_loading_performed"] is False
    assert result["inference_performed"] is False
    assert result["network_access_performed"] is False
    assert forbidden.isdisjoint(sys.modules)
    assert result["models"]["embedding"]["revision"] == profiler.EMBEDDING_REVISION
    assert result["models"]["reranker"]["revision"] == profiler.RERANKER_REVISION


def test_offline_flags_are_set_before_fake_workload(monkeypatch):
    monkeypatch.setattr(profiler, "memory_state", lambda: {"total_ram_bytes": 100, "available_ram_bytes": 10**12})
    monkeypatch.setattr(profiler, "_cache_snapshot", lambda _name, revision: {"exact_revision_present": True, "revision": revision})
    monkeypatch.setattr(profiler, "collect_profile_context", lambda: {"environment": {}, "models": {}})
    monkeypatch.setattr(profiler, "select_fixtures", lambda: {"selected_case_ids": [], "selected_stable_locators": []})
    seen = {}

    def workload(scenario, selection):
        seen.update(HF=os.environ.get("HF_HUB_OFFLINE"), TRANSFORMERS=os.environ.get("TRANSFORMERS_OFFLINE"))
        return {"scenario": scenario, "status": "FAKE_TEST_ONLY"}

    result = profiler.run_scenario("embedding-load", min_available_ram_gib=0, workload=workload)
    assert result["environment_gate"] == "PASSED"
    assert seen == {"HF": "1", "TRANSFORMERS": "1"}


def test_fake_provider_workload_is_identified_as_non_evidence(monkeypatch):
    monkeypatch.setattr(profiler, "memory_state", lambda: {"total_ram_bytes": 100, "available_ram_bytes": 10**12})
    monkeypatch.setattr(profiler, "_cache_snapshot", lambda _name, revision: {"exact_revision_present": True, "revision": revision})
    monkeypatch.setattr(profiler, "collect_profile_context", lambda: {"environment": {}, "models": {}})
    monkeypatch.setattr(profiler, "select_fixtures", lambda: {"selected_case_ids": [], "selected_stable_locators": []})
    result = profiler.run_scenario("warm-embedding", min_available_ram_gib=0,
                                  workload=lambda *_: {"status": "FAKE_TEST_ONLY", "latency_ms": 1})
    assert result["scenario_result"]["status"] == "FAKE_TEST_ONLY"
    assert result["environment_gate"] == "PASSED"
    assert "official_evidence" not in result


def test_windows_memory_fallback_collects_physical_and_available_ram(monkeypatch):
    class Status:
        dwLength = 0
        dwMemoryLoad = 0
        ullTotalPhys = 800
        ullAvailPhys = 200
        ullTotalPageFile = 0
        ullAvailPageFile = 0
        ullTotalVirtual = 0
        ullAvailVirtual = 0
        ullAvailExtendedVirtual = 0

    class FakeKernel:
        @staticmethod
        def GlobalMemoryStatusEx(ptr):
            ptr.ullTotalPhys = 800
            ptr.ullAvailPhys = 200
            return True

    class FakeStructure:
        def __init_subclass__(cls):
            for name, _field_type in cls._fields_:
                setattr(cls, name, 0)

    fake_ctypes = types.SimpleNamespace(Structure=FakeStructure, c_ulong=int, c_ulonglong=int, sizeof=lambda _: 10,
                                        byref=lambda value: value, windll=types.SimpleNamespace(kernel32=FakeKernel()))
    # Exercise only portable fallback if psutil cannot be loaded.
    monkeypatch.setattr(profiler, "_psutil", lambda: (_ for _ in ()).throw(RuntimeError("missing")))
    monkeypatch.setattr(profiler.os, "name", "nt")
    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)
    result = profiler.memory_state()
    assert result == {"total_ram_bytes": 800, "available_ram_bytes": 200}


def test_rss_sampler_uses_process_rss(monkeypatch):
    reads = []

    class Process:
        def __init__(self, pid):
            assert pid == os.getpid()

        def memory_info(self):
            reads.append(2048)
            return types.SimpleNamespace(rss=2048)

    fake = types.SimpleNamespace(Process=Process)
    monkeypatch.setitem(sys.modules, "psutil", fake)
    sampler = profiler.RssSampler(interval_seconds=0.001)
    with sampler:
        import time
        time.sleep(0.01)
    assert reads
    assert sampler.peak_rss_bytes == 2048


def test_profile_json_gate_never_serializes_fake_measurements():
    gate = profiler.resource_gate("both-loaded", available_ram_bytes=1, threshold_bytes=2)
    assert gate["status"] == "ENVIRONMENT_GATE"
    assert "latency" not in gate and "rss" not in gate and "throughput" not in gate


def test_provider_identity_is_exported_with_explicit_revision_name():
    from app.ai.embeddings.schemas import EmbeddingProviderIdentity

    provider = types.SimpleNamespace(identity=EmbeddingProviderIdentity(
        provider="LOCAL", provider_version="sentence-transformers/6.1.0", model_name=profiler.EMBEDDING_MODEL,
        model_version=profiler.EMBEDDING_REVISION, dimensions=1024,
        embedding_input_version="v1", normalize_embeddings=True,
    ))
    identity = profiler._provider_identity(provider)
    assert identity["model_name"] == profiler.EMBEDDING_MODEL
    assert identity["model_revision"] == profiler.EMBEDDING_REVISION
    assert "model_version" not in identity


def test_concurrency_pair_records_shared_arrival_and_request_offsets():
    ticks = iter(float(value) for value in range(20))
    pair = profiler.run_concurrency_pair(lambda: "a", lambda: "b", clock=lambda: next(ticks),
                                         wall_clock=lambda: profiler.datetime(2026, 1, 1, tzinfo=profiler.timezone.utc))
    assert pair["common_arrival"] == "2026-01-01T00:00:00+00:00"
    assert pair["request_a_start_offset_ms"] >= 0
    assert pair["request_a_complete_offset_ms"] > pair["request_a_start_offset_ms"]
    assert pair["request_b_start_offset_ms"] >= 0
    assert pair["request_b_complete_offset_ms"] > pair["request_b_start_offset_ms"]
    assert pair["pair_makespan_ms"] == max(pair["request_a_complete_offset_ms"], pair["request_b_complete_offset_ms"])
    assert set(pair["errors"].values()) == {None}


def test_concurrency_overlap_is_derived_from_timestamp_intervals():
    assert profiler.derive_overlap_observed(0, 10, 9, 15) is True
    assert profiler.derive_overlap_observed(0, 10, 10, 15) is False


def test_serialized_concurrency_latency_includes_wait_from_common_arrival():
    # arrival=0; A runs [0,100]; B waits, then runs [100,200].
    ticks = iter([0.0, 0.0, 0.1, 0.1, 0.2])
    pair = profiler.run_concurrency_pair(lambda: None, lambda: None, clock=lambda: next(ticks),
        wall_clock=lambda: profiler.datetime(2026, 1, 1, tzinfo=profiler.timezone.utc))
    assert pair["request_a_execution_ms"] == pytest.approx(100)
    assert pair["request_a_latency_ms"] == pytest.approx(100)
    assert pair["request_b_execution_ms"] == pytest.approx(100)
    assert pair["request_b_latency_ms"] == pytest.approx(200)
    assert pair["pair_makespan_ms"] == pytest.approx(200)
    assert pair["request_b_latency_ms"] > pair["request_b_execution_ms"]
    assert pair["overlap_observed"] is False


def test_concurrency_has_two_warmup_workloads_before_ten_measured_pairs():
    events = []
    def embed(query): events.append(("embed", query))
    def rerank(query, _candidates): events.append(("rerank", query))
    def pair_runner(request_a, request_b):
        events.append("pair")
        request_a(); request_b()
        return {"overlap_observed": False}
    result = profiler.measure_concurrency_2(["qa", "qb"], [], embed, rerank, pair_runner=pair_runner)
    assert events[:4] == [("embed", "qa"), ("rerank", "qa"), ("embed", "qb"), ("rerank", "qb")]
    assert events[4] == "pair" and events.count("pair") == 10
    assert result["warmup_workloads"] == 2 and result["pair_repetitions"] == 10
    assert result["arrivals_per_pair"] == 2


def test_ingestion_preparation_and_warmup_are_outside_timer_and_full_set_is_measured():
    events = []
    class Formatter:
        def format(self, item):
            events.append(("format", item))
            return item
    def embed(batch, *, batch_size):
        events.append(("embed", list(batch), batch_size))
        return [[1.0] for _ in batch]
    times = iter([10.0, 12.0])
    result = profiler.measure_ingestion_embedding(["a", "b", "c"], embed, 2,
        context_builder=lambda blocks: list(blocks), formatter_factory=Formatter, clock=lambda: next(times))
    assert events[:3] == [("format", "a"), ("format", "b"), ("format", "c")]
    assert events[3] == ("embed", ["a", "b"], 2)  # warmup precedes first timer read
    assert events[4:] == [("embed", ["a", "b"], 2), ("embed", ["c"], 2)]
    assert result["input_count"] == 3 and result["measured_batch_count"] == 2
    assert result["warmup_batch_count"] == 1 and result["elapsed_seconds"] == 2.0
    assert result["total_chars"] == 3 and result["total_utf8_bytes"] == 3


def test_both_loaded_timing_starts_after_both_first_use_operations():
    events = []
    times = iter([0, 100, 200, 300, 400, 405])
    result = profiler.measure_both_loaded_workload(
        lambda: events.append("embedding_first"), lambda: events.append("reranker_first"),
        lambda: events.append("warm_embed"), lambda: events.append("warm_rerank"), clock=lambda: next(times))
    assert events == ["embedding_first", "reranker_first", "warm_embed", "warm_rerank"]
    assert result == {"embedding_cold_first_use_ms": 100000, "reranker_cold_first_use_ms": 100000,
                      "both_loaded_workload_ms": 5000}


@pytest.mark.parametrize("scenario", ["embedding-load", "reranker-load"])
def test_cold_load_uses_three_fresh_processes_and_preserves_raw_samples(scenario):
    calls = []
    samples = [10.0, 30.0, 20.0]
    def fake_runner(command, **_kwargs):
        calls.append(command)
        index = len(calls) - 1
        child = {"environment_gate": "PASSED", "test_fixture_only": True,
                 "scenario_result": {"status": "MEASURED", "cold_first_use_ms": samples[index],
                                     "steady_rss_bytes": 1000 + index, "peak_rss_bytes": 2000 + index}}
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(child), stderr="")
    result = profiler.run_fresh_process_repetitions(scenario, runner=fake_runner, test_only_fixture=True)
    assert len(calls) == 3
    assert all("--_child" in command for command in calls)
    assert result["raw_samples_ms"] == samples and result["median_ms"] == 20.0
    assert result["fresh_process_repetitions"] == 3
    assert result["steady_rss_samples_bytes"] == [1000, 1001, 1002]
    assert result["median_steady_rss_bytes"] == 1001
    assert result["peak_rss_samples_bytes"] == [2000, 2001, 2002]
    assert result["max_observed_peak_rss_bytes"] == 2002
    assert len(result["sample_scenarios"]) == 3
    assert result["status"] == "TEST_FIXTURE_ONLY"
    assert result["real_provider_measurement"] is False


def test_cold_load_stops_cleanly_when_child_hits_environment_gate():
    def fake_runner(_command, **_kwargs):
        child = {"status": "ENVIRONMENT_GATE", "reason": "INSUFFICIENT_AVAILABLE_RAM", "scenario": "embedding-load"}
        return types.SimpleNamespace(returncode=2, stdout=json.dumps(child), stderr="")
    result = profiler.run_fresh_process_repetitions("embedding-load", runner=fake_runner)
    assert result["status"] == "ENVIRONMENT_GATE"
    assert result["reason"] == "INSUFFICIENT_AVAILABLE_RAM"
    assert result["repetitions_completed"] == 0


def test_canonical_memory_sections_are_explicit_and_nonempty():
    memory = profiler._canonical_memory_sections(
        {"baseline_rss_bytes": 500, "steady_rss_bytes": 510, "peak_rss_bytes": 520},
        {"steady_rss_samples_bytes": [1000, 1100, 1200], "median_steady_rss_bytes": 1100,
         "peak_rss_samples_bytes": [2000, 2100, 2200], "max_observed_peak_rss_bytes": 2200},
        {"steady_rss_samples_bytes": [3000, 3100, 3200], "median_steady_rss_bytes": 3100,
         "peak_rss_samples_bytes": [4000, 4100, 4200], "max_observed_peak_rss_bytes": 4200},
        {"steady_rss_bytes": 700, "peak_rss_bytes": 750},
    )
    assert set(memory) == {"baseline", "embedding_only", "reranker_only", "both_loaded"}
    assert memory["baseline"] == {"baseline_rss_bytes": 500, "steady_rss_bytes": 510, "peak_rss_bytes": 520}
    assert memory["embedding_only"]["steady_rss_samples_bytes"] == [1000, 1100, 1200]
    assert memory["embedding_only"]["median_steady_rss_bytes"] == 1100
    assert memory["embedding_only"]["peak_rss_samples_bytes"] == [2000, 2100, 2200]
    assert memory["embedding_only"]["max_observed_peak_rss_bytes"] == 2200
    assert memory["reranker_only"]["steady_rss_samples_bytes"] == [3000, 3100, 3200]
    assert memory["reranker_only"]["median_steady_rss_bytes"] == 3100
    assert memory["reranker_only"]["peak_rss_samples_bytes"] == [4000, 4100, 4200]
    assert memory["reranker_only"]["max_observed_peak_rss_bytes"] == 4200
    assert memory["both_loaded"] == {"steady_rss_bytes": 700, "peak_rss_bytes": 750}


def test_aggregate_refuses_incomplete_or_environment_gated_evidence():
    test_dir = Path(__file__).parent / ".step83-aggregate-test"
    test_dir.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="missing required"):
        profiler.aggregate_profile([])
    gate = test_dir / "gate.json"
    gate.write_text(json.dumps({"scenario": "baseline", "status": "ENVIRONMENT_GATE"}), encoding="utf-8")
    with pytest.raises(ValueError, match="not marked as a real"):
        profiler.aggregate_profile([gate])
    gate.unlink(missing_ok=True)
    test_dir.rmdir()


def test_aggregate_rejects_fake_provider_measurements():
    test_dir = Path(__file__).parent / ".step83-aggregate-test"
    test_dir.mkdir(exist_ok=True)
    path = test_dir / "fake-baseline.json"
    path.write_text(json.dumps({"scenario": "baseline", "real_provider_measurement": False,
        "environment_gate": "PASSED", "scenario_result": {"status": "FAKE_TEST_ONLY"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="not marked as a real"):
        profiler.aggregate_profile([path])
    path.unlink(missing_ok=True)
    test_dir.rmdir()


def test_model_config_mismatch_blocks_before_provider_construction(monkeypatch):
    monkeypatch.setattr(profiler, "memory_state", lambda: {"total_ram_bytes": 10**12, "available_ram_bytes": 10**12})
    settings = types.SimpleNamespace(embedding_model_name="wrong-model", embedding_model_revision="wrong-rev",
        reranker_model_name=profiler.RERANKER_MODEL, reranker_model_revision=profiler.RERANKER_REVISION)
    monkeypatch.setattr("app.core.config.get_settings", lambda: settings)
    result = profiler.run_scenario("embedding-load", min_available_ram_gib=0,
                                   workload=lambda *_: pytest.fail("provider must not be constructed"))
    assert result == {"status": "ENVIRONMENT_GATE", "reason": "MODEL_CONFIG_MISMATCH", "scenario": "embedding-load",
                      "model": "embedding", "expected": {"model": profiler.EMBEDDING_MODEL, "revision": profiler.EMBEDDING_REVISION},
                      "actual": {"model": "wrong-model", "revision": "wrong-rev"}}


def test_baseline_runs_without_heavy_ram_gate_or_model_cache(monkeypatch):
    monkeypatch.setattr(profiler, "memory_state", lambda: {"total_ram_bytes": 10, "available_ram_bytes": 1})
    monkeypatch.setattr("app.core.config.get_settings", lambda: types.SimpleNamespace(
        embedding_model_name=profiler.EMBEDDING_MODEL, embedding_model_revision=profiler.EMBEDDING_REVISION,
        reranker_model_name=profiler.RERANKER_MODEL, reranker_model_revision=profiler.RERANKER_REVISION))
    monkeypatch.setattr(profiler, "collect_profile_context", lambda: {"models": {}, "environment": {}})
    result = profiler.run_scenario("baseline", workload=lambda *_: {"status": "MEASURED"})
    assert result["scenario"] == "baseline" and result["real_provider_measurement"] is False
    assert result["environment_gate"] == "PASSED"


def test_settings_mismatch_checks_each_scenario_model_scope():
    settings = types.SimpleNamespace(embedding_model_name=profiler.EMBEDDING_MODEL,
        embedding_model_revision=profiler.EMBEDDING_REVISION, reranker_model_name="wrong",
        reranker_model_revision="wrong")
    mismatch = profiler._expected_model_settings(settings, "warm-reranking")
    assert mismatch["model"] == "reranker"


def test_text_size_summary_reports_character_and_utf8_counts():
    result = profiler.text_size_summary(["a", "中"])
    assert result["characters"]["total"] == 2
    assert result["utf8_bytes"]["total"] == 4

