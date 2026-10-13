from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import is_dataclass
from uuid import UUID
from uuid import NAMESPACE_URL, uuid5

from app.ai.memory.composition import derive_memory_token_budget, with_conversation_memory
from app.ai.memory.schemas import ConversationMemory, MemoryTurn, empty_memory
from app.ai.memory.sanitizer import sanitize_historical_assistant_text
from app.ai.prompting.evidence import InternalContextEvidence
from app.ai.prompting.schemas import LearningContext, PromptBudget, PromptPackage
from app.ai.prompting.token_counter import TiktokenTokenCounter
from app.ai.prompting.errors import CONTEXT_BUDGET_EXHAUSTED
from .fixed_evidence import FixedEvidence


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_value(value):
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if is_dataclass(value):
        return _json_value(vars(value))
    return value


def learning_context_for(case: dict) -> LearningContext | None:
    context = case.get("lesson_context")
    if not context:
        return None
    identity = context.get("hsk_identity") or ""
    match = re.search(r"\bHSK\s*(\d+)\b", identity, flags=re.IGNORECASE)
    return LearningContext(
        hsk_level=int(match.group(1)) if match else None,
        lesson_title=context.get("lesson_title"),
        current_module=context.get("lesson_locator"),
    )


class FixedConversationMemoryFactory:
    def __init__(self, token_counter=None, max_turns: int = 3):
        self.token_counter = token_counter or TiktokenTokenCounter()
        self.max_turns = max_turns

    def build(self, turns: list[dict] | None, *, token_budget: int) -> ConversationMemory:
        turns = turns or []
        if type(token_budget) is not int or token_budget < 0 or not 0 <= self.max_turns <= 3:
            raise ValueError("Invalid fixed memory budget")
        if not turns or self.max_turns == 0 or token_budget == 0:
            return empty_memory(omitted_turn_count=len(turns))
        normalized = []
        sanitized_omitted = 0
        for row in turns:
            user_text, assistant_text = row.get("user_text"), row.get("assistant_text")
            if not isinstance(user_text, str) or not user_text.strip() or not isinstance(assistant_text, str) or not assistant_text.strip():
                raise ValueError("Malformed fixed conversation turn")
            assistant_text = sanitize_historical_assistant_text(assistant_text)
            if not assistant_text.strip():
                sanitized_omitted += 1
                continue
            normalized.append({"user_text": user_text, "assistant_text": assistant_text})
        start = max(0, len(normalized) - self.max_turns)
        omitted = sanitized_omitted + start
        selected = []
        counted = []
        for index, row in enumerate(normalized[start:], start=start):
            user_text, assistant_text = row["user_text"], row["assistant_text"]
            count = self.token_counter.count(user_text) + self.token_counter.count(assistant_text)
            turn_id = f"step74-memory:{index}"
            turn = MemoryTurn(
                user_text=user_text, assistant_text=assistant_text,
                user_message_id=uuid5(NAMESPACE_URL, turn_id + ":user"),
                assistant_message_id=uuid5(NAMESPACE_URL, turn_id + ":assistant"),
                user_sequence_number=2 * index + 1,
                assistant_sequence_number=2 * index + 2,
            )
            selected.append(turn)
            counted.append(count)
        total = sum(counted)
        while selected and total > token_budget:
            selected.pop(0)
            total -= counted.pop(0)
            omitted += 1
        if not selected:
            return empty_memory(omitted_turn_count=omitted)
        return ConversationMemory(
            turns=tuple(selected), selected_turn_count=len(selected),
            omitted_turn_count=omitted, token_count=total, status="APPLIED",
        )


def package_snapshot(package: PromptPackage) -> dict:
    return {
        "system_instructions": package.system_instructions,
        "learning_context": package.learning_context,
        "context_blocks": [
            {
                "source_label": block.source_label,
                "text": block.text,
                "title": getattr(block, "title", None),
                "url": getattr(block, "url", None),
                "domain": getattr(block, "domain", None),
            }
            for block in package.context_blocks
        ],
        "user_query": package.user_query,
        "source_map": _json_value(package.source_map),
        "budget_usage": vars(package.budget_usage),
        "conversation_memory": [
            {"user_text": turn.user_text, "assistant_text": turn.assistant_text}
            for turn in (package.conversation_memory.turns if package.conversation_memory else ())
        ],
    }


class ProductionPromptFactory:
    def __init__(self, *, prompt_builder, token_counter, generation_config, memory_factory=None,
                 memory_max_turns: int = 3):
        self.prompt_builder = prompt_builder
        self.token_counter = token_counter
        self.generation_config = generation_config
        self.memory_factory = memory_factory or FixedConversationMemoryFactory(
            token_counter=token_counter, max_turns=memory_max_turns
        )

    def build(self, case: dict, evidence: list[FixedEvidence]) -> tuple[PromptPackage, dict]:
        prompt_budget = PromptBudget(
            model_input_limit=self.generation_config.model_input_limit,
            reserved_output_tokens=self.generation_config.max_output_tokens,
            serialization_overhead_tokens=0,
        )
        context_evidence = []
        internal_order = 0
        for item in evidence:
            if item.candidate is not None:
                internal_order += 1
                context_evidence.append(InternalContextEvidence(internal_order, item.candidate))
            elif item.external is not None:
                context_evidence.append(item.external)
        try:
            built = self.prompt_builder.build_from_evidence(
                user_query=case["question"], evidence=tuple(context_evidence),
                prompt_budget=prompt_budget, learning_context=learning_context_for(case),
            )
        except Exception as exc:
            if getattr(exc, "code", None) == CONTEXT_BUDGET_EXHAUSTED:
                raise RuntimeError("FIXED_EVIDENCE_CONTEXT_BUDGET_EXHAUSTED") from None
            raise
        if built.status != "SUCCEEDED" or built.package is None:
            raise RuntimeError("PROMPT_CONTEXT_BUILD_FAILED")
        if built.omitted_count or built.selected_count != len(evidence):
            raise RuntimeError("FIXED_EVIDENCE_CONTEXT_BUDGET_EXHAUSTED")
        package = built.package
        memory_budget = derive_memory_token_budget(package)
        history = case.get("conversation_context") if case["bucket"] == "MULTI_TURN_CONTEXT" else None
        memory = self.memory_factory.build(history, token_budget=memory_budget)
        package = with_conversation_memory(package, memory)
        canonical = json.dumps(package_snapshot(package), ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
        memory_record = {
            "original_turn_count": len(history or []),
            "selected_turn_count": memory.selected_turn_count,
            "omitted_turn_count": memory.omitted_turn_count,
            "token_count": memory.token_count,
            "selected_turns": [
                {"user_text": turn.user_text, "assistant_text": turn.assistant_text}
                for turn in memory.turns
            ],
        } if history is not None else None
        return package, {
            "prompt_package_sha256": _sha(canonical),
            "source_map_snapshot": package_snapshot(package)["source_map"],
            "learning_context": {
                "hsk_level": learning_context_for(case).hsk_level,
                "lesson_title": learning_context_for(case).lesson_title,
                "current_module": learning_context_for(case).current_module,
            } if case.get("lesson_context") else None,
            "fixed_memory": memory_record,
        }
