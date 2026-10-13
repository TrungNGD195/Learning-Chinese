# Step 0.3 — User Journey & Core Use Cases

## 1. Document Purpose

Tài liệu này mô tả user journeys và core use cases chính thức của MVP web application học tiếng Trung cho người Việt.

Đây là Product Definition specification.

Không implement:

- frontend;
- backend;
- database;
- API;
- authentication;
- RAG;
- LLM integration;
- document ingestion;

trong Step này.

Nếu repository đã tồn tại, chỉ cần lưu specification dưới dạng documentation.

---

# 2. Product Context

Product là web application dành cho người Việt bắt đầu học tiếng Trung từ con số 0.

Current curriculum scope:

```text
HSK 1
→ HSK 2
→ HSK 3
```

Core product direction:

```text
Structured Learning
+
Exercise
+
AI Assistance
```

Product không phải chatbot-first.

---

# 3. User Roles

Có hai role chính trong MVP:

```text
Learner
Admin
```

## Learner

Người Việt học tiếng Trung từ beginner đến HSK 3.

## Admin

Người xây dựng, quản lý và publish learning content.

---

# 4. Learner Entry Flow

Sau authentication:

```text
Login
  ↓
Home / Dashboard
```

Dashboard phải có khả năng hiển thị:

- current HSK;
- current lesson;
- learning progress percentage;
- Continue Learning action.

Dashboard cũng cho phép learner xem các HSK level.

---

# 5. HSK Navigation Flow

Conceptual navigation:

```text
Home
 ↓
HSK Levels
 ↓
Select HSK
 ↓
Lessons
```

Learner có thể nhìn thấy HSK level và lesson nhưng chỉ nội dung đã unlocked mới được truy cập theo progression rules.

Current progression:

```text
HSK1
→ HSK2
→ HSK3
```

Lessons cũng sequential.

---

# 6. Pronunciation Foundations

Trước curriculum lesson chính, product có một learning module riêng:

```text
Pronunciation Foundations
```

Nội dung gồm:

```text
Tones / Thanh điệu
Initials / Thanh mẫu
Finals / Vận mẫu
```

Đây không phải phần của từng HSK lesson.

Learner phải học foundation này trước khi bắt đầu normal lesson curriculum.

Exact completion rule chưa được quyết định tại Step 0.3.

Không tự quyết định:

- quiz requirement;
- score threshold;
- audio implementation;
- pronunciation scoring.

Các requirement này phải được chốt ở Step sau.

---

# 7. Canonical Lesson Structure

Lesson flow:

```text
Open Lesson
    ↓
Vocabulary
    ↓
Grammar
    ↓
Exercise
```

Vocabulary xuất hiện trước Grammar.

Grammar xuất hiện trước Exercise.

---

# 8. Theory Completion

Theory bao gồm:

```text
Vocabulary
+
Grammar
```

Learner không tự bấm một nút đơn giản để tuyên bố đã hoàn thành.

System về sau phải có khả năng xác định learner đã đi qua toàn bộ required vocabulary và grammar content.

Conceptual rule:

```text
Vocabulary content completed
AND
Grammar content completed
→ Theory Complete
```

Exact tracking mechanism chưa được xác định.

---

# 9. Vocabulary Content

Vocabulary item phải có khả năng support:

- Chinese characters;
- pinyin;
- Vietnamese meaning;
- part of speech;
- examples.

---

# 10. Grammar Content

Grammar item phải có khả năng support:

- structure;
- explanation;
- usage cases;
- examples;
- optional notes.

---

# 11. AI in Lesson

MVP không yêu cầu một general AI Tutor page riêng.

AI chỉ cần có entry point bên trong lesson.

Conceptual interaction:

```text
Learner
  ↓
Current Lesson
  ↓
Open AI Chat Window
  ↓
Enter free-form text
  ↓
AI receives:
- learner question
- current lesson context
  ↓
AI response
```

