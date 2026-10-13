import json
import sys
from collections import Counter
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from evaluation import validate_dataset as validator  # noqa: E402


BUCKETS = validator.BUCKETS
SCHEMA_VERSION = "1.0.0"
DATASET_VERSION = "v0.8.0"
GATE_COUNTS = {
    "CURRENT_LESSON_ANSWERABLE": (20, 16),
    "INTERNAL_KB_FALLBACK": (10, 8),
    "TRUSTED_EXTERNAL_FALLBACK": (5, 4),
    "NO_EVIDENCE_REFUSAL": (8, 6),
    "OUT_OF_DOMAIN_REFUSAL": (7, 6),
    "MULTI_TURN_CONTEXT": (10, 8),
}
SCHEMA = json.loads(
    (REPOSITORY_ROOT / "evaluation" / "schemas" / "evaluation_case.schema.json").read_text(encoding="utf-8")
)


def case_for(
    bucket="CURRENT_LESSON_ANSWERABLE",
    *,
    case_id="case-001",
    split="DEVELOPMENT",
    status="DRAFT",
):
    tier_behavior = {
        "CURRENT_LESSON_ANSWERABLE": ("CURRENT_LESSON", "ANSWER"),
        "INTERNAL_KB_FALLBACK": ("INTERNAL_KB", "FALLBACK_INTERNAL"),
        "TRUSTED_EXTERNAL_FALLBACK": ("TRUSTED_EXTERNAL", "FALLBACK_EXTERNAL"),
        "NO_EVIDENCE_REFUSAL": ("NONE", "REFUSE_NO_EVIDENCE"),
        "OUT_OF_DOMAIN_REFUSAL": ("NONE", "REFUSE_OUT_OF_DOMAIN"),
        "MULTI_TURN_CONTEXT": ("CURRENT_LESSON", "ANSWER"),
    }
    tier, behavior = tier_behavior[bucket]
    answerable = bucket in {
        "CURRENT_LESSON_ANSWERABLE", "INTERNAL_KB_FALLBACK",
        "TRUSTED_EXTERNAL_FALLBACK", "MULTI_TURN_CONTEXT",
    }
    source_kind = "EXTERNAL_URL" if tier == "TRUSTED_EXTERNAL" else "INTERNAL_CHUNK"
    evidence = []
    if answerable:
        if source_kind == "EXTERNAL_URL":
            evidence.append({
                "evidence_id": "evidence-1", "source_kind": source_kind,
                "url": "https://fixture.example.invalid/lesson", "domain": "fixture.example.invalid",
                "title": "Temporary validator fixture", "relevance_role": "REQUIRED",
                "requirement_id": "requirement-1",
            })
        else:
            evidence.append({
                "evidence_id": "evidence-1", "source_kind": source_kind,
                "stable_locator": "fixture://lesson/grammar/item-1", "source_title": "Temporary fixture",
                "lesson_locator": "lesson-fixture-1", "relevance_role": "REQUIRED",
                "requirement_id": "requirement-1",
            })
    scope = {"scope_kind": tier}
    if tier == "CURRENT_LESSON":
        scope["lesson_locator"] = "lesson-fixture-1"
    value = {
        "case_id": case_id,
        "schema_version": SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "bucket": bucket,
        "split": split,
        "question": "Temporary synthetic validation question.",
        "expected_information": ["One independently meaningful expected fact."] if answerable else [],
        "required_evidence": evidence,
        "acceptable_evidence": [],
        "expected_scope": scope,
        "expected_tier": tier,
        "expected_behavior": behavior,
        "expected_answer_properties": [],
        "expected_citation_sources": ["evidence-1"] if answerable else [],
        "critical_failure_expectations": [],
        "review_status": status,
    }
    if bucket in {"CURRENT_LESSON_ANSWERABLE", "INTERNAL_KB_FALLBACK", "MULTI_TURN_CONTEXT"}:
        value["lesson_context"] = {"lesson_locator": "lesson-fixture-1", "hsk_identity": "HSK_FIXTURE"}
    if bucket == "MULTI_TURN_CONTEXT":
        value["conversation_context"] = [{
            "user_text": "Earlier synthetic question.",
            "assistant_text": "Earlier synthetic answer.",
        }]
    return value


