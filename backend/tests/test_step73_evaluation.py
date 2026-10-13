from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import pytest

from app.evaluation.step73.evaluation import (
    DATASET, FIXTURES, acceptance_rates, attempt_metrics, evidence_groups, load_cases,
    plan_attempts, threshold_sweep,
)
from app.evaluation.step73.fixtures import (
    FIXTURE_ROOT, EXPECTED_HASHES, _fixture_locator_metadata, _fixture_provenance_records,
    assert_evaluation_database, load_fixture_pack,
)
from app.core.config import Settings


def test_accepted_fixture_pack_hashes_counts_and_stable_identities():
    manifest, blocks, hashes = load_fixture_pack()
    assert manifest["status"] == "ACCEPTED_FOR_EVALUATION_FIXTURE"
    assert len(manifest["sources"]) == 4 and len(blocks) == 26
    assert len({block["stable_locator"] for block in blocks}) == 26
    assert hashes["fixture_manifest_sha256"] == EXPECTED_HASHES["manifest.json"]
    assert set(hashes["per_source_sha256"].values()) == {
        EXPECTED_HASHES[f"sources/{Path(path).name}"] for path in [
            "internal-kb-beginner-notes.json", "lesson-01-greetings.json",
            "lesson-02-numbers-age.json", "lesson-03-family.json",
        ]
    }
    assert not any(block.get("chunk_id") or block.get("id") for block in blocks)


def test_frozen_dataset_excludes_ood_and_attempt_counts_are_exact():
    manifest, cases = load_cases(DATASET)
    assert manifest["dataset_version"] == "v0.8.0"
    assert all(case["bucket"] != "OUT_OF_DOMAIN_REFUSAL" for case in cases)
    counts = Counter((case["split"], attempt["tier"], attempt["label"])
                     for case in cases for attempt in plan_attempts(case))
    assert counts == Counter({
        ("DEVELOPMENT", "CURRENT_LESSON", "POSITIVE"): 20,
        ("DEVELOPMENT", "CURRENT_LESSON", "NEGATIVE"): 16,
        ("DEVELOPMENT", "INTERNAL_KB", "POSITIVE"): 12,
        ("DEVELOPMENT", "INTERNAL_KB", "NEGATIVE"): 10,
        ("HOLDOUT", "CURRENT_LESSON", "POSITIVE"): 5,
        ("HOLDOUT", "CURRENT_LESSON", "NEGATIVE"): 4,
        ("HOLDOUT", "INTERNAL_KB", "POSITIVE"): 3,
        ("HOLDOUT", "INTERNAL_KB", "NEGATIVE"): 3,
    })
    assert (sum(v for (split, _, _), v in counts.items() if split == "DEVELOPMENT"),
            sum(v for (split, _, _), v in counts.items() if split == "HOLDOUT")) == (58, 15)
    multi = next(case for case in cases if case["bucket"] == "MULTI_TURN_CONTEXT")
    assert all(attempt["query"] if "query" in attempt else multi["question"] for attempt in plan_attempts(multi))


def test_attempt_planning_multiturn_uses_current_question_only():
    _, cases = load_cases()
    case = next(case for case in cases if case["bucket"] == "MULTI_TURN_CONTEXT")
    assert case.get("conversation_context")
    plans = plan_attempts(case)
    assert plans
    assert all("conversation_context" not in plan for plan in plans)


def test_required_equivalence_group_any_member_is_a_hit_and_singleton_works():
    case = {"required_evidence": [
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "a", "requirement_id": "same", "evidence_id": "ea"},
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "b", "requirement_id": "same", "evidence_id": "eb"},
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "c", "requirement_id": "single", "evidence_id": "ec"},
    ], "acceptable_evidence": []}
    groups, grades, _ = evidence_groups(case)
    assert groups == [{"a", "b"}, {"c"}]
    rows = [{"stable_locators": ["a"]}, {"stable_locators": ["c"]}]
    result = attempt_metrics(rows, case, positive=True)
    assert result["recall20"] == 1.0
    assert [row["relevance_grade"] for row in rows] == [2, 2]
    assert grades["a"] == 2


def test_required_grade_wins_overlap_and_acceptable_evidence_counts_for_precision():
    case = {"required_evidence": [{"source_kind": "INTERNAL_CHUNK", "stable_locator": "both",
                                    "requirement_id": "required", "evidence_id": "req"}],
            "acceptable_evidence": [{"source_kind": "INTERNAL_CHUNK", "stable_locator": "both",
                                      "evidence_id": "acc"},
                                     {"source_kind": "INTERNAL_CHUNK", "stable_locator": "acceptable",
                                      "evidence_id": "acc2"}]}
    rows = [{"stable_locators": ["both"]}, {"stable_locators": ["acceptable"]}]
    metrics = attempt_metrics(rows, case, positive=True)
    assert [row["relevance_grade"] for row in rows] == [2, 1]
    assert metrics["precision5"] == pytest.approx(0.4)


def test_ndcg_does_not_double_count_equivalent_evidence_members():
    case = {"required_evidence": [
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "a", "requirement_id": "equivalent", "evidence_id": "a"},
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "b", "requirement_id": "equivalent", "evidence_id": "b"},
        {"source_kind": "INTERNAL_CHUNK", "stable_locator": "c", "requirement_id": "other", "evidence_id": "c"},
    ], "acceptable_evidence": []}
    rows = [{"stable_locators": ["a"]}, {"stable_locators": ["b"]}, {"stable_locators": ["c"]}]
    metrics = attempt_metrics(rows, case, positive=True)
    assert metrics["recall5"] == 1.0
    assert metrics["ndcg5"] <= 1.0


