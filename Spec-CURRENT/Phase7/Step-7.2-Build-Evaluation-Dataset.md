# Step 7.2 — Build Evaluation Dataset

## Implementation Goal

Xây foundation cho evaluation dataset của Phase 7 dựa trên taxonomy đã chốt ở Step 7.1.

System under evaluation:

```text
Lesson Chat RAG
```

Dataset phải đủ ground truth để Step 7.3–7.5 đánh giá:
- retrieval quality;
- generation quality;
- citation quality;
- end-to-end behavior;
- operational behavior.

Step này không implement metric formulas, judge logic, regression thresholds hoặc CI gates.

## Dataset Unit

Một `EvaluationCase` đại diện cho **một RAG request hoàn chỉnh**.

Schema phải support:
- single-turn case;
- optional prior conversation context cho multi-turn case.

Logical shape:

```text
EvaluationCase
├── case_id
├── schema_version
├── dataset_version
├── bucket
├── split
├── question
├── conversation_context?
├── lesson_context?
├── expected_information[]
├── reference_answer?
├── required_evidence[]
├── acceptable_evidence[]
├── expected_scope
├── expected_tier
├── expected_behavior
├── expected_answer_properties
├── expected_citation_sources[]
├── critical_failure_expectations[]
└── review_status
```

`reference_answer` là optional supporting field, không phải ground-truth source duy nhất.

## Required Behavior Buckets

Dataset V0 phải có 6 bucket:

```text
CURRENT_LESSON_ANSWERABLE
INTERNAL_KB_FALLBACK
TRUSTED_EXTERNAL_FALLBACK
NO_EVIDENCE_REFUSAL
OUT_OF_DOMAIN_REFUSAL
MULTI_TURN_CONTEXT
```

Meaning:

```text
CURRENT_LESSON_ANSWERABLE
→ current Lesson đã có usable evidence

INTERNAL_KB_FALLBACK
→ current Lesson không đủ
→ internal KB có usable evidence

TRUSTED_EXTERNAL_FALLBACK
→ internal sources không đủ
→ trusted external source cần thiết

NO_EVIDENCE_REFUSAL
→ không tier nào có usable evidence
→ deterministic refusal

OUT_OF_DOMAIN_REFUSAL
→ ngoài Chinese-learning domain
→ refuse

MULTI_TURN_CONTEXT
→ prior conversation turns are needed to interpret the learner's conversational intent or answer context
→ BUT the current question text must still contain enough semantic information for V0 retrieval to find the required evidence without query rewriting
```

Citation correctness/coverage được đánh giá xuyên các bucket answerable/fallback, không cần bucket citation riêng.

## Ground Truth Representation

Không dùng một exact `gold_answer` duy nhất làm source of truth.

Ground truth chính:

```text
expected_information[]
```

Mỗi item là một atomic information unit cần xuất hiện trong answer đúng/đủ.

Example:

```text
expected_information:
- sentence-final 了 can indicate a new/change-of-state situation
- distinguish it from aspectual 了 after a verb
- explanation should be suitable for beginner learner
```

Optional:

```text
reference_answer
```

chỉ phục vụ:
- reviewer readability;
- later evaluator support;
- debugging.

Không dùng exact-string match với reference answer làm correctness metric.

## Evidence Annotation

### Internal Evidence

Annotate ở Chunk level hoặc stable evaluation locator tương đương.

Tách:

```text
required_evidence[]
acceptable_evidence[]
```

`required_evidence`:
- evidence bắt buộc phải được retrieve để trả lời đầy đủ.

`acceptable_evidence`:
- source/chunk khác vẫn hợp lệ và đủ support.

Logical evidence item:

```text
EvidenceRef
├── source_kind = INTERNAL_CHUNK
├── chunk_id? / stable_locator
├── source_title
├── lesson_id?
├── section/page/locator?
└── relevance_role = REQUIRED | ACCEPTABLE
```

Không hard-code physical DB UUID nếu repository fixture cần stable semantic locator để survives reseeding; implementation phải inspect codebase/test data strategy trước khi chọn exact representation.

### External Evidence

Annotate ở trusted source/URL level:

```text
source_kind = EXTERNAL_URL
url
domain
title?
```