def manifest_for(development, holdout):
    rows = list(development) + list(holdout)
    approved = [case for case in rows if case["review_status"] == "APPROVED"]
    statuses = Counter(case["review_status"] for case in rows)
    all_buckets = Counter(case["bucket"] for case in rows)
    approved_buckets = Counter(case["bucket"] for case in approved)
    all_splits = Counter(case["split"] for case in rows)
    approved_splits = Counter(case["split"] for case in approved)
    return {
        "dataset_name": "lesson_chat_rag",
        "dataset_version": DATASET_VERSION,
        "schema_version": SCHEMA_VERSION,
        "system_under_evaluation": "Lesson Chat RAG",
        "created_at": "2026-10-07T00:00:00Z",
        "updated_at": "2026-10-07T00:00:00Z",
        "case_count_total": len(rows),
        "draft_count": statuses["DRAFT"],
        "approved_count_total": len(approved),
        "rejected_count": statuses["REJECTED"],
        "case_count_by_bucket": {bucket: all_buckets[bucket] for bucket in BUCKETS},
        "approved_count_by_bucket": {bucket: approved_buckets[bucket] for bucket in BUCKETS},
        "development_count": all_splits["DEVELOPMENT"],
        "holdout_count": all_splits["HOLDOUT"],
        "approved_development_count": approved_splits["DEVELOPMENT"],
        "approved_holdout_count": approved_splits["HOLDOUT"],
        "approval_policy": "MANUAL_HUMAN_REVIEW_REQUIRED; CODEX_MUST_NOT_SELF_APPROVE",
    }


def run_in_memory_dataset(monkeypatch, development=(), holdout=(), *, mode="STRUCTURAL", manifest_update=None):
    development, holdout = list(development), list(holdout)
    manifest = manifest_for(development, holdout)
    if manifest_update:
        manifest.update(manifest_update)

    def fake_read_json(_path, label):
        return SCHEMA if label == "EvaluationCase schema" else manifest

    def fake_read_jsonl(path, expected_split, found_manifest):
        rows = development if path.name == "development.jsonl" else holdout
        return [
            validator._validate_case(
                case, expected_split=expected_split, manifest=found_manifest,
                line_label=f"{path.name}:{index}",
            )
            for index, case in enumerate(rows, start=1)
        ]

    monkeypatch.setattr(validator, "_read_json", fake_read_json)
    monkeypatch.setattr(validator, "_read_jsonl", fake_read_jsonl)
    dataset_dir = REPOSITORY_ROOT / "evaluation" / "datasets" / "lesson_chat_rag" / "v0"
    return validator.validate_dataset(dataset_dir, mode)


def official_case_rows():
    development, holdout = [], []
    for bucket, (total, development_count) in GATE_COUNTS.items():
        for index in range(total):
            split = "DEVELOPMENT" if index < development_count else "HOLDOUT"
            case = case_for(bucket, case_id=f"{bucket.lower()}-{index:02d}", split=split, status="APPROVED")
            (development if split == "DEVELOPMENT" else holdout).append(case)
    return development, holdout


