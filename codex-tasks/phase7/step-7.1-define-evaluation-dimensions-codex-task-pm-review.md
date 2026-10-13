# Codex Task — Step 7.1: Define Evaluation Dimensions

## ROLE

You are implementing **Step 7.1 — Define Evaluation Dimensions** for the Trung-Chinese-Learning project.

Act as an implementation engineer for this Step only.  
Do not redesign product scope, RAG architecture, evaluation strategy, or future Phase 7 work.

---

## SOURCE OF TRUTH

Read in this order:

1. `PROJECT_CONTEXT.md`
2. `PM-Control/04-Decision-Log-and-Open-Gates.md`
3. `Phase7/Step-7.1-Define-Evaluation-Dimensions.md`
4. Direct runtime dependencies:
   - `Phase6/Step-6.8-End-to-End-RAG.md`
   - `Phase6/Step-6.9-Conversation-Memory.md`
   - `Phase6/Step-6.10-Citations.md`
5. Current repository state

If documents materially conflict, do not invent a resolution. Report `BLOCKED — DECISION NEEDED`.

---

## CURRENT STATE

PM state:

```text
Step 6.8-A implementation accepted
Calibration gate remains open
Step 7.1 = CURRENT
Step 7.2/7.3 = NOT STARTED
Step 6.8-B = NOT STARTED
```

Current accepted internal runtime priority:

CURRENT_LESSON
→ INTERNAL_KB

Phase-7 evaluation taxonomy must also be able to represent the future
TRUSTED_EXTERNAL fallback tier defined for Step 6.8-B, without implying
that external retrieval is implemented in Step 7.1.

Only move to a broader tier when the higher-priority tier has no usable evidence.

Semantic no-evidence may complete successfully with deterministic refusal.

Technical retrieval/reranker/context/provider failure is not semantic no-evidence and must not trigger semantic fallback.

Conversation memory is conversational context, not trusted evidence.

Citation structural/provenance validation already exists; semantic citation quality belongs to Phase 7.

---

## OBJECTIVE

Freeze the evaluation taxonomy for **Lesson Chat RAG** so later Steps can build datasets, metrics, judges and regression evaluation without redefining what quality means.

Step 7.1 defines:

```text
WHAT should be evaluated
```

It does not define how it will be scored.

---

## IN SCOPE

Create/update Step 7.1 evaluation documentation using the repository's existing documentation convention.

Document and freeze:

1. System under evaluation.
2. Five evaluation groups.
3. Clear definition of every dimension.
4. Critical failure policy.
5. Separation of semantic quality from operational quality.
6. Runtime-policy distinctions inherited from accepted Phase 6 behavior.
7. Logical downstream contract required by Step 7.2.
8. Verification examples showing that different failure layers can be distinguished.

Preferred documentation location if no existing equivalent convention exists:

```text
docs/evaluation/step-7.1-define-evaluation-dimensions.md
```

Reuse an existing evaluation documentation structure if one already exists. Do not create a parallel structure unnecessarily.

---

## FROZEN TAXONOMY

### Retrieval Quality

#### Retrieval Relevance

Evaluate whether retrieved evidence is actually relevant to the learner question and the information required to answer it.

This concerns the retrieved evidence itself, not whether the final answer is correct.

#### Retrieval Coverage

Evaluate whether the retrieved evidence collectively contains enough relevant evidence to support the information required for a complete answer.

Do not confuse this with answer completeness.

#### Scope Correctness

Evaluate whether retrieval respected the allowed request/tier scope, including lesson/source/active-knowledge constraints.

Retrieving semantically relevant but out-of-scope evidence is still a retrieval failure.

---

### Generation Quality

#### Answer Correctness

Evaluate whether the generated answer is factually and linguistically correct relative to the expected information.

Correctness is separate from citation quality and faithfulness.

#### Faithfulness / Groundedness

Evaluate whether factual or instructional claims in the answer are supported by the evidence actually supplied to generation.

A claim may be true in the real world but still fail faithfulness if it is unsupported by the provided evidence.

#### Completeness

Evaluate whether the answer covers the required expected information.