Không tạo fake internal Chunk cho external source.

## Expected Scope / Tier / Behavior

Mỗi case phải có canonical expectation:

```text
expected_scope
expected_tier
expected_behavior
```

Expected tier values:

```text
CURRENT_LESSON
INTERNAL_KB
TRUSTED_EXTERNAL
NONE
```

Expected behavior canonical values:

```text
ANSWER
FALLBACK_INTERNAL
FALLBACK_EXTERNAL
REFUSE_NO_EVIDENCE
REFUSE_OUT_OF_DOMAIN
```

Multi-turn case vẫn dùng các behavior trên; `MULTI_TURN_CONTEXT` là dataset bucket, không phải runtime behavior.

### V0 multi-turn retrieval constraint

Step 6.9 provides conversation history to generation/context handling but V0 does **not** require history-aware query rewriting before retrieval. Therefore an approved `MULTI_TURN_CONTEXT` case must satisfy both:

```text
conversation_context is required to interpret the conversational intent/answer correctly
AND
the current question text by itself remains retrieval-sufficient for the expected evidence
```

Do not add V0 benchmark cases whose current turn is only an unresolved pointer such as “Còn cái đó thì sao?” when retrieving the expected evidence would require rewriting the query from prior turns. Such cases belong to a future query-rewrite capability.

`expected_scope` phải đủ để Step 7.3/7.5 xác định retrieval có vượt scope hay không.

## Dataset Size V0

Minimum implementation gate:

```text
60 APPROVED cases
```

Recommended minimum distribution:

```text
CURRENT_LESSON_ANSWERABLE  20
INTERNAL_KB_FALLBACK       10
TRUSTED_EXTERNAL_FALLBACK   5
NO_EVIDENCE_REFUSAL         8
OUT_OF_DOMAIN_REFUSAL       7
MULTI_TURN_CONTEXT         10
-----------------------------
TOTAL                      60
```

Portfolio target after the product is already functioning:

```text
120 APPROVED cases
```

The 120-case target must not block initial implementation/evaluation release. Expand toward it only after the 60-case official dataset is stable and the core pipeline works.

## Development / Holdout Split

Use approximately:

```text
80% DEVELOPMENT
20% HOLDOUT
```

Minimum 60-case V0 split:

```text
CURRENT_LESSON_ANSWERABLE   16 dev / 4 holdout
INTERNAL_KB_FALLBACK         8 dev / 2 holdout
TRUSTED_EXTERNAL_FALLBACK    4 dev / 1 holdout
NO_EVIDENCE_REFUSAL          6 dev / 2 holdout
OUT_OF_DOMAIN_REFUSAL        6 dev / 1 holdout
MULTI_TURN_CONTEXT           8 dev / 2 holdout
-----------------------------------------------
TOTAL                       48 dev / 12 holdout
```

Split phải stratified theo bucket.

Development:
- có thể xem kết quả chi tiết;
- dùng để debug/tune retrieval/prompt/reranker/model.

Holdout:
- không dùng để tune theo từng case;
- dùng để kiểm tra generalization và regression.

Case split assignment phải stable khi rerun.

## Case Creation / Review Workflow

Allowed flow:

```text
Approved Lesson / Internal KB / Product Policy
↓
draft evaluation question
↓
optional LLM-assisted drafting/paraphrasing
↓
manual review
↓
annotate expected_information
↓
annotate evidence/scope/tier/behavior
↓
APPROVED
↓
eligible for official evaluation dataset
```

LLM có thể hỗ trợ:
- draft questions;
- paraphrases;
- edge-case suggestions.

LLM không được tự quyết unreviewed:
- ground truth;
- required evidence;
- expected behavior;
- expected tier.

Use review status equivalent to:

```text
DRAFT
APPROVED
REJECTED
```

Official benchmark chỉ dùng `APPROVED`.

## Storage Format

Use repo-controlled JSONL.

Recommended structure:

```text
evaluation/
├── datasets/
│   └── lesson_chat_rag/
│       └── v0/
│           ├── development.jsonl
│           ├── holdout.jsonl
│           ├── manifest.json
│           └── README.md
├── schemas/
│   └── evaluation_case.schema.json
└── README.md
```

