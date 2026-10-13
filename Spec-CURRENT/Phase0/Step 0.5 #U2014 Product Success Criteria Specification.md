# Step 0.5 — Product Success Criteria Specification

## 1. Purpose

Tài liệu này định nghĩa success criteria chính thức cho MVP web application học tiếng Trung dành cho người Việt.

Document phải được sử dụng làm reference khi:

- thiết kế system architecture;
- xây database;
- implement backend/frontend;
- xây AI/RAG;
- xây evaluation;
- triển khai production;
- thiết lập monitoring.

Không implement code trong Step này.

---

# 2. Product Context

Product dành cho người Việt bắt đầu học Chinese từ zero tới HSK 3.

Core learning flow:

```text id="y8f0qq"
Pronunciation Foundations
→ HSK Curriculum
→ Lesson
→ Vocabulary
→ Grammar
→ Exercise
→ Periodic Test
→ Progression
```

AI hỗ trợ:

- lesson Q&A;
- vocabulary/grammar explanation;
- free-form exercise grading;
- admin exercise/test generation.

---

# 3. Success Criteria Architecture

Success criteria được chia thành:

```text id="ti6abr"
TIER 1
Must-pass Before Launch

TIER 2
Quality Targets

TIER 3
Product Analytics
```

Tier 1 failure có thể block production launch.

Tier 2 dùng cho iterative quality improvement.

Tier 3 dùng để phân tích product/learner behavior.

---

# 4. Tier 1 — Authentication

Before launch verify:

- learner registration works;
- learner login works;
- learner logout works;
- authenticated state works;
- Admin authentication works;
- role separation works.

---

# 5. Tier 1 — Pronunciation Foundations

Learner flow:

```text id="ta14hy"
Tones
→ Initials
→ Finals
→ Foundations Complete
→ HSK1 available
```

No quiz required.

No pronunciation score required.

Completion state must persist.

---

# 6. Tier 1 — Lesson Flow

Required end-to-end flow:

```text id="t2ysue"
Open Lesson
→ View Vocabulary
→ View Grammar
→ Theory Complete
→ Start Exercise
→ Submit
→ Grade
→ View Feedback
```

All critical transitions must work.

---

# 7. Tier 1 — Lesson Completion

Official requirement:

```text id="d8gg00"
theory_completed = true

AND

best_valid_exercise_score >= 90
```

results in:

```text id="bcrjbn"
lesson_completed = true
```

---

# 8. Tier 1 — Curriculum Unlocking

After lesson completion:

```text id="ssslaf"
next curriculum unit
→ UNLOCKED
```

After a required periodic test:

```text id="2k2ynq"
test_score >= 90
→ test completed
→ next curriculum unit unlocked
```

System must never unlock future units incorrectly.

---

# 9. Tier 1 — Progress Persistence

Progress must survive:

- page refresh;
- logout/login;
- browser restart;
- normal application restart.

Persistent states include:

- pronunciation completion;
- lesson theory completion;
- lesson completion;
- HSK progress;
- exercise/test attempts;
- unlock state.

---

# 10. Tier 1 — Exercise History

All attempts must be retained.

System must not keep only best/latest attempt.

Historical data must remain queryable.

---

# 11. Tier 1 — Exercise Grading

Objective questions must use deterministic grading where appropriate.

Free-form:

- translations;
- sentence writing;

use LLM-based grading.

LLM output must include:

```text id="j5ho0m"
score
is_correct
feedback
grading_status
```

---

# 12. Tier 1 — LLM Grading Uncertainty

If LLM cannot grade confidently:

```text id="o9s5z3"
grading_status = uncertain
```

That question must:

```text id="rz495q"
NOT count as incorrect
NOT reduce learner score
```

Exact technical implementation will be designed later.

---

# 13. Tier 1 — Exercise Feedback

Learner must receive:

- overall score;
- per-question result;
- correct/reference answer;
- explanation;
- free-form feedback.

---

# 14. Tier 1 — AI Lesson Assistant

AI must satisfy the following functional quality requirements:

