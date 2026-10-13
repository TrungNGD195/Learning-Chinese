from __future__ import annotations

from typing import Any

from app.evaluation.step73.evaluation import evidence_groups, grade_candidate

from .citations import evaluate_citation_semantics
from .contracts import ActualBehavior, CRITICAL_FAILURES, RESULT_SCHEMA_VERSION, E2ECaseResult

ANSWER_BEHAVIORS = {ActualBehavior.ANSWER, ActualBehavior.FALLBACK_INTERNAL,
                    ActualBehavior.FALLBACK_EXTERNAL}


def derive_actual_behavior(trace: dict[str, Any]) -> ActualBehavior:
    """Derive behavior exclusively from captured production events, never expected labels."""
    citation = trace.get("citation_validation") or {}
    deterministic_citation_failure = (
        not citation.get("valid", True)
        and citation.get("error_code") in {
            "CITATION_MISSING", "CITATION_FORMAT_INVALID", "CITATION_UNKNOWN_SOURCE",
            "CITATION_SOURCE_RESOLUTION_FAILED", "CITATION_EXTERNAL_URL_INVALID",
        }
    )
    if ((trace.get("technical_error") or {}).get("code")
            or (trace.get("persistence") or {}).get("error_code")):
        return ActualBehavior.TECHNICAL_FAILURE
    if trace.get("actual_behavior") == ActualBehavior.TECHNICAL_FAILURE:
        return ActualBehavior.TECHNICAL_FAILURE
    if any(row.get("retrieval_status") == "TECHNICAL_FAILURE"
           or row.get("rerank_status") == "TECHNICAL_FAILURE"
           for row in trace.get("tiers_attempted", [])):
        return ActualBehavior.TECHNICAL_FAILURE
    domain = trace.get("domain_guard", {})
    if (domain.get("status") == "REFUSED" and domain.get("out_of_domain_detected") is True
            and not trace.get("generation", {}).get("called")):
        return ActualBehavior.REFUSE_OUT_OF_DOMAIN
    selected = trace.get("selected_tier")
    generation = trace.get("generation", {})
    status = trace.get("persistence", {}).get("final_message_status")
    if generation.get("error_code") or (status == "FAILED" and not deterministic_citation_failure):
        return ActualBehavior.TECHNICAL_FAILURE
    if selected == "CURRENT_LESSON" and generation.get("called"):
        return ActualBehavior.ANSWER
    if selected == "INTERNAL_KB" and generation.get("called"):
        return ActualBehavior.FALLBACK_INTERNAL
    if selected == "TRUSTED_EXTERNAL" and generation.get("called"):
        return ActualBehavior.FALLBACK_EXTERNAL
    if selected in (None, "NONE") and trace.get("semantic_no_evidence") is True:
        return ActualBehavior.REFUSE_NO_EVIDENCE
    return ActualBehavior.TECHNICAL_FAILURE


def _selected_evidence_satisfies_step73(case: dict, selected: list[dict]) -> bool:
    """Use Step 7.3 internal groups and frozen exact-URL external identities."""
    groups, grades, _ = evidence_groups(case)
    external_groups: dict[str, set[str]] = {}
    for evidence in case.get("required_evidence", []):
        if evidence.get("source_kind") != "EXTERNAL_URL":
            continue
        requirement_id = evidence.get("requirement_id")
        url = evidence.get("url")
        if not requirement_id or not isinstance(url, str) or not url:
            return False
        external_groups.setdefault(requirement_id, set()).add(url)
    if not groups and not external_groups:
        return False
    seen: set[int] = set()
    for item in selected:
        locators = set(item.get("stable_locators") or [])
        if item.get("stable_locator"):
            locators.add(item["stable_locator"])
        for index, group in enumerate(groups):
            # This is the Step 7.3 group identity rule: any equivalent locator in a
            # required group satisfies that requirement; irrelevant evidence cannot.
            if grade_candidate(locators & group, grades) > 0:
                seen.add(index)
    required_count = len(groups) + len(external_groups)
    seen_external: set[str] = set()
    selected_urls = {row.get("url") for row in selected if row.get("source_kind") == "EXTERNAL_URL"}
    for index, alternatives in enumerate(external_groups.values(), start=len(groups)):
        if alternatives & selected_urls:
            seen_external.add(str(index))
    return len(seen) + len(seen_external) == required_count


