# Codex Task — Step 7.2 Build Evaluation Dataset

## Subtask
Materialize the final `TRUSTED_EXTERNAL_FALLBACK` bucket from the PM-frozen specialist review.

This is **Step 7.2 evaluation dataset/fixture work only**.

Do **not** implement Step 6.8-B runtime external retrieval and do **not** start Step 7.3.

## 1. Canonical input checkpoint

```text
dataset_version = v0.7.0
55 total
55 APPROVED
0 DRAFT
0 REJECTED

CURRENT_LESSON_ANSWERABLE = 20/20
INTERNAL_KB_FALLBACK = 10/10
NO_EVIDENCE_REFUSAL = 8/8
OUT_OF_DOMAIN_REFUSAL = 7/7
MULTI_TURN_CONTEXT = 10/10
TRUSTED_EXTERNAL_FALLBACK = 0/5

approved split = 44 DEVELOPMENT / 11 HOLDOUT
STRUCTURAL = PASS
OFFICIAL_GATE = REVIEW_REQUIRED
```

Official remaining target:

```text
TRUSTED_EXTERNAL_FALLBACK = 5
4 DEVELOPMENT
1 HOLDOUT
```

## 2. Frozen semantics

Every case must preserve:

```text
bound CURRENT_LESSON insufficient
→ accepted Internal-KB fixture insufficient
→ reviewed trusted external source sufficient

expected_tier = TRUSTED_EXTERNAL
expected_behavior = FALLBACK_EXTERNAL
```

The accepted internal fixture corpus contains no teaching block for these five selected topics:

```text
比 comparison
在 + place before an action verb
什么 question-word placement
都 = both/all placement
还是 choice questions
```

Do not infer tier from the question alone; preserve the supplied `lesson_context`.

## 3. Create evaluation-only trusted external source registry

Create:

```text
evaluation/fixtures/lesson_chat_rag/trusted_external/v0.1.0/
├── README.md
└── reviewed-sources.json
```

Write `reviewed-sources.json` with exactly this logical content:

```json
{
  "fixture_pack": "lesson_chat_rag_trusted_external",
  "fixture_pack_version": "0.1.0",
  "status": "ACCEPTED_FOR_EVALUATION_FIXTURE",
  "scope": "EVALUATION_ONLY",
  "runtime_external_retrieval_implemented": false,
  "provider_selected": false,
  "domain_allowlist_configured": false,
  "source_count": 5,
  "sources": [
    {
      "source_id": "external.openlearn.chinese3.bi-comparison",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=109137&section=_unit3.4",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 3: 3",
      "reviewed_section_title": "3 Comparisons with bǐ 比",
      "reviewed_claims": [
        "A basic comparison with 比 uses the order A + 比 + B + adjective.",
        "比 is placed between the two compared people or things, with the adjective after B.",
        "The reviewed page illustrates the pattern with 王京比李月高。"
      ],
      "review_status": "ACCEPTED_FOR_EVALUATION_FIXTURE"
    },
    {
      "source_id": "external.openlearn.chinese2.zai-location",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=109075&section=_unit3.8",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 2: 7",
      "reviewed_section_title": "7 Location, location, location",
      "reviewed_claims": [
        "For an action at a location, the location expression 在 + place comes before the action verb.",
        "The reviewed page illustrates the pattern with 我在北京学中文。"
      ],
      "review_status": "ACCEPTED_FOR_EVALUATION_FIXTURE"
    },
    {
      "source_id": "external.openlearn.chinese2.shenme-placement",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=109075&section=_unit3.4",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 2: 3",
      "reviewed_section_title": "3 Asking questions with ‘what’ and ‘where’",
      "reviewed_claims": [
        "什么 replaces the unknown answer element and remains in the position where that answer would appear.",
        "The reviewed page uses 他明天晚上做什么？ to show 什么 after 做 in the answer slot."
      ],
      "review_status": "ACCEPTED_FOR_EVALUATION_FIXTURE"
    },
    {
      "source_id": "external.openlearn.chinese2.dou-placement",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=106447&section=5",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 2: Week 2: 4",
      "reviewed_section_title": "4 Use of dōu 都 (both/all)",
      "reviewed_claims": [
        "When 都 means both/all in a basic statement, it is placed before the verb.",
        "The reviewed page illustrates this placement with 老师们都是英国人吗？, where 都 precedes 是."
      ],
      "review_status": "ACCEPTED_FOR_EVALUATION_FIXTURE"
    },
    {
      "source_id": "external.openlearn.chinese2.haishi-choice",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=109075&section=_unit3.9",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 2: 8",
      "reviewed_section_title": "8 Choice questions with háishi 还是",
      "reviewed_claims": [
        "还是 links the alternatives in a choice question.",
        "A choice question with 还是 does not add 吗 at the end.",
        "The reviewed page illustrates the pattern with 她是英国人还是美国人？"
      ],
      "review_status": "ACCEPTED_FOR_EVALUATION_FIXTURE"
    }
  ]
}
```

