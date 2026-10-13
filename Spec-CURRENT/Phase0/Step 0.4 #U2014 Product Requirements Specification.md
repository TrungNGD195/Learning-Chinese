# Step 0.4 — Product Requirements Specification

## 1. Purpose

Tài liệu này là Product Requirements Specification cho MVP web application học tiếng Trung dành cho người Việt.

Tài liệu tổng hợp các product decisions đã được chốt qua:

- Step 0.1 — Problem & Target User
- Step 0.2 — Product Scope & MVP
- Step 0.3 — User Journey & Core Use Cases
- Step 0.4 — Product Requirements

Đây chưa phải implementation specification cho một subsystem cụ thể.

Không tự ý lựa chọn technology stack hoặc implement application nếu chưa được yêu cầu ở Step sau.

---

# 2. Product Overview

Product là một web application dành cho người Việt bắt đầu học tiếng Trung từ số 0.

Current curriculum boundary:

```text
HSK 1
→ HSK 2
→ HSK 3
```

Core learning model:

```text
Pronunciation Foundations
        ↓
Structured Lessons
        ↓
Vocabulary
        ↓
Grammar
        ↓
Exercise
        ↓
Assessment
        ↓
Sequential Progression
```

AI là supporting component cho learner và admin.

AI không thay thế structured curriculum.

---

# 3. User Roles

MVP có hai role chính:

```text
LEARNER
ADMIN
```

---

# 4. Learner Authentication

Learner phải có thể:

- register bằng email/password;
- login;
- logout;
- xem basic profile;
- đổi password.

User identity phải persistent để lưu learning progress.

Google/social login không thuộc MVP.

---

# 5. Learner Dashboard

Sau khi login, learner vào Home/Dashboard.

Dashboard phải hiển thị tối thiểu:

- current HSK;
- current lesson;
- overall/current HSK progress;
- Continue Learning;
- HSK 1;
- HSK 2;
- HSK 3.

Locked HSK/lesson có thể hiển thị nhưng không được truy cập nội dung.

---

# 6. Pronunciation Foundations

Trước khi learner được học HSK 1 Lesson 1, learner phải hoàn thành:

```text
Pronunciation Foundations
├── Thanh điệu / Tones
├── Thanh mẫu / Initials
└── Vận mẫu / Finals
```

Không có quiz requirement.

Không có score requirement.

Completion condition:

```text
tones_completed
AND
initials_completed
AND
finals_completed
→ pronunciation_foundation_completed
```

Sau khi completed:

```text
HSK1 Lesson1
→ available according to curriculum
```

Không implement:

- speech recognition;
- pronunciation scoring;
- voice assessment;
- STT;
- TTS;

chỉ từ requirement này.

---

# 7. HSK Progression

Curriculum phải sequential:

```text
Pronunciation Foundations
↓
HSK 1
↓
HSK 2
↓
HSK 3
```

Learner không được skip HSK level.

HSK tiếp theo chỉ được unlock khi toàn bộ required curriculum units của HSK hiện tại đã complete.

---

# 8. Curriculum Units

Curriculum unit có thể là:

```text
LESSON
PERIODIC_TEST
```

Order được admin/curriculum xác định.

Ví dụ:

```text
Lesson 1
Lesson 2
Lesson 3
Test 1
Lesson 4
Lesson 5
Test 2
```

Không hard-code số lesson giữa các test.

---

# 9. Lesson Structure

Canonical lesson order:

```text
Vocabulary
→ Grammar
→ Exercise
```

---

# 10. Vocabulary Requirement

Vocabulary item phải support về mặt product:

- Chinese character(s);
- Pinyin;
- Vietnamese meaning;
- part of speech;
- one or more examples.

Exact schema chưa được thiết kế.

---

# 11. Grammar Requirement

Grammar item phải support:

- structure;
- Vietnamese explanation;
- usage scenarios;
- examples;
- optional notes.

Exact schema chưa được thiết kế.

---

# 12. Theory Completion

Lesson theory gồm:

```text
Vocabulary
+
Grammar
```

Theory không được complete chỉ vì learner bấm một nút tự khai báo.

System phải track việc learner đã mở/xem toàn bộ required:

- vocabulary items;
- grammar sections.

Conceptual rule:

```text
all_required_vocabulary_viewed
AND
all_required_grammar_viewed
→ theory_completed
```

Exact frontend/backend tracking implementation chưa được quyết định.