An answer may be correct on the points it includes but still be incomplete.

#### Language Quality

Evaluate whether the answer is clear, natural, understandable and appropriate for the learner-facing language context.

Language quality must not compensate for factual or grounding failures.

#### Learning Usefulness

Evaluate whether the answer helps a beginner understand or learn the concept effectively, using suitable explanation/examples where appropriate.

Learning usefulness must not justify introducing unsupported information.

---

### Citation Quality

#### Citation Correctness

Evaluate whether each citation points to a valid current source and whether that source actually supports the claim associated with the citation.

Structural validity/provenance alone is not sufficient for semantic citation correctness.

#### Citation Coverage

Evaluate whether claims requiring grounding have appropriate citation coverage.

A response with valid citations on only some required grounded claims fails citation coverage even if those individual citations are correct.

---

### End-to-End Behavior Quality

#### Context Adherence

Evaluate whether the response correctly follows the current learner question, lesson/learning context and relevant conversation context.

Conversation memory is context only:

```text
Conversation Memory
!=
Retrieved Evidence
```

Previous assistant messages must not override current retrieved evidence and must not become citation sources.

#### Fallback Correctness

Evaluate whether evidence-tier selection and transitions obey runtime policy.

Expected priority:

```text
CURRENT_LESSON
→ INTERNAL_KB
→ TRUSTED_EXTERNAL
```

A broader tier may be selected only when the higher-priority tier has no usable evidence.

Examples of failure:

```text
CURRENT_LESSON usable
→ INTERNAL_KB selected
→ Fallback Correctness failure
```

and:

```text
technical retrieval failure
→ broader semantic fallback
→ critical policy failure
```

#### Abstention / Refusal Correctness

Evaluate whether the system refuses when policy requires refusal and answers when usable allowed evidence exists.

Examples:

```text
valid semantic no-evidence
→ deterministic refusal
→ behavioral success
```

```text
out-of-domain request
→ required refusal
```

```text
usable allowed evidence exists
→ unnecessary refusal
→ failure
```

---

### Operational Quality

#### Latency

Evaluate execution time as an operational property of the Lesson Chat RAG request/stages.

Do not define percentile formulas, thresholds or regression gates in Step 7.1.

#### Technical Success Rate

Evaluate whether the system completed the intended technical lifecycle without infrastructure/provider/runtime failure.

Important distinction:

```text
valid semantic no-evidence refusal
→ technical success
```

while:

```text
retrieval/provider/reranker/context/citation technical failure
→ technical failure
```

A technical failure treated as semantic no-evidence is a critical policy failure.

---

## CRITICAL FAILURE POLICY

Critical failures must be represented separately from normal dimension quality.

At minimum include:

```text
serious factual error
confident unsupported claim / hallucination
fabricated citation/source
citation provenance mismatch
out-of-domain answer instead of refusal
confident answer with insufficient evidence
retrieval scope violation
tier/fallback policy violation
technical failure treated as no-evidence
required citation missing
```

A critical failure may also cause one or more dimensions to fail, but it must never be hidden by an averaged quality score.

For citation handling:

- partial citation coverage is a `Citation Coverage` failure;
- violation of a mandatory citation requirement may additionally be a critical failure.

Do not define numeric severity weights in Step 7.1.

---

## DOWNSTREAM LOGICAL CONTRACT FOR STEP 7.2

Freeze the semantic requirements equivalent to:

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

This is a logical contract only.

Do not create the final dataset schema, JSONL persistence format, database table, dataset size, split strategy or bucket distribution in Step 7.1.

Step 7.2 may later normalize this logical contract into more concrete fields, but it must not redefine the Step 7.1 taxonomy.

---

## REQUIRED VERIFICATION EXAMPLES

The documentation must clearly distinguish at least:

```text
retrieval correct + answer wrong
→ Generation failure
```

```text
retrieval wrong
→ Retrieval failure
```

```text
factually correct but unsupported
→ Faithfulness failure
```

```text
correct answer + wrong supporting source
→ Citation Correctness failure
```

```text
valid citation on only some required claims
→ Citation Coverage failure
```

