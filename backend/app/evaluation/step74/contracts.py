from __future__ import annotations

from enum import StrEnum
from typing import Literal
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


DIMENSIONS = (
    "answer_correctness",
    "faithfulness_groundedness",
    "completeness",
    "language_quality",
    "learning_usefulness",
)
CRITICAL_FAILURES = (
    "SERIOUS_FACTUAL_ERROR",
    "UNSUPPORTED_CONFIDENT_CLAIM",
    "CONTRADICTED_BY_EVIDENCE",
)
RUBRIC_VERSION = "lesson-chat-generation-rubric/v1"
JUDGE_PROMPT_VERSION = "lesson-chat-generation-judge/v1"
HUMAN_ANNOTATION_VERSION = "lesson-chat-generation-human/v0.1.0"
JUDGE_MODEL = "gpt-5.4-2026-03-05"
GENERATOR_MODEL = "gpt-5.4-mini-2026-03-17"
DATASET_VERSION = "v0.8.0"
DATASET_SCHEMA_VERSION = "1.0.0"
DATASET_NAME = "lesson_chat_rag"
ELIGIBLE_CASE_POLICY_VERSION = "step74-eligible/v1"
FIXED_EVIDENCE_POLICY_VERSION = "step72-approved-fixtures/v1"
FIXED_MEMORY_POLICY_VERSION = "production-memory-budget-max3/v1"


class ClaimVerdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


def validate_annotation_consistency(*, scores: dict[str, int], claims: list, critical_failures: list[str]) -> None:
    """Enforce the frozen rubric's cross-field consistency for supplied judgments."""
    verdicts = {claim.verdict for claim in claims}
    verdicts = {value.value if isinstance(value, ClaimVerdict) else value for value in verdicts}
    failures = set(critical_failures)
    faithfulness = scores["faithfulness_groundedness"]

    if "CONTRADICTED" in verdicts:
        if faithfulness != 0 or "CONTRADICTED_BY_EVIDENCE" not in failures:
            raise ValueError("contradicted claims require faithfulness 0 and the frozen critical failure")
    if "CONTRADICTED_BY_EVIDENCE" in failures and "CONTRADICTED" not in verdicts:
        raise ValueError("contradicted critical failure requires a contradicted claim")
    if "UNSUPPORTED_CONFIDENT_CLAIM" in failures:
        if "UNSUPPORTED" not in verdicts or faithfulness == 2:
            raise ValueError("unsupported-confident critical failure conflicts with claim/faithfulness fields")
    if "SERIOUS_FACTUAL_ERROR" in failures and scores["answer_correctness"] != 0:
        raise ValueError("serious factual error requires correctness score 0")
    if faithfulness == 2 and (
        verdicts & {"UNSUPPORTED", "CONTRADICTED"}
        or failures & {"UNSUPPORTED_CONFIDENT_CLAIM", "CONTRADICTED_BY_EVIDENCE"}
    ):
        raise ValueError("faithfulness 2 conflicts with unsupported or contradicted claims/failures")


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    score: StrictInt = Field(ge=0, le=2)
    rationale: str = Field(min_length=1)


class DimensionScores(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    answer_correctness: DimensionScore
    faithfulness_groundedness: DimensionScore
    completeness: DimensionScore
    language_quality: DimensionScore
    learning_usefulness: DimensionScore


class ClaimFaithfulness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(pattern=r"^C[1-9][0-9]*$")
    claim_text: str = Field(min_length=1)
    verdict: ClaimVerdict
    supporting_evidence_ids: list[str]
    concise_rationale: str = Field(min_length=1)


class HumanClaimFaithfulness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(pattern=r"^C[1-9][0-9]*$")
    claim_text: str = Field(min_length=1)
    verdict: ClaimVerdict
    supporting_evidence_ids: list[str]
    concise_note: str | None = None


class GenerationJudgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.0.0"]
    case_id: str = Field(min_length=1)
    dimension_scores: DimensionScores
    claims: list[ClaimFaithfulness]
    critical_failures: list[str]
    concise_overall_rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_critical_failures(self):
        if len(self.critical_failures) != len(set(self.critical_failures)) or any(
            item not in CRITICAL_FAILURES for item in self.critical_failures
        ):
            raise ValueError("invalid critical failure enum")
        claim_ids = [claim.claim_id for claim in self.claims]
        if claim_ids != [f"C{index}" for index in range(1, len(claim_ids) + 1)]:
            raise ValueError("claim IDs must be deterministic and contiguous from C1")
        validate_annotation_consistency(
            scores={name: getattr(self.dimension_scores, name).score for name in DIMENSIONS},
            claims=self.claims,
            critical_failures=self.critical_failures,
        )
        return self

    def validate_evidence_ids(self, case_id: str, evidence_ids: set[str]) -> None:
        if self.case_id != case_id:
            raise ValueError("judge case_id does not match request")
        for claim in self.claims:
            unknown = set(claim.supporting_evidence_ids) - evidence_ids
            if unknown:
                raise ValueError("judge referenced unknown fixed evidence ID")


class AnnotationStatus(StrEnum):
    DRAFT = "DRAFT"
    NEEDS_ADJUDICATION = "NEEDS_ADJUDICATION"
    HUMAN_APPROVED = "HUMAN_APPROVED"


class HumanGenerationAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    generation_run_id: str | None = None
    generated_answer_sha256: str | None = None
    annotation_version: str = HUMAN_ANNOTATION_VERSION
    rubric_version: str = RUBRIC_VERSION
    scores: dict[str, int] | None = None
    claim_faithfulness: list[HumanClaimFaithfulness] | None = None
    critical_failures: list[str] = Field(default_factory=list)
    concise_notes: str | None = None
    review_status: AnnotationStatus = AnnotationStatus.DRAFT

    @model_validator(mode="after")
    def prevent_codex_approval_without_binding(self):
        if self.review_status == AnnotationStatus.HUMAN_APPROVED and (
            not self.generation_run_id or not self.generated_answer_sha256
        ):
            raise ValueError("approved human annotation must bind to a generated answer")
        if self.scores is not None and (
            set(self.scores) != set(DIMENSIONS)
            or any(type(score) is not int or score not in (0, 1, 2) for score in self.scores.values())
        ):
            raise ValueError("human scores must cover exactly the five frozen dimensions")
        if (len(self.critical_failures) != len(set(self.critical_failures))
                or any(item not in CRITICAL_FAILURES for item in self.critical_failures)):
            raise ValueError("invalid human critical failure enum")
        if self.claim_faithfulness is not None:
            claim_ids = [claim.claim_id for claim in self.claim_faithfulness]
            if claim_ids != [f"C{index}" for index in range(1, len(claim_ids) + 1)]:
                raise ValueError("human claim IDs must be deterministic and contiguous from C1")
        if self.review_status == AnnotationStatus.HUMAN_APPROVED:
            if self.scores is None or self.claim_faithfulness is None:
                raise ValueError("approved human annotation must include scores and claim faithfulness")
            validate_annotation_consistency(
                scores=self.scores,
                claims=self.claim_faithfulness,
                critical_failures=self.critical_failures,
            )
        return self


class JudgeTechnicalFailure(Exception):
    """Normalized judge failure; provider text and credentials are never retained."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class JudgeCallResult:
    result: GenerationJudgeResult
    latency_ms: int
    attempt_count: int = 1
    request_id: str | None = None
    token_usage: dict | None = None
