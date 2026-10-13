# Step 0.1 — Problem & Target User

## 1. Document Purpose

Tài liệu này mô tả product context đã được chốt tại Step 0.1 của project xây dựng web application học tiếng Trung cho người Việt.

Đây là specification về **problem domain và target user**, không phải yêu cầu implement feature.

Coding agent không được bắt đầu xây database, API, frontend, RAG hoặc lựa chọn technology stack trong Step này.

Mục tiêu của Step là tạo nền product context chính xác để các Step sau sử dụng.

---

# 2. Project Context

Project là một web application học tiếng Trung dành cho người Việt.

Product hướng tới người bắt đầu từ con số 0 và cung cấp lộ trình học trong phạm vi:

- HSK 1
- HSK 2
- HSK 3

Product phải hỗ trợ quá trình học toàn diện gồm:

- Listening
- Speaking
- Reading
- Writing
- Vocabulary
- Grammar
- Pronunciation
- Practice

Product không được thiết kế như một chatbot AI thuần túy.

Core product direction là:

```text
Structured Learning Platform
+
AI Learning Assistant
```

Learning structure là trung tâm.

AI đóng vai trò hỗ trợ learning experience.

---

# 3. Primary Target User

Primary user là:

> Người Việt bắt đầu học tiếng Trung từ con số 0 và muốn học có hệ thống tới trình độ tương ứng HSK 3.

Primary user không được giả định:

- đã biết tiếng Trung;
- đã hiểu hệ thống HSK;
- đã có kiến thức ngữ pháp Trung Quốc;
- đã biết cách tự xây lộ trình học.

Product phải phù hợp với beginner.

---

# 4. Secondary User

Một secondary user đã được xác định sơ bộ:

## Admin / Content Creator

Admin chịu trách nhiệm quản lý hoặc xây dựng learning content.

AI trong tương lai có thể hỗ trợ admin:

- tạo bài luyện tập;
- tạo câu hỏi;
- tạo bài kiểm tra;
- tạo ví dụ.

Chi tiết quyền hạn và workflow của admin chưa được chốt ở Step này.

Không tự thiết kế RBAC hoặc admin API tại Step 0.1.

---

# 5. User Problems

Product được xây để giải quyết các vấn đề sau.

## 5.1 Lack of Structured Learning Path

Người mới học thường không có một lộ trình rõ ràng về:

- học nội dung gì;
- thứ tự học;
- khi nào luyện tập;
- khi nào chuyển bài;
- kiến thức nào thuộc HSK level nào.

Product phải hướng tới một structured learning experience.

---

## 5.2 Lack of Immediate Guidance

Khi gặp vấn đề với:

- vocabulary;
- grammar;
- examples;
- lesson content;

learner thường không có người hướng dẫn ngay lập tức.

Product sẽ có AI assistant để hỗ trợ giải thích kiến thức.

Chi tiết AI architecture chưa được quyết định.

---

## 5.3 Fragmented Learning Materials

Learning materials thường bị phân tán giữa nhiều nguồn.

Product hướng tới việc tập trung learning experience trong một hệ thống có cấu trúc.

---

## 5.4 Vocabulary Retention Difficulty

Learner gặp khó khăn trong việc ghi nhớ vocabulary nếu chỉ học nghĩa của từ.

Product trong tương lai cần tạo điều kiện cho vocabulary xuất hiện trong context, examples và exercises.

Exact learning methodology chưa được chốt.

---

## 5.5 Lack of Grammar Practice

Learner có thể đọc grammar theory nhưng không có đủ cơ hội áp dụng.

Expected learning pattern về mặt product là:

```text
Learn theory
→ View examples
→ Apply knowledge
→ Practice
→ Receive feedback
```

Exact exercise types chưa được chốt.

---

# 6. Desired User Outcome

Sau khi hoàn thành learning scope HSK 1–3, product hướng tới việc giúp learner:

1. Có nền tảng vocabulary HSK 1–3.
2. Hiểu grammar tương ứng.
3. Có nền tảng pronunciation.
4. Phát triển listening skill.
5. Phát triển speaking skill.
6. Phát triển reading skill.
7. Phát triển writing skill.
8. Có thể giao tiếp tiếng Trung cơ bản.
9. Có nền tảng để tham gia kỳ thi HSK.
10. Có khả năng áp dụng kiến thức thay vì chỉ ghi nhớ lý thuyết.

Đây là product goals.

Không coi các mục trên là measurable acceptance metrics tại Step này.

Metrics sẽ được định nghĩa ở Step Product Success Criteria.

---

# 7. Product Direction

Product phải ưu tiên structured learning.

Expected conceptual learning flow:

```text
Learning Path
    ↓
Lesson
    ↓
Theory / Knowledge
    ↓
Examples
    ↓
Practice / Exercise
    ↓
Feedback
    ↓
Progress
    ↓
Next Learning Content
```

Không được thay thế flow trên bằng free-form AI chat làm interaction chính của toàn bộ product.

AI chat là support capability.

---

# 8. AI Role

## 8.1 Learner-facing AI

AI dự kiến hỗ trợ:

### Vocabulary Explanation

AI có thể giúp learner hiểu từ vựng.

### Grammar Explanation

AI có thể giải thích grammar bằng cách phù hợp với learner.

### Lesson-related Q&A

Learner có thể đặt câu hỏi liên quan tới lesson đang học.

### Example Generation

AI có thể tạo thêm examples để minh họa vocabulary hoặc grammar.

---

## 8.2 Admin-facing AI

AI dự kiến hỗ trợ admin:

### Exercise Generation

Hỗ trợ tạo learning exercises.

### Test Generation

Hỗ trợ tạo bài kiểm tra hoặc câu hỏi đánh giá.

---

# 9. AI Constraints Not Yet Decided

Step này không được tự quyết định:

- LLM model;
- LLM provider;
- local model hoặc cloud model;
- prompt architecture;
- agent architecture;
- RAG implementation;
- embedding model;
- vector database;
- retrieval algorithm;
- reranker;
- AI guardrails;
- AI generation approval workflow;
- automatic publishing of AI-generated content.

Các quyết định trên thuộc các Step sau.

---

# 10. Knowledge Scope

Knowledge scope hiện tại giới hạn ở:

```text
HSK 1
HSK 2
HSK 3
```

Project hiện có:

> Giáo trình HSK 1–3.

Giáo trình này dự kiến trở thành một knowledge source quan trọng cho learning content và AI/RAG.

Không ingest dữ liệu tại Step này.

Không tự quyết định document parser, chunk strategy hoặc embedding strategy.

---

# 11. Four-skill Requirement

Product phải được thiết kế về mặt domain để không loại bỏ bất kỳ kỹ năng nào sau đây:

```text
Listening
Speaking
Reading
Writing
```

Tuy nhiên Step 0.1 chưa quyết định:

- UI cho từng skill;
- lesson schema;
- exercise schema;
- audio infrastructure;
- speech recognition;
- text-to-speech;
- pronunciation scoring;
- speaking evaluation.

Các vấn đề đó phải được xử lý ở Step sau khi có requirement đầy đủ.

---

# 12. Product Positioning Statement

Canonical product description hiện tại:

> Một web app dành cho người Việt bắt đầu học tiếng Trung từ con số 0, cung cấp lộ trình học có cấu trúc từ HSK 1 đến HSK 3 cho cả nghe, nói, đọc và viết; kết hợp lý thuyết, thực hành và AI hỗ trợ để người học nắm vững từ vựng, ngữ pháp, phát âm, giao tiếp cơ bản và chuẩn bị cho kỳ thi HSK.

Các Step sau có thể refine câu chữ nhưng không được thay đổi core product direction nếu chưa có quyết định mới từ product owner.

---

# 13. Current Architecture State

Project hiện mới ở Product Definition.

Architecture V0 ở mức conceptual gồm:

```text
User
 ↓
Frontend
 ↓
Backend
 ├── Business / Learning Logic
 ├── User / Progress Logic
 └── AI / RAG Orchestration
       │
       ├── Relational Data Store
       │
       └── RAG Pipeline
             ├── Knowledge Store
             └── LLM
```

