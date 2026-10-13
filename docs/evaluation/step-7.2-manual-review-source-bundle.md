# Step 7.2 Manual Dataset Review — Source Bundle

Inventory date: 2026-10-07  
Purpose: provide traceable repository fixture material for human review of Step 7.2 cases. This is a source inventory, not evaluation ground truth. Nothing here changes the Step 7.2 dataset or its approval state.

## Review rules

- The entries below are test fixtures authored to exercise application behavior. They are not curated or independently reviewed curriculum.
- `PUBLISHED` in a disposable test row means only that the fixture exercises the published-lesson path. It is not editorial approval.
- IDs generated with `uuid4()` and database rows created by tests are not stable across runs. Use the source file and fixture/function path as the stable locator for review; do not copy a generated runtime ID into a case as a durable source identity.
- No raw files, private learner data, database credentials, or live database rows were included.
- A human reviewer must independently verify educational correctness and suitability before using fixture content as evaluation evidence. Codex-authored annotations remain `DRAFT`.

## Lesson fixture: greetings / vocabulary

| Field | Repository evidence |
|---|---|
| Stable semantic locator | `backend/tests/test_step56_lesson_pipeline.py::lesson_context` → `Lesson.title`, `Vocabulary.hanzi`, `Vocabulary.pinyin`, `Vocabulary.vietnamese_meaning`, `LessonVocabulary.example` |
| Lesson identity/title | Test-created lesson titled `Chinese greetings`; database identity is generated per run |
| HSK identity | Test creates an HSK level with a generated level number in the 4,000,000–4,999,999 range; this is deliberately synthetic and is **not a valid HSK level** |
| Content type | Vocabulary, with a lesson vocabulary example |
| Source/document title | `Chinese greetings` (fixture lesson; not an imported document) |
| Section/page/locator | Vocabulary entity fields; fixture does not define page or named section |
| Chunk/entity identity | Entity IDs are generated per run; no stable Chunk ID is provided |
| Actual fixture content | Hanzi `你好`; pinyin `nǐ hǎo`; Vietnamese meaning `xin chào`; example `你好！` |
| Status represented | Lesson status is `PUBLISHED` in the fixture; this does not establish human content approval |

Source: `backend/tests/test_step56_lesson_pipeline.py`, fixture `lesson_context`.

## Lesson fixture: ordered vocabulary and grammar snapshot

| Field | Repository evidence |
|---|---|
| Stable semantic locator | `backend/tests/test_step52_lesson_ingestion.py::test_published_lesson_snapshot_is_canonical_and_hash_addressed` → snapshot `lesson`, `vocabulary[]`, and `grammar[]` fields |
| Lesson identity/title | Test-created lesson titled `Snapshot`; runtime ID is generated per run |
| HSK identity | Title `Snapshot HSK`; numeric level is intentionally generated outside the real HSK range, so it is not a valid HSK identity |
| Content type | Vocabulary and grammar |
| Source/document title | `Snapshot` (test-created lesson) |
| Section/page/locator | Snapshot field arrays and their persisted ordering; no page locator |
| Chunk/entity identity | Vocabulary/grammar and link IDs are generated per run; no stable Chunk ID |
| Actual fixture content | Vocabulary: `甲` / `jiǎ` / `一乛`, and `乙` / `yǐ` / `二`. Grammar names: `first` and `second`, each with an explanation field. The fixture main assertion checks deterministic ordering, not correctness of the lesson material. |
| Status represented | Lesson starts as `PUBLISHED`; the test also changes it to `DRAFT` and `ARCHIVED` to test rejection |

Source: `backend/tests/test_step52_lesson_ingestion.py`, test `test_published_lesson_snapshot_is_canonical_and_hash_addressed`.

## Lesson context and retrieval examples: locator examples only

The following are test assertions and formatter inputs, not persisted course content:

- `backend/tests/test_step66_prompt_schemas.py::test_learning_context_contains_only_frozen_semantic_fields` uses HSK `2`, lesson title `我的朋友`, and module `Grammar` as a value-shape example.
- `backend/tests/test_step66_prompt_formatter.py::candidate` uses `original 你好 text`, content type `GRAMMAR`, HSK `2`, lesson title `我的朋友`, and section `Greetings` to verify formatting and metadata handling.
- These values do not have an associated lesson row, curriculum source, stable entity/chunk ID, or approval state. They are **not source evidence** for an answerable evaluation case.

## Internal knowledge documents and chunk artifacts

No repository-controlled, review-approved internal knowledge document with substantive source content and stable citation locators was found in the inspected fixtures or checked-in source files.

The test fixture `backend/tests/test_step56_document_pipeline.py::document_context` creates a synthetic document titled `Chinese basics` with body `Chinese learning begins with clear, structured examples.` Its source metadata says `source_origin="Test source"`, `usage_rights_note="Test only"`, and its initial review status is `PENDING`. The content is generic pipeline test input; it is not suitable evidence for `INTERNAL_KB_FALLBACK` and is not included as a knowledge source.

The local `backend/storage/documents/` tree contains 85 parsed and 85 transformed lesson artifacts, but no raw lesson source files. The transformed artifacts inspected have only two test-style titles (`Admin contract lesson` and `Lifecycle lesson`), empty provenance, and generated UUID paths. They do not establish a reviewed source, stable lesson/HSK identity, or approval status, so their contents are excluded from this bundle.

## Bucket suitability from repository evidence

| Step 7.2 bucket | Finding |
|---|---|
| `CURRENT_LESSON_ANSWERABLE` | The greetings and snapshot fixtures above can help a human review the required case fields and lesson-source relationships. They are synthetic pipeline fixtures, so they do not by themselves support an approved ground-truth case. A real stable lesson identity, valid HSK level, and reviewer verification are missing. |
| `INTERNAL_KB_FALLBACK` | No suitable source found. The only inspected document example is generic, test-only, and initially `PENDING`; there is no reviewed internal document with usable content and stable citation locator. |
| `NO_EVIDENCE_REFUSAL` | The repository contains tests that stub zero retrieved candidates, but this does not prove that the real permitted corpus contains no evidence for a particular question. No case-level `no evidence` claim is made. |
| `MULTI_TURN_CONTEXT` | Conversation/memory tests use generated users, lessons, IDs, and generic messages. No reviewed lesson-backed conversation fixture with durable source locators was found. Those tests can guide interaction shape only, not ground-truth annotation. |

## Inventory

```yaml
lesson sources found: 2 test-created lesson fixtures with extractable Chinese-learning fields; neither is reviewed curriculum
internal KB sources found: 0 reviewed source documents; 1 generic pending document fixture excluded as evidence
stable locators available: test file + test/function + semantic model field paths; no stable database/entity/chunk IDs or page locators
usable reviewed/fixture sources: fixture excerpts above for human orientation only; none sufficient for approval without independent source review
missing content: approved lesson corpus with valid HSK identities; reviewed internal KB documents and section/page/chunk locators; reviewed multi-turn lesson-grounded conversations; evidence sufficient to establish true NO_EVIDENCE cases
risks: test fixtures contain generated IDs and intentionally synthetic HSK numbers; PUBLISHED fixture status is not editorial approval; transformed storage artifacts have missing provenance and no raw source files
```

## Scope

This bundle does not add or approve EvaluationCases, alter JSONL or manifest files, change validator behavior, infer evidence groups, add external URLs, access a database, or implement Step 7.3.
