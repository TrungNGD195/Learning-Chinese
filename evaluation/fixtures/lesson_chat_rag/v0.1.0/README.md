# Lesson Chat RAG Evaluation Fixture Content Pack v0.1.0

Status: `ACCEPTED_FOR_EVALUATION_FIXTURE`  
Purpose: synthetic, repo-controlled source content for Step 7.2 human case drafting. This is not EvaluationCase ground truth.

## Identity and scope

- The pack contains exactly three synthetic HSK1 lesson sources and one broader synthetic Internal-KB source.
- `HSK1` and `hsk_level_number: 1` identify this project's synthetic beginner fixture level only. They do not certify alignment with an official HSK syllabus.
- Lesson sources declare `intended_scope: CURRENT_LESSON`; the broader notes source declares `intended_scope: INTERNAL_KB` and carries the same synthetic `hsk_level_number: 1` identity.
- All `source_id`, `block_id`, `lesson_locator`, `source_locator`, and `stable_locator` values are semantic strings. No generated database IDs are used.
- All source blocks are accepted for evaluation fixture use. This does not automatically approve EvaluationCases or replace specialist review of case ground truth.
- Multi-turn entries are specialist-reviewed fixture leads accepted for evaluation-fixture use. They are not EvaluationCases and their fixture acceptance does not itself approve dataset cases. Negative-space targets are review prompts, not approved NO_EVIDENCE cases.
- TRUSTED_EXTERNAL source count is zero.

## Contents

| File | Source ID | Kind | Blocks |
|---|---|---|---:|
| `sources/lesson-01-greetings.json` | `fixture.lesson.hsk1.01.greetings` | LESSON | 7 |
| `sources/lesson-02-numbers-age.json` | `fixture.lesson.hsk1.02.numbers-age` | LESSON | 7 |
| `sources/lesson-03-family.json` | `fixture.lesson.hsk1.03.family` | LESSON | 7 |
| `sources/internal-kb-beginner-notes.json` | `fixture.internal-kb.hsk1.beginner-notes` | INTERNAL_KB | 5 |
| **Total** |  |  | **26** |

`coverage/coverage-matrix.json` records lesson versus broader Internal-KB boundaries. `coverage/negative-space-targets.json` records corpus-wide omission targets. `multi-turn-review-leads.jsonl` contains four specialist-reviewed accepted fixture leads.

## Stable locator format

Each Lesson source uses `fixture:hsk1:lesson:<number>:<slug>` as its canonical `lesson_locator`; every Lesson block's `stable_locator` extends that prefix. Each block repeats its `source_id` and includes `block_id`, `source_locator`, and a unique `stable_locator`. Locators point to semantic fixture content, never to a runtime-generated UUID.

## Verification

The pack can be structurally checked by counting the four declared source files and 26 blocks, checking locator uniqueness and UUID absence, checking each coverage matrix reference against source blocks, and scanning educational block text for the registered negative-space forms. Structural checks do not establish linguistic correctness or case validity.
