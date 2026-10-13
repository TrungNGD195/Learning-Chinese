from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from app.ai.embeddings.service import EmbeddingService
from app.ai.reranking.service import RerankingService
from app.ai.reranking.transformers_provider import TransformersRerankerProvider
from app.ai.retrieval.scopes import RetrievalScope, build_scope_filter
from app.ai.retrieval.service import SemanticRetrievalService
from app.ai.vector_storage.service import VectorStorageService
from app.core.config import Settings, get_settings
from app.database.models import EmbeddingProfile, KnowledgeSource, KnowledgeVersion
from app.evaluation.step73.evaluation import (
    DATASET, ROOT, attempt_metrics, evidence_groups, load_cases, metric_deltas, plan_attempts, threshold_sweep,
)
from app.evaluation.step73.fixtures import FIXTURE_ROOT, assert_evaluation_database, bootstrap
from app.ingestion.storage import LocalFileStorage


def _dump(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _candidate_row(candidate, locator_to_evidence: dict[str, list[str]]) -> dict:
    metadata = candidate.locator_metadata or {}
    locators = sorted(metadata.get("fixture_stable_locators", []))
    return {
        "chunk_id": str(candidate.chunk_id), "rank": candidate.rank,
        "chunk_index": candidate.chunk_index, "stable_locators": locators,
        "evidence_ids": sorted({eid for locator in locators for eid in locator_to_evidence.get(locator, [])}),
        "content": candidate.content, "content_type": candidate.content_type,
        "source_type": candidate.source_type,
        "source_id": str(candidate.source_lesson_id or candidate.source_document_id),
        "lesson_id": str(candidate.chunk_lesson_id) if candidate.chunk_lesson_id else None,
        "lesson_title": candidate.lesson_title, "document_title": candidate.document_title,
        "hsk_level_number": candidate.hsk_level_number,
        "section": candidate.section, "page_number": candidate.page_number,
        "retrieval_score": candidate.retrieval_score,
        "relevance_grade": 0, "matched_evidence_id": None, "scope_pass": True,
    }


def _candidate_in_scope(candidate, tier: str, lesson_id: UUID | None) -> bool:
    if tier == "CURRENT_LESSON":
        return (
            candidate.source_type == "LESSON"
            and candidate.source_document_id is None
            and candidate.source_lesson_id == lesson_id
            and candidate.chunk_lesson_id == lesson_id
        )
    if tier == "INTERNAL_KB":
        # Step 6.8-A's INTERNAL_KB policy is the unfiltered internal retrieval
        # scope: active Lesson knowledge plus approved/active Documents. V0's
        # source schema has no external source family; ACTIVE version/profile
        # gates are applied by SemanticRetrievalService's existing SQL path.
        if candidate.source_type == "LESSON":
            return (
                candidate.source_document_id is None
                and candidate.source_lesson_id is not None
                and candidate.chunk_lesson_id == candidate.source_lesson_id
            )
        if candidate.source_type == "DOCUMENT":
            return (
                candidate.source_document_id is not None
                and candidate.source_lesson_id is None
                and candidate.chunk_lesson_id is None
            )
    return False


def _retrieval_filter_for_tier(tier: str, lesson_id: UUID | None):
    """Use the exact shared production scope policy for evaluation attempts."""
    scope = RetrievalScope(tier)
    return build_scope_filter(
        scope,
        trusted_lesson_id=lesson_id if scope is RetrievalScope.CURRENT_LESSON else None,
    )


def _as_dict(candidate, locator_to_evidence: dict[str, list[str]]) -> dict:
    return _candidate_row(candidate, locator_to_evidence)


def _mean_metric(attempts: list[dict], key: str) -> float | None:
    values = [item[key] for item in attempts if item.get(key) is not None]
    return sum(values) / len(values) if values else None


def _aggregate(attempts: list[dict]) -> dict:
    positive = [item for item in attempts if item["label"] == "POSITIVE"]
    negative = [item for item in attempts if item["label"] == "NEGATIVE"]
    result = {"attempt_count": len(attempts), "positive_attempts": len(positive), "negative_attempts": len(negative)}
    for prefix, rows in (("semantic", positive), ("reranked", positive)):
        key_prefix = "semantic_" if prefix == "semantic" else "reranked_"
        field_prefix = "semantic_" if prefix == "semantic" else "reranked_"
        for metric in ("recall20", "recall5", "precision5", "ndcg5"):
            result[field_prefix + metric] = _mean_metric(rows, prefix + "_" + metric)
    result["scope_violations"] = sum(item["scope_violation"] for item in attempts)
    result["scope_violation_rate"] = result["scope_violations"] / len(attempts) if attempts else 0.0
    result["cases_with_scope_violation"] = len({item["case_id"] for item in attempts if item["scope_violation"]})
    result["negative_score_distributions"] = {
        "fallback_negatives": [item["max_rerank_score"] for item in negative if item["bucket"] == "INTERNAL_KB_FALLBACK"],
        "trusted_external_internal_negatives": [item["max_rerank_score"] for item in negative if item["bucket"] == "TRUSTED_EXTERNAL_FALLBACK"],
        "no_evidence_diagnostics": [item["max_rerank_score"] for item in negative if item["bucket"] == "NO_EVIDENCE_REFUSAL"],
    }
    result["reranker_deltas"] = {
        metric: (_mean_metric(positive, "delta_" + metric)) for metric in ("recall5", "precision5", "ndcg5")
    }
    return result


async def _evaluate_attempt(session, case: dict, plan: dict, settings: Settings,
                            embedding_provider, reranker_provider, lesson_ids: dict[str, str]) -> dict:
    tier = plan["tier"]
    lesson_locator = plan.get("lesson_locator")
    lesson_id = UUID(lesson_ids[lesson_locator]) if lesson_locator else None
    filters = _retrieval_filter_for_tier(tier, lesson_id)
    semantic = await SemanticRetrievalService(session, provider=embedding_provider,
                                               settings=settings).retrieve(case["question"], retrieval_filter=filters)
    semantic = semantic[:20]
    evidence_by_locator: dict[str, list[str]] = defaultdict(list)
    for evidence in [*case["required_evidence"], *case["acceptable_evidence"]]:
        if evidence.get("source_kind") == "INTERNAL_CHUNK":
            evidence_by_locator[evidence["stable_locator"]].append(evidence["evidence_id"])
    semantic_rows = [_as_dict(candidate, evidence_by_locator) for candidate in semantic]
    for row, candidate in zip(semantic_rows, semantic, strict=True):
        row["scope_pass"] = _candidate_in_scope(candidate, tier, lesson_id)
    rerank = RerankingService(provider=reranker_provider, settings=settings).rerank(case["question"], semantic)
    reranked_rows = [_as_dict(candidate, evidence_by_locator) for candidate in rerank.scored_candidates]
    for row, candidate in zip(reranked_rows, rerank.scored_candidates, strict=True):
        row["rerank_rank"] = candidate.rerank_rank
        row["rerank_score"] = candidate.rerank_score
        row["scope_pass"] = _candidate_in_scope(candidate, tier, lesson_id)
    semantic_metrics = attempt_metrics(semantic_rows, case, positive=plan["label"] == "POSITIVE")
    reranked_metrics = attempt_metrics(reranked_rows, case, positive=plan["label"] == "POSITIVE")
    delta = metric_deltas(semantic_metrics, reranked_metrics)
    violation = any(not row["scope_pass"] for row in [*semantic_rows, *reranked_rows])
    required_groups, _, _ = evidence_groups(case)
    return {
        "case_id": case["case_id"], "bucket": case["bucket"], "split": case["split"],
        "tier": tier, "label": plan["label"], "query": case["question"],
        "lesson_locator": lesson_locator, "required_evidence_groups": [sorted(g) for g in required_groups],
        "semantic_candidates": semantic_rows, "semantic_top20_metrics": {
            "recall20": semantic_metrics.get("recall20")},
        "semantic_top5_metrics": {k: semantic_metrics.get(k) for k in ("recall5", "precision5", "ndcg5")},
        "reranked_candidates": reranked_rows,
        "reranked_top5_metrics": {k: reranked_metrics.get(k) for k in ("recall5", "precision5", "ndcg5")},
        "reranker_deltas": delta,
        "max_rerank_score": max((row["rerank_score"] for row in reranked_rows[:5]), default=None),
        "max_relevant_rerank_score": max((row["rerank_score"] for row in reranked_rows[:5]
                                          if row["relevance_grade"] > 0), default=None),
        "scope_violation": violation,
        "semantic_recall20": semantic_metrics.get("recall20"),
        "semantic_recall5": semantic_metrics.get("recall5"),
        "semantic_precision5": semantic_metrics.get("precision5"),
        "semantic_ndcg5": semantic_metrics.get("ndcg5"),
        "reranked_recall5": reranked_metrics.get("recall5"),
        "reranked_precision5": reranked_metrics.get("precision5"),
        "reranked_ndcg5": reranked_metrics.get("ndcg5"),
        "delta_recall5": delta.get("recall5"), "delta_precision5": delta.get("precision5"),
        "delta_ndcg5": delta.get("ndcg5"),
    }


def _git_commit(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                              capture_output=True, check=True).stdout.strip()
    except Exception:
        return None


async def run_step73(*, reset: bool = False) -> dict:
    initial = get_settings()
    if initial.app_env != "test":
        raise RuntimeError("Step 7.3 only runs against APP_ENV=test")
    # This evaluation-local immutable settings copy allows null threshold only for this path.
    settings = initial.model_copy(update={"rag_evidence_calibration_mode": True, "rag_min_rerank_score": None})
    engine = create_async_engine(settings.effective_database_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    run_id = "step73-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    run_dir = ROOT / "evaluation/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    storage_root = settings.document_storage_root
    if not storage_root.is_absolute():
        storage_root = ROOT / "backend" / storage_root
    storage = LocalFileStorage(storage_root)
    manifest, cases = load_cases(DATASET)
    try:
        async with maker() as session:
            actual_db = await session.scalar(text("select current_database()"))
            db_identity = assert_evaluation_database(settings, actual_db)
            bootstrap_record = await bootstrap(session, storage, settings=settings,
                                               actual_database=actual_db, reset=reset)
            resolved_locators = set(bootstrap_record["runtime_map"])
            referenced_locators = {
                evidence["stable_locator"]
                for case in cases for evidence in [*case["required_evidence"], *case["acceptable_evidence"]]
                if evidence.get("source_kind") == "INTERNAL_CHUNK"
            }
            if not referenced_locators.issubset(resolved_locators):
                raise RuntimeError("Approved dataset references an INTERNAL_CHUNK locator absent from ACTIVE fixture provenance")
            lesson_ids = bootstrap_record.get("lesson_runtime_ids", {})
            if len(lesson_ids) != 3:
                # An idempotent bootstrap stores source/version ids; re-resolve Lesson ids from sources.
                for source_id, version_id in bootstrap_record["source_runtime_ids"].items():
                    if source_id.startswith("fixture.lesson."):
                        version = await session.get(KnowledgeVersion, UUID(version_id))
                        source = await session.get(KnowledgeSource, version.knowledge_source_id)
                        from app.database.models import Lesson
                        lesson = await session.get(Lesson, source.lesson_id)
                        import json as _json
                        pack = _json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
                        source_json = next(_json.loads((FIXTURE_ROOT / row["path"]).read_text(encoding="utf-8"))
                                           for row in pack["sources"] if row["source_id"] == source_id)
                        lesson_ids[source_json["lesson_locator"]] = str(lesson.id)
            active_profiles = list((await session.scalars(select(EmbeddingProfile).where(
                EmbeddingProfile.status == "ACTIVE",
            ))).all())
            if len(active_profiles) != 1 or (active_profiles[0].model_name, active_profiles[0].model_version) != (
                settings.embedding_model_name, settings.embedding_model_revision,
            ):
                raise RuntimeError("Exactly one accepted pinned embedding profile must be ACTIVE")
            active_versions = list((await session.scalars(select(KnowledgeVersion).where(
                KnowledgeVersion.status == "ACTIVE",
            ))).all())
            active_sources = list((await session.scalars(select(KnowledgeSource))).all())
            if len(active_versions) != 4 or len(active_sources) != 4:
                raise RuntimeError("Evaluation DB must contain exactly four ACTIVE fixture sources and no other corpus")
            await session.rollback()

            embedding_provider = SentenceTransformerEmbeddingProvider(settings)
            reranker_provider = TransformersRerankerProvider(settings)
            by_case: dict[str, list[dict]] = {}
            attempts: list[dict] = []
            for case in cases:
                case_attempts = []
                for plan in plan_attempts(case):
                    item = await _evaluate_attempt(session, case, plan, settings,
                                                   embedding_provider, reranker_provider, lesson_ids)
                    case_attempts.append(item)
                    attempts.append(item)
                by_case[case["case_id"]] = case_attempts
            development = [a for a in attempts if a["split"] == "DEVELOPMENT"]
            holdout = [a for a in attempts if a["split"] == "HOLDOUT"]
            if (len(development), len(holdout)) != (58, 15):
                raise RuntimeError(f"Attempt plan does not match frozen 58/15 contract: {len(development)}/{len(holdout)}")
            calibration = threshold_sweep(development)
            recommendation = calibration["recommended_threshold"]
            holdout_threshold = acceptance_rates_for_holdout(holdout, recommendation) if recommendation is not None else None
            all_summary = _aggregate(attempts)
            by_tier = {tier: _aggregate([a for a in attempts if a["tier"] == tier])
                       for tier in ("CURRENT_LESSON", "INTERNAL_KB")}
            by_bucket = {bucket: _aggregate([a for a in attempts if a["bucket"] == bucket])
                         for bucket in sorted({a["bucket"] for a in attempts})}
            by_split = {split: _aggregate([a for a in attempts if a["split"] == split])
                        for split in ("DEVELOPMENT", "HOLDOUT")}
            cases_rows = []
            for case in cases:
                cases_rows.append({"case_id": case["case_id"], "bucket": case["bucket"],
                                   "split": case["split"], "expected_tier": case["expected_tier"],
                                   "question": case["question"],
                                   "lesson_context": case.get("lesson_context"),
                                   "expected_information": case["expected_information"],
                                   "required_evidence": case["required_evidence"],
                                   "acceptable_evidence": case["acceptable_evidence"],
                                   "expected_scope": case["expected_scope"],
                                   "expected_behavior": case["expected_behavior"],
                                   "tier_attempts": by_case[case["case_id"]],
                                   "case_scope_violation": any(x["scope_violation"] for x in by_case[case["case_id"]])})
            with (run_dir / "cases.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
                for row in cases_rows:
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            _dump(run_dir / "fixture-bootstrap.json", bootstrap_record)
            _dump(run_dir / "fixture-runtime-map.json", {
                "fixture_bootstrap_id": bootstrap_record["fixture_bootstrap_id"],
                "fixture_hashes": bootstrap_record["fixture_hashes"],
                "stable_locator_to_active_chunk_ids": bootstrap_record["runtime_map"],
            })
            _dump(run_dir / "threshold-calibration.json", {
                "calibration_artifact_version": "1.0.0", "dataset_version": manifest["dataset_version"],
                "reranker_identity": {"model": settings.reranker_model_name, "revision": settings.reranker_model_revision,
                                      "provider_version": reranker_provider.identity.provider_version,
                                      "input_version": settings.reranker_input_version},
                "selection_split": "DEVELOPMENT", "verification_split": "HOLDOUT",
                "positive_definition": "at least one relevant reranked Top-5 candidate with raw score >= threshold",
                "negative_definition": "at least one reranked Top-5 candidate with raw score >= threshold",
                "development_sample_counts": {"total": len(development),
                    "positive": sum(a["label"] == "POSITIVE" for a in development),
                    "negative": sum(a["label"] == "NEGATIVE" for a in development)},
                "threshold_candidates": calibration["candidates"], "pareto_frontier": calibration["pareto_frontier"],
                "recommendation_policy": "minimize overall false acceptance; maximize overall true acceptance; maximize minimum tier true acceptance; then choose higher threshold",
                "recommendation_status": calibration["recommendation_status"],
                "recommended_threshold": recommendation,
                "development_tradeoff_at_recommendation": calibration.get("recommendation_tradeoff"),
                "holdout_verification_at_frozen_recommendation": holdout_threshold,
            })
            _dump(run_dir / "summary.json", {
                "run_id": run_id, "dataset_version": manifest["dataset_version"],
                "case_counts_by_split": {split: sum(c["split"] == split for c in cases) for split in ("DEVELOPMENT", "HOLDOUT")},
                "case_counts_by_bucket": {bucket: sum(c["bucket"] == bucket for c in cases)
                                           for bucket in sorted({c["bucket"] for c in cases})},
                "tier_attempt_counts_by_split_tier_label": _attempt_counts(attempts),
                "metrics_overall": all_summary, "metrics_by_split": by_split,
                "metrics_by_tier": by_tier, "metrics_by_bucket": by_bucket,
                "threshold_recommendation_status": calibration["recommendation_status"],
                "recommended_threshold": recommendation,
                "development_calibration_headline": calibration.get("recommendation_tradeoff"),
                "holdout_verification_headline": holdout_threshold,
                "scope_violation_rate": all_summary["scope_violation_rate"],
                "cases_with_scope_violation": all_summary["cases_with_scope_violation"],
            })
            commit = _git_commit(ROOT)
            model_manifest = {
                "run_id": run_id, "timestamp": datetime.now(UTC).isoformat(), "evaluation_step": "7.3",
                "dataset_version": manifest["dataset_version"], "dataset_schema_version": manifest["schema_version"],
                "dataset_splits": ["DEVELOPMENT", "HOLDOUT"], "code_commit": commit,
                "code_commit_available": commit is not None,
                "embedding_profile": {"id": str(active_profiles[0].id), "provider": active_profiles[0].provider,
                    "provider_version": active_profiles[0].provider_version, "dimensions": active_profiles[0].dimensions,
                    "input_version": active_profiles[0].embedding_input_version,
                    "normalize_embeddings": active_profiles[0].normalize_embeddings},
                "embedding_model": settings.embedding_model_name,
                "embedding_model_version": settings.embedding_model_revision,
                "chunking_version": "structure_aware/v1", "candidate_k": 20,
                "reranker_model": settings.reranker_model_name,
                "reranker_model_version": settings.reranker_model_revision, "reranker_top_k": 5,
                "reranker_config": {"input_version": settings.reranker_input_version,
                    "batch_size": settings.reranker_batch_size, "device": reranker_provider.device},
                "retrieval_filter_config": {
                    "CURRENT_LESSON": "build_scope_filter(CURRENT_LESSON, trusted_lesson_id)",
                    "INTERNAL_KB": "build_scope_filter(INTERNAL_KB) -> None; active Lesson knowledge + approved active Documents; no external source family",
                },
                "RAG_EVIDENCE_CALIBRATION_MODE": True,
                "runtime_RAG_MIN_RERANK_SCORE_before_run": initial.rag_min_rerank_score,
                "fixture_bootstrap_artifacts": ["fixture-bootstrap.json", "fixture-runtime-map.json"],
                "fixture_bootstrap_id": bootstrap_record["fixture_bootstrap_id"],
                "fixture_pack": "lesson_chat_rag", "fixture_pack_version": "0.1.0",
                "fixture_hashes": bootstrap_record["fixture_hashes"],
                "evaluation_database_isolation": db_identity,
                "fixture_source_count": 4, "fixture_block_count": 26,
                "runtime_RAG_MIN_RERANK_SCORE_modified": False,
            }
            _dump(run_dir / "manifest.json", model_manifest)
            return {"run_id": run_id, "run_dir": str(run_dir), "manifest": model_manifest,
                    "summary": json.loads((run_dir / "summary.json").read_text(encoding="utf-8")),
                    "calibration": json.loads((run_dir / "threshold-calibration.json").read_text(encoding="utf-8")),
                    "bootstrap": bootstrap_record, "code_commit": commit,
                    "attempts": attempts, "cases": cases}
    finally:
        await engine.dispose()


def acceptance_rates_for_holdout(holdout: list[dict], threshold: float) -> dict:
    from app.evaluation.step73.evaluation import acceptance_rates
    return acceptance_rates(holdout, threshold)


def _attempt_counts(attempts: list[dict]) -> dict:
    result = defaultdict(int)
    for attempt in attempts:
        result[f"{attempt['split']}/{attempt['tier']}/{attempt['label']}"] += 1
    return dict(sorted(result.items()))
