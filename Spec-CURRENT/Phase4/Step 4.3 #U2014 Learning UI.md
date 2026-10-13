# Step 4.3 — Learning UI

## Goal

Implement the learner-facing UI for:

- lessons;
- vocabulary;
- grammar;
- assessments;
- assessment results;
- learning progress.

Use the backend APIs from Step 4.2.

The frontend must remain presentation-focused and must not become authoritative for learning progression, grading or completion.

---

# Lesson Flow

Use the logical lesson flow:

```text
Lesson Header
→ Vocabulary
→ Grammar
→ Exercise
```

Do not implement detailed AI Chat behavior in this step.

AI Chat belongs to Step 4.4.

---

# Lesson Header

Display learner-facing information such as:

```text
HSK level
lesson number
lesson title
progress
completion state
```

All progress/completion values must come from backend responses.

Do not derive authoritative lesson state locally.

---

# Vocabulary UI

For each lesson vocabulary item, support display of:

```text
hanzi
pinyin
Vietnamese meaning
part of speech
example
optional note
```

Use learner-friendly cards/list presentation rather than requiring a dense table layout.

---

# Vocabulary Viewing

Do not mark Vocabulary as viewed merely because lesson data was fetched.

Use a deliberate learner interaction such as opening/expanding the item.

Flow:

```text
learner opens vocabulary details
→ lessonApi.markVocabularyViewed(...)
```

The backend operation is idempotent.

Frontend may immediately update presentation state after successful response, but backend remains authoritative.

---

# Grammar UI

Each grammar section should support:

```text
name
structure
explanation
usage
examples
optional note
```

Use an expandable/readable section presentation appropriate for learner content.

---

# Grammar Viewing

Do not mark Grammar viewed on page load.

Flow:

```text
learner opens grammar section
→ lessonApi.markGrammarViewed(...)
```

The backend operation is idempotent.

---

# Theory Completion

Do not implement a frontend-controlled `mark theory complete` behavior.

Render theory state returned by backend.

Example learner-facing state:

```text
Vocabulary 8 / 10 viewed
Grammar 2 / 3 viewed
Theory incomplete
```

Backend is the source of truth.

---

# Exercise Entry

Provide a learner-facing entry/action equivalent to:

```text
Start Exercise
```

Use backend-provided availability/access state.

Do not unlock the Assessment based only on frontend-local counting logic.

---

# Assessment UI

Reuse one Assessment UI model for:

```text
LESSON_EXERCISE
PERIODIC_TEST
```

Create a common assessment shell responsible for:

```text
question number
prompt
answer area
question navigation
submission action
```

---

# Question Rendering

Use a type-driven renderer.

Equivalent structure:

```text
QuestionRenderer
├── MultipleChoiceQuestion
├── FillBlankQuestion
├── MatchingQuestion
├── ReorderQuestion
└── FreeTextQuestion
```

Support approved question types:

```text
MCQ
FILL_BLANK
MATCHING
REORDER_SENTENCE
VI_TO_ZH_TRANSLATION
ZH_TO_VI_TRANSLATION
SENTENCE_WRITING
```

Map exact enum values to the backend contract.

Do not place all question-specific interaction logic in one giant page component.

---

# Temporary Answers

Before submission, maintain temporary frontend answer state equivalent to:

```text
question_id
→ current answer
```

This state exists only to construct the submission request.

It is not the authoritative grading/result state.

---

# Submission

Submit through the approved Assessment API integration.

Flow:

```text
current answers
→ assessmentApi.submitAttempt(...)
→ FastAPI
→ grading
→ persisted result
→ response/result page
```

Frontend must not:

- grade objective questions;
- invoke AI grading;
- calculate authoritative pass/fail;
- update learner progress directly;
- unlock the next curriculum unit.

---

# Assessment Result

Use route:

```text
/assessment-attempts/:attemptId/result
```

Render backend result information including where available:

```text
score
passed status
individual question result
feedback
correct answer
grading status
UNCERTAIN state
attempt metadata
```

Do not reinterpret UNCERTAIN as incorrect.

---

# Failed Result Flow

If the learner has not passed:

```text
Result
→ review answers
→ Retry
```

Do not force learner navigation back to theory.

AI assistance may be added in Step 4.4.

---

# Passed Result Flow

If backend reports the learning unit as passed/completed:

