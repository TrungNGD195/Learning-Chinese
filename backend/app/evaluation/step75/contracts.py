from __future__ import annotations

from enum import StrEnum
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


TRACE_SCHEMA_VERSION = "1.0.0"
RESULT_SCHEMA_VERSION = "1.0.0"
POLICY_VERSION = "lesson-chat-e2e-policy/v1"
CITATION_SEMANTICS_VERSION = "lesson-chat-citation-semantics/v1"
JUDGE_PROMPT_VERSION = "lesson-chat-e2e-judge/v1"
RUBRIC_VERSION = "lesson-chat-e2e-rubric/v1"
JUDGE_SCHEMA_VERSION = "1.0.0"
ANNOTATION_VERSION = "lesson-chat-e2e-human/v0.1.0"

CRITICAL_FAILURES = (
    "SERIOUS_FACTUAL_ERROR", "UNSUPPORTED_CONFIDENT_CLAIM", "CONTRADICTED_BY_EVIDENCE",
    "FABRICATED_CITATION_OR_SOURCE", "CITATION_PROVENANCE_MISMATCH", "REQUIRED_CITATION_MISSING",
    "RETRIEVAL_SCOPE_VIOLATION", "TIER_FALLBACK_POLICY_VIOLATION",
    "OUT_OF_DOMAIN_ANSWER", "CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE",
    "TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE",
)
JUDGE_CRITICAL_FAILURES = (
    "SERIOUS_FACTUAL_ERROR", "UNSUPPORTED_CONFIDENT_CLAIM", "CONTRADICTED_BY_EVIDENCE",
    "FABRICATED_CITATION_OR_SOURCE", "REQUIRED_CITATION_MISSING",
)
DIMENSIONS = ("answer_correctness", "faithfulness_groundedness", "completeness",
              "language_quality", "learning_usefulness")


class ActualBehavior(StrEnum):
    ANSWER = "ANSWER"
    FALLBACK_INTERNAL = "FALLBACK_INTERNAL"
    FALLBACK_EXTERNAL = "FALLBACK_EXTERNAL"
    REFUSE_NO_EVIDENCE = "REFUSE_NO_EVIDENCE"
    REFUSE_OUT_OF_DOMAIN = "REFUSE_OUT_OF_DOMAIN"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


class TierAttemptTrace(BaseModel):
    model_config = ConfigDict(extra="allow")
    tier: Literal["CURRENT_LESSON", "INTERNAL_KB", "TRUSTED_EXTERNAL"]
    attempt_index: StrictInt = Field(ge=1)
    scope_identity: str
    retrieval_status: Literal["SUCCESS", "TECHNICAL_FAILURE"]
    semantic_candidates: list[dict] = Field(default_factory=list)
    candidate_count: StrictInt = Field(ge=0)
    rerank_status: Literal["SUCCESS", "TECHNICAL_FAILURE", "NOT_APPLICABLE"]
    reranked_evidence: list[dict] = Field(default_factory=list)
    max_rerank_score: float | None = None
    evidence_gate_threshold: float | None = None
    evidence_gate_passed: StrictBool = False
    scope_violation: StrictBool = False
    retrieval_latency_ms: StrictInt | None = Field(default=None, ge=0)
    rerank_latency_ms: StrictInt | None = Field(default=None, ge=0)
    error_code: str | None = None