1. Answer relevant Chinese-learning questions.
2. Receive current lesson context automatically.
3. Prefer lesson context.
4. Prefer internal knowledge.
5. Use trusted external knowledge when internal knowledge is insufficient.
6. Return citations for retrieved knowledge.
7. Refuse unrelated domain questions.
8. Avoid guessing when evidence is insufficient.
9. Explain in Vietnamese suitable for beginner learners.

---

# 15. Tier 1 — AI Citation

Retrieved answers must have source attribution.

MVP citation:

```text id="qbdb0j"
Source / Document Name
+
Section or Page when available
```

Fabricated citations are prohibited.

---

# 16. Tier 1 — AI Content Generation

Lesson exercise generation must be limited to:

```text id="gmfpkg"
Knowledge belonging to selected lesson
```

Periodic test generation must be limited to:

```text id="j7cdb6"
Knowledge explicitly selected by Admin
```

---

# 17. Tier 1 — Human Approval

AI-generated content must follow:

```text id="lr5kfz"
Generate
→ Draft
→ Admin Review
→ Admin Edit
→ Admin Approve
→ Publish
```

No automatic publication.

---

# 18. Tier 1 — Document Ingestion

Supported document types:

```text id="hfc5nc"
PDF
DOCX
TXT
MD
```

Critical workflow:

```text id="xioyep"
Upload
→ Extract
→ Preview
→ Admin Review
→ Approve
→ Active KB
```

Unapproved content must not be used by production RAG.

---

# 19. Tier 1 — Security

Before production verify:

- passwords are never stored in plaintext;
- protected APIs require authentication;
- role authorization exists;
- learner cannot invoke Admin operations;
- user cannot read another user's private learning/chat data;
- secrets are not committed/hard-coded;
- uploaded file types/content are validated;
- AI endpoints have basic rate limiting.

---

# 20. Tier 1 — Backup / Recovery

Production database requires daily backup.

Success criterion is not only backup creation.

Must verify:

```text id="iyq88d"
Create Backup
→ Restore
→ Validate Restored Data
```

At least one successful restore test is required before production readiness is considered complete.

---

# 21. Tier 2 — AI Answer Quality

AI must prioritize correctness over answer coverage.

Expected decision pattern:

```text id="us5kmn"
Reliable evidence
→ Answer

Internal evidence insufficient
→ External retrieval

Still insufficient
→ State uncertainty / cannot answer confidently
```

The AI must not hallucinate merely to provide an answer.

---

# 22. Tier 2 — Context Adherence

When answering within a lesson, response must remain relevant to:

- current lesson;
- learner's current HSK context;
- related vocabulary;
- related grammar.

Going outside lesson scope is acceptable only when needed to explain the learner's question.

---

# 23. Tier 2 — Explanation Quality

AI response should:

- use understandable Vietnamese;
- retain Chinese text where relevant;
- include Pinyin where useful;
- use examples when necessary;
- avoid unnecessary advanced terminology.

---

# 24. Tier 2 — LLM Grading Agreement

Create a manually reviewed evaluation dataset for free-form answer grading.

Initial target:

```text id="5ot4r2"
LLM / Human Agreement >= 95%
```

Evaluation dataset should include:

- exact correct answers;
- valid alternative answers;
- partially correct answers;
- clearly wrong answers;
- ambiguous answers.

---

# 25. Tier 2 — Grading Abstention

A confident incorrect grade is considered worse than an abstention when the answer is genuinely ambiguous.

Evaluation must explicitly test uncertainty behavior.

---

# 26. Tier 2 — Retrieval Quality

At product level, RAG should:

- retrieve relevant material;
- avoid significantly unrelated material;
- attach correct source attribution;
- correctly fallback when internal KB is insufficient;
- prefer trusted sources externally.

Exact retrieval metrics will be specified during the Evaluation phase.

---

# 27. Tier 2 — Content Generation Quality

AI-generated exercises must satisfy:

- requested lesson scope;
- requested question count;
- requested types;
- requested difficulty;
- valid output structure.

