# Step 0.2 — Product Scope & MVP Specification

## 1. Document Purpose

Tài liệu này là specification self-contained cho Step 0.2 của project web application học tiếng Trung dành cho người Việt.

Mục tiêu của Step là chốt:

- MVP scope;
- core product behavior;
- learning progression;
- learner capabilities;
- admin capabilities;
- AI scope;
- explicit out-of-scope features.

Đây vẫn là Product Definition phase.

Không implement application code, database schema, API hoặc AI pipeline tại Step này trừ khi repository yêu cầu lưu documentation.

---

# 2. Project Context

Product là một web application dành cho người Việt bắt đầu học tiếng Trung từ con số 0.

Current curriculum scope:

```text
HSK 1
→ HSK 2
→ HSK 3
```

Product hướng tới structured learning kết hợp AI assistance.

Product không phải chatbot-first.

Core product mental model:

```text
Structured Learning Platform
+
AI Learning Assistant
```

Existing knowledge source:

- Giáo trình HSK 1–3.

Curriculum sẽ dựa trên giáo trình này nhưng product owner có thể tự thiết kế hoặc điều chỉnh một số phần.

---

# 3. Primary User

Primary user:

> Người Việt bắt đầu học tiếng Trung từ zero và học theo chương trình HSK 1–3.

User phải có authenticated account.

Current authentication scope:

- email/password;
- basic profile.

Google authentication không thuộc MVP.

---

# 4. Secondary User

Secondary user:

> Admin / Content Creator.

Admin chịu trách nhiệm quản lý learning content và sử dụng AI như một authoring assistant.

---

# 5. MVP Core Learning Model

MVP phải tập trung vào flow:

```text
Curriculum
→ Lesson
→ Theory
→ Exercise
→ Evaluation
→ Progression
```

Trong đó lesson theory hiện tập trung vào:

```text
Vocabulary
+
Grammar
```

AI hỗ trợ xuyên suốt nhưng không thay thế curriculum.

---

# 6. Curriculum Structure

Logical structure:

```text
HSK 1
 ├── Lesson 1
 ├── Lesson 2
 ├── ...
 └── Lesson N

HSK 2
 ├── Lesson 1
 └── ...

HSK 3
 └── ...
```

Curriculum:

- dựa trên giáo trình HSK 1–3 hiện có;
- có thể điều chỉnh hoặc bổ sung một số phần;
- không buộc phải phản ánh 1:1 cấu trúc textbook.

Exact lesson list chưa được thiết kế ở Step này.

---

# 7. Sequential Progression

User mới phải bắt đầu tại:

```text
HSK 1
→ Lesson 1
```

Default state:

```text
HSK 1          UNLOCKED
HSK 2          LOCKED
HSK 3          LOCKED

HSK 1 Lesson 1 UNLOCKED
Other Lessons  LOCKED
```

Không cho phép learner tự skip progression trong MVP.

---

# 8. Lesson Completion Rule

Một lesson chỉ được coi là complete khi thỏa mãn đồng thời:

```text
theory_completed = true

AND

exercise_score >= 90%
```

Canonical rule:

```text
PASS_THRESHOLD = 90%
```

Không được tự thay đổi threshold.

---

# 9. Exercise Retry Behavior

Learner có thể làm exercise nhiều lần.

Rules:

1. Không giới hạn số lần retry trong MVP.
2. Chỉ cần một attempt đạt `>=90%` để lesson được pass.
3. Sau khi pass, learner vẫn có thể làm exercise lại.
4. Việc làm lại không được biến lesson thành incomplete.
5. Best score phải có khả năng được lưu.
6. Latest score phải có khả năng được lưu.
7. Mỗi attempt cần có khả năng được lưu để phục vụ history.

Exact database representation chưa được quyết định.

---

# 10. Lesson Unlock Behavior

Khi learner complete lesson hiện tại:

```text
current lesson → COMPLETE
next lesson    → UNLOCKED
```

Nếu learner complete lesson cuối cùng của HSK level:

```text
current HSK level → COMPLETE
next HSK level    → UNLOCKED
```

Ví dụ:

```text
HSK1 Lesson N completed
        ↓
HSK1 completed
        ↓
HSK2 Lesson 1 unlocked
```

HSK 3 là curriculum boundary hiện tại.

---

# 11. Previous Content Access

Learner luôn được phép quay lại:

- lesson đã hoàn thành;
- vocabulary đã học;
- grammar đã học;
- exercise đã pass.

Không lock lại previous content.

---

# 12. Vocabulary Requirements

Mỗi vocabulary item về mặt domain cần support:

- Chinese characters / Hán tự;
- Pinyin / phiên âm;
- Vietnamese meaning;
- Part of speech / loại từ;
- Example(s).

Exact schema chưa được thiết kế.

---

# 13. Grammar Requirements

Mỗi grammar point về mặt domain cần support:

- grammar structure;
- Vietnamese explanation;
- usage cases;
- examples;
- optional notes.

Exact schema chưa được thiết kế.

---

# 14. Exercise Types

MVP phải được thiết kế để sau này có thể support các exercise type sau:

1. Multiple choice.
2. Fill in the blank.
3. Matching.
4. Reorder sentence.
5. Vietnamese → Chinese translation.
6. Chinese → Vietnamese translation.
7. Sentence writing.

Không yêu cầu mọi lesson chứa tất cả exercise type.

Exact answer representation và grading mechanism chưa được quyết định.

---

# 15. Tests

MVP có hai dạng assessment:

## Lesson Exercise

Gắn với từng lesson và tham gia trực tiếp vào progression rule.

## Admin-created Test

Admin có thể tạo các bài kiểm tra riêng.

MVP không bao gồm full HSK mock exam system.

---

# 16. Four Skills

Long-term product objective vẫn gồm:

- Listening.
- Speaking.
- Reading.
- Writing.

Tuy nhiên dedicated skill learning modules không thuộc MVP.

Current MVP không yêu cầu:

- listening path;
- speaking path;
- independent reading progression;
- independent writing progression.

Một số text exercise có thể gián tiếp luyện reading/writing.

Không xây skill mastery system tại Step này.

---

# 17. Audio and Speech

Explicitly out of MVP:

- Speech-to-Text.
- Text-to-Speech.
- Pronunciation scoring.
- Voice recording workflow.
- Voice AI conversation.
- Dedicated pronunciation assessment.
- Listening audio pipeline.

Không lựa chọn speech provider hoặc model tại Step này.

---

# 18. Learner AI Capabilities

Learner-facing AI MVP cần được thiết kế để support:

## Vocabulary Explanation

Giải thích vocabulary.

## Grammar Explanation

Giải thích grammar.

## Lesson Q&A

Trả lời câu hỏi liên quan lesson hiện tại.

## Example Generation

Sinh thêm examples cho vocabulary hoặc grammar.

## General Chinese Q&A

Có thể trả lời câu hỏi về tiếng Trung ngoài nội dung internal knowledge base.

---

# 19. AI Entry Points

## Lesson Context — MVP

MVP chỉ expose learner AI chat trong Lesson.

Learner có thể hỏi AI ngay trong lesson và AI phải biết learner đang ở lesson nào.

Conceptual input:

```text
user
+
current lesson
+
question
```

`General Chat` / standalone global chat **không thuộc MVP**. Không tạo route/UI/API riêng cho global chat trong V0. Nếu sau này product cần capability này, nó sẽ được thêm bằng một product/architecture decision mới và migration/interface riêng.

`General Chinese Q&A` vẫn có thể xảy ra từ Lesson Chat: nếu câu hỏi còn thuộc Chinese-learning domain nhưng internal knowledge không đủ, RAG có thể đi theo trusted external fallback policy. Điều này không tạo một standalone General Chat surface.

---

# 20. AI Knowledge Routing

AI queries được chia thành ba categories.

## Category A — Answerable using Internal Knowledge Base

Conceptual flow:

```text
Question
→ Internal Retrieval
→ Knowledge Base
→ LLM
→ Answer
→ Citation
```