Learner không cần tự cung cấp lesson identifier bằng text.

System phải biết lesson context.

---

# 12. AI Conversation Behavior

AI interaction sử dụng free-text chat.

A conversation có thể gồm nhiều messages:

```text
Conversation
 ├── User Message
 ├── AI Message
 ├── User Message
 └── AI Message
```

Conversation phải có khả năng liên kết với lesson tương ứng.

Learner có thể xem lại conversation history theo từng session.

Exact persistence schema chưa được thiết kế.

---

# 13. Lesson Exercise Flow

Sau khi theory được complete:

```text
Start Exercise
    ↓
Answer Questions
    ↓
Submit
    ↓
Grade
    ↓
Result
```

---

# 14. Exercise Types

MVP exercise types đã chốt:

- multiple choice;
- fill in the blank;
- matching;
- reorder sentence;
- Vietnamese to Chinese translation;
- Chinese to Vietnamese translation;
- sentence writing.

Không yêu cầu mọi exercise chứa tất cả type.

---

# 15. Exercise Feedback

Result phải có khả năng hiển thị:

```text
Overall Score
+
Correct / Incorrect for each question
+
Correct Answer
+
Explanation
```

Learner phải có thể hiểu tại sao đáp án của mình sai.

AI có thể được dùng trong lesson để hỏi thêm về incorrect answer.

---

# 16. Free-form Answer Grading

Các dạng:

- Vietnamese → Chinese translation;
- Chinese → Vietnamese translation;
- sentence writing;

sẽ sử dụng LLM để grading trong MVP.

Không tự implement grading strategy tại Step 0.3.

Future requirements phải xác định:

- grader input;
- expected grader output;
- correctness criteria;
- equivalent valid answers;
- confidence handling;
- failure behavior.

---

# 17. Exercise Pass Rule

Existing product rule:

```text
PASS_THRESHOLD = 90%
```

Lesson completion cần:

```text
Theory Complete
AND
Exercise Score >= 90%
```

---

# 18. Failed Exercise Journey

Nếu:

```text
score < 90%
```

required journey:

```text
Result
  ↓
Review Incorrect Answers
  ↓
View Correct Answers
  ↓
View Explanations
  ↓
Optional AI Questions
  ↓
Retry Exercise
```

Learner không bắt buộc quay lại theory trước khi retry.

Learner có thể tự quay lại theory.

Exercise attempts không bị giới hạn.

---

# 19. Passed Exercise Journey

Nếu learner đạt:

```text
score >= 90%
```

và theory đã complete:

```text
Lesson Complete
      ↓
Next Lesson Unlocked
```

Result page phải có:

```text
Next Lesson
```

action.

Hoặc

```text
Back Home
```

Không auto-redirect learner sang lesson tiếp theo.

---

# 20. Revisiting Content

Sau khi pass:

- learner vẫn được mở lesson cũ;
- learner vẫn được học lại vocabulary;
- learner vẫn được học lại grammar;
- learner vẫn được làm lại exercise.

Một attempt thấp hơn sau khi pass không được làm mất trạng thái completed.

---

# 21. Periodic Tests

Ngoài lesson exercise, product có periodic tests.

Conceptual curriculum:

```text
Lesson 1
Lesson 2
Lesson 3
    ↓
Test
    ↓
Lesson 4
...
```

Số lesson giữa hai test chưa được chốt.

---

# 22. Test Knowledge Scope

Khác với lesson exercise:

```text
Lesson Exercise
→ knowledge của một lesson
```

Test:

```text
Test
→ knowledge được chọn từ nhiều lesson đã học
```

Admin có thể chọn:

- vocabulary từ nhiều lesson;
- grammar từ nhiều lesson;

để tạo test scope.

---

# 23. Test Attempts

Learner được phép làm periodic test nhiều lần.

System tương lai phải lưu tất cả test attempts.

