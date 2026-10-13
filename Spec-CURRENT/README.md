# Trung-Chinese-Learning — Current Specification Source of Truth

**Status:** CURRENT / REVIEWED BASELINE  
**Baseline:** v1.0-reviewed  
**Purpose:** Đây là bộ đặc tả duy nhất được dùng làm source of truth cho PM, specialist chats và Codex.

## 1. Quy tắc sử dụng

- Không dùng lại `docs.zip` / bộ spec cũ để implementation.
- Không trộn file cũ với folder này.
- Mọi thay đổi architecture-significant phải đi qua PM Decision Log trước khi cập nhật Step Specification.
- Codex không được nhận toàn bộ project như một task lớn. Quy tắc thực thi: **one Codex task = one frozen Step Specification**.
- Trước mỗi task Codex phải đọc `PROJECT_CONTEXT.md`, `PM-Control/04-Decision-Log-and-Open-Gates.md`, Step hiện tại và dependency specs do specialist/PM chỉ định.
- Specialist không được tự thay đổi product scope/architecture. Nếu spec và repository conflict ở mức đáng kể, trả về `BLOCKED / Decision Needed` cho PM.

## 2. Cấu trúc

```text
Trung-Chinese-Learning-Spec-CURRENT/
├── README.md
├── PROJECT_CONTEXT.md
├── Phase0/   Product Definition
├── Phase1/   System Design / Architecture
├── Phase2/   Data Model / Schema
├── Phase3/   Backend Implementation
├── Phase4/   Frontend Implementation
├── Phase5/   Data Engineering / Ingestion
├── Phase6/   AI / RAG
├── Phase7/   Evaluation
├── Phase8/   QA / Deployment / Production Readiness
└── PM-Control/
```

Có **60 Step Specifications** trong Phase 0–8.

## 3. Thứ tự đọc cho Codex

### Luôn đọc

1. `PROJECT_CONTEXT.md`
2. `PM-Control/04-Decision-Log-and-Open-Gates.md`
3. Step Specification hiện tại
4. Dependency specs được task packet chỉ định
5. Repository state hiện tại
6. Codex task instructions của Step

### Không cần đọc mặc định

Các tài liệu PM audit/ownership/quality checklist không cần nạp vào mọi Codex task trừ khi PM/Specialist chỉ định.

## 4. Trạng thái implementation

Baseline đã review toàn hệ thống. Tuy nhiên từng Step executable vẫn phải được **just-in-time freeze** dựa trên repository state thực tế trước khi Codex chạy.

Tại baseline này, **Step 3.1 — Backend Skeleton** là Step đầu tiên được mở cho Wave 1 sau pre-implementation review của App Engineering Specialist.

## 5. Bộ cũ

Bạn có thể xóa bộ cũ khỏi working directory. Nếu muốn giữ lịch sử, lưu riêng ngoài project dưới dạng archive. Nó không còn là implementation source of truth.