def test_checked_in_dataset_is_structural_and_official_gate_passes():
    dataset = REPOSITORY_ROOT / "evaluation" / "datasets" / "lesson_chat_rag" / "v0"
    report = validator.validate_dataset(dataset, "STRUCTURAL")
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == DATASET_VERSION
    checked_in_cases = []
    for filename in ("development.jsonl", "holdout.jsonl"):
        cases = [
            json.loads(line)
            for line in (dataset / filename).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert all(case["dataset_version"] == DATASET_VERSION for case in cases)
        checked_in_cases.extend(cases)
    no_evidence_cases = [case for case in checked_in_cases if case["bucket"] == "NO_EVIDENCE_REFUSAL"]
    assert len(no_evidence_cases) == 8
    assert all(
        case["review_status"] == "APPROVED"
        and case["expected_tier"] == "NONE"
        and case["expected_behavior"] == "REFUSE_NO_EVIDENCE"
        and not case["required_evidence"]
        and not case["acceptable_evidence"]
        and not case["expected_citation_sources"]
        for case in no_evidence_cases
    )
    assert report["case_count_total"] == 60
    assert report["draft_count"] == 0
    assert report["approved_count_total"] == 60
    assert report["rejected_count"] == 0
    assert report["development_count"] == 48 and report["holdout_count"] == 12
    assert report["approved_development_count"] == 48
    assert report["approved_holdout_count"] == 12
    assert report["case_count_by_bucket"]["CURRENT_LESSON_ANSWERABLE"] == 20
    assert report["case_count_by_bucket"]["INTERNAL_KB_FALLBACK"] == 10
    assert report["case_count_by_bucket"]["OUT_OF_DOMAIN_REFUSAL"] == 7
    assert report["approved_count_by_bucket"]["OUT_OF_DOMAIN_REFUSAL"] == 7
    ood_cases = [case for case in checked_in_cases if case["bucket"] == "OUT_OF_DOMAIN_REFUSAL"]
    assert len(ood_cases) == 7
    assert Counter(case["split"] for case in ood_cases) == {"DEVELOPMENT": 6, "HOLDOUT": 1}
    assert [case["case_id"] for case in ood_cases] == [f"ood-refusal-synthetic-{index:03d}" for index in range(1, 8)]
    assert all(
        case["review_status"] == "APPROVED"
        and case["expected_tier"] == "NONE"
        and case["expected_behavior"] == "REFUSE_OUT_OF_DOMAIN"
        and case["expected_information"] == []
        and case["required_evidence"] == []
        and case["acceptable_evidence"] == []
        and case["expected_scope"] == {"scope_kind": "NONE"}
        and case["expected_citation_sources"] == []
        and case["critical_failure_expectations"] == ["OUT_OF_DOMAIN_ANSWER"]
        for case in ood_cases
    )
    assert report["approved_count_by_bucket"]["CURRENT_LESSON_ANSWERABLE"] == 20
    assert report["approved_count_by_bucket"]["INTERNAL_KB_FALLBACK"] == 10
    assert report["case_count_by_bucket"]["NO_EVIDENCE_REFUSAL"] == 8
    assert report["approved_count_by_bucket"]["NO_EVIDENCE_REFUSAL"] == 8
    multiturn_cases = [case for case in checked_in_cases if case["bucket"] == "MULTI_TURN_CONTEXT"]
    assert len(multiturn_cases) == 10
    assert report["case_count_by_bucket"]["MULTI_TURN_CONTEXT"] == 10
    assert report["approved_count_by_bucket"]["MULTI_TURN_CONTEXT"] == 10
    assert Counter(case["split"] for case in multiturn_cases) == {"DEVELOPMENT": 8, "HOLDOUT": 2}
    for case in multiturn_cases:
        assert case["review_status"] == "APPROVED"
        assert case["conversation_context"]
        assert (case["expected_tier"], case["expected_behavior"]) in {
            ("CURRENT_LESSON", "ANSWER"),
            ("INTERNAL_KB", "FALLBACK_INTERNAL"),
        }
        assert case["required_evidence"]
        evidence_ids = {evidence["evidence_id"] for evidence in case["required_evidence"]}
        assert set(case["expected_citation_sources"]).issubset(evidence_ids)
        assert all(evidence["source_kind"] == "INTERNAL_CHUNK" for evidence in case["required_evidence"])
    trusted_cases = [case for case in checked_in_cases if case["bucket"] == "TRUSTED_EXTERNAL_FALLBACK"]
    assert len(trusted_cases) == 5
    assert report["case_count_by_bucket"]["TRUSTED_EXTERNAL_FALLBACK"] == 5
    assert report["approved_count_by_bucket"]["TRUSTED_EXTERNAL_FALLBACK"] == 5
    assert Counter(case["split"] for case in trusted_cases) == {"DEVELOPMENT": 4, "HOLDOUT": 1}
    registry_path = REPOSITORY_ROOT / "evaluation" / "fixtures" / "lesson_chat_rag" / "trusted_external" / "v0.1.0" / "reviewed-sources.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    sources_by_url = {source["url"]: source for source in registry["sources"]}
    for case in trusted_cases:
        assert case["review_status"] == "APPROVED"
        assert case["expected_tier"] == "TRUSTED_EXTERNAL"
        assert case["expected_behavior"] == "FALLBACK_EXTERNAL"
        assert case["required_evidence"]
        assert all(evidence["source_kind"] == "EXTERNAL_URL" for evidence in case["required_evidence"])
        evidence_ids = {evidence["evidence_id"] for evidence in case["required_evidence"]}
        assert set(case["expected_citation_sources"]).issubset(evidence_ids)
        for evidence in case["required_evidence"]:
            assert evidence["requirement_id"]
            source = sources_by_url[evidence["url"]]
            assert (evidence["domain"], evidence["title"]) == (source["domain"], source["title"])
    official = validator.validate_dataset(dataset, "OFFICIAL_GATE")
    assert official["approved_count_total"] == 60
    assert official["approved_development_count"] == 48
    assert official["approved_holdout_count"] == 12


def test_structural_mode_accepts_draft_and_rejected_without_official_counts(monkeypatch):
    draft = case_for(case_id="a-draft", status="DRAFT")
    rejected = case_for(
        "NO_EVIDENCE_REFUSAL", case_id="b-rejected", split="HOLDOUT", status="REJECTED"
    )
    result = run_in_memory_dataset(monkeypatch, [draft], [rejected])
    assert (result["draft_count"], result["rejected_count"], result["approved_count_total"]) == (1, 1, 0)


def test_official_gate_accepts_exact_approved_distribution_in_synthetic_memory_fixture(monkeypatch):
    development, holdout = official_case_rows()
    development.sort(key=lambda case: case["case_id"])
    holdout.sort(key=lambda case: case["case_id"])
    result = run_in_memory_dataset(monkeypatch, development, holdout, mode="OFFICIAL_GATE")
    assert result["approved_count_total"] == 60
    assert result["approved_development_count"] == 48
    assert result["approved_holdout_count"] == 12
    assert result["approved_count_by_bucket"] == {bucket: total for bucket, (total, _) in GATE_COUNTS.items()}
    assert result["approved_split_count_by_bucket"] == validator.OFFICIAL_APPROVED_SPLIT_COUNTS


def test_official_gate_enforces_bucket_stratified_split_counts(monkeypatch):
    development, holdout = official_case_rows()
    development[0]["split"] = "HOLDOUT"
    internal_fallback = next(case for case in holdout if case["bucket"] == "INTERNAL_KB_FALLBACK")
    internal_fallback["split"] = "DEVELOPMENT"
    development, holdout = [
        case for case in development + holdout if case["split"] == "DEVELOPMENT"
    ], [case for case in development + holdout if case["split"] == "HOLDOUT"]
    development.sort(key=lambda case: case["case_id"])
    holdout.sort(key=lambda case: case["case_id"])
    with pytest.raises(validator.ReviewRequiredError, match="CURRENT_LESSON_ANSWERABLE/DEVELOPMENT"):
        run_in_memory_dataset(monkeypatch, development, holdout, mode="OFFICIAL_GATE")


def test_duplicate_case_id_across_splits_fails(monkeypatch):
    with pytest.raises(validator.DatasetValidationError, match="duplicate case_id"):
        run_in_memory_dataset(
            monkeypatch,
            [case_for(case_id="same-id")],
            [case_for(case_id="same-id", split="HOLDOUT")],
        )


def test_case_order_must_be_stable_by_case_id(monkeypatch):
    with pytest.raises(validator.DatasetValidationError, match="ordered by case_id"):
        run_in_memory_dataset(
            monkeypatch,
            [case_for(case_id="z-last"), case_for(case_id="a-first")],
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda case: case.update(bucket="UNKNOWN"), "bucket must be one of"),
        (lambda case: case.pop("expected_information"), "missing required fields"),
        (lambda case: case.update(schema_version="9.0"), "schema_version mismatch"),
        (lambda case: case.update(dataset_version="v9"), "dataset_version mismatch"),
        (lambda case: case.update(split="HOLDOUT"), "does not match its JSONL file"),
    ],
)
def test_invalid_enum_or_missing_fields_fail_structural_validation(monkeypatch, change, message):
    case = case_for()
    change(case)
    with pytest.raises(validator.DatasetValidationError, match=message):
        run_in_memory_dataset(monkeypatch, [case])


