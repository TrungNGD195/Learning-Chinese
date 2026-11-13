# Mandarin audio

All learner audio uses useMandarinAudio / lib/audio/browserMandarin.ts.
Ordinary initials, finals, tones, sandhi, vocabulary and sentences use the
device Mandarin speech voice: prefer installed/local, rate 0.8, pitch 1.
No Azure credential, cloud synthesis endpoint or database migration is needed.

## Fixed recordings

- Seven special-i sounds: special-i-native-v7 WAVs; original MP3s, LICENSE and
  baseline provenance in v6. Rebuild with clean-special-i-recordings.py.
- Isolated ai/eng/er: isolated-finals-v1; original MP3s and hashes retained.
  Rebuild with prepare-isolated-finals.py.
- Isolated ong: isolated-finals-v4, sourced from the retained v2 original and
  prepared take. Rebuild with prepare-ong-alternative.py then
  prepare-ong-durations.py. Pitch-preserving duration variants cover
  250-1250 ms, in 50 ms increments. Match the completed device-voice zhong
  duration for this session when available; otherwise select 550 ms.

Only configured recording paths are accepted. Files load through the central
public-file transport, are decoded completely before playback and cached as
AudioBuffers. Reuse one AudioContext/output gain; cancel prior playback and
ignore stale requests. Do not close the device at natural endings. Last
consumer unmount clears the cache and closes the context. Native-file errors
never fall back to the reported-bad browser pronunciations. Missing Mandarin
voices disable only controls needing browser speech, not fixed recordings.

## Navigation and learning

There are 21 initials, 36 finals, five tone examples and 12 sandhi examples.
Four sections sit horizontally above a grouped, scrollable sound index.
Direct selection previews material without writing or skipping saved progress.
Initials use legal tone-one carrier syllables, with tone marks omitted in UI.
Finals offer isolated and combined examples separately; i/mi remain unchanged.

## Distribution and QA

Every retained set contains source/output hashes and processing notes.
The special-i source repository declares the Unlicense. The isolated-final
upstream repositories do not establish redistribution rights themselves.
On 2026-11-13 the owner explicitly confirmed their redistribution rights and
requested retaining these recordings in deployment. See
public/academy/audio/distribution-rights.json. This is an owner attestation,
not independent license verification or expert pronunciation approval.
Speaker identity remains unspecified; listening status remains PENDING_QA.
Do not regenerate audio or call TTS as part of normal build or deployment.

## Verification

Run frontend lint, the complete Vitest suite and the production build.
Tests cover direct selection, progression protection, playback lifecycle,
cancellation, errors and unavailable voices. The pronunciation workspace
browser script uses mocked API responses, without live learner progress writes.
Retired voice previews, TTS pipelines and rejected recordings were removed.
