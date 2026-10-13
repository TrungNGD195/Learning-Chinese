# Step 7.1 — Define Evaluation Dimensions

## Objective

Freeze what quality means for the V0 Lesson Chat RAG evaluation so dataset,
metrics, and later evaluation work can consume one stable taxonomy. This Step
defines what is evaluated; it does not define how quality is scored.

## System Under Evaluation

The system under evaluation is **Lesson Chat RAG**: a learner's lesson-scoped
request, its retrieval and evidence-tier behavior, generated answer and
citations, plus the technical lifecycle that completes the request.

The taxonomy can represent the future tier order:

```text
CURRENT_LESSON → INTERNAL_KB → TRUSTED_EXTERNAL
```

Only move to a broader tier when the higher-priority tier has no usable
evidence. `TRUSTED_EXTERNAL` is included so the taxonomy can describe that
future behavior; this Step does not enable or implement external retrieval.
Free-form grading and Admin exercise/test generation are outside this system's
scope.

## Evaluation Dimensions

### Retrieval Quality

| Dimension | Definition |
|---|---|
| Retrieval Relevance | Whether retrieved evidence is relevant to the learner's question and the information needed to answer it. This evaluates evidence itself, not final-answer correctness. |
| Retrieval Coverage | Whether retrieved evidence collectively contains enough relevant information to support a complete answer. This is distinct from whether the answer includes that information. |
| Scope Correctness | Whether retrieval obeys the allowed request and tier scope, including lesson, source, and active-knowledge constraints. Relevant evidence retrieved from outside the allowed scope is still a failure. |

### Generation Quality

| Dimension | Definition |
|---|---|
| Answer Correctness | Whether the answer is factually and linguistically correct relative to the expected information. |
| Faithfulness / Groundedness | Whether factual or instructional claims are supported by evidence actually supplied to generation. A true claim can fail this dimension when that evidence does not support it. |
| Completeness | Whether the answer covers the required expected information. Correct included points do not make an answer complete when required points are missing. |
| Language Quality | Whether the answer is clear, natural, understandable, and appropriate for the learner-facing language context. Fluency cannot compensate for incorrect or unsupported claims. |
| Learning Usefulness | Whether the answer helps a beginner understand the concept through suitable explanation or examples, without introducing unsupported information. |

### Citation Quality

| Dimension | Definition |
|---|---|
| Citation Correctness | Whether each citation points to a valid current source and that source supports the claim associated with it. Structural validity and provenance alone do not establish semantic correctness. |
| Citation Coverage | Whether claims that require grounding have appropriate citation coverage. Correct citations on only some required claims still fail coverage. |

### End-to-End Behavior Quality

| Dimension | Definition |
|---|---|
| Context Adherence | Whether the answer follows the current learner question, lesson context, and relevant conversation context. Conversation memory is context, not retrieved evidence or citation provenance; prior assistant messages cannot override current evidence. |
| Fallback Correctness | Whether evidence-tier selection and transitions follow the priority policy. A broader tier is permitted only when the higher-priority tier has no usable evidence. |
| Abstention / Refusal Correctness | Whether the system refuses when policy requires refusal and answers when usable allowed evidence exists. This includes out-of-domain refusal and avoiding unnecessary refusal when sufficient allowed evidence exists. |

### Operational Quality

Operational quality is reported separately from semantic answer quality.

| Dimension | Definition |
|---|---|
| Latency | Execution time of the Lesson Chat RAG request or its stages. This definition does not set percentile formulas, limits, or regression gates. |
| Technical Success Rate | Whether the intended technical lifecycle completes without infrastructure, provider, or runtime failure. A valid deterministic no-evidence refusal is a technical success; a retrieval, reranker, context, provider, or citation-processing failure is a technical failure. |

## Semantic and Operational Separation

Semantic outcomes describe evidence quality, answer quality, behavior, and
citations. Operational outcomes describe whether the request ran successfully
and how long it took. They are distinct classifications: a valid semantic
no-evidence refusal is behaviorally correct and technically successful, while
a technical failure must not be relabeled as semantic no-evidence or trigger a
broader semantic fallback.

```text
Conversation Memory ≠ Retrieved Evidence
```

Memory may help interpret the learner's conversation. It is not evidence for a
claim, a retrieval result, or a citation source.

## Critical Failure Policy

Critical failures are a separate outcome layer, not ordinary scored
dimensions. They may also fail one or more dimensions, but must never be
hidden by an averaged quality score. At minimum, classify these as critical:

- serious factual error;
- confident unsupported claim or hallucination;
- fabricated citation or source;
- citation provenance mismatch;
- answering an out-of-domain request instead of refusing;
- confident answer when evidence is insufficient;
- retrieval scope violation;
- tier or fallback policy violation;
- technical failure treated as no-evidence;
- missing a required citation.

Partial citation coverage is a Citation Coverage failure. If a mandatory
citation requirement is violated, it is additionally a critical failure.
Step 7.1 assigns no numeric severity weights.

## Classification Examples

| Observed result | Classification |
|---|---|
| Retrieval is correct, but the answer is wrong | Generation Quality failure, specifically Answer Correctness. |
| Retrieved evidence is wrong or irrelevant | Retrieval Quality failure, specifically Retrieval Relevance; assess Retrieval Coverage separately when evidence is insufficient. |
| Answer is factually correct but unsupported by supplied evidence | Faithfulness / Groundedness failure. |
| Answer is correct but its citation points to the wrong supporting source | Citation Correctness failure. |
| Only some claims requiring grounding have valid citations | Citation Coverage failure. |
| CURRENT_LESSON has usable evidence but a broader tier is selected | Fallback Correctness failure and tier/fallback policy critical failure. |
| Technical retrieval failure is treated as a broader-tier fallback or no-evidence | Critical policy failure; it is also an operational technical failure. |
| No tier has usable evidence and the system gives the required deterministic refusal | Abstention / Refusal Correctness success and Technical Success. |
| A citation/source is fabricated | Citation Quality failure and Critical Failure. |
| An out-of-domain question is answered | Abstention / Refusal Correctness failure and Critical Failure. |
| Usable allowed evidence exists but the system refuses unnecessarily | Abstention / Refusal Correctness failure. |

## Step 7.2 Logical EvaluationCase Contract

Each downstream case must provide enough logical ground truth to assess the
frozen dimensions and critical failures:

```text
EvaluationCase
├── question
├── expected_information
├── relevant_evidence
├── expected_scope
├── expected_behavior
├── expected_answer_properties
├── expected_citation_sources
└── critical_failure_expectations
```

This is a semantic contract only. Step 7.1 does not define dataset storage,
serialization, persistence, identifiers, versioning, sampling, splits, or
case counts. Step 7.2 may normalize the contract into concrete fields, but
must preserve this taxonomy and its meaning.

## Scope Boundaries

Step 7.1 defines the evaluation target, dimensions, critical-failure policy,
classification distinctions, and the logical Step 7.2 contract. It does not
implement or select:

- a dataset, dataset schema, or persistence format;
- metric formulas, including Recall@K, Precision@K, nDCG, MRR, or K values;
- sampling strategy, dataset size, or development/holdout split;
- judge logic, LLM-as-a-Judge, or a human rubric scale;
- pass or regression thresholds, a CI gate, or benchmark runner;
- `RAG_MIN_RERANK_SCORE` or calibration behavior;
- Step 7.2, Step 7.3, Step 6.8-B, or external retrieval infrastructure.

No database schema, migration, dependency, public API, or production runtime
change is part of this Step.
