"""Test-only FastAPI entry point with deterministic AI boundaries."""

from __future__ import annotations

from uuid import UUID

from app.ai.rag.schemas import (
    NO_EVIDENCE_CONTENT,
    RagRunResult,
    RagRunStatus,
    RagTierUsed,
)
from app.admin import service as admin_service
from app.ai.generation.schemas import (
    GeneratedMultipleChoiceQuestion,
    GeneratedMCQOption,
    StructuredAssessmentGenerationOutput,
    StructuredAssessmentGenerationProviderResult,
)
from app.conversation.ai_chat import ChatRequest, get_ai_chat_service
from app.exercise.grading import GradeResult, get_ai_grader
from app.main import app


class DeterministicChat:
    async def generate_reply(self, request: ChatRequest) -> RagRunResult:
        # The fixture contains no active vector corpus. This deliberately exercises
        # semantic no-evidence persistence without pretending that it is a grounded
        # answer or calling a paid/local model.
        return RagRunResult(
            assistant_message_id=request.assistant_message_id,
            status=RagRunStatus.NO_EVIDENCE,
            assistant_content=NO_EVIDENCE_CONTENT,
            tiers_attempted=(
                RagTierUsed.CURRENT_LESSON,
                RagTierUsed.INTERNAL_KB,
                RagTierUsed.TRUSTED_EXTERNAL,
            ),
            tier_used=RagTierUsed.NONE,
            current_lesson_candidate_count=0,
            current_lesson_scored_count=0,
            internal_kb_candidate_count=0,
            internal_kb_scored_count=0,
            selected_context_count=0,
            memory_selected_turn_count=0,
            retrieval_trace=(),
            validated_citations=(),
        )


class DeterministicGrader:
    async def grade(self, *, question: dict, answer: dict) -> GradeResult:
        if question["type"] == "multiple_choice":
            correct = answer.get("option_id") in question["correct_option_ids"]
            return GradeResult("GRADED", float(question["points"]) if correct else 0.0, correct)
        if answer.get("text") == "[step81-uncertain]":
            return GradeResult("UNCERTAIN", None, None, "Manual review required.")
        if answer.get("text") == "[step81-fail]":
            raise RuntimeError("deterministic Step 8.1 grading failure")
        return GradeResult("GRADED", 0.0, False, "Answer does not match the reference.")


class DeterministicGenerationProvider:
    async def generate(self, request):
        # Runtime source_refs are constrained to Admin-selected material. The
        # provider reads one allowed ref from the already-built request payload.
        import re

        match = re.search(r'"allowed_source_refs"\s*:\s*\[\s*"([^"]+)"', request.user_content)
        if not match:
            raise RuntimeError("Step 8.1 generation fixture has no allowed source ref")
        output = StructuredAssessmentGenerationOutput(
            questions=[GeneratedMultipleChoiceQuestion(
                type="multiple_choice",
                prompt="Which word means hello?",
                source_refs=[match.group(1)],
                options=[
                    GeneratedMCQOption(option_text="你好", is_correct=True),
                    GeneratedMCQOption(option_text="再见", is_correct=False),
                ],
            )]
        )
        return StructuredAssessmentGenerationProviderResult(
            output=output,
            provider="step81_deterministic_test",
            model="step81-deterministic-fixture",
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            provider_preflight_input_tokens=1,
            latency_ms=0,
            attempt_count=1,
            provider_request_id=None,
        )


app.dependency_overrides[get_ai_chat_service] = DeterministicChat
app.dependency_overrides[get_ai_grader] = DeterministicGrader
admin_service.get_assessment_generation_provider = DeterministicGenerationProvider