Một offline knowledge pipeline cũng được dự kiến:

```text
HSK Source Materials
       ↓
Data Ingestion
       ↓
Parsing / Cleaning
       ↓
Transformation
       ↓
Chunking
       ↓
Embedding
       ↓
Vector Index
```

Đây chỉ là V0 architecture direction.

Không implement architecture trong Step 0.1.

---

# 14. Data Categories Identified

Ba loại data đã được nhận diện ở mức conceptual.

## Product Data

Ví dụ trong tương lai có thể gồm:

- user;
- lesson;
- learning progress;
- exercise result;
- conversation.

Schema chưa được chốt.

## Knowledge Data

Nguồn chính ban đầu:

- HSK 1–3 textbooks/materials.

Knowledge này về sau có thể được xử lý cho RAG.

## AI Runtime Data

Trong tương lai có thể xuất hiện:

- learner question;
- retrieved context;
- LLM answer;
- generation metadata.

Chưa thiết kế persistence.

---

# 15. Functional Behavior

Không có runtime functional behavior cần implement trong Step này.

Step 0.1 chỉ yêu cầu lưu lại product definition.

Nếu repository đã tồn tại, có thể tạo documentation theo cấu trúc thích hợp, ví dụ:

```text
docs/
└── product/
    └── step-0.1-problem-target-user.md
```

Nếu repository chưa tồn tại, chỉ cần cung cấp document output.

Không tạo application code chỉ để hoàn thành Step này.

---

# 16. Data Model / Schema

Không có database schema được chốt trong Step 0.1.

Không tự tạo các bảng như:

```text
users
courses
lessons
progress
documents
chunks
```

Các entity trên mới chỉ là giả thuyết kiến trúc.

Schema chính thức sẽ được thiết kế ở Phase Data & Database Foundation.

---

# 17. API Contract

Không có API contract trong Step 0.1.

Không tự định nghĩa endpoint.

---

# 18. Inputs

Inputs của Step:

- Product idea.
- Target user definition.
- User pain points.
- Desired learner outcome.
- HSK 1–3 knowledge boundary.
- Existing HSK 1–3 textbooks/materials.
- Initial AI capability expectations.
- Requirement rằng product sẽ có authenticated users.
- Product intended to become a deployable product for real users.

---

# 19. Outputs

Expected output của Step:

1. Primary target user definition.
2. Secondary user identification.
3. Problem statement.
4. User pain points.
5. Desired learner outcomes.
6. Knowledge boundary.
7. Initial AI role.
8. Product direction.
9. Product positioning statement.
10. Documentation of unresolved decisions.

Không có executable output.

---

# 20. Business Rules Identified So Far

Các business rules chính thức ở mức product direction:

### BR-01

Primary learner phải được coi là beginner có thể bắt đầu từ zero Chinese knowledge.

### BR-02

Learning scope hiện tại không vượt quá HSK 3.

### BR-03

Product phải hướng tới cả bốn kỹ năng:

- listening;
- speaking;
- reading;
- writing.

### BR-04

Structured learning path là core experience.

### BR-05

AI là supporting capability, không phải toàn bộ product.

### BR-06

AI learner-facing phải có khả năng được thiết kế để hỗ trợ:

- vocabulary explanation;
- grammar explanation;
- lesson Q&A;
- example generation.

### BR-07

AI admin-facing phải có khả năng được thiết kế để hỗ trợ:

- exercise generation;
- test generation.

### BR-08

User authentication sẽ tồn tại vì hệ thống cần support user-specific learning experience và progress trong tương lai.

Chi tiết authentication implementation chưa được quyết định.

---

# 21. Technology Decisions Already Fixed

Không có technology implementation decision cụ thể nào được chốt tại Step 0.1.

Các architecture component dưới đây tồn tại ở mức conceptual:

- web frontend;
- backend;
- relational data layer;
- AI/LLM layer;
- RAG capability;
- ingestion pipeline.

Không được từ tài liệu này suy ra rằng phải dùng một framework hoặc vendor cụ thể.