---

# 13. Lesson Exercise Types

MVP phải support product requirement cho:

1. Multiple Choice
2. Fill in the Blank
3. Matching
4. Reorder Sentence
5. Vietnamese → Chinese Translation
6. Chinese → Vietnamese Translation
7. Sentence Writing

Một lesson không bắt buộc chứa mọi exercise type.

---

# 14. Objective Exercise Grading

Các dạng có expected answer/key rõ ràng phải được chấm deterministic.

Examples:

```text
Multiple Choice
Matching
Reorder Sentence
Structured Fill-in-the-Blank
```

Không gọi LLM cho câu có thể chấm reliably bằng stored answer/rules.

---

# 15. Free-form Exercise Grading

Các dạng free-form gồm:

```text
Vietnamese → Chinese
Chinese → Vietnamese
Sentence Writing
```

được đánh giá bằng LLM.

LLM grading result phải có tối thiểu:

```text
score
is_correct
feedback
```

Exact schema/API chưa được thiết kế.

---

# 16. Uncertain LLM Grading

LLM không được bắt buộc đưa ra judgement khi không đủ chắc chắn.

Conceptual state cần support:

```text
GRADE_CONFIDENT
GRADE_UNCERTAIN
```

Nếu uncertain:

```text
question_result → excluded from score calculation
```

System không được tự động coi uncertain answer là incorrect.

Exact handling, retry hoặc later review behavior sẽ được thiết kế trong AI/Evaluation phase.

---

# 17. Lesson Exercise Pass Threshold

Official pass threshold:

```text
90%
```

Lesson exercise attempts không giới hạn.

System phải lưu exercise attempts.

---

# 18. Exercise Result

Sau submit learner phải nhận được:

- overall valid score;
- correct/incorrect status của từng gradable question;
- correct/reference answer;
- explanation;
- feedback cho free-form answers.

Uncertain questions phải được phân biệt với incorrect questions.

---

# 19. Lesson Completion

Lesson được complete khi:

```text
theory_completed = true
AND
best_valid_exercise_score >= 90
```

Sau khi complete:

```text
lesson.completed = permanent for current MVP behavior
```

Attempt sau có score thấp hơn không được reset completion.

---

# 20. Exercise Retry

Learner được retry lesson exercise unlimited times.

Nếu score dưới 90%:

```text
Result
→ Review Errors
→ View Correct Answers / Explanations
→ Optional AI Assistance
→ Retry
```

Không yêu cầu learner học lại theory trước khi retry.

---

# 21. Periodic Tests

Admin quyết định vị trí periodic test trong curriculum.

Test có thể bao phủ knowledge từ nhiều lesson.

Test scope được tạo từ selected:

- vocabulary;
- grammar;

của nhiều lesson.

---

# 22. Periodic Test Pass Rule

Test threshold:

```text
90%
```

Retry:

```text
UNLIMITED
```

---

# 23. Periodic Test as Gate

Periodic test là mandatory progression gate.

Nếu curriculum:

```text
Lesson 1
Lesson 2
Lesson 3
Test 1
Lesson 4
```

thì:

```text
Lesson1-3 completed
→ Test1 unlocked

Test1 score < 90
→ Lesson4 locked

Test1 score >= 90
→ Test1 completed
→ Lesson4 unlocked
```

---

# 24. Test Attempt History

Mọi test attempt phải được lưu.

System phải có khả năng lưu:

- attempt timestamp;
- score;
- submitted answers;
- grading results.

Không chỉ lưu best score.

---

# 25. Progress Calculation

Progress được tính bằng required curriculum units.

Formula:

```text
progress_percentage =
completed_required_units
/
total_required_units
* 100
```

Required unit gồm:

```text
Lesson
Periodic Test
```

Pronunciation Foundations có thể được hiển thị như prerequisite riêng; cách nó được đưa vào percentage UI sẽ được quyết định khi thiết kế progress UI nếu cần.

---

# 26. Previous Content Access

Completed content vẫn accessible.

Learner có thể:

- mở lại lesson;
- xem vocab;
- xem grammar;
- làm lại exercise;
- làm lại test;
- xem history.

Không lock lại historical content.

---

# 27. Exercise/Test History

Learner phải có thể xem history gồm:

- attempt time;
- score;
- attempt results;
- answers;
- correct/incorrect status;
- best score.

Exact UI chưa được thiết kế.

