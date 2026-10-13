from dataclasses import fields

import pytest

from app.ai.prompting.errors import INVALID_PROMPT_BUDGET, PROMPT_CONTEXT_BUILD_FAILED
from app.ai.prompting.schemas import LearningContext, PromptBudget


@pytest.mark.parametrize(
    "values",
    [
        (1, 0, 0),
        (10, 0, 0),
        (10, 2, 3),
        (10, 0, 9),
        (10, 5, 5),
        (10, 10, 0),
        (10, 0, 10),
        (10, 11, 0),
    ],
)
def test_prompt_budget_accepts_structurally_valid_values(values):
    assert PromptBudget(*values) == PromptBudget(*values)


@pytest.mark.parametrize(
    "values",
    [
        (0, 0, 0),
        (-1, 0, 0),
        (10, -1, 0),
        (10, 0, -1),
        (10, True, 0),
        (True, 0, 0),
        (10, 0, False),
    ],
)
def test_prompt_budget_rejects_invalid_structure_and_bool_as_int(values):
    with pytest.raises(Exception) as raised:
        PromptBudget(*values)
    assert getattr(raised.value, "code", None) == INVALID_PROMPT_BUDGET
    assert "True" not in str(raised.value)


def test_learning_context_contains_only_frozen_semantic_fields():
    assert [field.name for field in fields(LearningContext)] == [
        "hsk_level",
        "lesson_title",
        "current_module",
    ]
    assert LearningContext(2, "我的朋友", "Grammar") == LearningContext(
        hsk_level=2,
        lesson_title="我的朋友",
        current_module="Grammar",
    )


@pytest.mark.parametrize(
    "value",
    [True, "2", 2.0],
)
def test_learning_context_rejects_bool_or_non_integer_hsk(value):
    with pytest.raises(Exception) as raised:
        LearningContext(hsk_level=value)
    assert getattr(raised.value, "code", None) == PROMPT_CONTEXT_BUILD_FAILED