def test_review_status_must_be_draft_approved_or_rejected(monkeypatch):
    case = case_for()
    case["review_status"] = "PENDING"
    with pytest.raises(validator.DatasetValidationError, match="review_status must be one of"):
        run_in_memory_dataset(monkeypatch, [case])


def test_approved_answerable_case_requires_expected_information_and_evidence(monkeypatch):
    empty_information = case_for(status="APPROVED")
    empty_information["expected_information"] = []
    with pytest.raises(validator.DatasetValidationError, match="empty expected_information"):
        run_in_memory_dataset(monkeypatch, [empty_information])

    no_evidence = case_for(case_id="no-ev", status="APPROVED")
    no_evidence["required_evidence"] = []
    no_evidence["expected_citation_sources"] = []
    with pytest.raises(validator.DatasetValidationError, match="no required/acceptable evidence"):
        run_in_memory_dataset(monkeypatch, [no_evidence])


def test_required_evidence_requires_requirement_id_even_for_singletons(monkeypatch):
    case = case_for()
    case["required_evidence"][0].pop("requirement_id")
    with pytest.raises(validator.DatasetValidationError, match="requirement_id is required even for singleton"):
        run_in_memory_dataset(monkeypatch, [case])


def test_evidence_ids_must_be_unique_within_a_case(monkeypatch):
    case = case_for()
    duplicate = dict(case["required_evidence"][0])
    duplicate["requirement_id"] = "another-requirement"
    case["required_evidence"].append(duplicate)
    with pytest.raises(validator.DatasetValidationError, match="duplicate evidence_id"):
        run_in_memory_dataset(monkeypatch, [case])


