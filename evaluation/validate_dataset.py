"""Validate the repo-controlled Lesson Chat RAG evaluation dataset."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


BUCKETS = (
    "CURRENT_LESSON_ANSWERABLE",
    "INTERNAL_KB_FALLBACK",
    "TRUSTED_EXTERNAL_FALLBACK",
    "NO_EVIDENCE_REFUSAL",
    "OUT_OF_DOMAIN_REFUSAL",
    "MULTI_TURN_CONTEXT",
)
SPLITS = ("DEVELOPMENT", "HOLDOUT")
TIERS = ("CURRENT_LESSON", "INTERNAL_KB", "TRUSTED_EXTERNAL", "NONE")
BEHAVIORS = (
    "ANSWER",
    "FALLBACK_INTERNAL",
    "FALLBACK_EXTERNAL",
    "REFUSE_NO_EVIDENCE",
    "REFUSE_OUT_OF_DOMAIN",
)
REVIEW_STATUSES = ("DRAFT", "APPROVED", "REJECTED")
SOURCE_KINDS = ("INTERNAL_CHUNK", "EXTERNAL_URL")
RELEVANCE_ROLES = ("REQUIRED", "ACCEPTABLE")
CRITICAL_FAILURES = (
    "SERIOUS_FACTUAL_ERROR",
    "UNSUPPORTED_CONFIDENT_CLAIM",
    "FABRICATED_CITATION_OR_SOURCE",
    "CITATION_PROVENANCE_MISMATCH",
    "OUT_OF_DOMAIN_ANSWER",
    "CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE",
    "RETRIEVAL_SCOPE_VIOLATION",
    "TIER_FALLBACK_POLICY_VIOLATION",
    "TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE",
    "REQUIRED_CITATION_MISSING",
)

OFFICIAL_APPROVED_COUNTS = {
    "CURRENT_LESSON_ANSWERABLE": 20,
    "INTERNAL_KB_FALLBACK": 10,
    "TRUSTED_EXTERNAL_FALLBACK": 5,
    "NO_EVIDENCE_REFUSAL": 8,
    "OUT_OF_DOMAIN_REFUSAL": 7,
    "MULTI_TURN_CONTEXT": 10,
}
OFFICIAL_APPROVED_SPLIT_COUNTS = {
    "CURRENT_LESSON_ANSWERABLE": {"DEVELOPMENT": 16, "HOLDOUT": 4},
    "INTERNAL_KB_FALLBACK": {"DEVELOPMENT": 8, "HOLDOUT": 2},
    "TRUSTED_EXTERNAL_FALLBACK": {"DEVELOPMENT": 4, "HOLDOUT": 1},
    "NO_EVIDENCE_REFUSAL": {"DEVELOPMENT": 6, "HOLDOUT": 2},
    "OUT_OF_DOMAIN_REFUSAL": {"DEVELOPMENT": 6, "HOLDOUT": 1},
    "MULTI_TURN_CONTEXT": {"DEVELOPMENT": 8, "HOLDOUT": 2},
}
SCHEMA_RELATIVE_PATH = Path("schemas/evaluation_case.schema.json")
MANIFEST_RELATIVE_PATH = Path("manifest.json")
SPLIT_FILES = {
    "DEVELOPMENT": "development.jsonl",
    "HOLDOUT": "holdout.jsonl",
}

CASE_FIELDS = {
    "case_id", "schema_version", "dataset_version", "bucket", "split",
    "question", "conversation_context", "lesson_context",
    "expected_information", "reference_answer", "required_evidence",
    "acceptable_evidence", "expected_scope", "expected_tier",
    "expected_behavior", "expected_answer_properties",
    "expected_citation_sources", "critical_failure_expectations", "review_status",
}
CASE_REQUIRED_FIELDS = CASE_FIELDS - {"conversation_context", "lesson_context", "reference_answer"}
EVIDENCE_COMMON_FIELDS = {"evidence_id", "source_kind", "relevance_role"}
INTERNAL_EVIDENCE_FIELDS = {
    "evidence_id", "source_kind", "stable_locator", "chunk_id", "source_title",
    "lesson_locator", "section", "page_or_locator", "relevance_role", "requirement_id",
}
EXTERNAL_EVIDENCE_FIELDS = {
    "evidence_id", "source_kind", "url", "domain", "title",
    "relevance_role", "requirement_id",
}
SCOPE_FIELDS = {"scope_kind", "lesson_locator", "constraints"}
CONSTRAINT_FIELDS = {
    "hsk_identities", "content_types", "source_types", "source_categories", "source_languages",
}
LESSON_CONTEXT_FIELDS = {"lesson_locator", "hsk_identity", "lesson_title"}
TURN_FIELDS = {"user_text", "assistant_text"}


class DatasetValidationError(ValueError):
    """Stored data does not satisfy the structural dataset contract."""


class ReviewRequiredError(DatasetValidationError):
    """Structure is valid, but manual review has not met the official gate."""


def _fail(message: str) -> None:
    raise DatasetValidationError(message)


def _object(value, label: str, allowed: set[str], required: set[str]) -> dict:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    missing = required - value.keys()
    extra = value.keys() - allowed
    if missing:
        _fail(f"{label} missing required fields: {', '.join(sorted(missing))}")
    if extra:
        _fail(f"{label} has unknown fields: {', '.join(sorted(extra))}")
    return value


def _nonempty_string(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label} must be a non-empty string")
    return value


def _string_list(value, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        suffix = "non-empty " if nonempty else ""
        _fail(f"{label} must be a {suffix}array")
    for index, item in enumerate(value):
        _nonempty_string(item, f"{label}[{index}]")
    return value


def _enum(value, choices: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in choices:
        _fail(f"{label} must be one of: {', '.join(choices)}")
    return value


def _validate_manifest(manifest: object, dataset_dir: Path, schema: dict) -> dict:
    required = {
        "dataset_name", "dataset_version", "schema_version", "system_under_evaluation",
        "created_at", "updated_at", "case_count_total", "draft_count", "approved_count_total",
        "rejected_count", "case_count_by_bucket", "approved_count_by_bucket",
        "development_count", "holdout_count", "approved_development_count",
        "approved_holdout_count", "approval_policy",
    }
    manifest = _object(manifest, "manifest", required, required)
    for key in ("dataset_name", "dataset_version", "schema_version", "system_under_evaluation", "approval_policy"):
        _nonempty_string(manifest[key], f"manifest.{key}")
    if manifest["system_under_evaluation"] != "Lesson Chat RAG":
        _fail("manifest.system_under_evaluation must be Lesson Chat RAG")
    if manifest["approval_policy"] != "MANUAL_HUMAN_REVIEW_REQUIRED; CODEX_MUST_NOT_SELF_APPROVE":
        _fail("manifest.approval_policy does not preserve the manual approval rule")
    if manifest["schema_version"] != schema.get("x-schema-version"):
        _fail("manifest.schema_version does not match the checked-in case schema")
    for key in ("created_at", "updated_at"):
        value = _nonempty_string(manifest[key], f"manifest.{key}")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            _fail(f"manifest.{key} must be an ISO-8601 timestamp")
    for key in (
        "case_count_total", "draft_count", "approved_count_total", "rejected_count",
        "development_count", "holdout_count", "approved_development_count", "approved_holdout_count",
    ):
        if type(manifest[key]) is not int or manifest[key] < 0:
            _fail(f"manifest.{key} must be a non-negative integer")
    for key in ("case_count_by_bucket", "approved_count_by_bucket"):
        counts = _object(manifest[key], f"manifest.{key}", set(BUCKETS), set(BUCKETS))
        if any(type(count) is not int or count < 0 for count in counts.values()):
            _fail(f"manifest.{key} values must be non-negative integers")
    return manifest


def _validate_evidence(item: object, *, label: str, expected_role: str) -> dict:
    if not isinstance(item, dict):
        _fail(f"{label} must be an object")
    source_kind = item.get("source_kind")
    _enum(source_kind, SOURCE_KINDS, f"{label}.source_kind")
    allowed = INTERNAL_EVIDENCE_FIELDS if source_kind == "INTERNAL_CHUNK" else EXTERNAL_EVIDENCE_FIELDS
    required = EVIDENCE_COMMON_FIELDS | {"relevance_role"}
    if source_kind == "INTERNAL_CHUNK":
        required |= {"stable_locator", "source_title"}
    else:
        required |= {"url", "domain"}
    item = _object(item, label, allowed, required)
    _nonempty_string(item["evidence_id"], f"{label}.evidence_id")
    _enum(item["relevance_role"], RELEVANCE_ROLES, f"{label}.relevance_role")
    if item["relevance_role"] != expected_role:
        _fail(f"{label}.relevance_role must be {expected_role}")
    if source_kind == "INTERNAL_CHUNK":
        for key in ("stable_locator", "source_title"):
            _nonempty_string(item[key], f"{label}.{key}")
        for key in ("chunk_id", "lesson_locator", "section", "page_or_locator"):
            if key in item and item[key] is not None:
                _nonempty_string(item[key], f"{label}.{key}")
    else:
        url = _nonempty_string(item["url"], f"{label}.url")
        domain = _nonempty_string(item["domain"], f"{label}.domain").lower()
        try:
            parsed = urlsplit(url)
        except ValueError:
            _fail(f"{label}.url is malformed")
        hostname = parsed.hostname.lower() if parsed.hostname else None
        if parsed.scheme != "https" or not hostname or hostname != domain:
            _fail(f"{label} must identify an HTTPS URL whose hostname matches domain")
        if "title" in item and item["title"] is not None:
            _nonempty_string(item["title"], f"{label}.title")
    if "requirement_id" in item and item["requirement_id"] is not None:
        _nonempty_string(item["requirement_id"], f"{label}.requirement_id")
    return item


def _validate_case(case: object, *, expected_split: str, manifest: dict, line_label: str) -> dict:
    case = _object(case, line_label, CASE_FIELDS, CASE_REQUIRED_FIELDS)
    for key in ("case_id", "schema_version", "dataset_version", "question"):
        _nonempty_string(case[key], f"{line_label}.{key}")
    if case["schema_version"] != manifest["schema_version"]:
        _fail(f"{line_label}.schema_version mismatch with manifest")
    if case["dataset_version"] != manifest["dataset_version"]:
        _fail(f"{line_label}.dataset_version mismatch with manifest")
    bucket = _enum(case["bucket"], BUCKETS, f"{line_label}.bucket")
    split = _enum(case["split"], SPLITS, f"{line_label}.split")
    if split != expected_split:
        _fail(f"{line_label}.split does not match its JSONL file")
    tier = _enum(case["expected_tier"], TIERS, f"{line_label}.expected_tier")
    behavior = _enum(case["expected_behavior"], BEHAVIORS, f"{line_label}.expected_behavior")
    _enum(case["review_status"], REVIEW_STATUSES, f"{line_label}.review_status")

    for key in ("expected_information", "expected_answer_properties", "expected_citation_sources", "critical_failure_expectations"):
        _string_list(case[key], f"{line_label}.{key}")
    for failure in case["critical_failure_expectations"]:
        if failure not in CRITICAL_FAILURES:
            _fail(f"{line_label}.critical_failure_expectations contains an unknown label: {failure}")
    if "reference_answer" in case and case["reference_answer"] is not None and not isinstance(case["reference_answer"], str):
        _fail(f"{line_label}.reference_answer must be a string or null")

    if "conversation_context" in case:
        context = case["conversation_context"]
        if not isinstance(context, list):
            _fail(f"{line_label}.conversation_context must be an array")
        for index, turn in enumerate(context):
            turn_label = f"{line_label}.conversation_context[{index}]"
            turn = _object(turn, turn_label, TURN_FIELDS, TURN_FIELDS)
            for key in TURN_FIELDS:
                _nonempty_string(turn[key], f"{turn_label}.{key}")
    if "lesson_context" in case:
        context = _object(case["lesson_context"], f"{line_label}.lesson_context", LESSON_CONTEXT_FIELDS, {"lesson_locator"})
        _nonempty_string(context["lesson_locator"], f"{line_label}.lesson_context.lesson_locator")
        for key in ("hsk_identity", "lesson_title"):
            if key in context and context[key] is not None:
                _nonempty_string(context[key], f"{line_label}.lesson_context.{key}")

    required_evidence = case["required_evidence"]
    acceptable_evidence = case["acceptable_evidence"]
    if not isinstance(required_evidence, list) or not isinstance(acceptable_evidence, list):
        _fail(f"{line_label}.required_evidence and acceptable_evidence must be arrays")
    all_evidence = []
    for index, evidence in enumerate(required_evidence):
        evidence_label = f"{line_label}.required_evidence[{index}]"
        evidence = _validate_evidence(evidence, label=evidence_label, expected_role="REQUIRED")
        if not evidence.get("requirement_id"):
            _fail(f"{evidence_label}.requirement_id is required even for singleton evidence")
        all_evidence.append(evidence)
    for index, evidence in enumerate(acceptable_evidence):
        evidence = _validate_evidence(
            evidence, label=f"{line_label}.acceptable_evidence[{index}]", expected_role="ACCEPTABLE"
        )
        all_evidence.append(evidence)
    evidence_ids = [item["evidence_id"] for item in all_evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        _fail(f"{line_label} has duplicate evidence_id values")
    evidence_by_id = set(evidence_ids)
    if any(source_id not in evidence_by_id for source_id in case["expected_citation_sources"]):
        _fail(f"{line_label}.expected_citation_sources references unknown evidence_id")
    if len(case["expected_citation_sources"]) != len(set(case["expected_citation_sources"])):
        _fail(f"{line_label}.expected_citation_sources contains duplicates")
    if len(case["critical_failure_expectations"]) != len(set(case["critical_failure_expectations"])):
        _fail(f"{line_label}.critical_failure_expectations contains duplicates")

    scope = _object(case["expected_scope"], f"{line_label}.expected_scope", SCOPE_FIELDS, {"scope_kind"})
    scope_kind = _enum(scope["scope_kind"], TIERS, f"{line_label}.expected_scope.scope_kind")
    if scope_kind != tier:
        _fail(f"{line_label}.expected_scope.scope_kind must match expected_tier")
    if "lesson_locator" in scope and scope["lesson_locator"] is not None:
        _nonempty_string(scope["lesson_locator"], f"{line_label}.expected_scope.lesson_locator")
    if "constraints" in scope and scope["constraints"] is not None:
        constraints = _object(
            scope["constraints"], f"{line_label}.expected_scope.constraints",
            CONSTRAINT_FIELDS, set(),
        )
        canonical_constraints = {
            "content_types": {"DOCUMENT_TEXT", "VOCABULARY", "GRAMMAR", "LESSON_GENERAL"},
            "source_types": {"DOCUMENT", "LESSON"},
            "source_categories": {"CURRICULUM_MATERIAL", "INTERNAL_AUTHORED"},
            "source_languages": {"vi", "zh", "en"},
        }
        for key, values in constraints.items():
            values = _string_list(values, f"{line_label}.expected_scope.constraints.{key}", nonempty=True)
            if key in canonical_constraints and any(value not in canonical_constraints[key] for value in values):
                _fail(f"{line_label}.expected_scope.constraints.{key} contains a non-canonical value")
            if key == "hsk_identities" and len(values) != len(set(values)):
                _fail(f"{line_label}.expected_scope.constraints.hsk_identities contains duplicates")

    if tier == "CURRENT_LESSON":
        if not scope.get("lesson_locator"):
            _fail(f"{line_label}.expected_scope requires lesson_locator for CURRENT_LESSON")
        lesson_context = case.get("lesson_context")
        if lesson_context and scope["lesson_locator"] != lesson_context["lesson_locator"]:
            _fail(f"{line_label} expected scope and lesson_context locators differ")

    bucket_contract = {
        "CURRENT_LESSON_ANSWERABLE": ("CURRENT_LESSON", "ANSWER", "INTERNAL_CHUNK"),
        "INTERNAL_KB_FALLBACK": ("INTERNAL_KB", "FALLBACK_INTERNAL", "INTERNAL_CHUNK"),
        "TRUSTED_EXTERNAL_FALLBACK": ("TRUSTED_EXTERNAL", "FALLBACK_EXTERNAL", "EXTERNAL_URL"),
    }
    if bucket in bucket_contract:
        required_tier, required_behavior, required_source_kind = bucket_contract[bucket]
        if (tier, behavior) != (required_tier, required_behavior):
            _fail(f"{line_label} has bucket-specific tier/behavior mismatch")
        if bucket != "TRUSTED_EXTERNAL_FALLBACK" and "lesson_context" not in case:
            _fail(f"{line_label} requires lesson_context for its bucket")
        if case["review_status"] == "APPROVED" and not case["expected_information"]:
            _fail(f"{line_label} approved answerable case has empty expected_information")
        if case["review_status"] == "APPROVED" and not all_evidence:
            _fail(f"{line_label} approved answerable case has no required/acceptable evidence")
        if not required_evidence or any(item["source_kind"] != required_source_kind for item in required_evidence):
            _fail(f"{line_label} requires required evidence of source_kind {required_source_kind}")
    elif bucket == "NO_EVIDENCE_REFUSAL":
        if (tier, behavior) != ("NONE", "REFUSE_NO_EVIDENCE"):
            _fail(f"{line_label} has invalid NO_EVIDENCE_REFUSAL tier/behavior")
        if required_evidence or acceptable_evidence or case["expected_citation_sources"]:
            _fail(f"{line_label} NO_EVIDENCE_REFUSAL must not expect evidence or citations")
    elif bucket == "OUT_OF_DOMAIN_REFUSAL":
        if (tier, behavior) != ("NONE", "REFUSE_OUT_OF_DOMAIN"):
            _fail(f"{line_label} has invalid OUT_OF_DOMAIN_REFUSAL tier/behavior")
        if required_evidence or acceptable_evidence or case["expected_citation_sources"]:
            _fail(f"{line_label} OUT_OF_DOMAIN_REFUSAL must not expect evidence or citations")
    elif bucket == "MULTI_TURN_CONTEXT":
        if not case.get("conversation_context"):
            _fail(f"{line_label} MULTI_TURN_CONTEXT requires non-empty conversation_context")
        normal_behavior = {
            "CURRENT_LESSON": "ANSWER",
            "INTERNAL_KB": "FALLBACK_INTERNAL",
            "TRUSTED_EXTERNAL": "FALLBACK_EXTERNAL",
        }
        if tier not in normal_behavior or behavior != normal_behavior[tier]:
            _fail(f"{line_label} MULTI_TURN_CONTEXT requires a normal tier/behavior pair")
        # Retrieval sufficiency of the current turn is a manual semantic review.

    return case


def _read_json(path: Path, label: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"{label} cannot be read as UTF-8 JSON: {exc}")


def _parse_jsonl_content(content: str, label: str, expected_split: str, manifest: dict) -> list[dict]:
    cases = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            _fail(f"{label}:{line_number} is a blank line; JSONL permits one object per line")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            _fail(f"{label}:{line_number} has invalid JSON: {exc}")
        cases.append(_validate_case(
            value, expected_split=expected_split, manifest=manifest,
            line_label=f"{label}:{line_number}",
        ))
    return cases


def _read_jsonl(path: Path, expected_split: str, manifest: dict) -> list[dict]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _fail(f"{path.name} cannot be read as UTF-8: {exc}")
    return _parse_jsonl_content(content, path.name, expected_split, manifest)


def validate_dataset(dataset_dir: Path | str, mode: str = "STRUCTURAL") -> dict:
    """Validate dataset structure or enforce the manually approved official gate."""
    mode = mode.upper()
    if mode not in {"STRUCTURAL", "OFFICIAL_GATE"}:
        _fail("mode must be STRUCTURAL or OFFICIAL_GATE")
    dataset_dir = Path(dataset_dir)
    schema_path = dataset_dir.parents[2] / SCHEMA_RELATIVE_PATH
    schema = _read_json(schema_path, "EvaluationCase schema")
    if not isinstance(schema, dict):
        _fail("EvaluationCase schema must be a JSON object")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        _fail("EvaluationCase schema must declare JSON Schema 2020-12")
    manifest = _validate_manifest(
        _read_json(dataset_dir / MANIFEST_RELATIVE_PATH, "manifest"), dataset_dir, schema
    )
    cases = []
    for split, filename in SPLIT_FILES.items():
        cases.extend(_read_jsonl(dataset_dir / filename, split, manifest))

    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        _fail("duplicate case_id across development/holdout dataset files")
    for split in SPLITS:
        split_ids = [case["case_id"] for case in cases if case["split"] == split]
        if split_ids != sorted(split_ids):
            _fail(f"{split} cases must be ordered by case_id")

    status_counts = Counter(case["review_status"] for case in cases)
    bucket_counts = Counter(case["bucket"] for case in cases)
    approved = [case for case in cases if case["review_status"] == "APPROVED"]
    approved_bucket_counts = Counter(case["bucket"] for case in approved)
    approved_bucket_split_counts = Counter((case["bucket"], case["split"]) for case in approved)
    split_counts = Counter(case["split"] for case in cases)
    approved_split_counts = Counter(case["split"] for case in approved)
    actual = {
        "case_count_total": len(cases),
        "draft_count": status_counts["DRAFT"],
        "approved_count_total": len(approved),
        "rejected_count": status_counts["REJECTED"],
        "case_count_by_bucket": {bucket: bucket_counts[bucket] for bucket in BUCKETS},
        "approved_count_by_bucket": {bucket: approved_bucket_counts[bucket] for bucket in BUCKETS},
        "approved_split_count_by_bucket": {
            bucket: {split: approved_bucket_split_counts[(bucket, split)] for split in SPLITS}
            for bucket in BUCKETS
        },
        "development_count": split_counts["DEVELOPMENT"],
        "holdout_count": split_counts["HOLDOUT"],
        "approved_development_count": approved_split_counts["DEVELOPMENT"],
        "approved_holdout_count": approved_split_counts["HOLDOUT"],
    }
    for key, value in actual.items():
        if key not in manifest:
            continue
        if manifest[key] != value:
            _fail(f"manifest.{key} mismatch: expected {value!r}, found {manifest[key]!r}")

    report = {"mode": mode, **actual}
    if mode == "OFFICIAL_GATE":
        mismatches = []
        if actual["approved_count_total"] != 60:
            mismatches.append(f"approved_count_total={actual['approved_count_total']} (expected 60)")
        if actual["approved_development_count"] != 48:
            mismatches.append(f"approved_development_count={actual['approved_development_count']} (expected 48)")
        if actual["approved_holdout_count"] != 12:
            mismatches.append(f"approved_holdout_count={actual['approved_holdout_count']} (expected 12)")
        for bucket, expected in OFFICIAL_APPROVED_COUNTS.items():
            found = actual["approved_count_by_bucket"][bucket]
            if found != expected:
                mismatches.append(f"{bucket}={found} (expected {expected})")
            for split, expected_split_count in OFFICIAL_APPROVED_SPLIT_COUNTS[bucket].items():
                found_split_count = actual["approved_split_count_by_bucket"][bucket][split]
                if found_split_count != expected_split_count:
                    mismatches.append(
                        f"{bucket}/{split}={found_split_count} (expected {expected_split_count})"
                    )
        if mismatches:
            raise ReviewRequiredError("Official approval gate not met: " + "; ".join(mismatches))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir", type=Path,
        default=Path(__file__).parent / "datasets" / "lesson_chat_rag" / "v0",
    )
    parser.add_argument("--mode", choices=("STRUCTURAL", "OFFICIAL_GATE"), default="STRUCTURAL")
    args = parser.parse_args(argv)
    try:
        report = validate_dataset(args.dataset_dir, args.mode)
    except ReviewRequiredError as exc:
        print(f"REVIEW_REQUIRED: {exc}", file=sys.stderr)
        return 2
    except DatasetValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
