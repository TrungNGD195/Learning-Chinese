# Local textbook sources

Keep the original textbooks in `docs/` locally. They are ignored by Git and are
not needed to build or run the application. Lesson content, source attribution,
and the draft import manifest remain versioned in the repository.

| Local filename | Usage |
| --- | --- |
| `HSK1 3.0 Hanu 24.6.26.pdf` | Pronunciation course and HSK 1 lesson 1 draft |
| `HSK2 3.0 Hanu 29.6.26.pdf` | Reference for future HSK 2 authoring |

SHA-256 checksums of the source copies used during authoring:

```text
aefe72aa1a0dd1710d1b6a5888d63ec5f9561cee0466322c75c2a24349b1fe85  HSK1 3.0 Hanu 24.6.26.pdf
8a851d6707b5a37bb0f148e751a1374111d56571916691a6e3ac0dcc4cc5d5a1  HSK2 3.0 Hanu 29.6.26.pdf
```

The HSK 1 lesson manifest is `backend/content/hsk1/lesson-01.json` and the
idempotent draft importer is `backend/scripts/create_hsk1_lesson1_draft.py`.
Importing a draft does not publish it to students. Use the admin review and
publication workflow before making authored content available.
