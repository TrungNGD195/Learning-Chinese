from __future__ import annotations

import logging
import json
from dataclasses import replace

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
        return {**common, "reference_answer": None, "rubric": question.explanation, "config": None,
                "options": [item.model_dump() for item in question.options]}
    if isinstance(question, GeneratedFillBlankQuestion):
        return {**common, "reference_answer": question.reference_answer, "rubric": question.explanation,
                "config": {"accepted_answers": question.accepted_answers}}
    if isinstance(question, GeneratedMatchingQuestion):
        return {**common, "reference_answer": None, "rubric": question.explanation,
                "config": {"left_items": [item.model_dump() for item in question.left_items],
                           "right_items": [item.model_dump() for item in question.right_items],
                           "correct_pairs": [item.model_dump() for item in question.correct_pairs]}}
    if isinstance(question, GeneratedReorderSentenceQuestion):
        return {**common, "reference_answer": None, "rubric": question.explanation,
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
        if request.question_count > self.settings.ai_generation_max_questions:
            return await self._generate_batches(request, scope)
        return await self._generate_once(request, scope)

    async def _generate_batches(self, request, scope):
        questions, results = [], []
        remaining = request.question_count
        # One type per batch guarantees coverage and keeps every provider call
        # within the existing ten-question/output-token limits.
        types = list(request.allowed_types)
        counts = [request.question_count // len(types) + (index < request.question_count % len(types)) for index in range(len(types))]
        for kind, count in zip(types, counts, strict=True):
            while count:
                size = min(count, self.settings.ai_generation_max_questions)
                batch = request.model_copy(update={"question_count": size, "allowed_types": [kind]})
                result = await self._generate_once(batch, scope, previous_questions=questions)
                if len(result.output.questions) != size or any(item.type != kind for item in result.output.questions):
                    raise AssessmentGenerationInvalidOutput
                questions.extend(result.output.questions)
                results.append(result)
                count -= size
                remaining -= size
        signatures = [(item.type, ' '.join(item.prompt.split()).casefold()) for item in questions]
        if remaining or len(set(signatures)) != len(signatures):
            raise AssessmentGenerationInvalidOutput
        def token_sum(field):
            values = [getattr(result, field) for result in results]
            return sum(values) if all(value is not None for value in values) else None
        return replace(results[-1], output=StructuredAssessmentGenerationOutput(questions=questions),
                       input_tokens=token_sum('input_tokens'), output_tokens=token_sum('output_tokens'), total_tokens=token_sum('total_tokens'),
                       provider_preflight_input_tokens=sum(result.provider_preflight_input_tokens for result in results),
                       latency_ms=sum(result.latency_ms for result in results), attempt_count=sum(result.attempt_count for result in results))

    async def _generate_once(self, request, scope, previous_questions=()):
        system, user = build_generation_prompt(scope, request)
        if previous_questions:
            payload = json.loads(user)
            payload['previous_question_prompts_to_avoid'] = [item.prompt for item in previous_questions]
            user = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            system += '\nDo not repeat any previous_question_prompts_to_avoid; vary the tested item and task.'
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
