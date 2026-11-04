"""Defaults for new assessments; explicitly configured thresholds remain valid."""


def default_pass_threshold(assessment_type: str) -> int:
    return 80 if assessment_type == "LESSON_EXERCISE" else 90


def insert_pass_threshold(context) -> int:
    return default_pass_threshold(context.get_current_parameters().get("type"))
