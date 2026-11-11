# HSK access and lesson practice

The pronunciation foundation is required before HSK1. Students can enter HSK2
or HSK3 directly without completing pronunciation or any earlier HSK level.
Required lessons and periodic tests still progress in order inside each level.
An empty advanced level remains selectable and shows an empty catalog, not a
lock. Draft and archived content remain unavailable to students.

The administrator's lesson-exercise generator defaults to 30 questions and at
least three selected formats (four objective formats are selected initially).
Periodic-test generation retains its existing separate settings. Small draft
generation requests remain accepted by the API for editorial work; the full
30-question request requires varied formats. Manual draft editing remains
available.

Lesson exercises may combine the current lesson with earlier lessons in the
same HSK level. Generation materializes the current lesson first, followed by
earlier non-archived lessons (including drafts visible to the editor). It excludes
later lessons and other levels. The v2 prompt requests approximately 20% review
questions when earlier material is available. This broadens question content;
it adds no completion prerequisites. The reviewed HSK1 lesson 2–5 drafts use
exactly 24 current-focus and six review questions each, with four objective
formats, an 80% threshold, and unchanged attempt-history behavior.

Full exercises are generated in bounded per-format batches of up to ten
questions, using the existing provider and output-token limits. The combined
output must contain exactly the requested count, allowed formats, valid source
references and consistent answer keys. Repeated prompts are rejected. A failed
batch cannot persist a partial exercise. Every generated result remains DRAFT
until an administrator reviews and publishes it.

Lesson 1's existing exercise has been expanded from 20 to 30 questions: ten
multiple choice, ten fill-blank, six matching and four ordering questions.
The added material uses the lesson's existing vocabulary. Its original twenty
question IDs, options and order are preserved, as are the thirteen edited words
and the exercise's DRAFT status and 80% threshold. No real attempts existed.
The guarded idempotent script `backend/scripts/upgrade_lesson1_practice_30.py`
refuses a published exercise, existing attempt history or changed original
questions; applying it requires a backup file. No learning history is deleted.

Students still complete vocabulary, grammar and current-version readings before
practice. A passing lesson exercise still requires at least 80% by default;
explicitly configured thresholds and recorded attempts are preserved.