def _scope_matches(case: dict, selected: list[dict]) -> bool:
    expected = case.get("expected_scope") or {}
    scope_kind = expected.get("scope_kind")
    if scope_kind == "CURRENT_LESSON":
        lesson = expected.get("lesson_locator")
        return bool(lesson) and all(
            row.get("lesson_locator") == lesson
            or lesson in (row.get("stable_locators") or [])
            for row in selected
        )
    if scope_kind == "INTERNAL_KB":
        return all(row.get("source_kind") != "EXTERNAL_URL" for row in selected)
    if scope_kind == "TRUSTED_EXTERNAL":
        return all(row.get("source_kind") == "EXTERNAL_URL" for row in selected)
    return not selected if scope_kind == "NONE" else False


def _context_isolation_ok(trace: dict, case: dict | None = None) -> bool:
    prompt = trace.get("prompt", {})
    memory = trace.get("memory", {})
    judge_context = (trace.get("judge_result") or {}).get("context_adherence", {})
    if not prompt.get("built"):
        return not trace.get("generation", {}).get("called")
    source_map = prompt.get("source_map_snapshot") or {}
    context_labels = {block.get("label") for block in prompt.get("context_blocks", [])
                      if isinstance(block, dict) and block.get("label")}
    memory_labels = set(memory.get("historical_citation_labels") or [])
    selected_labels = {row.get("label") for row in trace.get("selected_evidence", []) if row.get("label")}
    if context_labels and not context_labels.issubset(source_map):
        return False
    if selected_labels and set(source_map) != selected_labels:
        return False
    if memory_labels & set(source_map):
        return False
    if memory.get("applied") and memory.get("historical_citation_markers_removed") is not True:
        return False
    if any(judge_context.get(key) is True for key in (
        "material_violation", "memory_used_as_evidence", "historical_citation_label_leak",
        "current_evidence_overridden_by_history")):
        return False
    if case and case.get("bucket") == "MULTI_TURN_CONTEXT":
        required_turns = len(case.get("conversation_context") or [])
        snapshot = memory.get("sanitized_context")
        turns = (snapshot or {}).get("turns") if isinstance(snapshot, dict) else None
        if not (
            required_turns > 0
            and memory.get("production_path_ran") is True
            and memory.get("builder_invocation_count", 0) >= 1
            and memory.get("composition_applied") is True
            and memory.get("applied") is True
            and memory.get("dropped_after_preflight") is not True
            and memory.get("selected_turn_count") == required_turns
            and memory.get("generation_selected_turn_count") == required_turns
            and isinstance(turns, list)
            and len(turns) == required_turns
            and memory.get("sanitized_context_sha256")
            and memory.get("historical_citation_markers_removed") is True
            and isinstance(trace.get("judge_result"), dict)
            and isinstance(judge_context, dict)
            and all(judge_context.get(key) is False for key in (
                "material_violation", "memory_used_as_evidence",
                "historical_citation_label_leak", "current_evidence_overridden_by_history",
            ))
        ):
            return False
    return True


def _tier_policy_ok(case: dict, trace: dict, selected_tier: str) -> bool:
    order = {"CURRENT_LESSON": 0, "INTERNAL_KB": 1, "TRUSTED_EXTERNAL": 2}
    attempted = [row.get("tier") for row in trace.get("tiers_attempted", [])]
    if any(tier not in order for tier in attempted):
        return False
    if [order[tier] for tier in attempted] != sorted(order[tier] for tier in attempted):
        return False
    if selected_tier != "NONE" and (selected_tier not in attempted or attempted[-1] != selected_tier):
        return False
    if any(row.get("usable_higher_priority_evidence") and row.get("tier") != selected_tier
           for row in trace.get("tiers_attempted", [])):
        return False
    behavior = case.get("expected_behavior")
    if behavior == "REFUSE_NO_EVIDENCE":
        return trace.get("all_applicable_tiers_semantically_exhausted") is True
    if behavior == "REFUSE_OUT_OF_DOMAIN" and case.get("expected_tier") == "NONE":
        return selected_tier == "NONE"
    expected = case.get("expected_tier")
    expected_attempts = {"CURRENT_LESSON": ["CURRENT_LESSON"],
                         "INTERNAL_KB": ["CURRENT_LESSON", "INTERNAL_KB"],
                         "TRUSTED_EXTERNAL": ["CURRENT_LESSON", "INTERNAL_KB", "TRUSTED_EXTERNAL"]}
    return selected_tier == expected and attempted == expected_attempts.get(expected, [])


