# Replacement pronunciation takes

Source: https://github.com/davinfifield/mp3-chinese-pinyin-sound
Pinned commit: aa25ecce7b7fb02757b2c2b8e3c01aa975812edc
Upstream repository declares the Unlicense; its exact LICENSE and the
unmodified input MP3s are preserved in originals/. Upstream does not
name the speaker. These are not Chen Wang recordings.

Prepared 2026-11-13: decoded complete syllables to PCM16 WAV, removed
low-frequency rumble (100 Hz zero-phase filter), applied constant gain
against accepted si/zhi/chi loudness, ramped only the 20 ms low-level
file edges, appended 120 ms silence. No voiced-release fade, syllable
splice, pitch shift, speed change, repetition or time stretching.
Previous versions remain preserved separately. The v6 set is unified
under one source; its zi/ci/shi/ri WAVs are byte-identical to v5.
All source URLs, hashes and gain values: manifest.json.
Human listening QA: PENDING_QA. Technical checks are not phonetic approval.