def test_evidence_role_must_match_its_list(monkeypatch):
    case = case_for()
    case["required_evidence"][0]["relevance_role"] = "ACCEPTABLE"
    with pytest.raises(validator.DatasetValidationError, match="relevance_role must be REQUIRED"):
        run_in_memory_dataset(monkeypatch, [case])


def test_equivalent_required_evidence_shares_group_and_acceptable_may_omit_it(monkeypatch):
    case = case_for()
    equivalent = dict(case["required_evidence"][0])
    equivalent["evidence_id"] = "evidence-2"
    case["required_evidence"].append(equivalent)
    acceptable = dict(equivalent)
    acceptable.update(evidence_id="evidence-3", relevance_role="ACCEPTABLE")
    acceptable.pop("requirement_id")
    case["acceptable_evidence"].append(acceptable)
    case["expected_citation_sources"] = ["evidence-1", "evidence-2", "evidence-3"]
    assert run_in_memory_dataset(monkeypatch, [case])["case_count_total"] == 1


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda case: case.update(expected_citation_sources=["unknown"]), "unknown evidence_id"),
        (lambda case: case.update(expected_behavior="REFUSE_NO_EVIDENCE"), "bucket-specific tier/behavior mismatch"),
        (lambda case: case.update(conversation_context=[]), "requires non-empty conversation_context"),
    ],
)
def test_citation_bucket_and_multi_turn_invariants_fail(monkeypatch, mutate, message):
    bucket = "MULTI_TURN_CONTEXT" if "conversation_context" in message else "CURRENT_LESSON_ANSWERABLE"
    case = case_for(bucket)
    mutate(case)
    with pytest.raises(validator.DatasetValidationError, match=message):
        run_in_memory_dataset(monkeypatch, [case])


def test_refusal_mappings_require_empty_evidence_and_citations(monkeypatch):
    case = case_for("NO_EVIDENCE_REFUSAL")
    case["expected_behavior"] = "REFUSE_OUT_OF_DOMAIN"
    with pytest.raises(validator.DatasetValidationError, match="invalid NO_EVIDENCE_REFUSAL"):
        run_in_memory_dataset(monkeypatch, [case])


def test_external_fixture_is_structural_metadata_only_and_never_fetched(monkeypatch):
    case = case_for("TRUSTED_EXTERNAL_FALLBACK")
    result = run_in_memory_dataset(monkeypatch, [case])
    assert result["case_count_by_bucket"]["TRUSTED_EXTERNAL_FALLBACK"] == 1


def test_external_url_must_be_https_and_match_its_domain(monkeypatch):
    case = case_for("TRUSTED_EXTERNAL_FALLBACK")
    case["required_evidence"][0]["url"] = "javascript:alert(1)"
    with pytest.raises(validator.DatasetValidationError, match="HTTPS URL"):
        run_in_memory_dataset(monkeypatch, [case])


def test_manifest_counts_must_match_all_rows(monkeypatch):
    with pytest.raises(validator.DatasetValidationError, match="manifest.draft_count mismatch"):
        run_in_memory_dataset(monkeypatch, [case_for()], manifest_update={"draft_count": 0})


def test_jsonl_rejects_invalid_json_and_blank_lines():
    manifest = manifest_for([], [])
    with pytest.raises(validator.DatasetValidationError, match="has invalid JSON"):
        validator._parse_jsonl_content("{broken}\n", "dev.jsonl", "DEVELOPMENT", manifest)
    with pytest.raises(validator.DatasetValidationError, match="blank line"):
        validator._parse_jsonl_content("\n", "dev.jsonl", "DEVELOPMENT", manifest)


def test_manifest_bucket_split_counts_include_nonapproved_rows(monkeypatch):
    draft = case_for(case_id="draft-a", status="DRAFT")
    rejected = case_for(
        "OUT_OF_DOMAIN_REFUSAL", case_id="rejected-b", split="HOLDOUT", status="REJECTED"
    )
    result = run_in_memory_dataset(monkeypatch, [draft], [rejected])
    assert result["case_count_by_bucket"]["CURRENT_LESSON_ANSWERABLE"] == 1
    assert result["approved_count_by_bucket"]["CURRENT_LESSON_ANSWERABLE"] == 0
    assert result["development_count"] == result["holdout_count"] == 1
