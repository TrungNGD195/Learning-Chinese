from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol


@dataclass(frozen=True)
class GradeResult:
    grading_status: str
    score: float | None
    is_correct: bool | None
    feedback: str | None = None


class AIGrader(Protocol):
    async def grade(self, *, question: dict, answer: dict) -> GradeResult: ...


class GradingUnavailable(Exception):
    pass


class UnavailableAIGrader:
    async def grade(self, *, question: dict, answer: dict) -> GradeResult:
        raise GradingUnavailable


@lru_cache(maxsize=1)
def get_ai_grader() -> AIGrader:
    """Reuse the process-level structured grading provider; its API key is lazy."""
    from app.ai.grading.factory import get_grading_service

    return get_grading_service()


class DeterministicGrader:
    def grade(self, question: dict, answer: dict) -> GradeResult:
        kind, config = question["type"], question["config"] or {}
        points = float(question["points"])
        correct = False
        if kind == "multiple_choice":
            correct = answer["option_id"] in question["correct_option_ids"]
        elif kind == "fill_blank":
            if not isinstance(question["reference_answer"], str):
                raise ValueError("Fill-blank question has no reference answer")
            accepted = config.get("accepted_answers", [])
            if not isinstance(accepted, list) or not all(isinstance(value, str) for value in accepted):
                raise ValueError("Invalid accepted_answers configuration")
            correct = answer["text"].strip() in {question["reference_answer"].strip(), *(value.strip() for value in accepted)}
        elif kind == "matching":
            left = config.get("left_items"); right = config.get("right_items"); expected = config.get("correct_pairs")
            if not isinstance(left, list) or not isinstance(right, list) or not isinstance(expected, list):
                raise ValueError("Invalid matching configuration")
            left_ids = {item.get("id") for item in left if isinstance(item, dict)}
            right_ids = {item.get("id") for item in right if isinstance(item, dict)}
            pairs = answer["pairs"]
            if any(pair["left_id"] not in left_ids or pair["right_id"] not in right_ids for pair in pairs):
                raise ValueError("Pair references an unknown item")
            if len({pair["left_id"] for pair in pairs}) != len(pairs) or len({pair["right_id"] for pair in pairs}) != len(pairs):
                raise ValueError("Pairs must be one-to-one")
            correct = {(p["left_id"], p["right_id"]) for p in pairs} == {
                (p["left_id"], p["right_id"]) for p in expected if isinstance(p, dict)
            }
        elif kind == "reorder_sentence":
            items = config.get("items"); expected = config.get("correct_order")
            if not isinstance(items, list) or not isinstance(expected, list):
                raise ValueError("Invalid reorder configuration")
            item_ids = [item.get("id") for item in items if isinstance(item, dict)]
            if len(set(item_ids)) != len(item_ids) or set(expected) != set(item_ids) or len(expected) != len(item_ids):
                raise ValueError("Invalid correct_order configuration")
            if len(answer["item_ids"]) != len(item_ids) or set(answer["item_ids"]) != set(item_ids):
                raise ValueError("Ordering references unknown or duplicate items")
            correct = answer["item_ids"] == expected
        else:
            raise ValueError("Unsupported deterministic question type")
        return GradeResult("GRADED", points if correct else 0.0, correct)