The README must state:

```text
Purpose:
- deterministic Step 7.2 reviewed external evidence identities only.

Review status:
- all listed sources are ACCEPTED_FOR_EVALUATION_FIXTURE.
- only the reviewed claims in reviewed-sources.json are accepted as Step 7.2 ground truth.

Runtime boundary:
- no provider selected;
- no domain allowlist configured;
- no runtime network/retrieval behavior implemented;
- Step 6.8-B remains NOT STARTED.

Provenance:
- EvaluationCases cite exact HTTPS URLs through EXTERNAL_URL EvidenceRef.
- source_id is a stable evaluation-fixture identity.
- URL/domain/title in cases must match the reviewed registry.

Negative-space safety:
- these five reviewed topics are distinct from the eight accepted NO_EVIDENCE targets.
- do not broaden reviewed claims or add unrelated external pages in this task.
```

Do not modify the existing accepted internal fixture pack under:

```text
evaluation/fixtures/lesson_chat_rag/v0.1.0/
```

## 4. Exact reviewed EvaluationCases

Materialize exactly the following five cases. They are already specialist-reviewed and are authorized for `APPROVED` materialization only after PM freezes this task.

Do not regenerate, paraphrase, substitute, or expand them.

```json
{
  "case_id": "trusted-external-bi-comparison-001",
  "schema_version": "1.0.0",
  "dataset_version": "v0.8.0",
  "bucket": "TRUSTED_EXTERNAL_FALLBACK",
  "split": "DEVELOPMENT",
  "question": "How do I use 比 to say that one person is taller than another?",
  "lesson_context": {
    "lesson_locator": "fixture:hsk1:lesson:02:numbers-age",
    "hsk_identity": "HSK1 (synthetic project fixture identity; not official syllabus certification)",
    "lesson_title": "Numbers and age (synthetic HSK1 fixture)"
  },
  "expected_information": [
    "A basic comparison with 比 follows the order A + 比 + B + adjective.",
    "比 is placed between the two people or things being compared, and the adjective comes after B.",
    "The reviewed source illustrates this with 王京比李月高。"
  ],
  "required_evidence": [
    {
      "evidence_id": "trusted-external-bi-comparison-001-e1",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=109137&section=_unit3.4",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 3: 3",
      "relevance_role": "REQUIRED",
      "requirement_id": "trusted-external-bi-comparison-001-req-1"
    }
  ],
  "acceptable_evidence": [],
  "expected_scope": {
    "scope_kind": "TRUSTED_EXTERNAL"
  },
  "expected_tier": "TRUSTED_EXTERNAL",
  "expected_behavior": "FALLBACK_EXTERNAL",
  "expected_answer_properties": [
    "Use the reviewed trusted external source only after both the bound current Lesson and broader Internal KB are insufficient.",
    "Answer in Vietnamese at a beginner-friendly level and cite the required reviewed external URL.",
    "Do not treat this evaluation-only source record as evidence that runtime external retrieval, provider selection, or a domain allowlist has been implemented."
  ],
  "expected_citation_sources": [
    "trusted-external-bi-comparison-001-e1"
  ],
  "critical_failure_expectations": [
    "SERIOUS_FACTUAL_ERROR",
    "UNSUPPORTED_CONFIDENT_CLAIM",
    "FABRICATED_CITATION_OR_SOURCE",
    "CITATION_PROVENANCE_MISMATCH",
    "CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE",
    "RETRIEVAL_SCOPE_VIOLATION",
    "TIER_FALLBACK_POLICY_VIOLATION",
    "REQUIRED_CITATION_MISSING"
  ],
  "review_status": "APPROVED"
}
```