Knowledge base chủ yếu xuất phát từ HSK learning materials.

---

## Category B — Chinese-related but Internal Knowledge Insufficient

Nếu question vẫn liên quan tiếng Trung nhưng knowledge base không đủ:

```text
Question
→ Detect insufficient internal knowledge
→ External Knowledge Retrieval
→ LLM
→ Answer
→ External Sources
```

Requirements:

- answer phải có reliable source attribution;
- external source phải được phân biệt với internal knowledge;
- system không được fabricate citation.

Exact search/retrieval provider chưa được chọn.

---

## Category C — Outside Chinese Domain

Nếu câu hỏi không liên quan đến:

- Chinese language;
- Chinese vocabulary;
- Chinese grammar;
- Chinese learning;
- relevant Chinese linguistic/cultural knowledge cần thiết để giải thích ngôn ngữ;

AI phải từ chối.

Exact classifier/guardrail strategy chưa được chọn.

---

# 21. Source Citation Requirement

AI response sử dụng retrieved knowledge phải có khả năng cung cấp nguồn.

Không được:

- tạo source giả;
- dẫn nguồn không được retrieval;
- tuyên bố internal KB chứa thông tin nếu câu trả lời thực tế lấy từ external source.

Citation format chưa được thiết kế.

---

# 22. Admin Capabilities

Admin MVP cần support về mặt product:

## Course Management

- create;
- update;
- delete/manage.

Exact delete behavior chưa chốt.

## Lesson Management

- create;
- edit/manage;
- organize within HSK/course.

## Vocabulary Management

- add;
- edit;
- remove/manage vocabulary content.

## Grammar Management

- add;
- edit;
- remove/manage grammar content.

## Document Upload

Admin có thể upload learning/reference documents.

Exact ingestion behavior chưa được thiết kế.

## Exercise/Test Creation

Admin có thể:

- tạo exercise thủ công;
- tạo test;
- yêu cầu AI generate exercise;
- yêu cầu AI generate test.

---

# 23. AI-generated Content Workflow

AI-generated learning content không được publish tự động.

Required workflow:

```text
Admin provides generation request
        ↓
AI generates content
        ↓
Content saved/displayed as DRAFT
        ↓
Admin reviews
        ↓
Admin may edit
        ↓
Admin approves
        ↓
Content may be published
```

Human review là mandatory.

Không được implement autonomous publish behavior.

---

# 24. Authentication Scope

MVP account capabilities:

- register using email/password;
- login;
- basic profile;
- persistent learner identity.

Exact authentication technology chưa được chọn.

---

# 25. Learner Data to Support

Future system design phải support:

- learner profile;
- theory completion;
- exercise attempts;
- latest score;
- best score;
- lesson completion;
- lesson unlock state;
- HSK completion;
- HSK unlock state;
- exercise history;
- AI conversation history.

Database model chưa được chốt.

---

# 26. Admin Analytics

Admin MVP cần xem ít nhất:

## Total Users

```text
total registered users
```

## Users by HSK Level

Ví dụ conceptual:

```text
HSK1: X learners
HSK2: Y learners
HSK3: Z learners
```

Exact definition của "đang học HSK" sẽ được chốt khi data model được thiết kế.

## Average Exercise Score

Admin có thể xem average exercise score.

Aggregation dimensions chưa được chốt.

Không xây analytics warehouse hoặc BI infrastructure tại Step này.

---

# 27. Canonical Learner Flow

Required MVP flow:

```text
Register
   ↓
Login
   ↓
HSK1 available
   ↓
Open Lesson 1
   ↓
Study Vocabulary
   ↓
Study Grammar
   ↓
Ask AI when necessary
   ↓
Mark / satisfy Theory Completion
   ↓
Start Lesson Exercise
   ↓
Submit answers
   ↓
Calculate Score
   ↓
Score < 90%
   ├── Save Attempt
   └── Allow Retry

Score >= 90%
   ↓
Save Attempt
   ↓
Mark Lesson Complete
   ↓
Unlock Next Lesson
   ↓
Continue Curriculum
```

