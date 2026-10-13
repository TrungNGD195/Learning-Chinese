from __future__ import annotations

from .contracts import CRITICAL_FAILURES, DIMENSIONS, RUBRIC_VERSION

RUBRICS = {
    "answer_correctness": {
        "ground_truth": "expected_information[]; reference_answer is secondary and is never exact-matched",
        "2": "Presented information is correct; core Chinese-learning explanation is factually and linguistically correct; no materially misleading statement. Paraphrase is allowed.",
        "1": "Mostly correct; only minor imprecision that does not materially change core teaching, or partially correct framing that avoids a materially false core claim.",
        "0": "Material factual or linguistic error affects the requested concept; expected information is misstated; answer misleads about core teaching; or core answer is wrong regardless of fluency.",
    },
    "faithfulness_groundedness": {
        "ground_truth": "fixed provided evidence only; true but unsupported outside facts remain unsupported",
        "2": "Every material factual or instructional claim is SUPPORTED; no contradicted or material unsupported claims.",
        "1": "Core teaching is supported; at most a minor peripheral unsupported detail exists and no material claim is contradicted.",
        "0": "A core/material claim is unsupported, any material claim is contradicted, or the answer materially relies on facts absent from fixed evidence.",
    },
    "completeness": {
        "ground_truth": "atomic expected_information[]",
        "2": "All required expected-information units are adequately covered.",
        "1": "Core answer is present but one or more units are omitted or underexplained; enough remains partly useful.",
        "0": "Most/core required information is missing or response barely addresses the request.",
    },
    "language_quality": {
        "ground_truth": "beginner Chinese learner suitability, not generic literary fluency",
        "2": "Vietnamese is clear and natural; Chinese examples, pinyin and meaning are clear when relevant; concise and beginner-friendly.",
        "1": "Understandable overall with minor awkwardness, verbosity, organization, formatting, or wording issue that does not materially distort learning.",
        "0": "Difficult to understand; errors materially obscure or distort learning; or substantially inappropriate for beginner comprehension.",
    },
    "learning_usefulness": {
        "ground_truth": "pedagogical usefulness for the learner's actual question",
        "2": "Directly addresses intent, makes requested rule/meaning/usage actionable, uses supported helpful explanation/example/contrast, and has beginner-appropriate depth.",
        "1": "Useful but limited; explanation/example incomplete, somewhat generic or verbose, while still giving practical value.",
        "0": "Does not help the learner apply/understand, is materially off-topic/confusing, or is too advanced/irrelevant.",
    },
}

JUDGE_INSTRUCTIONS = """Evaluate only the supplied fixed-evidence generation case. Score all five dimensions independently from 0 to 2. expected_information is the primary correctness/completeness ground truth; reference_answer is secondary and wording need not match it. Evaluate faithfulness only against the supplied fixed evidence. Do not use outside knowledge to rescue unsupported claims; a real-world true fact may still be UNSUPPORTED here. Identify material factual, Chinese-language, grammar/usage, and instructional claims as SUPPORTED, UNSUPPORTED, or CONTRADICTED. Use only evidence IDs supplied in this request. Apply exactly SERIOUS_FACTUAL_ERROR, UNSUPPORTED_CONFIDENT_CLAIM, and CONTRADICTED_BY_EVIDENCE. Language Quality and Learning Usefulness cannot compensate for correctness or faithfulness failures. Do not evaluate retrieval, tier fallback, refusal policy, or citation semantic correctness. Return concise evaluation rationale only; do not reveal hidden chain-of-thought."""

CRITICAL_FAILURE_DEFINITIONS = {
    "SERIOUS_FACTUAL_ERROR": "A material error in the core requested teaching that would likely misteach the learner.",
    "UNSUPPORTED_CONFIDENT_CLAIM": "A material factual or instructional claim is not supported by supplied evidence and is stated as established fact or instruction rather than explicitly uncertain.",
    "CONTRADICTED_BY_EVIDENCE": "A material generated claim directly conflicts with supplied fixed evidence.",
}


def rubrics_for_prompt() -> dict:
    return {"rubric_version": RUBRIC_VERSION, "dimensions": RUBRICS,
            "critical_failures": CRITICAL_FAILURE_DEFINITIONS,
            "dimension_order": list(DIMENSIONS)}