def test_negative_attempt_metrics_are_na():
    case = {"required_evidence": [], "acceptable_evidence": []}
    assert attempt_metrics([], case, positive=False) == {"recall": None, "precision": None, "ndcg": None}


def test_threshold_false_acceptance_uses_max_of_reranked_top5():
    attempts = [{"label": "NEGATIVE", "tier": "CURRENT_LESSON", "reranked_candidates": [
        {"rerank_score": -2.0}, {"rerank_score": 0.25}, {"rerank_score": -4.0},
    ]}]
    assert acceptance_rates(attempts, 0.25)["negative_attempts_falsely_accepted"] == 1
    assert acceptance_rates(attempts, 0.251)["negative_attempts_falsely_accepted"] == 0


def test_threshold_true_acceptance_requires_relevant_candidate():
    attempts = [
        {"label": "POSITIVE", "tier": "CURRENT_LESSON", "reranked_candidates": [
            {"rerank_score": 0.8, "relevance_grade": 0}, {"rerank_score": 0.4, "relevance_grade": 2}]},
        {"label": "POSITIVE", "tier": "INTERNAL_KB", "reranked_candidates": [
            {"rerank_score": 0.7, "relevance_grade": 2}]},
        {"label": "NEGATIVE", "tier": "CURRENT_LESSON", "reranked_candidates": [{"rerank_score": 0.8}]},
        {"label": "NEGATIVE", "tier": "INTERNAL_KB", "reranked_candidates": [{"rerank_score": 0.9}]},
    ]
    result = acceptance_rates(attempts, 0.75)
    assert result["positive_attempts_accepted"] == 0
    assert result["negative_attempts_falsely_accepted"] == 2


def test_threshold_sweep_uses_only_supplied_development_attempts_and_raw_scores():
    attempts = []
    for tier in ("CURRENT_LESSON", "INTERNAL_KB"):
        attempts.extend([
            {"tier": tier, "label": "POSITIVE", "reranked_candidates":[
                {"rerank_score": 0.3123456789, "relevance_grade": 2}]},
            {"tier": tier, "label": "NEGATIVE", "reranked_candidates":[{"rerank_score": 0.125}]},
        ])
    result = threshold_sweep(attempts)
    assert result["candidates"][-1]["threshold"] == math.nextafter(0.3123456789, math.inf)
    assert any(row["threshold"] == 0.3123456789 for row in result["candidates"])
    assert result["recommended_threshold"] is not None
    # A holdout score is not an input unless explicitly passed; no external split lookup exists here.
    assert all("HOLDOUT" not in row for row in result["candidates"])


def test_threshold_sweep_pathological_missing_tier_samples_requires_review():
    result = threshold_sweep([{"tier": "CURRENT_LESSON", "label": "POSITIVE",
                              "reranked_candidates": [{"rerank_score": 0.1, "relevance_grade": 2}]}])
    assert result["recommended_threshold"] is None
    assert result["recommendation_status"] == "REVIEW_REQUIRED"


def test_source_provenance_resolver_supports_split_and_merge_without_text_matching():
    _, blocks, _ = load_fixture_pack()
    lesson = next(block for block in blocks if block["source_kind"] == "LESSON")
    lesson_source_blocks = [block for block in blocks if block["source_id"] == lesson["source_id"]]
    voc = [block for block in lesson_source_blocks if block["content_type"] == "VOCABULARY"]
    split_meta = {"source_ranges": [
        {"source_locator": {"section": "VOCABULARY", "order_index": 0}},
        {"source_locator": {"section": "VOCABULARY", "order_index": 1}},
    ]}
    locators = _fixture_locator_metadata(split_meta, lesson["source_id"], "LESSON", lesson_source_blocks)
    records = _fixture_provenance_records(split_meta, "LESSON", lesson_source_blocks)
    assert locators == sorted([voc[0]["stable_locator"], voc[1]["stable_locator"]])
    assert {item["stable_locator"] for item in records} == set(locators)
    # Repeating one typed source range represents a split block and retains the locator.
    split = {"source_ranges": [split_meta["source_ranges"][0], split_meta["source_ranges"][0]]}
    assert _fixture_locator_metadata(split, lesson["source_id"], "LESSON", lesson_source_blocks) == [voc[0]["stable_locator"]]


def test_evaluation_database_guard_requires_test_and_distinct_normal_target():
    settings = Settings(app_env="test", debug=False, secret_key="test-only",
                        test_database_url="postgresql+psycopg://u:p@localhost/chinese_learning_test",
                        database_url="postgresql+psycopg://u:p@localhost/chinese_learning")
    result = assert_evaluation_database(settings, "chinese_learning_test")
    assert result["database_isolation"] == "DEDICATED_TEST_EVALUATION"
    with pytest.raises(RuntimeError):
        assert_evaluation_database(settings.model_copy(update={"app_env": "development"}), "chinese_learning_test")
    with pytest.raises(RuntimeError):
        assert_evaluation_database(settings.model_copy(update={"test_database_url": "postgresql+psycopg://u:p@localhost/chinese_learning"}),
                                   "chinese_learning")
