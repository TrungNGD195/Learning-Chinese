# Step 7.5 — End-to-End RAG Evaluation

> **Current PM freeze D-103 through D-105:** This note supersedes conflicting legacy text below.
> The current approved dataset is v0.8.0 with 60 cases (48 DEVELOPMENT / 12 HOLDOUT);
> the official plan is 84 executions (48 DEVELOPMENT once each, 12 HOLDOUT three times).
> D-103 requires the exact hard-validity AND formula with no numeric quality threshold.
> D-104 freezes the Step-7.5 judge contract and D-100 provider configuration; offline mode
> must not call the judge. D-105 requires actual_behavior to come only from the captured
> production trace. Current production has no explicit OOD guard/result/response contract.
> An expected REFUSE_OUT_OF_DOMAIN label is compared only after execution: an answer or
> fallback fails with OUT_OF_DOMAIN_ANSWER; generic no-evidence remains REFUSE_NO_EVIDENCE
> and fails without that critical; technical errors remain TECHNICAL_FAILURE. The evaluator
> never synthesizes OOD behavior or implements an OOD feature.

## Targeted offline implementation rework

Specialist rework keeps the frozen methodology and uses evaluation-local observers around the current production-shaped request seams. The observer records actual per-tier retrieval candidates, reranked evidence and scores, the configured evidence-gate threshold and result, prompt construction, and the exact `PromptPackage.source_map`. It reads the final Assistant, `MessageRetrieval`, and `MessageCitation` rows after learner-service finalization and validates the completed trace using `E2EExecutionTrace`.

Internal required evidence continues to use Step-7.3 requirement/equivalent-locator groups. Trusted external required evidence uses exact `EXTERNAL_URL` identity groups from the frozen annotations. Every required group must be met. A selected context whose actual rerank score is below `RAG_MIN_RERANK_SCORE` is a gate failure. Citation-only critical failures affect citation and final E2E validity without being reclassified as generation failures under D-103.

Local integration tests use the real PostgreSQL retrieval, pinned embedding/reranking providers, prompt/memory/citation services, and learner application/persistence path. The paid LLM boundary is replaced with a deterministic no-network test provider, and external search uses only the accepted fixture provider. These tests explicitly skip when the isolated test database or exact pinned model snapshots are unavailable. The offline rework does not perform the official 84-execution run.

## Implementation Goal

Xây end-to-end evaluation cho Lesson Chat RAG bằng cách chạy đúng production-shaped request path từ user input đến final persisted assistant response.

Step này kết hợp:
- retrieval;
- reranking;
- prompt/context construction;
- conversation memory;
- LLM generation;
- citation validation;
- tier fallback/refusal;
- persistence/finalization;
- operational metrics.

Regression comparison/gating thuộc Step 7.6.

## E2E Evaluation Path

```text
EvaluationCase
↓
Conversation Context
↓
Scope Derivation
↓
CURRENT_LESSON
↓
INTERNAL_KB
↓
TRUSTED_EXTERNAL nếu cần
↓
Reranking
↓
Prompt + Memory
↓
LLM
↓
Citation Validation
↓
Persistence / Finalization
↓
Final Assistant Response
```

Không bypass retriever bằng gold evidence.

Relationship giữa các Step:

```text
7.3
→ retriever isolated

7.4
→ generator isolated

7.5
→ actual system behavior
```

## Dataset Coverage

Official E2E evaluation dùng toàn bộ 6 bucket từ Step 7.2:

```text
CURRENT_LESSON_ANSWERABLE
INTERNAL_KB_FALLBACK
TRUSTED_EXTERNAL_FALLBACK
NO_EVIDENCE_REFUSAL
OUT_OF_DOMAIN_REFUSAL
MULTI_TURN_CONTEXT
```

Current official dataset gate: 60 APPROVED cases (48 DEVELOPMENT / 12 HOLDOUT), producing 84 planned executions. The 120-case portfolio is a later expansion target only.

## Per-Case Outcome

Không tạo một RAG score duy nhất làm source of truth.

Per-case giữ riêng:

```text
retrieval_ok
generation_ok
citation_ok
context_ok
fallback_ok
refusal_ok
technical_ok
critical_failures[]
e2e_case_pass
```

Rule:

```text
required dimensions pass
+
no critical failure
→ E2E PASS
```

Critical failure không được bù bởi average score cao ở dimension khác.

## Citation Semantic Evaluation

Step 6.10 đã validate structural citation correctness:

```text
syntax
label existence
current source_map membership
provenance resolution
```

Step 7.5 đánh giá thêm semantic citation quality.

Claim-level flow:

```text
Generated Answer
↓
grounded claims
↓
citation(s)
↓
resolved source content
↓
SUPPORTED
UNSUPPORTED
CONTRADICTED
```

Đánh giá:

```text
Citation Correctness
Citation Coverage
```

Use:

```text
deterministic runtime checks
+
calibrated semantic judge
+
human calibration/adjudication
```

LLM judge không thay runtime CitationValidator.

## Fallback / Refusal Evaluation

Step 7.2 đã có:

```text
expected_tier
expected_behavior
```

Step 7.5 phải capture actual execution trace và compare trực tiếp.

Expected tiers:

```text
CURRENT_LESSON
INTERNAL_KB
TRUSTED_EXTERNAL
NONE
```

Canonical expected behaviors:

```text
ANSWER
FALLBACK_INTERNAL
FALLBACK_EXTERNAL
REFUSE_NO_EVIDENCE
REFUSE_OUT_OF_DOMAIN
```

Critical policy failures gồm:

```text
skip usable higher-priority tier
technical error treated as no-evidence
answer instead of required refusal
refuse despite usable allowed evidence
```

## Trusted External Evaluation

External retrieval vendor vẫn chưa được chốt.

V0 dùng deterministic trusted-external test adapter/fixture:

```text
TRUSTED_EXTERNAL request
↓
known trusted fixture results
↓
normal downstream RAG pipeline
```

Mục tiêu test:
- tier transition;
- external provenance;
- URL validation;
- generation;
- citation.

Không chọn vendor mới chỉ để hoàn thành evaluation.

## Multi-Turn Evaluation

`MULTI_TURN_CONTEXT` phải kiểm tra:

```text
current query được hiểu đúng từ recent conversation
history không trở thành retrieved evidence
historical [S<number>] markers không leak
current citations chỉ resolve current source_map
```

Invariant:

```text
Conversation Memory
≠
Retrieved Evidence
```

Nếu model dùng unsupported information chỉ từ history:

```text
→ faithfulness / grounding failure
```

## Operational Evaluation

Per E2E execution lưu:

```text
total_latency
retrieval_latency
rerank_latency
llm_latency
citation_finalization_latency
token_usage
technical_status
```

Aggregate tối thiểu:

```text
p50 total latency
p95 total latency
technical failure rate
```

Reference targets hiện tại có thể được report nhưng chưa trở thành regression gate trong Step 7.5.

## Stochasticity Policy

Development:

```text
1 execution / case
```

Holdout:

```text
3 executions / case
```

Với 96 development + 24 holdout:

```text
96 × 1
+
24 × 3
=
168 E2E executions
```

Holdout repeats dùng để đo:
- pass consistency;
- critical-failure recurrence;
- score variance;
- stochastic instability.

## E2E Run Artifact

Recommended structure:

```text
evaluation/runs/<run_id>/e2e/
├── manifest.json
├── cases.jsonl
└── summary.json
```

### manifest.json

Tối thiểu:

```text
run_id
timestamp
dataset_version
dataset_split
code_commit
embedding_profile/model
chunking identity
retrieval config
reranker config
prompt version/hash
LLM provider/model/config
judge model/version
rubric version
external fixture version
```

### cases.jsonl

Per execution lưu structured trace:

```text
case_id
repeat_index
conversation input
expected_tier
expected_behavior
actual_tier_transitions
retrieval candidates
reranked evidence
source_map
prompt/context identity
generated answer
validated citations
dimension results
critical_failures[]
latencies
token_usage
final_message_status
error_code?
e2e_case_pass
```

Không lưu:
- secret/API key;
- credentials;
- raw private production learner data.

### summary.json

Aggregate tối thiểu:

```text
overall E2E pass rate
pass rate by bucket
citation correctness/coverage summary
fallback/refusal correctness
critical failure count/rate
p50/p95 latency
technical failure rate
holdout pass consistency
holdout critical-failure recurrence
holdout score variance
```

## Threshold Policy

Step 7.5 chưa đặt:
- overall pass gate;
- bucket pass gate;
- citation threshold;
- latency regression threshold;
- stochasticity threshold.

Các threshold/regression policy thuộc Step 7.6.

## Out of Scope

Không implement trong Step 7.5:
- regression comparison;
- baseline-vs-candidate gate;
- CI quality gate;
- production monitoring;
- real external vendor selection.

## Verification

Verify tối thiểu:

```text
CURRENT_LESSON có usable evidence
→ actual tier = CURRENT_LESSON
→ no unnecessary fallback
```

```text
CURRENT_LESSON insufficient
+
INTERNAL_KB usable
→ FALLBACK_INTERNAL
→ answer
```

```text
internal tiers insufficient
+
trusted external fixture usable
→ FALLBACK_EXTERNAL
→ external provenance/citation valid
```

```text
no usable evidence
→ REFUSE_NO_EVIDENCE
→ no hallucinated answer
```

```text
out-of-domain
→ REFUSE_OUT_OF_DOMAIN
```

```text
technical retrieval failure
→ not treated as no-evidence
→ critical policy failure if fallback happens
```

```text
claim [S1]
+
S1 resolves
+
source does not support claim
→ Citation Correctness failure
```

```text
factual claim cần grounding
+
không có citation
→ Citation Coverage failure
```

```text
multi-turn query cần history
→ answer uses relevant history
→ history still not treated as evidence
```

```text
historical [S1]
→ does not resolve against current source_map
```

```text
holdout case 3 repeats
→ pass/fail consistency report được
```

```text
same dataset + same system config
→ run artifact đủ metadata để reproduce
```

## Acceptance Criteria

- [ ] Full production-shaped RAG path được evaluate.
- [ ] Cả 6 dataset buckets được chạy trong official E2E evaluation.
- [ ] Current gate supports 60 APPROVED cases (48 DEVELOPMENT / 12 HOLDOUT) and 84 planned executions; 120 is a later portfolio target.
- [ ] Per-case dimension results và boolean `e2e_case_pass` tồn tại.
- [ ] Citation semantic correctness/coverage được đánh giá claim-level.
- [ ] Expected tier/behavior được compare với actual execution trace.
- [ ] Trusted external V0 dùng deterministic fixture, không cần real vendor.
- [ ] Multi-turn memory/evidence isolation được verify.
- [ ] Operational latency và technical status được capture.
- [ ] Development chạy 1×/case, holdout 3×/case.
- [ ] E2E run artifact có manifest + cases + summary.
- [ ] Chưa đặt premature regression/pass gates.
- [ ] Step 7.6 có thể dùng E2E artifacts trực tiếp để regression compare.