```json
{
  "case_id": "trusted-external-zai-location-001",
  "schema_version": "1.0.0",
  "dataset_version": "v0.8.0",
  "bucket": "TRUSTED_EXTERNAL_FALLBACK",
  "split": "DEVELOPMENT",
  "question": "Where does 在 + place go when I say an action happens at a location, such as studying Chinese in Beijing?",
  "lesson_context": {
    "lesson_locator": "fixture:hsk1:lesson:03:family",
    "hsk_identity": "HSK1 (synthetic project fixture identity; not official syllabus certification)",
    "lesson_title": "Family (synthetic HSK1 fixture)"
  },
  "expected_information": [
    "For an action at a location, use Subject + 在 + Place + Verb (+ Object).",
    "The 在 + place phrase comes before the action verb.",
    "The reviewed source gives 我在北京学中文。 as an example."
  ],
  "required_evidence": [
    {
      "evidence_id": "trusted-external-zai-location-001-e1",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=109075&section=_unit3.8",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 2: 7",
      "relevance_role": "REQUIRED",
      "requirement_id": "trusted-external-zai-location-001-req-1"
    }
  ],
  "acceptable_evidence": [],
  "expected_scope": {
    "scope_kind": "TRUSTED_EXTERNAL"
  },
  "expected_tier": "TRUSTED_EXTERNAL",
  "expected_behavior": "FALLBACK_EXTERNAL",
  "expected_answer_properties": [
    "Use the reviewed trusted external source only after both the bound current Lesson and broader Internal KB are insufficient.",
    "Answer in Vietnamese at a beginner-friendly level and cite the required reviewed external URL.",
    "Do not treat this evaluation-only source record as evidence that runtime external retrieval, provider selection, or a domain allowlist has been implemented."
  ],
  "expected_citation_sources": [
    "trusted-external-zai-location-001-e1"
  ],
  "critical_failure_expectations": [
    "SERIOUS_FACTUAL_ERROR",
    "UNSUPPORTED_CONFIDENT_CLAIM",
    "FABRICATED_CITATION_OR_SOURCE",
    "CITATION_PROVENANCE_MISMATCH",
    "CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE",
    "RETRIEVAL_SCOPE_VIOLATION",
    "TIER_FALLBACK_POLICY_VIOLATION",
    "REQUIRED_CITATION_MISSING"
  ],
  "review_status": "APPROVED"
}
```

```json
{
  "case_id": "trusted-external-shenme-placement-001",
  "schema_version": "1.0.0",
  "dataset_version": "v0.8.0",
  "bucket": "TRUSTED_EXTERNAL_FALLBACK",
  "split": "DEVELOPMENT",
  "question": "In a Chinese 'what' question, where does 什么 go instead of moving to the front like English 'what'?",
  "lesson_context": {
    "lesson_locator": "fixture:hsk1:lesson:01:greetings",
    "hsk_identity": "HSK1 (synthetic project fixture identity; not official syllabus certification)",
    "lesson_title": "Greetings and names (synthetic HSK1 fixture)"
  },
  "expected_information": [
    "什么 replaces the unknown answer element and stays in the position where that answer would appear.",
    "In 他明天晚上做什么？, 什么 appears after 做 in the position occupied by the requested information."
  ],
  "required_evidence": [
    {
      "evidence_id": "trusted-external-shenme-placement-001-e1",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=109075&section=_unit3.4",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 2: 3",
      "relevance_role": "REQUIRED",
      "requirement_id": "trusted-external-shenme-placement-001-req-1"
    }
  ],
  "acceptable_evidence": [],
  "expected_scope": {
    "scope_kind": "TRUSTED_EXTERNAL"
  },
  "expected_tier": "TRUSTED_EXTERNAL",
  "expected_behavior": "FALLBACK_EXTERNAL",
  "expected_answer_properties": [
    "Use the reviewed trusted external source only after both the bound current Lesson and broader Internal KB are insufficient.",
    "Answer in Vietnamese at a beginner-friendly level and cite the required reviewed external URL.",
    "Do not treat this evaluation-only source record as evidence that runtime external retrieval, provider selection, or a domain allowlist has been implemented."
  ],
  "expected_citation_sources": [
    "trusted-external-shenme-placement-001-e1"
  ],
  "critical_failure_expectations": [
    "SERIOUS_FACTUAL_ERROR",
    "UNSUPPORTED_CONFIDENT_CLAIM",
    "FABRICATED_CITATION_OR_SOURCE",
    "CITATION_PROVENANCE_MISMATCH",
    "CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE",
    "RETRIEVAL_SCOPE_VIOLATION",
    "TIER_FALLBACK_POLICY_VIOLATION",
    "REQUIRED_CITATION_MISSING"
  ],
  "review_status": "APPROVED"
}
```