---

# 28. Lesson AI Chat

AI chat chỉ cần tích hợp trong lesson ở MVP.

Learner nhập free text.

System phải tự cung cấp current lesson context.

Conceptual request:

```text
Learner Question
+
Current Lesson
+
Conversation Context
```

Learner không phải tự nhập lesson name/id.

---

# 29. AI Knowledge Priority

AI answering priority phải theo:

```text
Current Lesson Context
        ↓
Internal Knowledge Base
        ↓
External Knowledge Retrieval
```

Không bypass relevant internal knowledge để dùng web/external knowledge ngay từ đầu.

---

# 30. Internal Knowledge Behavior

Nếu internal knowledge đủ:

```text
Question
→ Retrieve Internal Knowledge
→ Generate Grounded Answer
→ Return Source Citation
```

---

# 31. External Knowledge Fallback

Nếu:

```text
Internal Knowledge Insufficient
AND
Question belongs to allowed Chinese-learning domain
```

system được phép tự động sử dụng external retrieval.

Không cần yêu cầu learner xác nhận.

Conceptual flow:

```text
Question
→ Internal Retrieval
→ insufficient
→ External Retrieval
→ trusted-source preference
→ LLM
→ Answer + Sources
```

---

# 32. Trusted Source Preference

External retrieval phải ưu tiên:

- authoritative sources;
- trusted dictionaries;
- official educational sources;
- reliable Chinese-language references.

Không yêu cầu whitelist tuyệt đối trong MVP.

Do not fabricate source trust.

---

# 33. AI Citation

Answer dựa trên retrieved knowledge phải có citation.

MVP citation requirement:

```text
Source / Document Name
+
Section or Page when available
```

Internal và external citations phải có khả năng phân biệt nguồn.

Citation không được fabricated.

---

# 34. AI Domain Restriction

Allowed:

- Chinese vocabulary;
- Chinese grammar;
- Chinese pronunciation;
- Chinese language learning;
- language-related cultural context;
- relevant linguistic questions.

Outside-domain general questions phải từ chối.

Example:

```text
"为什么 红茶 means black tea?"
→ ALLOW
```

```text
"Ai vô địch Champions League?"
→ REFUSE
```

Exact guardrail implementation chưa được chọn.

---

# 35. Conversation Storage

AI conversation phải được lưu theo session.

Conceptually:

```text
Conversation
├── Message
├── Message
└── Message
```

Conversation phải liên kết được với:

- learner;
- relevant lesson.

---

# 36. Conversation Retention

Default:

```text
retain until learner deletes conversation
```

Không có automatic expiration requirement.

Learner có thể delete entire conversation.

Delete single message không thuộc MVP.

---

# 37. Admin Course/Content Management

Admin phải có khả năng quản lý:

- HSK/course;
- lesson;
- vocabulary;
- grammar;
- lesson exercise;
- periodic test.

Exact CRUD APIs chưa được thiết kế.

---

# 38. AI Lesson Exercise Generation

Admin chọn lesson.

Generation phải dựa trên lesson knowledge.

Admin được phép chọn generation configuration, ví dụ:

- knowledge scope;
- vocabulary;
- grammar;
- number of questions;
- exercise types;
- difficulty.

Exact parameter set sẽ được finalized khi AI generation subsystem được thiết kế.

---

# 39. AI Periodic Test Generation

Admin có thể chọn:

- vocabulary across multiple lessons;
- grammar across multiple lessons;
- number of questions;
- exercise type distribution;
- difficulty;
- related test settings.

Selected content là scope của generation.

AI không tự quyết định curriculum coverage ngoài scope admin chọn.

---

# 40. AI-generated Content Approval

Mandatory workflow:

```text
Generate
→ Draft
→ Admin Review
→ Admin Edit if needed
→ Approve
→ Publish
```

Automatic AI publication bị cấm.

---

# 41. Document Upload

Supported MVP file types:

```text
.pdf
.docx
.txt
.md
```

Image-only/scanned document OCR không thuộc requirement hiện tại.

---

# 42. Document Knowledge Workflow

Document không được tự động trở thành active RAG knowledge sau upload.

Required workflow:

```text
Upload
→ Process / Extract
→ Preview
→ Admin Review
→ Approve
→ Active Knowledge Base
```

Nếu chưa approved:

```text
not_available_to_production_RAG = true
```

