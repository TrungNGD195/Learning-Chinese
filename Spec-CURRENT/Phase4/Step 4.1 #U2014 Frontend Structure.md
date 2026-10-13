# Step 4.1 — Frontend Structure

## Goal

Create the frontend structural foundation for the Chinese-learning application.

This step defines:

- frontend stack;
- route map;
- screen hierarchy;
- layout boundaries;
- feature-level source structure.

Do not implement real backend integration, detailed lesson UI, AI Chat behavior, or advanced frontend state handling yet.

---

# Frontend Stack

Use:

```text
React
TypeScript
Vite
```

Do not introduce Next.js.

The frontend is a browser application that consumes the existing FastAPI backend over HTTP/JSON.

---

# Architectural Boundary

Preserve:

```text
Browser
→ React Frontend
→ FastAPI Backend
```

Frontend must remain a presentation/client layer.

Do not move backend responsibilities such as:

- business rules;
- grading;
- curriculum unlock;
- progress calculation;
- authorization;
- AI provider calls;

into frontend code.

---

# Public Routes

Create route boundaries for:

```text
/login
/register
/forgot-password
/reset-password
```

These belong to PublicLayout.

Do not build a complex public marketing website in this step.

---

# Learner Routes

Define:

```text
/dashboard
/pronunciation
/hsk/:hskLevel
/lessons/:lessonId
/assessments/:assessmentId
/assessment-attempts/:attemptId/result
/progress
/history
/profile
```

These belong to LearnerLayout.

---

# Dashboard

Route:

```text
/dashboard
```

Reserve UI sections for:

- current HSK;
- current curriculum unit;
- current lesson;
- overall progress;
- Continue Learning.

Actual data integration belongs to Step 4.2.

---

# Pronunciation

Route:

```text
/pronunciation
```

Represent the three required foundations:

```text
TONES
INITIALS
FINALS
```

Do not merge Pronunciation Foundations into Lesson 1.

---

# HSK Curriculum

Route:

```text
/hsk/:hskLevel
```

Reserve the screen for ordered curriculum units:

```text
Lesson
Periodic Test
```

and backend-derived state:

```text
LOCKED
AVAILABLE
COMPLETED
```

Do not implement client-side progression authority.

---

# Lesson

Route:

```text
/lessons/:lessonId
```

One Lesson screen should support UI regions for:

```text
Vocabulary
Grammar
Exercise
AI Chat
```

Do not create separate routes for each vocabulary or grammar item in MVP.

Detailed learning UI belongs to Step 4.3.

Detailed chat behavior belongs to Step 4.4.

---

# Assessment

Use:

```text
/assessments/:assessmentId
```

for both:

```text
LESSON_EXERCISE
PERIODIC_TEST
```

Do not create separate route families unless a later requirement justifies them.

---

# Assessment Result

Use:

```text
/assessment-attempts/:attemptId/result
```

This screen must eventually support:

- score;
- passed state;
- answer review;
- feedback;
- uncertain grading state.

Actual API integration belongs to Step 4.2.

---

# Progress and History

Create separate routes:

```text
/progress
/history
```

`/progress` represents current learning state.

`/history` represents historical assessment attempts and results.

Do not merge these into one generic page.

---

# Profile

Route:

```text
/profile
```

Reserve sections for:

- full name;
- email;
- current HSK/progress summary;
- password change entry.

---

# AI Chat

Do not create a standalone learner `/chat` route for MVP.

Lesson AI Chat should remain part of the Lesson flow.

Do not pre-build GLOBAL-chat routes, state, API abstractions, or UI for a deferred feature. A future product decision may extend the lesson-chat feature through an explicit forward change.

---

# Admin Routes

Use:

```text
/admin
```

as the Admin namespace.

Create route boundaries for:

```text
/admin
/admin/lessons
/admin/lessons/:lessonId
/admin/assessments
/admin/assessments/:assessmentId
/admin/documents
/admin/stats
```

These belong to AdminLayout.

---

# Admin Lesson Editor

`/admin/lessons/:lessonId` should act as a use-case-oriented editor for:

- lesson metadata;
- vocabulary;
- grammar;
- exercises;
- preview;
- publish/archive actions.

Do not expose database junction tables directly as the UI model.

---

# Admin Assessment Editor

`/admin/assessments/:assessmentId` should support both assessment types and lifecycle UI:

```text
DRAFT
→ REVIEW
→ PUBLISHED
```

Actual business actions will call backend APIs in later steps.

---

# Admin Documents

Create only structural/skeleton support for:

```text
/admin/documents
```

The actual upload/processing/review/approval pipeline belongs to Phase 5.

Do not implement ingestion logic in frontend Step 4.1.

---

# Layouts

Implement three top-level layout boundaries:

```text
PublicLayout
LearnerLayout
AdminLayout
```

Responsibilities should be presentation-only:

- navigation;
- header;
- content shell;
- page container.

Do not place business state calculations in layouts.

---

# Learner Navigation

Use main navigation equivalent to:

```text
Dashboard
Learn
Progress
History
Profile
```

Do not add standalone AI Chat navigation in MVP.

---

# Admin Navigation

Use:

```text
Dashboard
Lessons
Assessments
Documents
Stats
```

Do not expose implementation details such as:

```text
Chunks
Embeddings
Knowledge Versions
```

as primary product navigation.

---

# Source Structure

Use a feature-oriented structure:

```text
frontend/
└── src/
    ├── app/
    │   ├── router/
    │   └── layouts/
    │
    ├── features/
    │   ├── auth/
    │   ├── dashboard/
    │   ├── pronunciation/
    │   ├── curriculum/
    │   ├── lesson/
    │   ├── assessment/
    │   ├── progress/
    │   ├── history/
    │   ├── profile/
    │   ├── conversation/
    │   └── admin/
    │
    ├── components/
    ├── lib/
    ├── types/
    └── main.tsx
```

Do not create unnecessary empty files/directories solely to mirror a theoretical structure.

---

# Screen Hierarchy

Target logical hierarchy:

```text
Public
├── Login
├── Register
├── Forgot Password
└── Reset Password

Learner
├── Dashboard
├── Pronunciation Foundations
├── HSK Curriculum
├── Lesson
│   └── AI Chat panel
├── Assessment
├── Assessment Result
├── Progress
├── History
└── Profile

Admin
├── Dashboard
├── Lessons
│   └── Lesson Editor
├── Assessments
│   └── Assessment Editor
├── Documents
└── Stats
```

---

# Out of Scope

Do not implement yet:

- real FastAPI calls;
- API client layer;
- session restoration;
- detailed lesson UI;
- exercise interaction logic;
- progress visualization implementation;
- AI Chat interaction;
- streaming;
- retry/error framework;
- document ingestion UI workflow;
- advanced styling/design system.

These belong to later Phase 4 steps.

---

# Acceptance Criteria

- [ ] React + TypeScript + Vite project structure exists.
- [ ] Public/Learner/Admin route groups are defined.
- [ ] PublicLayout, LearnerLayout and AdminLayout exist.
- [ ] Learner screen hierarchy matches approved product flows.
- [ ] Admin routes are isolated under `/admin`.
- [ ] Lesson AI Chat remains embedded in lesson flow.
- [ ] Progress and History are separate screens.
- [ ] Assessment and Assessment Result have separate route responsibilities.
- [ ] Documents screen is only structural at this phase.
- [ ] Source tree is feature-oriented.
- [ ] No backend business logic is duplicated in frontend.

# Expected Deliverable

Frontend structural foundation plus:

```text
docs/frontend/
└── step-4.1-frontend-structure.md
```

Next Step:

**Step 4.2 — Backend API Integration**