```json
{
  "case_id": "trusted-external-dou-placement-001",
  "schema_version": "1.0.0",
  "dataset_version": "v0.8.0",
  "bucket": "TRUSTED_EXTERNAL_FALLBACK",
  "split": "DEVELOPMENT",
  "question": "Where does 都 go in a basic statement when it means 'both/all'?",
  "lesson_context": {
    "lesson_locator": "fixture:hsk1:lesson:03:family",
    "hsk_identity": "HSK1 (synthetic project fixture identity; not official syllabus certification)",
    "lesson_title": "Family (synthetic HSK1 fixture)"
  },
  "expected_information": [
    "When 都 means both/all in a basic statement, it is placed before the verb.",
    "The reviewed source illustrates this placement with 老师们都是英国人吗？, where 都 comes before 是."
  ],
  "required_evidence": [
    {
      "evidence_id": "trusted-external-dou-placement-001-e1",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=106447&section=5",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 2: Week 2: 4",
      "relevance_role": "REQUIRED",
      "requirement_id": "trusted-external-dou-placement-001-req-1"
    }
  ],
  "acceptable_evidence": [],
  "expected_scope": {
    "scope_kind": "TRUSTED_EXTERNAL"
  },
  "expected_tier": "TRUSTED_EXTERNAL",
  "expected_behavior": "FALLBACK_EXTERNAL",
  "expected_answer_properties": [
    "Use the reviewed trusted external source only after both the bound current Lesson and broader Internal KB are insufficient.",
    "Answer in Vietnamese at a beginner-friendly level and cite the required reviewed external URL.",
    "Do not treat this evaluation-only source record as evidence that runtime external retrieval, provider selection, or a domain allowlist has been implemented."
  ],
  "expected_citation_sources": [
    "trusted-external-dou-placement-001-e1"
  ],
  "critical_failure_expectations": [
    "SERIOUS_FACTUAL_ERROR",
    "UNSUPPORTED_CONFIDENT_CLAIM",
    "FABRICATED_CITATION_OR_SOURCE",
    "CITATION_PROVENANCE_MISMATCH",
    "CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE",
    "RETRIEVAL_SCOPE_VIOLATION",
    "TIER_FALLBACK_POLICY_VIOLATION",
    "REQUIRED_CITATION_MISSING"
  ],
  "review_status": "APPROVED"
}
```

```json
{
  "case_id": "trusted-external-haishi-choice-001",
  "schema_version": "1.0.0",
  "dataset_version": "v0.8.0",
  "bucket": "TRUSTED_EXTERNAL_FALLBACK",
  "split": "HOLDOUT",
  "question": "How do I form a choice question with 还是, and do I add 吗 at the end?",
  "lesson_context": {
    "lesson_locator": "fixture:hsk1:lesson:01:greetings",
    "hsk_identity": "HSK1 (synthetic project fixture identity; not official syllabus certification)",
    "lesson_title": "Greetings and names (synthetic HSK1 fixture)"
  },
  "expected_information": [
    "还是 links the alternatives in a choice question.",
    "A choice question with 还是 does not add 吗 at the end.",
    "The reviewed source gives 她是英国人还是美国人？ as an example."
  ],
  "required_evidence": [
    {
      "evidence_id": "trusted-external-haishi-choice-001-e1",
      "source_kind": "EXTERNAL_URL",
      "url": "https://www.open.edu/openlearn/mod/oucontent/view.php?id=109075&section=_unit3.9",
      "domain": "www.open.edu",
      "title": "Getting started with Chinese 2: 8",
      "relevance_role": "REQUIRED",
      "requirement_id": "trusted-external-haishi-choice-001-req-1"
    }
  ],
  "acceptable_evidence": [],
  "expected_scope": {
    "scope_kind": "TRUSTED_EXTERNAL"
  },
  "expected_tier": "TRUSTED_EXTERNAL",
  "expected_behavior": "FALLBACK_EXTERNAL",
  "expected_answer_properties": [
    "Use the reviewed trusted external source only after both the bound current Lesson and broader Internal KB are insufficient.",
    "Answer in Vietnamese at a beginner-friendly level and cite the required reviewed external URL.",
    "Do not treat this evaluation-only source record as evidence that runtime external retrieval, provider selection, or a domain allowlist has been implemented."
  ],
  "expected_citation_sources": [
    "trusted-external-haishi-choice-001-e1"
  ],
  "critical_failure_expectations": [
    "SERIOUS_FACTUAL_ERROR",
    "UNSUPPORTED_CONFIDENT_CLAIM",
    "FABRICATED_CITATION_OR_SOURCE",
    "CITATION_PROVENANCE_MISMATCH",
    "CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE",
    "RETRIEVAL_SCOPE_VIOLATION",
    "TIER_FALLBACK_POLICY_VIOLATION",
    "REQUIRED_CITATION_MISSING"
  ],
  "review_status": "APPROVED"
}
```