class E2EExecutionTrace(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: Literal["1.0.0"] = TRACE_SCHEMA_VERSION
    execution_id: str
    case_id: str
    repeat_index: StrictInt = Field(ge=1)
    conversation: dict
    domain_guard: dict
    tiers_attempted: list[TierAttemptTrace]
    selected_tier: Literal["CURRENT_LESSON", "INTERNAL_KB", "TRUSTED_EXTERNAL", "NONE"] | None = None
    selected_evidence: list[dict] = Field(default_factory=list)
    prompt: dict
    memory: dict
    generation: dict
    citation_validation: dict
    persistence: dict
    actual_behavior: ActualBehavior
    technical_error: dict | None = None
    timings: dict


class E2ECaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0.0"] = RESULT_SCHEMA_VERSION
    execution_id: str
    case_id: str
    split: Literal["DEVELOPMENT", "HOLDOUT"]
    bucket: str
    repeat_index: StrictInt = Field(ge=1)
    expected: dict
    actual: dict
    trace: dict
    retrieval_ok: StrictBool
    generation_applicable: StrictBool
    generation_ok: StrictBool
    citation_applicable: StrictBool
    citation_correctness_ok: StrictBool
    citation_coverage_ok: StrictBool
    citation_ok: StrictBool
    context_applicable: StrictBool
    context_ok: StrictBool
    fallback_ok: StrictBool
    refusal_ok: StrictBool
    technical_ok: StrictBool
    generation_dimension_scores: dict | None = None
    semantic_claims: list[dict] | None = None
    critical_failures: list[str]
    e2e_case_pass: StrictBool
    evaluator_errors: list[str]

    @model_validator(mode="after")
    def validate_hard_validity_formula(self):
        if self.citation_ok != (self.citation_correctness_ok and self.citation_coverage_ok):
            raise ValueError("E2E_CITATION_BOOLEAN_FORMULA_MISMATCH")
        required = (self.retrieval_ok and self.generation_ok and self.citation_ok
                    and self.context_ok and self.fallback_ok and self.refusal_ok
                    and self.technical_ok and not self.critical_failures)
        if self.e2e_case_pass != required:
            raise ValueError("E2E_D103_BOOLEAN_FORMULA_MISMATCH")
        if set(self.critical_failures) - set(CRITICAL_FAILURES):
            raise ValueError("E2E_CRITICAL_FAILURE_ENUM_INVALID")
        if len(self.critical_failures) != len(set(self.critical_failures)):
            raise ValueError("E2E_CRITICAL_FAILURE_DUPLICATED")
        return self


class ClaimVerdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    score: StrictInt = Field(ge=0, le=2)
    rationale: str = Field(min_length=1)


class E2EClaimEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claim_id: str = Field(pattern=r"^C[1-9][0-9]*$")
    claim_text: str = Field(min_length=1)
    requires_grounding: StrictBool
    cited_labels: list[str]
    supporting_labels: list[str]
    verdict: ClaimVerdict
    concise_rationale: str = Field(min_length=1)


class ContextAdherence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    material_violation: StrictBool
    memory_used_as_evidence: StrictBool
    historical_citation_label_leak: StrictBool
    current_evidence_overridden_by_history: StrictBool
    concise_rationale: str = Field(min_length=1)


class E2EJudgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.0.0"]
    case_id: str = Field(min_length=1)
    repeat_index: StrictInt = Field(ge=1)
    generation_dimension_scores: dict[str, DimensionScore]
    claims: list[E2EClaimEvaluation]
    context_adherence: ContextAdherence
    semantic_critical_failures: list[str]
    concise_overall_rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_frozen_semantics(self):
        if set(self.generation_dimension_scores) != set(DIMENSIONS):
            raise ValueError("JUDGE_DIMENSIONS_MUST_MATCH_FROZEN_SET")
        ids = [claim.claim_id for claim in self.claims]
        if ids != [f"C{i}" for i in range(1, len(ids) + 1)]:
            raise ValueError("JUDGE_CLAIM_IDS_NOT_CONTIGUOUS")
        if (len(self.semantic_critical_failures) != len(set(self.semantic_critical_failures))
                or set(self.semantic_critical_failures) - set(JUDGE_CRITICAL_FAILURES)):
            raise ValueError("JUDGE_CRITICAL_FAILURE_ENUM_INVALID")
        scores = self.generation_dimension_scores
        verdicts = {claim.verdict for claim in self.claims}
        failures = set(self.semantic_critical_failures)
        if ClaimVerdict.CONTRADICTED in verdicts and (
                scores["faithfulness_groundedness"].score != 0
                or "CONTRADICTED_BY_EVIDENCE" not in failures):
            raise ValueError("JUDGE_CONTRADICTION_CROSS_FIELD_INVALID")
        if "CONTRADICTED_BY_EVIDENCE" in failures and ClaimVerdict.CONTRADICTED not in verdicts:
            raise ValueError("JUDGE_CONTRADICTED_FAILURE_WITHOUT_CLAIM")
        if "UNSUPPORTED_CONFIDENT_CLAIM" in failures and (
                ClaimVerdict.UNSUPPORTED not in verdicts
                or scores["faithfulness_groundedness"].score == 2):
            raise ValueError("JUDGE_UNSUPPORTED_FAILURE_CONFLICT")
        if scores["faithfulness_groundedness"].score == 2 and verdicts & {
                ClaimVerdict.UNSUPPORTED, ClaimVerdict.CONTRADICTED}:
            raise ValueError("JUDGE_FAITHFULNESS_SCORE_CONFLICT")
        if "SERIOUS_FACTUAL_ERROR" in failures and scores["answer_correctness"].score != 0:
            raise ValueError("JUDGE_FACTUAL_ERROR_SCORE_CONFLICT")
        if any(claim.requires_grounding
               and not (set(claim.supporting_labels) & set(claim.cited_labels))
               for claim in self.claims):
            if "REQUIRED_CITATION_MISSING" not in failures:
                raise ValueError("JUDGE_REQUIRED_CITATION_FAILURE_MISSING")
        if (self.context_adherence.memory_used_as_evidence
                or self.context_adherence.historical_citation_label_leak
                or self.context_adherence.current_evidence_overridden_by_history):
            if not self.context_adherence.material_violation:
                raise ValueError("JUDGE_CONTEXT_VIOLATION_FLAG_REQUIRED")
        return self

    def validate_labels(self, *, case_id: str, repeat_index: int,
                        current_citation_labels: set[str], source_map_labels: set[str]) -> None:
        if self.case_id != case_id or self.repeat_index != repeat_index:
            raise ValueError("JUDGE_REQUEST_IDENTITY_MISMATCH")
        for claim in self.claims:
            if set(claim.cited_labels) - current_citation_labels:
                raise ValueError("JUDGE_UNKNOWN_CURRENT_CITATION_LABEL")
            if set(claim.supporting_labels) - source_map_labels:
                raise ValueError("JUDGE_UNKNOWN_SOURCE_MAP_LABEL")


class AnnotationStatus(StrEnum):
    DRAFT = "DRAFT"
    NEEDS_ADJUDICATION = "NEEDS_ADJUDICATION"
    HUMAN_APPROVED = "HUMAN_APPROVED"


class HumanE2EAnnotation(BaseModel):
    """DRAFT may be an unbound template; reviewed states require exact run bindings."""
    model_config = ConfigDict(extra="forbid")
    case_id: str
    repeat_index: int | None = None
    e2e_run_id: str | None = None
    execution_id: str | None = None
    generated_answer_sha256: str | None = None
    source_map_sha256: str | None = None
    validated_citations_sha256: str | None = None
    evidence_snapshot_sha256: str | None = None
    execution_output_sha256: str | None = None
    cases_artifact_sha256: str | None = None
    annotation_version: str = ANNOTATION_VERSION
    rubric_version: str = RUBRIC_VERSION
    generation_dimension_scores: dict[str, int] | None = None
    claims: list[E2EClaimEvaluation] | None = None
    context_adherence: ContextAdherence | None = None
    semantic_critical_failures: list[str] = Field(default_factory=list)
    concise_notes: str | None = None
    review_status: AnnotationStatus = AnnotationStatus.DRAFT

    @model_validator(mode="after")
    def validate_review_state(self):
        reviewed = self.review_status != AnnotationStatus.DRAFT
        bindings = (self.repeat_index == 1 and self.e2e_run_id and self.execution_id
                    and self.generated_answer_sha256 and self.source_map_sha256
                    and self.validated_citations_sha256 and self.evidence_snapshot_sha256
                    and self.execution_output_sha256 and self.cases_artifact_sha256)
        if reviewed and not bindings:
            raise ValueError("REVIEWED_ANNOTATION_REQUIRES_COMPLETE_RUNTIME_BINDING")
        if reviewed:
            for digest in (self.generated_answer_sha256, self.source_map_sha256,
                           self.validated_citations_sha256, self.evidence_snapshot_sha256,
                           self.execution_output_sha256, self.cases_artifact_sha256):
                if not re.fullmatch(r"[0-9a-f]{64}", digest or ""):
                    raise ValueError("REVIEWED_ANNOTATION_SHA256_INVALID")
        if self.review_status == AnnotationStatus.HUMAN_APPROVED:
            if self.generation_dimension_scores is None or set(self.generation_dimension_scores) != set(DIMENSIONS):
                raise ValueError("HUMAN_APPROVED_ANNOTATION_REQUIRES_FIVE_SCORES")
            if any(type(score) is not int or score not in (0, 1, 2)
                   for score in self.generation_dimension_scores.values()):
                raise ValueError("HUMAN_APPROVED_ANNOTATION_SCORE_INVALID")
            if self.claims is None or self.context_adherence is None:
                raise ValueError("HUMAN_APPROVED_ANNOTATION_REQUIRES_CLAIMS_AND_CONTEXT")
            claim_ids = [claim.claim_id for claim in self.claims]
            if claim_ids != [f"C{i}" for i in range(1, len(claim_ids) + 1)]:
                raise ValueError("HUMAN_ANNOTATION_CLAIM_IDS_NOT_CONTIGUOUS")
            if (len(self.semantic_critical_failures) != len(set(self.semantic_critical_failures))
                    or set(self.semantic_critical_failures) - set(JUDGE_CRITICAL_FAILURES)):
                raise ValueError("HUMAN_ANNOTATION_CRITICAL_FAILURE_ENUM_INVALID")
            verdicts = {claim.verdict for claim in self.claims}
            failures = set(self.semantic_critical_failures)
            faithfulness = self.generation_dimension_scores["faithfulness_groundedness"]
            if ClaimVerdict.CONTRADICTED in verdicts and (
                    faithfulness != 0 or "CONTRADICTED_BY_EVIDENCE" not in failures):
                raise ValueError("HUMAN_ANNOTATION_CONTRADICTION_CROSS_FIELD_INVALID")
            if "CONTRADICTED_BY_EVIDENCE" in failures and ClaimVerdict.CONTRADICTED not in verdicts:
                raise ValueError("HUMAN_ANNOTATION_CONTRADICTED_FAILURE_WITHOUT_CLAIM")
            if "SERIOUS_FACTUAL_ERROR" in failures and self.generation_dimension_scores["answer_correctness"] != 0:
                raise ValueError("HUMAN_ANNOTATION_FACTUAL_ERROR_SCORE_CONFLICT")
            if faithfulness == 2 and verdicts & {ClaimVerdict.UNSUPPORTED, ClaimVerdict.CONTRADICTED}:
                raise ValueError("HUMAN_ANNOTATION_FAITHFULNESS_SCORE_CONFLICT")
            if any(claim.requires_grounding
                   and not (set(claim.supporting_labels) & set(claim.cited_labels))
                   for claim in self.claims) and "REQUIRED_CITATION_MISSING" not in failures:
                raise ValueError("HUMAN_ANNOTATION_REQUIRED_CITATION_FAILURE_MISSING")
        if self.annotation_version != ANNOTATION_VERSION or self.rubric_version != RUBRIC_VERSION:
            raise ValueError("E2E_ANNOTATION_VERSION_MISMATCH")
        return self
