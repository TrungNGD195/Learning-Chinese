# Noise-cleaned unified special-i recordings

Source: https://github.com/davinfifield/mp3-chinese-pinyin-sound
Pinned commit: aa25ecce7b7fb02757b2c2b8e3c01aa975812edc
Speaker: not named by upstream. Repository license: Unlicense.
Exact LICENSE and unmodified MP3s remain in ../special-i-native-v6/originals/.

Modified 2026-11-13: noise-profile spectral cleanup from originals,
100 Hz high-pass, soft mask smoothed in time/frequency, constant gain,
20 ms quiet file-edge ramps and 120 ms trailing silence. No speech
gate, synthetic/replaced phonemes, speed/pitch edits, repeated cycles,
voice change or time stretching. PCM16 WAV at original 44.1 kHz.
Manifest records source/output hashes, measured noise reduction and
frication-band preservation. Measures are technical checks, not a
phonetic or perceptual certification. Human review: PENDING_QA.