AI-generated tests must satisfy selected multi-lesson scope.

All outputs remain editable drafts until Admin approval.

---

# 28. Tier 2 — Performance

Expected MVP load:

```text id="203kpx"
10–50 concurrent users
```

Normal application target:

```text id="4urotg"
p95 API latency < 1 second
```

AI target:

```text id="7t0cs6"
p95 first-response latency < 5 seconds
```

when technically practical under normal operating conditions.

These are quality targets, not formal contractual SLAs.

---

# 29. Tier 2 — Technical Error Rate

Initial targets:

```text id="j189li"
Normal API technical error rate < 1%

AI request technical failure rate < 2%
```

Valid domain refusals do not count as technical failures.

---

# 30. Reliability

No formal uptime SLA is required for the initial MVP.

Success means:

- system operates stably for expected users;
- ordinary failures do not corrupt data;
- application can recover from common operational issues.

---

# 31. Tier 3 — Learner Completion Metrics

Track:

```text id="xe02id"
Pronunciation Foundation Completion Rate

HSK1 Completion Rate
HSK2 Completion Rate
HSK3 Completion Rate

Per-Lesson Completion Rate
```

---

# 32. Lesson Completion Duration

For each learner/lesson store enough data to derive:

```text id="ubkfjn"
lesson_completion_duration =
lesson_completed_at - lesson_started_at
```

Recommended definition:

```text id="cuquna"
lesson_started_at
=
first actual learner entry/start of lesson
```

Analytics:

```text id="4skr5g"
Average Days to Complete Lesson
```

should be available per lesson.

---

# 33. HSK Completion Duration

Track:

```text id="0yp5zf"
hsk_completion_duration =
hsk_completed_at - hsk_started_at
```

where HSK starts when learner begins the first required unit of that HSK.

Analytics should support:

```text id="a0x038"
Average Days to Complete HSK1
Average Days to Complete HSK2
Average Days to Complete HSK3
```

These are observational metrics initially.

They are not yet used as time limits.

---

# 34. Exercise Analytics

Track:

```text id="yqbsjc"
Average Exercise Score
Average Attempts Before Pass
Lesson Exercise Pass Rate
Periodic Test Pass Rate
```

Metrics should eventually be aggregatable by:

- overall product;
- HSK;
- lesson;
- test.

---

# 35. Admin Dashboard Statistics

The following statistics belong to the Admin role.

Required MVP Admin Dashboard summary:

## User Statistics

```text id="cy69ib"
Total Users
Users by Current HSK
```

## Content Inventory

```text id="n80uot"
Total Lessons
Total Tests
```

## Learning Performance

```text id="i0tuqp"
Average Exercise Score
```

Future analytics may additionally expose:

- completion rates;
- completion duration;
- attempts before pass;
- test pass rates.

---

# 36. Product Usage Metrics

The product should preserve enough event/state data to later compute:

```text id="ha7r8o"
Registered Users
Active Users
Lessons Completed
Tests Completed
Exercise Attempts
AI Questions
```

Growth/retention optimization is not a current launch priority.

---

# 37. Current Product Priority

Initial priority order:

```text id="mtwnrd"
1. Correctness
2. Complete Learning Workflow
3. AI Quality
4. Reliability
5. Product Usage Optimization
6. Strict Learning Time Targets later
```

Do not introduce aggressive completion-time requirements yet.

---

# 38. MVP Go-Live Critical Flow

The product is not ready for production if any critical path below is broken:

```text id="fhz1uq"
Authentication
↓
Pronunciation Foundations
↓
Curriculum
↓
Lesson
↓
Theory Tracking
↓
Exercise
↓
Grading
↓
Feedback
↓
Progress Persistence
↓
Unlocking
↓
Periodic Test
↓
AI Lesson Q&A
↓
RAG / Citation
↓
External Knowledge Fallback
↓
Admin Content Management
↓
AI Content Generation
↓
Human Review
↓
Document Ingestion
↓
Admin Statistics
```

---

# 39. Data Implications

Future data model must make it possible to calculate success metrics.

