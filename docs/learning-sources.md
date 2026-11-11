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

Lesson 1 also contains the textbook's short greeting reading from printed page 1
(PDF page 3), stored in the manifest's `readings` section with pinyin and Vietnamese
translation. It is separate from pronunciation and practice questions.

To add only missing textbook readings to an already edited lesson-1 draft:

```powershell
python -m scripts.add_hsk1_lesson1_readings
python -m scripts.add_hsk1_lesson1_readings --apply
```

The first command is a dry run. The importer keeps existing reading edits and all
vocabulary associations, order, notes and examples. The current local draft's 13
administrator-selected words are preserved; the original fresh-install manifest
remains the initial textbook scaffold.

Students explicitly complete every reading. Vocabulary and grammar views plus
current reading completions are all required before opening, starting or submitting
a lesson exercise. Editing reading text increments its version; students must
confirm the updated reading, and historical exercise results remain available.
Lessons without readings have no additional reading requirement.

Pronunciation now includes a fourth section, **Biến điệu**, with 12 guided
examples. The HSK 1 textbook references are PDF pages 7–8, 18, 30 and 38
(printed pages 5–6, 16, 28 and 36): third-tone sandhi, half third tone,
neutral tone, 不 and 一. Supplementary phrase grouping and reduplication
examples were checked against the [EdUHK Mandarin pronunciation resource](https://corpus.eduhk.hk/mandarin_pronunciation/?page_id=33)
and [PolyU tone-sandhi guide](https://www.polyu.edu.hk/bepth/introduction-to-phonetics/tones/tone-sandhi/?sc_lang=en).

The UI separates original individual tones (Thanh gốc) from spoken forms
(Cách đọc). Written third-tone pinyin stays unchanged; changed marks on 一/不
show the spoken form, as in the textbook. Longer third-tone sequences depend
on phrase grouping; examples are explicitly illustrative rather than a single
universal transformation. Device speech is optional reference audio, not a
pronunciation assessment or a guaranteed teacher recording.

New learners complete all four pronunciation sections before explicitly
finishing and unlocking HSK 1. Earlier graduates retain their original completion
date and HSK access; the new sandhi section is available as supplementary study.

Lesson vocabulary now uses authentic stroke paths and medians from
`hanzi-writer-data` 2.0.1 (Make Me a Hanzi / Arphic). See
[third-party-notices.md](third-party-notices.md) for provenance and redistribution.
Stroke controls do not mark vocabulary as viewed or change theory progress.
# Pronunciation reminder editorial check (2026-11-05)

Per-sound reminders in `frontend/src/features/pronunciation/pronunciationTips.ts`
were checked against the supplied HSK1 textbook and PolyU's BEPTH pages:
[initial groups](https://www.polyu.edu.hk/bepth/introduction-to-phonetics/initials/initial-groups/),
[simple finals](https://www.polyu.edu.hk/bepth/introduction-to-phonetics/simple-finals/),
[compound finals](https://www.polyu.edu.hk/bepth/introduction-to-phonetics/compound-finals/compound-final-groups/),
[pinyin spelling](https://www.polyu.edu.hk/bepth/introduction-to-phonetics/spelling-rules-in-pinyin/)
and [tone sandhi](https://www.polyu.edu.hk/bepth/introduction-to-phonetics/tones/tone-sandhi/).
These are editorial verification references; source annotations are omitted from
the learning interface at the user's request. Existing source metadata is retained.