At the end of HSK level:

```text
All lessons completed
        ↓
HSK completed
        ↓
Next HSK unlocked
```

---

# 28. Progress State Requirements

Future system must distinguish at least:

```text
LOCKED
UNLOCKED
COMPLETED
```

Lesson completion and HSK completion must be deterministic from product rules.

Avoid relying only on frontend state.

Business rules must eventually be enforced by backend/domain logic.

No implementation required in Step 0.2.

---

# 29. Must-have MVP Features

The official MVP scope is:

- Email/password authentication.
- HSK 1–3 curriculum.
- Sequential HSK progression.
- Sequential lesson progression.
- Vocabulary content.
- Grammar content.
- Lesson exercises.
- 90% lesson pass rule.
- Exercise retries.
- Exercise history.
- Learning progress.
- AI lesson assistance.
- General Chinese AI Q&A.
- RAG over internal knowledge.
- External knowledge fallback for Chinese-related questions.
- AI answer source attribution.
- Domain restriction for non-Chinese questions.
- AI conversation history.
- Admin course management.
- Admin lesson management.
- Admin vocabulary management.
- Admin grammar management.
- Admin document upload.
- Manual exercise/test creation.
- AI exercise/test generation.
- Mandatory admin review before publishing AI content.
- Basic admin statistics.

---

# 30. Explicitly Out of MVP

Do not add the following unless product owner later changes the scope.

## Skills / Multimedia

- dedicated Listening module;
- dedicated Speaking module;
- dedicated four-skill progression;
- STT;
- TTS;
- pronunciation scoring;
- voice chat;
- audio pipeline.

## Learning Features

- flashcards;
- spaced repetition;
- vocabulary mastery tracking;
- grammar mastery tracking;
- placement tests;
- full HSK mock exam.

## Gamification

- XP;
- streak;
- badge;
- leaderboard.

## Authentication

- Google login;
- other social login.

## Commercial

- payment;
- subscriptions.

## Social

- social feed;
- learner-to-learner messaging;
- community system.

Do not implement these as "helpful additions".

---

# 31. Current Architecture State

Current architecture remains conceptual.

```text
Learner
   ↓
Frontend
   ↓
Backend
   ├── Authentication
   ├── Curriculum
   ├── Lesson
   ├── Exercise
   ├── Progress
   └── AI Orchestration
          ├── Internal RAG
          ├── External Knowledge Fallback
          └── Domain Guardrail

Backend
   ↓
Persistent Data Layer
```

Admin path:

```text
Admin
 ↓
Content Management
 ↓
AI Generation
 ↓
Draft
 ↓
Review
 ↓
Publish
```

No technology implementation has been selected.

---

# 32. Data Model

No physical database schema is defined in this Step.

Future data model will likely need to represent concepts such as:

- User.
- HSK Level.
- Course.
- Lesson.
- Vocabulary.
- Grammar.
- Exercise.
- Test.
- Exercise Attempt.
- Progress.
- Conversation.
- Message.
- Document.
- Generated Content Draft.

These are conceptual candidates only.

Do not generate final schema yet.

---

# 33. API Contract

No API contract has been approved.

Do not create endpoint specifications as official architecture in this Step.

API design belongs to later phases after use cases and requirements are complete.

---

# 34. Technology Decisions

No concrete technology has been selected for:

- frontend framework;
- backend framework;
- database;
- ORM;
- authentication library;
- LLM;
- embedding model;
- vector store;
- RAG framework;
- external search provider;
- cloud provider;
- file storage;
- Docker stack.

Do not select tools solely based on this specification.

---

# 35. Business Rules

## BR-001

All new learners start from HSK 1.

## BR-002

HSK levels progress sequentially:

```text
HSK1 → HSK2 → HSK3
```

## BR-003

Lessons progress sequentially.

## BR-004

A lesson is completed only when:

```text
theory complete
AND
score >= 90%
```

## BR-005

Exercise attempts may be repeated without an MVP limit.