## 5. Dataset update rules

Update:

```text
evaluation/datasets/lesson_chat_rag/v0/development.jsonl
evaluation/datasets/lesson_chat_rag/v0/holdout.jsonl
evaluation/datasets/lesson_chat_rag/v0/manifest.json
evaluation/datasets/lesson_chat_rag/v0/README.md
```

Rules:

1. Preserve all existing 55 cases semantically.
2. Add four supplied DEVELOPMENT cases and one supplied HOLDOUT case.
3. Keep deterministic ascending `case_id` order in each JSONL file.
4. Bump **every** dataset row from `v0.7.0` to `v0.8.0`.
5. Update manifest and README consistently.
6. Do not change the schema or validator behavior.

Expected final state:

```text
dataset_version = v0.8.0

60 total
60 APPROVED
0 DRAFT
0 REJECTED

CURRENT_LESSON_ANSWERABLE = 20
INTERNAL_KB_FALLBACK = 10
TRUSTED_EXTERNAL_FALLBACK = 5
NO_EVIDENCE_REFUSAL = 8
OUT_OF_DOMAIN_REFUSAL = 7
MULTI_TURN_CONTEXT = 10

48 DEVELOPMENT
12 HOLDOUT
```

## 6. Focused test update

Update checked-in snapshot assertions in:

```text
backend/tests/test_evaluation_dataset.py
```

At minimum:

```text
DATASET_VERSION = "v0.8.0"
```

The checked-in dataset test must now verify:

```text
60 total
60 APPROVED
0 DRAFT
0 REJECTED
48 DEVELOPMENT
12 HOLDOUT

TRUSTED_EXTERNAL_FALLBACK = 5
4 DEVELOPMENT / 1 HOLDOUT
all 5 APPROVED
expected_tier = TRUSTED_EXTERNAL
expected_behavior = FALLBACK_EXTERNAL
all REQUIRED evidence source_kind = EXTERNAL_URL
all expected citation IDs resolve to same-case evidence IDs
```

The checked-in test must no longer expect `OFFICIAL_GATE` to raise `ReviewRequiredError`.

Instead assert `OFFICIAL_GATE` passes with:

```text
approved_count_total = 60
approved_development_count = 48
approved_holdout_count = 12
```

Do not weaken generic validator tests.

## 7. Validation

Run:

```text
python evaluation/validate_dataset.py --mode STRUCTURAL
python evaluation/validate_dataset.py --mode OFFICIAL_GATE
python -m pytest -q backend/tests/test_evaluation_dataset.py
```

Expected:

```text
STRUCTURAL = PASS, exit 0
OFFICIAL_GATE = PASS, exit 0
60/60 APPROVED
48 DEVELOPMENT / 12 HOLDOUT
focused tests = PASS
```

A pytest cache permission warning is non-blocking if tests pass.

Refresh the existing Step 7.2 ZIP and inspect the ZIP directly.

## 8. Explicit non-goals

Do NOT:

- implement runtime external retrieval;
- choose an external retrieval provider;
- implement a runtime domain allowlist;
- make runtime network calls;
- add a web-search client;
- alter database schema;
- alter ingestion contracts;
- alter RAG architecture;
- alter retrieval/reranking behavior;
- modify `RAG_MIN_RERANK_SCORE`;
- start Step 6.8-B;
- start Step 7.3;
- add any source beyond the five exact reviewed URLs;
- substitute another URL/title/source;
- copy full external webpage content into the repository.

## 9. Acceptance Criteria

Complete only if:

- exactly five TRUSTED_EXTERNAL cases exist;
- exact split = 4 DEVELOPMENT / 1 HOLDOUT;
- exact reviewed URLs are used;
- required external evidence has `requirement_id`;
- citations resolve to same-case evidence IDs;
- existing 55 cases remain semantically unchanged;
- all 60 rows use `v0.8.0`;
- external source registry remains evaluation-only;
- STRUCTURAL passes;
- focused tests pass;
- OFFICIAL_GATE passes at 60/60;
- no Step 6.8-B or Step 7.3 implementation occurs.

## 10. Return handoff

Return:

```text
status:
files changed:
trusted external source registry:
case IDs materialized:
split:
counts:
dataset version:
STRUCTURAL result:
focused test result:
OFFICIAL_GATE result:
ZIP verification:
conflicts/issues:
```

Expected status:

```text
READY_FOR_SPECIALIST_REVIEW
```
