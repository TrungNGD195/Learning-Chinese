# Step 7.1 — Define Evaluation Dimensions

## Implementation Goal

Thiết lập documentation/config foundation cho Phase 7 Evaluation theo taxonomy đã chốt. Step này không chạy benchmark và không implement metric formulas.

System under evaluation của Phase 7 V0:

```text
Lesson Chat RAG
```

Không mở rộng Step 7.1 sang:
- free-form LLM grading evaluation;
- Admin exercise/test generation evaluation.

## Required Evaluation Taxonomy

Hệ thống evaluation phải dùng 5 nhóm dimension:

```text
Retrieval Quality
Generation Quality
Citation Quality
End-to-End Behavior Quality
Operational Quality
```

### Retrieval Quality

- Retrieval Relevance
- Retrieval Coverage
- Scope Correctness

### Generation Quality

- Answer Correctness
- Faithfulness / Groundedness
- Completeness
- Language Quality
- Learning Usefulness

### Citation Quality

- Citation Correctness
- Citation Coverage

### End-to-End Behavior Quality

- Context Adherence
- Fallback Correctness
- Abstention / Refusal Correctness

### Operational Quality

- Latency
- Technical Success Rate

## Critical Failure Policy

Critical failures phải được represent riêng, không được che bởi average quality score.

Bao gồm tối thiểu:

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

## Phase Boundaries

Step 7.1 chỉ định nghĩa:

```text
WHAT should be evaluated
```

Không implement/chốt:

```text
Recall@K
Precision@K
MRR
nDCG
Hit Rate
K
dataset size
sampling strategy
human rubric scale
LLM-as-a-Judge
pass threshold
regression threshold
CI gate
benchmark runner
```

Các phần này thuộc Step 7.2–7.6.

## Step 7.2 Contract

Thiết kế tài liệu/code structure sao cho Step 7.2 có thể tạo evaluation cases mang đủ logical ground truth tương đương:

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

Không bắt buộc tạo final persistence/schema cho EvaluationCase trong Step 7.1.

## Documentation

Tạo/cập nhật documentation phù hợp repository convention, ví dụ:

```text
docs/evaluation/
└── step-7.1-define-evaluation-dimensions.md
```

Nếu repository đã có evaluation module/docs convention thì reuse convention hiện tại thay vì tạo structure song song.

Documentation phải ghi rõ:
- system under evaluation;
- taxonomy;
- definition của từng dimension;
- critical failure policy;
- separation giữa semantic quality và operational quality;
- Step 7.1 boundaries;
- downstream contract cho Step 7.2.

## Verification

Verify tài liệu/taxonomy phân biệt được tối thiểu:

```text
retrieval correct + answer wrong
→ Generation failure

retrieval wrong
→ Retrieval failure

factually correct but unsupported
→ Faithfulness failure

correct answer + wrong supporting source
→ Citation Correctness failure

valid citation on only some required claims
→ Citation Coverage failure

CURRENT_LESSON has usable evidence but fallback occurs
→ Fallback Correctness failure

technical retrieval failure triggers external fallback
→ Critical policy failure

out-of-domain question is answered
→ Refusal failure

valid no-evidence refusal
→ behavioral success
→ not technical failure

fluent answer + fabricated citation
→ CRITICAL FAILURE
```

## Acceptance Criteria

- [ ] Phase 7 V0 targets Lesson Chat RAG only.
- [ ] Five evaluation groups are documented.
- [ ] Every agreed dimension has a clear definition.
- [ ] Critical failures are represented separately from scored dimensions.
- [ ] Operational quality is separate from semantic quality.
- [ ] No metric formula/dataset size/judge/regression threshold is prematurely selected.
- [ ] Step 7.2 can consume the taxonomy without redefining evaluation dimensions.
- [ ] No benchmark execution is added in Step 7.1.