Important timestamps/states likely required include:

```text id="gm8keu"
lesson_started_at
lesson_completed_at

hsk_started_at
hsk_completed_at

exercise_attempted_at
test_attempted_at

score
grading_status

pronunciation_completed_at
```

These are logical data requirements.

Do not create final database schema in this Step.

---

# 40. AI Evaluation Data Requirement

Future Evaluation phase must create datasets capable of testing:

## AI Q&A

- correct answer;
- incorrect answer;
- grounded answer;
- unsupported answer;
- out-of-domain question.

## LLM Grading

- exact correct;
- alternative correct;
- partially correct;
- incorrect;
- ambiguous.

## RAG

- question;
- expected relevant knowledge;
- expected source.

No evaluation dataset implementation is required now.

---

# 41. Technology Decisions

No specific tool is selected for:

- product analytics;
- AI evaluation;
- observability;
- monitoring;
- database;
- BI dashboard.

Do not introduce tools solely based on this document.

---

# 42. Explicit Non-goals

The following are not current success criteria:

- daily learner study-time requirement;
- completion deadlines;
- DAU growth targets;
- paid conversion;
- revenue;
- social engagement;
- leaderboard performance;
- formal enterprise uptime SLA.

These may be introduced in later product iterations.

---

# 43. Acceptance Criteria for Step 0.5

Step 0.5 is complete when success criteria exist for:

- [ ] learner core flow;
- [ ] curriculum progression;
- [ ] exercise/test grading;
- [ ] learner progress persistence;
- [ ] AI lesson assistant;
- [ ] AI uncertainty;
- [ ] citations;
- [ ] RAG behavior;
- [ ] AI content generation;
- [ ] document ingestion;
- [ ] security;
- [ ] backup and restore;
- [ ] AI grading agreement;
- [ ] latency;
- [ ] technical error rate;
- [ ] learner completion rates;
- [ ] average lesson completion time;
- [ ] average HSK completion time;
- [ ] exercise analytics;
- [ ] Admin Dashboard inventory statistics;
- [ ] MVP go-live critical flow.

---

# 44. Verification Checklist

Before closing Step 0.5:

- [ ] Core flow defines launch blockers.
- [ ] AI correctness is prioritized over answering every question.
- [ ] Out-of-domain refusal remains required.
- [ ] Uncertain LLM grades do not punish learner.
- [ ] LLM grading target is >=95% human agreement.
- [ ] RAG requires correct sourcing.
- [ ] Generated exercise remains constrained to lesson scope.
- [ ] Admin approval remains mandatory.
- [ ] Document approval remains mandatory.
- [ ] Security baseline remains launch-critical.
- [ ] Daily backup has restore verification.
- [ ] Expected concurrency remains 10–50.
- [ ] p95 API target remains <1 second.
- [ ] p95 AI first-response target remains <5 seconds where practical.
- [ ] Total Users is Admin statistic.
- [ ] Total Lessons is Admin statistic.
- [ ] Total Tests is Admin statistic.
- [ ] Lesson/HSK completion duration is tracked.
- [ ] No strict learning-time requirement has been added yet.

---

# 45. Expected Deliverable

Recommended project documentation:

```text id="hvys6m"
docs/product/
├── step-0.1-problem-target-user.md
├── step-0.2-product-scope-mvp.md
├── step-0.3-user-journey-use-cases.md
├── step-0.4-product-requirements.md
└── step-0.5-product-success-criteria.md
```

No executable implementation is required.

---

# 46. Product Definition Phase Completion

After this Step:

```text id="l0nl6t"
PHASE 0 — PRODUCT DEFINITION

0.1 Problem & Target User          ✓
0.2 Product Scope & MVP            ✓
0.3 User Journey & Core Use Cases  ✓
0.4 Product Requirements           ✓
0.5 Product Success Criteria       ✓

PHASE 0 COMPLETE
```

Next Phase:

```text id="zcx5yp"
PHASE 1 — SYSTEM DESIGN
```

Next Step:

**Step 1.1 — System Context**