Exact processing implementation thuộc Data Ingestion phase.

---

# 43. Document Usage

Approved document có hai intended use cases:

```text
AI Q&A Knowledge
AI Learning Content Generation
```

---

# 44. Admin Statistics

Admin dashboard phải cung cấp tối thiểu:

```text
Total Users
Users by Current HSK
Average Exercise Score
```

Không yêu cầu analytics warehouse hoặc dedicated BI system.

---

# 45. Content Deletion Rules

Nếu lesson/test/content đã có learner progress:

```text
HARD DELETE NOT ALLOWED
```

Admin chỉ được:

```text
Archive
or
Unpublish
```

Historical learner progress phải được preserve.

Exact implementation strategy sẽ được thiết kế trong data modeling phase.

---

# 46. Editing Completed Content

Nếu admin sửa lesson đã có learner hoàn thành:

```text
existing learner completion remains
```

Không tự reset learner progress trong MVP.

Minor/major content versioning nâng cao không nằm trong MVP requirement.

---

# 47. Security Requirements

Production MVP bắt buộc:

1. Password hashing.
2. Learner/Admin role separation.
3. Authentication for protected APIs.
4. Authorization based on role/ownership.
5. Secrets must not be hard-coded.
6. File upload validation.
7. Basic rate limiting for AI endpoints.

Exact libraries/providers chưa được chọn.

---

# 48. Performance Requirements

Normal application API target:

```text
< 1 second
```

under expected normal MVP conditions.

AI first-response target:

```text
< 5 seconds
```

when normally possible.

This is a target, not a strict SLA.

Long-running AI actions require visible loading state.

---

# 49. Expected Scale

Initial production target:

```text
10–50 concurrent users
```

System design must not prematurely optimize for massive scale.

Avoid unnecessary:

- microservices;
- distributed event infrastructure;
- Kubernetes-level complexity;

unless later requirements justify them.

---

# 50. Backup Requirement

Production persistent database must receive at least:

```text
DAILY BACKUP
```

Retention and restore strategy belong to deployment/operations phase.

---

# 51. Data Requirements Identified

Future system must persist data sufficient to represent:

## Identity

- learner/admin users;
- role.

## Curriculum

- HSK;
- lesson;
- order;
- periodic tests;
- prerequisites/unlock ordering.

## Learning Content

- vocabulary;
- grammar;
- exercises;
- tests.

## Learning State

- pronunciation completion;
- theory progress;
- lesson completion;
- HSK progress.

## Attempts

- exercise attempts;
- test attempts;
- answers;
- scores;
- grading outputs.

## AI

- conversations;
- messages;
- lesson context relationship.

## Knowledge

- uploaded documents;
- processing/review state;
- approval state;
- source metadata.

## Admin

- AI-generated drafts;
- review/publish state.

No physical schema is approved yet.

---

# 52. AI Runtime Outputs Identified

Future AI subsystem may need structured outputs for:

## Free-form grading

```text
score
is_correct
feedback
grading_status
```

## Answer generation

```text
answer
sources
```

## Content generation

```text
generated_draft
```

Exact schemas will be designed later.

---

# 53. Non-functional Requirements Summary

```text
Expected concurrency: 10–50

Normal API target:
< 1 second

AI first-response target:
< 5 seconds when practical

Database backup:
daily

Security:
authentication + authorization + password hashing
secret management
file validation
AI rate limiting
```

---

# 54. Technology Decisions

No concrete tool has been selected yet for:

- frontend;
- backend;
- database;
- ORM;
- LLM;
- embeddings;
- vector search;
- external search;
- file storage;
- document parser;
- deployment.

Do not select tools in this Step unless instructed separately.

---

# 55. Explicit Out of Scope

Do not add:

- dedicated listening module;
- dedicated speaking module;
- STT;
- TTS;
- pronunciation scoring;
- voice AI;
- flashcards;
- spaced repetition;
- gamification;
- payment/subscription;
- social features;
- full HSK mock exam;
- Google/social login;
- OCR for scanned documents;
- standalone general AI Tutor page.

---

# 56. Core Business Rules

## BR-001

Learner must complete Pronunciation Foundations before normal curriculum.

## BR-002

Pronunciation Foundations requires completion only, not a quiz.

## BR-003

HSK progression is sequential.

## BR-004

Curriculum units progress sequentially.

## BR-005

Lesson requires completed theory and >=90% exercise score.