---

# 22. Things That Must Not Be Changed

Không thay đổi các quyết định sau nếu chưa có instruction mới:

1. Primary target market là người Việt.
2. Learner bắt đầu từ zero Chinese knowledge.
3. Current curriculum scope là HSK 1–3.
4. Product phải support cả 4 kỹ năng.
5. Product phải có structured learning path.
6. Practice/exercise là thành phần quan trọng của learning flow.
7. AI đóng vai trò support.
8. AI learner-facing tập trung vào vocabulary, grammar, lesson Q&A và examples.
9. AI admin-facing có use case hỗ trợ tạo exercise/test.
10. HSK 1–3 materials hiện có là knowledge source ban đầu.
11. Product sẽ có authenticated users.

---

# 23. Out of Scope for This Step

Không thực hiện:

- UI design;
- coding;
- database schema;
- REST API;
- authentication implementation;
- lesson data model;
- exercise data model;
- ingestion;
- OCR;
- embedding;
- vector search;
- RAG;
- prompt engineering;
- LLM integration;
- evaluation;
- Docker;
- deployment;
- monitoring;
- cloud infrastructure.

---

# 24. Edge Cases / Open Questions

Các vấn đề sau cố ý chưa giải quyết:

- một lesson có thể chứa nhiều skill hay không;
- skill learning path có tách riêng hay không;
- HSK 1–3 curriculum được tổ chức theo textbook hay curriculum tự thiết kế;
- user có thể skip level hay không;
- placement test;
- spaced repetition;
- pronunciation assessment;
- speech-to-text;
- text-to-speech;
- writing correction;
- exercise types;
- grading mechanism;
- AI generated exercise review;
- exact HSK exam preparation behavior;
- teacher role;
- subscription/payment;
- gamification.

Không tự quyết định các vấn đề này.

Chúng phải được làm rõ ở các Step Product Scope, Use Cases và Requirements.

---

# 25. Acceptance Criteria

Step 0.1 được coi là hoàn thành khi documentation thể hiện rõ:

- [ ] Primary user là người Việt học Chinese từ zero.
- [ ] Current scope là HSK 1–3.
- [ ] Bốn kỹ năng được ghi nhận.
- [ ] User problems được mô tả.
- [ ] Desired learning outcomes được mô tả.
- [ ] Structured learning là core product direction.
- [ ] AI được mô tả là supporting capability.
- [ ] Learner AI use cases được ghi nhận.
- [ ] Admin AI use cases được ghi nhận.
- [ ] Existing HSK materials được ghi nhận là future knowledge source.
- [ ] Các quyết định kỹ thuật chưa chốt không bị tự động lựa chọn.
- [ ] Không có production code được thêm cho Step này.

---

# 26. Verification Checklist

Trước khi kết thúc Step:

- [ ] Không implement code.
- [ ] Không tự chọn framework.
- [ ] Không tự chọn database.
- [ ] Không tự chọn LLM.
- [ ] Không tự chọn vector database.
- [ ] Không tự thiết kế schema.
- [ ] Không tự thiết kế API.
- [ ] Product definition phản ánh chính xác target user.
- [ ] Pain points phản ánh đúng product problem.
- [ ] Product direction là structured learning + AI assistance.
- [ ] Scope không vượt HSK 3.
- [ ] Các open questions được giữ lại cho Step sau.

---

# 27. Expected Deliverables

Deliverable duy nhất cần thiết:

```text
docs/product/step-0.1-problem-target-user.md
```

hoặc một document tương đương chứa toàn bộ quyết định product của Step này.

Không cần executable implementation.

---

# 28. Final State After Step 0.1

Sau Step này project ở trạng thái:

```text
Product Idea
    ↓
Problem Defined       ✓
Target User Defined   ✓
User Outcomes Defined ✓
Initial AI Role       ✓
Knowledge Scope       ✓
Product Scope         NOT YET
Use Cases             NOT YET
Requirements          NOT YET
System Design         NOT YET
Implementation        NOT YET
```

Step tiếp theo về dependency là:

**Step 0.2 — Product Scope & MVP.**