```text
Result
→ show completion
→ show Next Lesson / Continue Learning action
```

Do not automatically redirect.

Use backend-provided next/available curriculum state.

---

# Progress Page

Route:

```text
/progress
```

Represent:

```text
Pronunciation Foundations
HSK1
HSK2
HSK3
```

Show ordered curriculum units within each HSK when available.

---

# Curriculum Progress

Represent both:

```text
LESSON
PERIODIC_TEST
```

as real curriculum units.

Example:

```text
Lesson 1         COMPLETED
Lesson 2         COMPLETED
Periodic Test    COMPLETED
Lesson 3         AVAILABLE
```

Do not hide tests from the progression model.

---

# Progress Percentage

Do not recompute authoritative percentages in frontend code.

Render the progress values returned by backend.

Backend business rules remain authoritative.

---

# Lesson Progress Detail

Where supported by backend responses, display:

```text
lesson state
theory progress
latest assessment score
best score
attempt count
completion date
```

Do not invent unavailable metrics.

---

# Current Learning Position

Clearly identify:

```text
current HSK
current curriculum unit
```

Provide a Continue Learning action that navigates to the backend-determined current target.

---

# No Gamification

Do not introduce MVP features such as:

```text
XP
streak
badges
leaderboards
hearts
```

They are out of product scope.

---

# No Vocabulary Mastery UI

Do not display:

```text
mastered vocabulary
weak vocabulary
SRS level
memory strength
```

because those states do not exist in the current product/data model.

Vocabulary theory UI may show only the supported viewed/not-viewed learning state.

---

# Responsive Scope

Ensure learner flows are usable on:

```text
desktop
tablet
mobile
```

Prioritize functional usability.

Do not spend this step on pixel-perfect responsive design or advanced animation systems.

---

# Suggested Structure

Equivalent feature structure:

```text
features/
├── lesson/
│   ├── LessonPage
│   ├── LessonHeader
│   ├── VocabularySection
│   ├── VocabularyCard
│   ├── GrammarSection
│   └── GrammarCard
│
├── assessment/
│   ├── AssessmentPage
│   ├── QuestionRenderer
│   ├── question-types/
│   └── AssessmentResultPage
│
└── progress/
    ├── ProgressPage
    ├── HskProgress
    └── CurriculumProgress
```

Exact files may differ if the same feature boundaries are preserved.

Do not generate unnecessary empty boilerplate.

---

# Tests

Add focused frontend tests for core behavior where useful:

- Vocabulary view action is triggered by learner interaction, not initial fetch.
- Grammar view action behaves equivalently.
- Backend theory state is rendered correctly.
- QuestionRenderer selects the appropriate renderer.
- Temporary answers are submitted in the expected request shape.
- Frontend does not calculate grading.
- Failed result exposes Retry.
- Passed result exposes Next/Continue action when backend allows it.
- Periodic Test renders inside curriculum progress.
- Backend-returned progress percentage is rendered without independent recalculation.

Use mocked API responses.

---

# Out of Scope

Do not implement yet:

- AI Chat interface;
- conversation list/panel behavior;
- AI retry behavior;
- streaming;
- global loading/error strategy;
- automatic auth session recovery;
- advanced frontend state framework;
- gamification;
- SRS;
- vocabulary mastery model.

These belong to later steps or future scope.

---

# Acceptance Criteria

- [ ] Lesson UI follows Vocabulary → Grammar → Exercise flow.
- [ ] Vocabulary and Grammar content are learner-readable.
- [ ] Theory viewing is triggered by actual learner interaction.
- [ ] Frontend does not directly mark theory complete.
- [ ] Assessment UI supports all approved Question types.
- [ ] Question rendering is type-based.
- [ ] Temporary answers remain frontend-only until submission.
- [ ] Backend performs grading and progression decisions.
- [ ] Assessment Result represents correct/incorrect/uncertain states.
- [ ] Retry and Next Lesson flows match backend state.
- [ ] Progress page includes Pronunciation, HSK and Periodic Test progression.
- [ ] Progress percentages come from backend.
- [ ] No unsupported gamification/mastery features are added.
- [ ] Learner flows remain usable across common screen sizes.

# Expected Deliverable

Learning UI foundation plus:

```text
docs/frontend/
└── step-4.3-learning-ui.md
```

Next Step:

**Step 4.4 — AI Chat UI**