# Step 7.6 — Regression Evaluation

## Implementation Goal

Xây regression evaluation để so sánh một candidate Lesson Chat RAG với một baseline đã được approve, sử dụng artifacts từ Step 7.3, 7.4 và 7.5.

Step này phải trả lời:

```text
candidate system
vs
approved baseline
→ tốt hơn, ổn định hay regression?
```

Không tích hợp CI/CD production gate trong Phase 7.

## Baseline Identity

Baseline phải được explicit promote/approve bằng:

```text
baseline_run_id
```

Không tự động coi run mới nhất là baseline.

Baseline và candidate phải capture cùng loại metadata:

```text
dataset_version
code_commit
embedding_profile
chunking_version
retrieval_config
reranker_config
prompt_version
llm_model_config
```

Regression comparison chỉ hợp lệ khi dataset/schema compatibility được xác nhận.

## Regression Layers

Report bắt buộc tách:

```text
Retrieval Regression
Generation Regression
End-to-End Regression
```

Nguồn dữ liệu:

```text
Step 7.3 artifacts
→ retrieval comparison

Step 7.4 artifacts
→ generation comparison

Step 7.5 artifacts
→ E2E comparison
```

Không chỉ nhìn một overall E2E pass rate.

## Critical Failure Gate

Critical failures là blocking gate độc lập.

Candidate FAIL nếu tạo thêm critical failure mới như:

```text
fabricated citation
scope violation
technical failure treated as no-evidence
wrong refusal/fallback behavior
serious factual error
confident unsupported claim
```

Rule:

```text
new critical failure
→ FAIL REGRESSION
```

Improvement ở metric khác không được bù.

Nếu baseline đã có critical failures:
- resolved failures phải được report;
- remaining failures vẫn không được coi là clean pass nếu policy yêu cầu zero critical failure.

## Numeric Regression Thresholds V0

### Retrieval metrics

Candidate không được giảm quá:

```text
2 percentage points
```

áp dụng cho các metric chính như:
- Recall@20
- Recall@5
- Precision@5
- nDCG@5

### Generation dimensions

Candidate mean score cho mỗi dimension không được giảm quá:

```text
0.10
```

trên thang:

```text
0–2
```

### E2E pass rate

Candidate không được giảm quá:

```text
2 percentage points
```

### Technical failure rate

Candidate không được tăng quá:

```text
1 percentage point
```

### p95 latency

Candidate không được tăng quá:

```text
20%
```

Các threshold trên là policy V0 và phải version được để có thể điều chỉnh sau khi tích lũy thêm baseline runs.

## Regression Classification

Mỗi metric/dimension được classify:

```text
REGRESSION
STABLE
IMPROVEMENT
```

Rule V0:

```text
delta < -threshold
→ REGRESSION

|delta| <= threshold
→ STABLE

delta > threshold
→ IMPROVEMENT
```

Critical failure gate luôn có priority cao hơn metric classification.

## Holdout Stability

Step 7.5 đã chạy holdout 3 lần/case.

Per-case classification:

```text
3/3 PASS
→ STABLE_PASS

2/3 PASS
→ UNSTABLE_PASS

1/3 PASS
→ UNSTABLE_FAIL

0/3 PASS
→ STABLE_FAIL
```

Regression comparison phải detect stability degradation.

Ví dụ:

```text
baseline = 3/3
candidate = 2/3
→ stability regression
```

Không chỉ aggregate mean của 3 repeats.

## Per-Case Transition Diff

Regression report bắt buộc giữ:

```text
FIXED_CASES
REGRESSED_CASES
UNCHANGED_PASS
UNCHANGED_FAIL
NEW_CRITICAL_FAILURES
RESOLVED_CRITICAL_FAILURES
```

Aggregate metrics không đủ.

Ví dụ:

```text
baseline E2E pass = 90%
candidate E2E pass = 90%
```

nhưng:

```text
5 cases fixed
5 different cases regressed
```

→ phải nhìn thấy trong report.

## Regression Artifact

Recommended structure:

```text
evaluation/regressions/<comparison_id>/
├── manifest.json
├── summary.json
├── cases.jsonl
└── report.md
```

### manifest.json

Tối thiểu:

```text
comparison_id
baseline_run_id
candidate_run_id
dataset_version
comparison_policy_version
timestamp
```

### summary.json

Tối thiểu:

```text
retrieval_metric_deltas
generation_dimension_deltas
e2e_pass_delta
technical_failure_delta
latency_delta
bucket_level_deltas
stability_deltas
critical_failure_deltas
gate_results
overall_status
```

### cases.jsonl

Per-case giữ:

```text
case_id
baseline_result
candidate_result
transition
baseline_critical_failures[]
candidate_critical_failures[]
stability_change?
notes?
```

### report.md

Human-readable summary:
- baseline vs candidate identity;
- metric table;
- bucket-level changes;
- regressed/fixed cases;
- critical failures;
- final gate decision.

## Final Status

Regression output có 3 trạng thái:

```text
PASS
FAIL
REVIEW_REQUIRED
```

### PASS

```text
no blocking critical failure
+
no metric exceeds regression threshold
+
no unresolved review condition
```

### FAIL

```text
new blocking critical failure
or
metric regression vượt threshold
or
stability regression vượt policy
```

### REVIEW_REQUIRED

Dùng khi:
- metric sát boundary và cần human judgment;
- judge/human disagreement đáng kể;
- artifact compatibility issue không đủ để auto-pass/fail;
- change có trade-off quan trọng nhưng chưa vi phạm hard gate.

Không tự động coi `REVIEW_REQUIRED` là PASS.

## Policy Versioning

Regression policy phải có:

```text
comparison_policy_version
```

Mọi threshold/gate change phải version được.

Không sửa silent policy rồi so các historical runs như thể cùng một rule.

## Out of Scope

Không implement trong Step 7.6:
- CI/CD integration;
- deployment gate wiring;
- production monitoring;
- automated rollback;
- online A/B testing.

Các phần này thuộc Phase 8–10 hoặc future iteration.

## Verification

Verify tối thiểu:

```text
baseline explicit approved run
+
candidate run
→ comparison valid
```

```text
candidate Recall@20 giảm 3 percentage points
→ REGRESSION
→ FAIL nếu không có override policy
```

```text
candidate generation mean giảm 0.05
→ STABLE
```

```text
candidate p95 latency tăng 25%
→ REGRESSION
```

```text
candidate tạo fabricated citation mới
→ NEW_CRITICAL_FAILURE
→ FAIL
```

```text
baseline case 3/3 PASS
candidate case 2/3 PASS
→ stability regression
```

```text
aggregate pass rate không đổi
+
một số case fixed
+
một số case regressed
→ per-case transitions vẫn hiển thị
```

```text
same comparison
+
comparison_policy_version khác
→ không silently reuse old decision
```

## Acceptance Criteria

- [ ] Baseline được explicit identify bằng `baseline_run_id`.
- [ ] Retrieval, Generation và E2E regression được report riêng.
- [ ] Critical failure gate độc lập với aggregate metrics.
- [ ] V0 numeric regression thresholds được implement/versioned.
- [ ] REGRESSION/STABLE/IMPROVEMENT classification tồn tại.
- [ ] Holdout pass consistency 0–3 được compare.
- [ ] Per-case transition diff được report.
- [ ] Regression artifact có manifest + summary + cases + report.
- [ ] Final status hỗ trợ PASS / FAIL / REVIEW_REQUIRED.
- [ ] Comparison policy có version.
- [ ] Chưa wire CI/CD hoặc deployment gate trong Phase 7.