```text
CURRENT_LESSON has usable evidence
+ broader tier selected
→ Fallback Correctness failure
→ tier/fallback policy critical failure
```

```text
technical retrieval failure
+ treated as semantic fallback/no-evidence
→ CRITICAL policy failure
```

```text
valid no-evidence deterministic refusal
→ behavioral success
→ technical success
```

```text
fabricated citation/source
→ Citation failure
→ CRITICAL FAILURE
```

---

## OUT OF SCOPE

Do not implement or select:

```text
Step 7.2 dataset
Step 7.3 retrieval metrics/calibration
Recall@K
Precision@K
MRR
nDCG
Hit Rate
K values
dataset size
sampling strategy
development/holdout split
human rubric scale
LLM-as-a-Judge
pass threshold
regression threshold
CI gate
benchmark runner
RAG_MIN_RERANK_SCORE value
Step 6.8-B
external retrieval provider/vendor
generation benchmark
regression framework
production monitoring
```

Do not add a new database schema or evaluation persistence model.

Do not implement future Phase 7 Steps opportunistically.

---

## FILES / COMPONENTS

Expected change is documentation-only unless the current repository already has a small evaluation taxonomy/config representation that Step 7.1 clearly needs.

Primary expected file:

```text
docs/evaluation/step-7.1-define-evaluation-dimensions.md
```

Before creating files:

1. inspect current repository conventions;
2. reuse existing evaluation/docs structure when available;
3. do not duplicate an existing Step 7.1 document.

No migration, API, database, backend runtime or frontend changes are expected.

---

## TEST / VERIFICATION

No benchmark execution is required.

Verify by review that:

- all five groups exist;
- all agreed dimensions have non-overlapping clear definitions;
- retrieval/generation/citation/behavior/operational failures can be distinguished;
- semantic no-evidence and technical failure are explicitly different;
- memory is context, not evidence;
- citation correctness and citation coverage are distinct;
- critical failures are separate from normal quality;
- Step 7.2 logical contract is preserved;
- no metric formula, threshold, dataset design or benchmark runner was introduced.

If repository documentation checks/formatters already exist, run only the relevant lightweight checks.

---

## ACCEPTANCE CRITERIA

- [ ] System under evaluation is Lesson Chat RAG only.
- [ ] Five evaluation groups are documented.
- [ ] Every required dimension has a clear definition.
- [ ] Retrieval Relevance, Retrieval Coverage and Scope Correctness are distinguishable.
- [ ] Answer Correctness, Faithfulness and Completeness are distinguishable.
- [ ] Citation Correctness and Citation Coverage are distinguishable.
- [ ] Context Adherence, Fallback Correctness and Refusal Correctness are distinguishable.
- [ ] Latency and Technical Success Rate are explicitly operational concerns.
- [ ] Semantic no-evidence refusal is recognized as valid behavioral/technical success.
- [ ] Technical failure cannot be reclassified as semantic no-evidence.
- [ ] Critical failures remain separate from scored/averaged quality.
- [ ] Downstream EvaluationCase logical contract is documented.
- [ ] No final dataset schema/persistence is created.
- [ ] No metric formula, K, judge strategy, threshold, calibration or benchmark execution is introduced.
- [ ] No Step 7.2/7.3/6.8-B implementation is introduced.

---

## CONSTRAINTS

- Keep the change small and documentation-focused.
- Do not add technology or dependencies.
- Do not change accepted Phase 6 runtime behavior.
- Do not close the calibration gate.
- Do not invent `RAG_MIN_RERANK_SCORE`.
- Do not enable external retrieval.
- Do not create architecture for future evaluation infrastructure.

---

## REQUIRED COMPLETION REPORT

Return:

```text
Step:
Status:

What was done:
- ...

Key decisions preserved:
- ...

Files/components changed:
- ...

Tests / verification:
- ...

Acceptance criteria status:
- ...

Problems / risks:
- ...

Decisions needed:
- ...

Recommended next action:
- ...
```

If a material conflict or ambiguity is discovered, stop and return:

```text
BLOCKED — DECISION NEEDED
```