def _critical_failures(case: dict, trace: dict, actual: ActualBehavior) -> list[str]:
    failures: list[str] = []
    expected_behavior = case.get("expected_behavior")
    if expected_behavior == "REFUSE_OUT_OF_DOMAIN" and actual in ANSWER_BEHAVIORS:
        failures.append("OUT_OF_DOMAIN_ANSWER")
    if trace.get("scope_violation") is True or any(
            tier.get("scope_violation") is True for tier in trace.get("tiers_attempted", [])):
        failures.append("RETRIEVAL_SCOPE_VIOLATION")
    if _tier_policy_violation_from_facts(trace):
        failures.append("TIER_FALLBACK_POLICY_VIOLATION")
    if _technical_failure_reclassified_from_facts(trace, actual):
        failures.append("TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE")
    if _confident_answer_with_insufficient_evidence(trace):
        failures.append("CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE")
    citation = trace.get("citation_validation", {})
    if not citation.get("valid", True) and citation.get("error_code") in {
            "CITATION_FORMAT_INVALID", "CITATION_UNKNOWN_SOURCE", "CITATION_EXTERNAL_URL_INVALID"}:
        failures.append("FABRICATED_CITATION_OR_SOURCE")
    if not citation.get("valid", True) and citation.get("error_code") == "CITATION_SOURCE_RESOLUTION_FAILED":
        failures.append("CITATION_PROVENANCE_MISMATCH")
    if not citation.get("valid", True) and citation.get("error_code") == "CITATION_MISSING":
        failures.append("REQUIRED_CITATION_MISSING")
    failures.extend(trace.get("deterministic_critical_failures") or [])
    judge = trace.get("judge_result") or {}
    failures.extend(judge.get("semantic_critical_failures") or [])
    unique = list(dict.fromkeys(failures))
    invalid = set(unique) - set(CRITICAL_FAILURES)
    if invalid:
        raise ValueError(f"E2E_CRITICAL_FAILURE_ENUM_INVALID: {sorted(invalid)}")
    return unique


def _tier_gate_from_runtime(row: dict) -> bool:
    """Recompute usable evidence from the captured reranker scores and gate."""
    threshold = row.get("evidence_gate_threshold")
    scores = [candidate.get("rerank_score") for candidate in row.get("reranked_evidence", [])]
    scores = [score for score in scores if isinstance(score, (int, float)) and not isinstance(score, bool)]
    if threshold is not None and scores:
        return any(score >= threshold for score in scores)
    return row.get("evidence_gate_passed") is True


def _tier_policy_violation_from_facts(trace: dict) -> bool:
    order = {"CURRENT_LESSON": 0, "INTERNAL_KB": 1, "TRUSTED_EXTERNAL": 2}
    rows = trace.get("tiers_attempted") or []
    names = [row.get("tier") for row in rows]
    if any(name not in order for name in names):
        return True
    if names != sorted(names, key=order.__getitem__) or len(names) != len(set(names)):
        return True
    selected = trace.get("selected_tier") or "NONE"
    if selected != "NONE" and (selected not in names or not names or names[-1] != selected):
        return True
    for index, row in enumerate(rows):
        usable = _tier_gate_from_runtime(row)
        if usable and index != len(rows) - 1:
            return True
        if row.get("retrieval_status") == "TECHNICAL_FAILURE" or row.get("rerank_status") == "TECHNICAL_FAILURE":
            if index < len(rows) - 1:
                return True
    if (selected == "NONE" and not _trace_has_technical_failure(trace)
            and any(_tier_gate_from_runtime(row) for row in rows)):
        return True
    if selected != "NONE" and rows and not _tier_gate_from_runtime(rows[-1]):
        return True
    return False