Không chỉ lưu latest result.

Test attempt history phải có khả năng giữ:

- score;
- attempt timestamp;
- answers/results.

Exact schema chưa được quyết định.

---

# 24. Test Progression Rule

Step 0.3 chưa quyết định periodic test có phải prerequisite để unlock subsequent lessons hay không.

Không tự quyết định behavior này.

Phải chờ Product Requirements Step.

---

# 25. Exercise History

Learner cần có UI/use case xem exercise/test history.

History phải có khả năng hiển thị:

- attempt time;
- score;
- attempts;
- submitted answers;
- correct/incorrect results;
- best score.

Exact UI chưa được thiết kế.

---

# 26. Learning Progress

Learner có thể xem progress.

Dashboard tối thiểu:

```text
Current HSK
Current Lesson
Progress %
Continue Learning
```

Exact progress calculation formula chưa được quyết định.

---

# 27. Learner Profile

MVP profile gồm:

- name;
- email;
- current HSK;
- learning progress;
- change password capability.

Không thêm:

- social profile;
- avatar ecosystem;
- friend system;
- public profile.

---

# 28. Admin Content Journey

Canonical flow:

```text
Admin Login
    ↓
Admin Dashboard
    ↓
Select HSK
    ↓
Select/Create Lesson
    ↓
Manage Vocabulary
    ↓
Manage Grammar
    ↓
Create Exercise
    ↓
Preview
    ↓
Publish
```

---

# 29. AI Lesson Exercise Generation

AI lesson exercise generation phải sử dụng knowledge của lesson được chọn.

Conceptual flow:

```text
Admin selects Lesson
       ↓
Lesson Vocabulary + Grammar
       ↓
AI Generation
       ↓
Exercise Draft
       ↓
Admin Review
       ↓
Admin Edit if needed
       ↓
Approve
       ↓
Publish
```

AI không được tự publish.

---

# 30. AI Test Generation

Test generation hỗ trợ multi-lesson knowledge selection.

Conceptual flow:

```text
Admin selects:
- vocabulary from selected lessons
- grammar from selected lessons

        ↓

AI generates Test Draft

        ↓

Admin Review/Edit

        ↓

Publish
```

Admin phải kiểm soát knowledge scope trước khi generation.

---

# 31. AI-generated Content Review

All AI-generated exercise/test content:

```text
GENERATED
→ DRAFT
→ REVIEWED
→ APPROVED
→ PUBLISHED
```

Admin phải được phép sửa generated draft.

Không cho phép:

```text
AI Generate
→ Automatic Publish
```

---

# 32. Document Upload

Admin có use case upload documents.

Uploaded documents có hai intended purposes:

## Purpose A

Cung cấp knowledge cho AI Q&A.

## Purpose B

Làm nguồn knowledge/reference cho content generation.

Conceptual flow:

```text
Document
   ├──→ AI Knowledge
   │
   └──→ Content Generation Knowledge
```

Không implement ingestion pipeline trong Step này.

---

# 33. Admin Analytics

Admin dashboard cần use cases:

```text
View total users
View users grouped by current HSK
View average exercise score
```

Không thiết kế analytics implementation ở Step này.

---

# 34. Core Learner Use Cases

Official learner use cases:

```text
UC-L01 Register
UC-L02 Login
UC-L03 View Home/Dashboard
UC-L04 View HSK levels
UC-L05 View lessons in HSK level

UC-L06 Learn Pronunciation Foundations

UC-L07 Open unlocked lesson
UC-L08 Learn vocabulary
UC-L09 Learn grammar
UC-L10 Ask AI within lesson
UC-L11 Complete lesson theory

UC-L12 Do lesson exercise
UC-L13 Submit exercise
UC-L14 View exercise result
UC-L15 View correct answers/explanations
UC-L16 Ask AI about exercise errors
UC-L17 Retry exercise

UC-L18 Complete lesson
UC-L19 Unlock next lesson
UC-L20 Unlock next HSK
UC-L21 Review previous lessons

UC-L22 Take periodic test
UC-L23 Retry periodic test

UC-L24 View learning progress
UC-L25 View exercise/test history
UC-L26 View AI conversation history
UC-L27 Manage basic profile
```