## BR-006

Lesson exercise attempts are unlimited.

## BR-007

Periodic tests are mandatory gates.

## BR-008

Periodic test pass threshold is 90%.

## BR-009

Periodic test attempts are unlimited.

## BR-010

All attempts are retained.

## BR-011

Passing a lesson/test is not reversed by a later lower score.

## BR-012

Previous content remains accessible.

## BR-013

AI uncertain grading is excluded from score calculation.

## BR-014

AI generated content requires admin approval.

## BR-015

Documents require admin approval before entering active KB.

## BR-016

Content with learner history cannot be hard deleted.

## BR-017

Editing content does not automatically reset existing learner completion.

## BR-018

External retrieval is allowed automatically for in-domain questions when internal knowledge is insufficient.

## BR-019

External retrieval must prefer trusted sources.

## BR-020

Retrieved answers require source citation.

---

# 57. End-to-End Acceptance Flow

MVP architecture created in future phases must be capable of supporting:

```text
ADMIN
→ create/upload learning source
→ preview extracted document
→ approve knowledge
→ create HSK curriculum
→ create lesson
→ create vocabulary
→ create grammar
→ generate exercise/test with AI
→ review/edit draft
→ publish

LEARNER
→ register
→ login
→ complete pronunciation foundations
→ view HSK1
→ open Lesson1
→ consume vocabulary
→ consume grammar
→ ask lesson-aware AI
→ theory completes
→ answer exercise
→ deterministic + LLM grading
→ receive detailed feedback
→ retry if required
→ pass >=90%
→ unlock next unit
→ pass periodic test >=90%
→ continue curriculum
→ progress/history persist

ADMIN
→ view total users
→ users by HSK
→ average exercise score
```

---

# 58. Acceptance Criteria for Step 0.4

The Product Requirements Step is complete when:

- [ ] learner functional requirements are explicit;
- [ ] admin requirements are explicit;
- [ ] AI requirements are explicit;
- [ ] knowledge/document requirements are explicit;
- [ ] progression rules are explicit;
- [ ] exercise/test rules are explicit;
- [ ] LLM grading uncertainty behavior is explicit;
- [ ] progress calculation is defined;
- [ ] content deletion behavior is defined;
- [ ] security baseline is defined;
- [ ] performance target is defined;
- [ ] scale target is defined;
- [ ] backup requirement is defined;
- [ ] out-of-scope remains explicit;
- [ ] no premature technology choice is introduced.

---

# 59. Verification Checklist

Before closing Step 0.4 verify:

- [ ] Pronunciation Foundations has no quiz.
- [ ] HSK progression remains sequential.
- [ ] Lessons remain sequential.
- [ ] Tests are curriculum gates.
- [ ] Lesson pass threshold remains 90%.
- [ ] Test pass threshold remains 90%.
- [ ] Retry remains unlimited.
- [ ] Objective questions do not unnecessarily require LLM.
- [ ] Free-form questions support LLM grading.
- [ ] Uncertain AI grading is not counted as wrong.
- [ ] Lesson AI receives current lesson context.
- [ ] Internal knowledge is preferred.
- [ ] External fallback is automatic for valid in-domain questions.
- [ ] Trusted-source preference exists.
- [ ] Citation includes source and page/section where available.
- [ ] Out-of-domain questions are refused.
- [ ] Conversation retained until user deletion.
- [ ] Uploaded knowledge requires approval.
- [ ] AI-generated content requires review.
- [ ] Historical content cannot be hard deleted.
- [ ] Existing learner completion is not automatically reset after edit.
- [ ] Security baseline is preserved.
- [ ] Architecture target remains suitable for 10–50 concurrent users.
- [ ] Daily database backup is required.

---

# 60. Expected Deliverable

Recommended output:

```text
docs/product/
├── step-0.1-problem-target-user.md
├── step-0.2-product-scope-mvp.md
├── step-0.3-user-journey-use-cases.md
└── step-0.4-product-requirements.md
```

No executable application code is required for Step 0.4.

---

# 61. Project State After Step 0.4

```text
Problem & Target User            ✓
Product Scope & MVP              ✓
User Journey & Core Use Cases    ✓
Product Requirements             ✓

Product Success Criteria         NOT YET
System Design                    NOT YET
Database Design                  NOT YET
Implementation                   NOT YET
```

Next Step:

**Step 0.5 — Product Success Criteria**