def _trace_has_technical_failure(trace: dict) -> bool:
    return bool(trace.get("technical_error") or (trace.get("persistence") or {}).get("error_code")
                or (trace.get("generation") or {}).get("error_code")
                or (trace.get("persistence") or {}).get("final_message_status") == "FAILED"
                or any(row.get("retrieval_status") == "TECHNICAL_FAILURE"
                       or row.get("rerank_status") == "TECHNICAL_FAILURE"
                       for row in trace.get("tiers_attempted", [])))


def _technical_failure_reclassified_from_facts(trace: dict, actual: ActualBehavior) -> bool:
    if not _trace_has_technical_failure(trace):
        return False
    return bool(trace.get("semantic_no_evidence")
                or actual == ActualBehavior.REFUSE_NO_EVIDENCE
                or ((trace.get("persistence") or {}).get("final_message_status") == "COMPLETED"
                    and not (trace.get("generation") or {}).get("called")))


def _confident_answer_with_insufficient_evidence(trace: dict) -> bool:
    if not (trace.get("generation") or {}).get("called"):
        return False
    selected = trace.get("selected_tier") or "NONE"
    if selected == "NONE":
        return True
    rows = [row for row in trace.get("tiers_attempted", []) if row.get("tier") == selected]
    return not rows or not _tier_gate_from_runtime(rows[-1])