Nếu repository convention hiện tại dùng `docs/evaluation/` cho documentation, giữ documentation ở đó nhưng dataset executable/artifact nên nằm dưới `evaluation/` hoặc convention tương đương sau khi inspect repo.

## Versioning

Require:
- stable `case_id`;
- explicit `schema_version`;
- explicit `dataset_version`;
- Git-tracked dataset files.

Không tái sử dụng một `case_id` cũ cho một semantic case khác.

Nếu annotation sai và được sửa:
- giữ case identity nếu vẫn là cùng semantic case;
- bump dataset version / record change;
- update manifest/changelog tương ứng.

Nếu question/intent thay đổi thành case khác:
- tạo `case_id` mới.

## Manifest

`manifest.json` nên chứa tối thiểu:

```text
dataset_name
dataset_version
schema_version
system_under_evaluation
created_at / updated_at
case_count_total
case_count_by_bucket
development_count
holdout_count
approval_policy
notes?
```

Không đưa runtime evaluation results vào dataset manifest.

## Validation

Tạo dataset validator để fail-fast trên ít nhất:

```text
duplicate case_id
unknown bucket
unknown split
unknown expected_tier
unknown expected_behavior
missing required fields
invalid review_status
APPROVED case thiếu expected_information
APPROVED answerable case thiếu evidence expectation
holdout/development overlap
wrong minimum official counts when validating the 60-case V0 gate; expanded portfolio datasets may exceed the minimum
```

Validator không đánh giá semantic correctness của human annotation.

## Security / Data Rules

Không commit:
- user private conversation data;
- production learner data;
- secrets;
- raw copyrighted textbooks nếu repository rights không cho phép.

Evaluation cases phải dùng:
- synthetic questions;
- curated project test content;
- permitted knowledge fixtures;
- approved references.

## Out of Scope

Không implement ở Step 7.2:
- Recall@K;
- Precision@K;
- MRR;
- nDCG;
- generation rubric scorer;
- LLM-as-a-Judge;
- citation semantic scorer;
- benchmark runner;
- regression comparison;
- regression gate;
- CI quality gate;
- production monitoring.

Các phần này thuộc Step 7.3–7.6 hoặc Phase 8/future evaluation work.

## Verification

Verify tối thiểu:

```text
120 approved cases
→ exact bucket counts
→ 96 development
→ 24 holdout
```

```text
same case_id xuất hiện hai lần
→ validation fail
```

```text
APPROVED CURRENT_LESSON_ANSWERABLE
+
no expected_information
→ validation fail
```

```text
APPROVED answerable case
+
no internal/external evidence expectation
→ validation fail
```

```text
NO_EVIDENCE_REFUSAL
→ expected_tier = NONE
→ expected_behavior = REFUSE_NO_EVIDENCE
```

```text
OUT_OF_DOMAIN_REFUSAL
→ expected_behavior = REFUSE_OUT_OF_DOMAIN
```

```text
MULTI_TURN_CONTEXT
→ conversation_context present
→ current question remains retrieval-sufficient without history-aware query rewriting
```

```text
holdout case
→ not duplicated in development
```

```text
LLM-drafted case
+
review_status != APPROVED
→ excluded from official benchmark
```

## Acceptance Criteria

- [ ] EvaluationCase schema exists.
- [ ] 6 behavior buckets are represented.
- [ ] Ground truth uses atomic expected information.
- [ ] Reference answer is optional, not sole truth.
- [ ] Internal evidence supports required/acceptable annotation.
- [ ] External evidence uses trusted URL/source representation.
- [ ] Expected scope/tier/behavior are canonical fields.
- [ ] V0 target is 120 approved cases.
- [ ] Exact 96/24 stratified development/holdout split is enforced.
- [ ] Manual approval is required before official benchmark inclusion.
- [ ] JSONL storage is used.
- [ ] Stable case IDs and explicit schema/dataset versions exist.
- [ ] Manifest exists.
- [ ] Dataset validation fails on structural inconsistencies.
- [ ] No evaluation metrics/judges/regression gates are prematurely implemented.
- [ ] Step 7.3 can consume the dataset directly for retrieval evaluation.