## BR-006

One attempt >=90% permanently satisfies the lesson score requirement.

## BR-007

Previously completed lessons remain accessible.

## BR-008

AI-generated learning content requires admin review.

## BR-009

AI must refuse non-Chinese-domain requests.

## BR-010

Chinese questions outside internal knowledge may use external knowledge retrieval.

## BR-011

Retrieved external information must provide source attribution.

## BR-012

MVP scope ends at HSK 3.

---

# 36. Constraints

The implementation in future Steps must prioritize:

- simplicity suitable for an MVP;
- deterministic progression rules;
- clear separation between curriculum logic and AI assistance;
- persistent learner progress;
- traceable AI knowledge sources;
- human approval for generated learning content.

Do not introduce microservices, event streaming, complex distributed infrastructure or other architectural complexity without a later requirement.

---

# 37. Edge Cases Identified

These must be handled or specified in later Steps.

## Exercise

- learner receives exactly 90%;
- learner receives a lower score after previously passing;
- learner retries a completed lesson;
- exercise content changes after learner passed;
- lesson is edited after learner completed it.

## Curriculum

- admin deletes a lesson with learner progress;
- admin reorders lessons;
- admin adds a new lesson between completed lessons;
- HSK level structure changes.

## AI

- internal retrieval returns no relevant document;
- external retrieval fails;
- retrieved sources conflict;
- AI cannot confidently answer;
- user asks mixed Chinese and unrelated question;
- source is unavailable;
- AI-generated exercise is invalid.

## Admin

- generated content rejected;
- generated content edited before publish;
- published content later edited.

Do not invent final behavior for unresolved cases at this Step.

---

# 38. Acceptance Criteria

Step 0.2 is complete when documentation clearly establishes:

- [ ] MVP core learning loop.
- [ ] HSK 1–3 curriculum boundary.
- [ ] Sequential HSK progression.
- [ ] Sequential lesson progression.
- [ ] Vocabulary scope.
- [ ] Grammar scope.
- [ ] Exercise types.
- [ ] 90% pass requirement.
- [ ] Unlimited retries.
- [ ] Previous lesson revisiting.
- [ ] Learner AI capabilities.
- [ ] Internal RAG behavior.
- [ ] External Chinese knowledge fallback.
- [ ] Citation requirement.
- [ ] Non-Chinese domain refusal.
- [ ] Admin capabilities.
- [ ] Human review for AI-generated content.
- [ ] Authentication MVP scope.
- [ ] Progress tracking scope.
- [ ] Admin analytics scope.
- [ ] Explicit Later feature list.
- [ ] No premature technology decisions.

---

# 39. Verification Checklist

Before closing Step 0.2:

- [ ] Do not implement application features.
- [ ] Do not create final database schema.
- [ ] Do not define final REST API.
- [ ] Do not select LLM.
- [ ] Do not select vector database.
- [ ] Do not select external search provider.
- [ ] Do not add voice functionality.
- [ ] Do not add spaced repetition.
- [ ] Do not add gamification.
- [ ] Do not add payment.
- [ ] Do not add mock HSK exams.
- [ ] Verify pass threshold remains exactly 90%.
- [ ] Verify AI content cannot bypass admin review.
- [ ] Verify out-of-domain AI questions are rejected.
- [ ] Verify MVP still centers on structured learning rather than chat.

---

# 40. Expected Deliverables

Recommended documentation output:

```text
docs/product/
├── step-0.1-problem-target-user.md
└── step-0.2-product-scope-mvp.md
```

The Step 0.2 document must contain the product decisions in this specification.

No executable implementation is required.

---

# 41. Project State After Step 0.2

```text
Product Idea                  ✓
Problem & Target User         ✓
Product Scope & MVP           ✓

User Journey & Core Use Cases NOT YET
Detailed Requirements         NOT YET
Success Criteria              NOT YET
System Design                 NOT YET
Database Design               NOT YET
Implementation                NOT YET
```

Next dependency:

**Step 0.3 — User Journey & Core Use Cases**