from __future__ import annotations


def evaluate_citation_semantics(*, claims: list[dict], current_citation_labels: set[str],
                                source_map: dict[str, dict], persisted_citations: list[dict]) -> dict:
    """Deterministic claim-level citation correctness and coverage checks."""
    failures: list[str] = []
    correctness = True
    coverage = True
    for claim in claims:
        cited = set(claim.get("cited_labels") or [])
        supporting = set(claim.get("supporting_labels") or [])
        if cited - current_citation_labels or cited - source_map.keys():
            correctness = False
            failures.append("FABRICATED_CITATION_OR_SOURCE")
            continue
        # Every label asserted as support must point to the exact current source map.
        if cited and not cited.issubset(supporting):
            correctness = False
        if claim.get("requires_grounding") and (
                not cited or not (cited & supporting)):
            coverage = False
            failures.append("REQUIRED_CITATION_MISSING")
    for persisted in persisted_citations:
        label = persisted.get("label")
        expected = source_map.get(label)
        if expected is None or any(persisted.get(key) != expected.get(key)
                                   for key in ("source_kind", "source_id", "url", "chunk_id")):
            correctness = False
            failures.append("CITATION_PROVENANCE_MISMATCH")
    return {"citation_correctness_ok": correctness, "citation_coverage_ok": coverage,
            "citation_ok": correctness and coverage,
            "critical_failures": list(dict.fromkeys(failures))}
