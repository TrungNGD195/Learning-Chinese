# Step 5.1 — Define Knowledge Sources

## Goal

Thiết lập source policy cho Data Ingestion Pipeline.

Hệ thống phải xác định rõ:

- loại knowledge source nào được support;
- cách phân loại Document source;
- provenance tối thiểu cần giữ;
- source nào đủ điều kiện bước vào ingestion;
- source nào được phép trở thành Active Knowledge.

Không triển khai parsing, cleaning, chunking, embedding hoặc retrieval trong Step này.

---

# Existing Knowledge Model

Giữ model đã có:

```text
KnowledgeSource
├── DOCUMENT
└── LESSON
```

Không thay `source_type` thành source category.

Không tạo KnowledgeSource riêng cho từng Vocabulary hoặc Grammar item.

---

# V0 Knowledge Sources

Support knowledge từ:

```text
Published Lesson Content
HSK1 curriculum textbook
HSK2 curriculum textbook
HSK3 curriculum textbook
internal authored notes
```

Internal authored notes là nội dung do team/user tự tìm hiểu, tổng hợp và tự viết.

Không mở generic Internet ingestion.

---

# Document Source Category

Định nghĩa document-level category tương đương:

```text
CURRICULUM_MATERIAL
INTERNAL_AUTHORED
```

Ý nghĩa:

```text
CURRICULUM_MATERIAL
→ HSK1–3 textbook/curriculum source

INTERNAL_AUTHORED
→ note/explanation/example do team tự tạo
```

Không thêm category speculative như:

```text
REFERENCE
SUPPLEMENTARY_MATERIAL
```

cho đến khi product thực sự có loại source đó.

---

# Source Type vs Category

Phải giữ separation:

```text
KnowledgeSource.source_type
= DOCUMENT | LESSON
```

và:

```text
Document.source_category
= CURRICULUM_MATERIAL | INTERNAL_AUTHORED
```

Không dùng:

```text
PDF
DOCX
TXT
MD
```

làm source category.

Đó là input/file format.

---

# No Authority Model

Không thêm:

```text
authority
trust_level
trust_score
source_score
PRIMARY
AUTHORITATIVE
SUPPLEMENTARY
```

vào data model của V0.

Source set hiện tại không cần abstraction này.

---

# Source Precedence

Ghi nhận business policy:

```text
Current Published Lesson
>
CURRICULUM_MATERIAL
>
INTERNAL_AUTHORED
>
External Retrieval
```

Không implement retrieval ranking/filtering trong Step này.

Phase 6 sẽ quyết định cách policy này được áp dụng trong retrieval/prompting.

---

# Allowed Knowledge Domain

Internal knowledge phải thuộc Chinese-learning domain:

```text
pronunciation
vocabulary
grammar
Chinese language learning
culture directly relevant to language usage
```

Không coi các nội dung Chinese-related nhưng không phục vụ việc học ngôn ngữ là eligible knowledge.

Ví dụ ngoài scope:

```text
general politics
general news
general history
unrelated travel material
```

Không triển khai LLM/domain classifier trong Step này.

Domain eligibility có thể được xác nhận trong Admin workflow.

---

# Supported Source Languages

V0 hỗ trợ Document source bằng:

```text
vi
zh
en
```

Document phải giữ source language.

Không triển khai multilingual embedding/retrieval trong Step này.

---

# Supported Input Types

Tiếp tục V0 contract:

```text
PDF
DOCX
TXT
MD
```

Không thêm:

```text
URL
HTML page
website crawling
OCR image ingestion
```

---

# No URL Ingestion

Không triển khai API kiểu:

```text
POST URL
→ fetch page
→ crawl
→ ingest
```

External web retrieval vẫn là runtime capability của Phase 6.

External content không tự động trở thành permanent internal knowledge.

---

# Document Provenance

Document phải có metadata đủ để trace source.

Required logical metadata:

```text
title
source_category
source_origin
source_language
```

Optional metadata:

```text
author_or_organization
publisher
edition_or_version
original_reference
description
usage_rights_note
```

Exact field naming có thể theo conventions hiện tại của codebase.

Nếu `documents` table đã có field equivalent thì reuse.

Không tạo duplicate field chỉ để match tên trong document này.

---

# Usage Rights

Giữ usage-right information ở mức lightweight.

Tối thiểu cần một field/nơi lưu equivalent với:

```text
usage_rights_note
```

Không xây license-management subsystem.

---

# Ingestion Eligibility

Một Document đủ điều kiện đi vào Raw Data Ingestion khi:

```text
input format được support
AND
source nằm trong allowed knowledge domain
AND
source origin được biết
AND
source_category hợp lệ
AND
source_language được support
```

Eligibility không có nghĩa source đã được approve cho retrieval.

---

# Document Review / Activation

Giữ workflow:

```text
Upload
→ Process
→ Preview
→ Admin Review
→ Approve / Reject
```

Processing được phép xảy ra trước approval để admin có dữ liệu preview.

Chỉ approved source mới được phép tạo/activate production retrieval knowledge.

Không expose rejected/unapproved source qua active retrieval.

---

# Published Lesson Knowledge

Lesson chỉ được đưa vào internal knowledge flow khi:

```text
Lesson.status = PUBLISHED
```

Không ingest DRAFT Lesson thành active knowledge.

Lesson không cần `Document.source_category`.

---

# External Retrieval

External Retrieval mặc định:

```text
request-scoped
```

Không tự động:

```text
external result
→ permanent Document
→ Chunk
→ Embedding
→ internal KB
```

Nếu muốn giữ external content lâu dài, nó phải trở thành normal Document source và đi qua ingestion + admin approval workflow.

---

# Non-Knowledge Data

Không tự động đưa các dữ liệu sau vào knowledge pipeline:

```text
Conversation
Message
Learner answer
AssessmentAttempt
Progress
Prompt
LLM response
Retrieval trace
AI runtime log
```

AI-generated draft chỉ được trở thành internal knowledge sau human review và chuyển thành:

```text
Published Lesson
```

hoặc:

```text
Approved Document
```

---

# No Hard-coded Source Whitelist

Không viết application logic phụ thuộc cụ thể vào:

```text
textbook name
publisher name
specific website
specific author
```

Eligibility dựa trên source policy và admin review.

Danh sách source cụ thể có thể nằm trong content/admin operation, không nằm trong hard-coded business rules.

---

# Schema / Domain Changes

Inspect existing `Document` model trước khi sửa.

Nếu chưa có representation tương đương, bổ sung tối thiểu:

```text
source_category
source_origin
source_language
usage_rights_note
```

và reuse existing fields cho:

```text
title
author
publisher
version
reference
description
```

nếu chúng đã tồn tại.

Nếu schema thay đổi:

- tạo Alembic migration mới;
- không rewrite migration đã apply;
- review migration thủ công.

Không thay đổi `KnowledgeSource.source_type`.

---

# Admin Contract

Admin create/upload Document flow phải có khả năng cung cấp hoặc xác nhận:

```text
title
source_category
source_origin
source_language
usage_rights_note when applicable
```

Không cần xây UX phức tạp trong Phase 5.1.

Nếu frontend Admin Document screen hiện vẫn là skeleton, backend/domain contract có thể được chuẩn bị trước; UI implementation chi tiết có thể thực hiện khi document ingestion flow được nối đầy đủ.

---

# Validation

Validate ít nhất:

```text
source_category ∈ {
  CURRICULUM_MATERIAL,
  INTERNAL_AUTHORED
}

source_language ∈ {
  vi,
  zh,
  en
}
```

`source_origin` không được rỗng đối với uploaded Document muốn đi vào ingestion.

Không sử dụng numeric trust score.

---

# Tests

Thêm focused tests cho source-policy behavior nếu Step này có code/domain changes.

Ít nhất kiểm tra:

- valid `CURRICULUM_MATERIAL`;
- valid `INTERNAL_AUTHORED`;
- unsupported source category bị reject;
- supported source languages `vi/zh/en`;
- unsupported source language bị reject theo V0 contract;
- missing required source origin bị reject trước ingestion eligibility;
- Published Lesson đủ điều kiện làm internal source;
- Draft Lesson không trở thành active internal knowledge;
- Document chưa approve không trở thành active retrieval knowledge;
- external retrieval result không tự động tạo permanent KnowledgeSource;
- transactional/runtime data không đi vào knowledge ingestion;
- không có authority/trust field hoặc business logic mới được thêm.

---

# Out of Scope

Không implement trong Step 5.1:

```text
raw file storage strategy
upload transport details
parser
PDF extraction
DOCX extraction
text cleaning
normalization
document transformation
metadata enrichment pipeline
chunking
embedding
vector storage
semantic retrieval
filtering
reranking
prompt construction
LLM generation
web crawling
URL ingestion
OCR
automatic source-quality scoring
authority/trust scoring
```

Các phần này thuộc Step/Phase sau.

---

# Acceptance Criteria

- [ ] KnowledgeSource vẫn dùng `DOCUMENT | LESSON`.
- [ ] V0 Document có `CURRICULUM_MATERIAL | INTERNAL_AUTHORED`.
- [ ] HSK1–3 textbooks map vào `CURRICULUM_MATERIAL`.
- [ ] Team-authored notes map vào `INTERNAL_AUTHORED`.
- [ ] Không có authority/trust model ở V0.
- [ ] Source precedence policy được document rõ.
- [ ] Source languages `vi/zh/en` được support.
- [ ] URL/web crawling không nằm trong ingestion V0.
- [ ] Document provenance tối thiểu được giữ.
- [ ] Usage-right information được giữ ở mức lightweight.
- [ ] Ingestion eligibility tách khỏi approval/activation.
- [ ] Chỉ approved Document mới được active retrieval.
- [ ] Chỉ Published Lesson mới được internal lesson knowledge.
- [ ] External Retrieval không tự động trở thành permanent KB.
- [ ] Transactional/AI-runtime data không tự động được ingest.
- [ ] Không có hard-coded source whitelist.
- [ ] Chưa implement parsing/chunking/embedding/RAG.

# Expected Deliverable

Source-policy foundation plus documentation:

```text
docs/data/
└── step-5.1-define-knowledge-sources.md
```

Next Step:

**Step 5.2 — Raw Data Ingestion**