def evaluate_case(case: dict, trace: dict, *, judge_completed: bool = False) -> dict:
    """Compare a completed actual trace with labels; never feeds labels into execution."""
    actual = derive_actual_behavior(trace)
    expected_behavior = case["expected_behavior"]
    expected_tier = case["expected_tier"]
    selected_tier = trace.get("selected_tier") or "NONE"
    selected = trace.get("selected_evidence") or []
    technical_ok = actual != ActualBehavior.TECHNICAL_FAILURE
    scope_ok = not trace.get("scope_violation", False) and not any(
        tier.get("scope_violation", False) for tier in trace.get("tiers_attempted", []))
    evidence_gate_ok = selected_tier == "NONE" or trace.get("selected_evidence_gate_passed") is True
    scope_matches = _scope_matches(case, selected)

    if expected_behavior in {"ANSWER", "FALLBACK_INTERNAL", "FALLBACK_EXTERNAL"}:
        retrieval_ok = (technical_ok and scope_ok and evidence_gate_ok and scope_matches
                        and _selected_evidence_satisfies_step73(case, selected))
    elif expected_behavior == "REFUSE_NO_EVIDENCE":
        tiers = trace.get("tiers_attempted", [])
        retrieval_ok = (technical_ok and scope_ok and not selected
                        and trace.get("all_applicable_tiers_semantically_exhausted") is True
                        and bool(tiers) and all(row.get("retrieval_status") == "SUCCESS"
                                                and row.get("rerank_status") in {"SUCCESS", "NOT_APPLICABLE"}
                                                for row in tiers))
    elif expected_behavior == "REFUSE_OUT_OF_DOMAIN":
        retrieval_ok = selected_tier == "NONE" and not selected and scope_ok
    else:
        raise ValueError("E2E_EXPECTED_BEHAVIOR_INVALID")

    if expected_behavior in {"ANSWER", "FALLBACK_INTERNAL", "FALLBACK_EXTERNAL"}:
        refusal_ok = actual in ANSWER_BEHAVIORS
    elif expected_behavior == "REFUSE_NO_EVIDENCE":
        refusal_ok = (actual == ActualBehavior.REFUSE_NO_EVIDENCE
                      and not trace.get("generation", {}).get("called")
                      and trace.get("persistence", {}).get("final_message_status") == "COMPLETED"
                      and trace.get("generation", {}).get("answer") == trace.get("frozen_no_evidence_content")
                      and not trace.get("citation_validation", {}).get("validated_citations"))
    else:  # D-105: generic no-evidence and technical failure are never OOD refusal.
        refusal_ok = (actual == ActualBehavior.REFUSE_OUT_OF_DOMAIN
                      and not trace.get("generation", {}).get("called")
                      and selected_tier == "NONE")

    generation_called = bool(trace.get("generation", {}).get("called"))
    generation_applicable = generation_called
    critical = _critical_failures(case, trace, actual)
    judge_failures = set((trace.get("judge_result") or {}).get("semantic_critical_failures") or [])
    generation_criticals = {"SERIOUS_FACTUAL_ERROR", "UNSUPPORTED_CONFIDENT_CLAIM",
                            "CONTRADICTED_BY_EVIDENCE"}
    generation_ok = (judge_completed and not (judge_failures & generation_criticals)) if generation_applicable else not generation_called
    citation_applicable = generation_called
    citation_trace = trace.get("citation_validation", {})
    citations = citation_trace.get("validated_citations") or []
    if citation_applicable:
        semantic_citations = evaluate_citation_semantics(
            claims=(trace.get("judge_result") or {}).get("claims") or [],
            current_citation_labels=set(citation_trace.get("cited_labels") or []),
            source_map=trace.get("prompt", {}).get("source_map_snapshot") or {},
            persisted_citations=trace.get("persistence", {}).get("persisted_citations") or [],
        )
        critical.extend(semantic_citations["critical_failures"])
        critical = list(dict.fromkeys(critical))
        citation_correctness_ok = (bool(citation_trace.get("valid"))
                                   and semantic_citations["citation_correctness_ok"])
        citation_coverage_ok = semantic_citations["citation_coverage_ok"]
        citation_ok = citation_correctness_ok and citation_coverage_ok
    else:
        empty_persistence = trace.get("persistence", {}).get("message_citation_count", 0) == 0
        citation_correctness_ok = (not citation_trace.get("attempted") and not citations
                                   and empty_persistence)
        citation_coverage_ok = citation_correctness_ok
        citation_ok = citation_correctness_ok
    context_applicable = bool(trace.get("prompt", {}).get("built"))
    context_ok = _context_isolation_ok(trace, case)
    fallback_ok = _tier_policy_ok(case, trace, selected_tier)
    technical_ok = technical_ok and trace.get("technical_error") is None
    e2e_pass = all((retrieval_ok, generation_ok, citation_ok, context_ok, fallback_ok,
                    refusal_ok, technical_ok)) and not critical
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "execution_id": trace["execution_id"], "case_id": case["case_id"],
        "split": case["split"], "bucket": case["bucket"], "repeat_index": trace["repeat_index"],
        "expected": {"tier": expected_tier, "behavior": expected_behavior,
                     "scope": case.get("expected_scope")},
        "actual": {"behavior": actual.value, "selected_tier": selected_tier,
                   "final_message_status": trace.get("persistence", {}).get("final_message_status")},
        "trace": trace, "retrieval_ok": retrieval_ok,
        "generation_applicable": generation_applicable, "generation_ok": generation_ok,
        "citation_applicable": citation_applicable, "citation_correctness_ok": citation_correctness_ok,
        "citation_coverage_ok": citation_coverage_ok, "citation_ok": citation_ok,
        "context_applicable": context_applicable, "context_ok": context_ok,
        "fallback_ok": fallback_ok, "refusal_ok": refusal_ok, "technical_ok": technical_ok,
        "generation_dimension_scores": (trace.get("judge_result") or {}).get("generation_dimension_scores"),
        "semantic_claims": (trace.get("judge_result") or {}).get("claims"),
        "critical_failures": critical, "e2e_case_pass": e2e_pass, "evaluator_errors": [],
    }
    return E2ECaseResult.model_validate(result).model_dump(mode="json")


def assert_expectations_are_post_execution(case: dict, trace_before_execution: dict) -> None:
    """Guard for adapters: traces may not contain labels before execution starts."""
    forbidden = {"expected_behavior", "expected_tier", "expected_scope"}
    if forbidden & trace_before_execution.keys():
        raise ValueError("EXPECTED_LABELS_MUST_NOT_ENTER_EXECUTION_TRACE")