---

# 35. Core Admin Use Cases

Official admin use cases:

```text
UC-A01 Login as admin
UC-A02 View admin dashboard

UC-A03 Manage HSK/course
UC-A04 Manage lesson
UC-A05 Manage vocabulary
UC-A06 Manage grammar

UC-A07 Create lesson exercise
UC-A08 Generate lesson exercise with AI

UC-A09 Create periodic test
UC-A10 Select vocab/grammar across lessons
UC-A11 Generate test with AI

UC-A12 Review AI-generated draft
UC-A13 Edit AI-generated draft
UC-A14 Approve/publish content

UC-A15 Upload documents

UC-A16 View total users
UC-A17 View users by current HSK
UC-A18 View average exercise score
```

---

# 36. Canonical Learner Journey

```text
Register
    ↓
Login
    ↓
Home / Dashboard
    ↓
Pronunciation Foundations
    ↓
HSK 1
    ↓
Lesson 1
    ↓
Vocabulary
    ↓
Grammar
    ↓
AI assistance when necessary
    ↓
Theory Complete
    ↓
Lesson Exercise
    ↓
Submit
    ↓
Result

score < 90%
    ↓
Review errors
    ↓
View explanation
    ↓
Optional AI assistance
    ↓
Retry

score >= 90%
    ↓
Lesson Complete
    ↓
Next Lesson Unlocked
    ↓
Next Lesson

After selected group of lessons:
    ↓
Periodic Test

Eventually:
    ↓
Complete HSK 1
    ↓
Unlock HSK 2
    ↓
...
    ↓
HSK 3
```

---

# 37. Current Architecture State

Architecture remains conceptual:

```text
Learner
  ↓
Web Application
  ├── Dashboard
  ├── Pronunciation Foundations
  ├── Curriculum
  ├── Lesson
  │    ├── Vocabulary
  │    ├── Grammar
  │    ├── Exercise
  │    └── AI Chat
  ├── Tests
  ├── Progress
  └── History
```

Admin:

```text
Admin
  ↓
Admin Application
  ├── Curriculum Management
  ├── Lesson Management
  ├── Exercise/Test Management
  ├── AI Generation
  ├── Document Upload
  └── Statistics
```

No implementation architecture is approved yet.

---

# 38. Database / Schema

No database schema is approved in this Step.

Do not generate final tables.

The journeys imply future data requirements but these will be modeled later.

---

# 39. API Contract

No API contract is approved.

Do not define final routes/endpoints at Step 0.3.

---

# 40. Technology Decisions

No new technology decisions are made in Step 0.3.

Do not choose:

- frontend framework;
- backend framework;
- database;
- ORM;
- LLM;
- vector database;
- RAG framework;
- cloud service.

---

# 41. Business Rules Carried Forward

The following existing rules remain fixed:

1. Learners start from HSK 1.
2. HSK progression is sequential.
3. Lesson progression is sequential.
4. Lesson requires completed theory + >=90% exercise score.
5. Exercise retries are unlimited.
6. Passing once permanently satisfies the exercise requirement.
7. Previous lessons remain accessible.
8. AI-generated content requires admin review.
9. AI is a supporting component, not the main curriculum.
10. Curriculum currently ends at HSK 3.

---

# 42. New Product Decisions from Step 0.3

## PD-031

A dedicated Pronunciation Foundations module exists before standard lessons.

## PD-032

Pronunciation Foundations covers:

- tones;
- initials;
- finals.

## PD-033

Normal lesson order is:

```text
Vocabulary
→ Grammar
→ Exercise
```

