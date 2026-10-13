from __future__ import annotations

import logging

from app.ai.generation.errors import (
    AI_GENERATION_INVALID_RESPONSE,
    AssessmentGenerationInvalidOutput,
    StructuredAssessmentGenerationProviderError,
)
from app.ai.generation.prompt import build_generation_prompt
from app.ai.generation.schemas import (
    GeneratedFillBlankQuestion,
    GeneratedMatchingQuestion,
    GeneratedMultipleChoiceQuestion,
    GeneratedReorderSentenceQuestion,
    MaterializedGenerationScope,
    StructuredAssessmentGenerationRequest,
    StructuredAssessmentGenerationProviderResult,
    StructuredAssessmentGenerationOutput,
    GeneratedQuestion,
)
from app.core.config import Settings

logger = logging.getLogger("app.ai.generation")


def map_generated_question(question: GeneratedQuestion, order_index: int) -> dict:
    common = {"type": question.type, "prompt": question.prompt, "order_index": order_index, "points": 1.0}
    if isinstance(question, GeneratedMultipleChoiceQuestion):
        return {**common, "reference_answer": None, "rubric": None, "config": None,
                "options": [item.model_dump() for item in question.options]}
    if isinstance(question, GeneratedFillBlankQuestion):
        return {**common, "reference_answer": question.reference_answer, "rubric": None,
                "config": {"accepted_answers": question.accepted_answers}}
    if isinstance(question, GeneratedMatchingQuestion):
        return {**common, "reference_answer": None, "rubric": None,
                "config": {"left_items": [item.model_dump() for item in question.left_items],
                           "right_items": [item.model_dump() for item in question.right_items],
                           "correct_pairs": [item.model_dump() for item in question.correct_pairs]}}
    if isinstance(question, GeneratedReorderSentenceQuestion):
        return {**common, "reference_answer": None, "rubric": None,
                "config": {"items": [item.model_dump() for item in question.items],
                           "correct_order": question.correct_order}}
    return {**common, "reference_answer": question.reference_answer, "rubric": question.rubric,
            "config": None}


def validate_and_map_output(
    result: StructuredAssessmentGenerationProviderResult,
    *, request, scope: MaterializedGenerationScope, domain_validator,
) -> list[dict]:
    output = result.output if isinstance(result, StructuredAssessmentGenerationProviderResult) else None
    if not isinstance(output, StructuredAssessmentGenerationOutput) or len(output.questions) != request.question_count:
        raise AssessmentGenerationInvalidOutput from None
    mapped = []
    allowed_refs = scope.allowed_source_refs
    try:
        for index, question in enumerate(output.questions, start=1):
            if question.type not in request.allowed_types:
                raise ValueError("question type not allowed")
            refs = question.source_refs
            if not refs or len(refs) != len(set(refs)) or any(not ref.strip() or ref not in allowed_refs for ref in refs):
                raise ValueError("source refs are invalid or outside selected scope")
            item = map_generated_question(question, index)
            domain_validator(item)
            mapped.append(item)
    except Exception:
        # The model result is untrusted; never expose its payload or an internal D-009 message.
        raise AssessmentGenerationInvalidOutput from None
    return mapped


class AssessmentGenerationService:
    def __init__(self, provider, settings: Settings):
        self.provider = provider
        self.settings = settings

    async def generate(self, request, scope: MaterializedGenerationScope):
        system, user = build_generation_prompt(scope, request)
        provider_request = StructuredAssessmentGenerationRequest(
            system_content=system, user_content=user,
            model=self.settings.llm_model, temperature=self.settings.llm_temperature,
            max_output_tokens=self.settings.ai_generation_max_output_tokens,
            reasoning_effort=self.settings.llm_reasoning_effort,
            model_input_limit=self.settings.llm_model_input_limit,
            request_timeout_seconds=self.settings.llm_request_timeout_seconds,
            max_transient_retries=self.settings.llm_max_transient_retries,
            generation_kind=request.type, requested_question_count=request.question_count,
            allowed_types=tuple(request.allowed_types), difficulty=request.difficulty,
        )
        result = await self.provider.generate(provider_request)
        if not isinstance(result, StructuredAssessmentGenerationProviderResult):
            raise StructuredAssessmentGenerationProviderError(AI_GENERATION_INVALID_RESPONSE)
        return result