## PD-034

Theory completion must represent consumption of required vocabulary and grammar content.

## PD-035

AI chat is embedded inside lesson in MVP.

## PD-036

AI automatically receives current lesson context.

## PD-037

Exercise results show:

- correctness;
- correct answer;
- explanation.

## PD-038

Free-form translation/writing answers are graded using an LLM.

## PD-039

Failed exercises allow immediate retry after reviewing feedback.

## PD-040

Successful result pages expose an explicit Next Lesson action.

## PD-041

Periodic tests cover selected knowledge from multiple previous lessons.

## PD-042

Periodic tests support unlimited retries.

## PD-043

All periodic test attempts must be retained.

## PD-044

AI conversations are stored/viewed by conversation session.

## PD-045

Admin may edit AI-generated content before approval.

## PD-046

Uploaded documents serve both AI Q&A and content-generation use cases.

---

# 43. Open Requirements

Do not invent answers for the following:

1. Exact Pronunciation Foundations completion condition.
2. Whether periodic tests gate curriculum progression.
3. Number of lessons between periodic tests.
4. Exact logic for detecting theory consumption/completion.
5. Exact LLM grading rubric.
6. LLM grading uncertainty behavior.
7. Exact progress percentage calculation.
8. Exact exercise/test history presentation.

These belong to subsequent requirement/design Steps.

---

# 44. Out of Scope

Do not implement:

- general AI Tutor page;
- voice conversation;
- STT;
- TTS;
- pronunciation scoring;
- full four-skill progression;
- flashcards;
- spaced repetition;
- gamification;
- payment;
- subscriptions;
- full HSK mock exam.

The Pronunciation Foundations module does not imply pronunciation scoring or speech recognition.

---

# 45. Acceptance Criteria

Step 0.3 is complete when documentation establishes:

- [ ] Learner entry journey.
- [ ] Dashboard journey.
- [ ] HSK navigation.
- [ ] Pronunciation Foundations position.
- [ ] Lesson content sequence.
- [ ] Theory completion concept.
- [ ] Lesson AI interaction.
- [ ] Exercise submission flow.
- [ ] Exercise feedback behavior.
- [ ] Retry behavior.
- [ ] Pass behavior.
- [ ] Periodic test journey.
- [ ] Exercise/test history.
- [ ] AI conversation history.
- [ ] Admin content journey.
- [ ] AI exercise generation journey.
- [ ] AI test generation journey.
- [ ] Document upload use cases.
- [ ] Learner use case list.
- [ ] Admin use case list.
- [ ] Unresolved requirements remain explicitly unresolved.

---

# 46. Verification Checklist

Before closing Step:

- [ ] No application code added.
- [ ] No final database schema created.
- [ ] No final API created.
- [ ] No AI architecture prematurely selected.
- [ ] No pronunciation scoring added.
- [ ] No General AI Tutor page added.
- [ ] AI remains lesson-aware.
- [ ] Lesson order remains Vocabulary → Grammar → Exercise.
- [ ] Pass threshold remains 90%.
- [ ] Test can cover multiple lessons.
- [ ] Test retries are allowed.
- [ ] All test attempts can be retained.
- [ ] AI-generated content still requires admin approval.
- [ ] Open questions are not silently resolved.

---

# 47. Expected Deliverables

Recommended documentation:

```text
docs/product/
├── step-0.1-problem-target-user.md
├── step-0.2-product-scope-mvp.md
└── step-0.3-user-journey-use-cases.md
```

No executable implementation required.

---

# 48. Project State After Step 0.3

```text
Problem & Target User          ✓
Product Scope & MVP            ✓
User Journey & Core Use Cases  ✓

Detailed Product Requirements  NOT YET
Success Criteria               NOT YET
System Design                  NOT YET
Database Design                NOT YET
Implementation                 NOT YET
```

Next Step:

**Step 0.4 — Product Requirements**