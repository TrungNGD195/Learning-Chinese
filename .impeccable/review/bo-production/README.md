# Bo academy production adoption — 2026-11-03

User approved the illustrated academy for the main application, with readable fonts and the dragon named Bo. Main local application: http://127.0.0.1:5173. Separate prototype remains at /journey-test.html.

## Evidence

- `frontend-tests.json`: 396 frontend tests passed. Metadata-editor tests now wait for initial form synchronization before modifying drafts; no API assertion was removed.
- `final-targeted.json`: 76 lesson/dashboard/authentication tests passed after the final markup corrections.
- `build.log`: TypeScript and production Vite build passed; existing large-bundle warning remains. `lint.log`: no errors; five existing administrative state-in-effect warnings remain.
- Backend: `tests/test_pronunciation_lesson.py` and `tests/test_progression_gates.py`, 2 passed against the dedicated PostgreSQL test database after migration 0013. Assertions cover direct lesson access being denied before final pronunciation completion. Existing production container already has migration 0013 and the matching progression service.
- `browser-verification.json`: 42 captures across 1440, 768 and 390px with no horizontal overflow, JavaScript errors, missing API fixtures or failed non-API resources. Real frontend routes use deterministic API fixtures. Exercises all 62 ordered pronunciation advances, three section completions and final lesson completion before HSK1 opens; vocabulary writes require explicit expansion; reading preferences work.
- `container-smoke.json`: deployed frontend at port 5173, five successful asset/source requests, real backend login at 1440 and 390px without API interception or JavaScript errors. Docker frontend CSS and dashboard source hashes match the checked workspace files.
- `finish-review.md`: initial six material fixes; `finish-verdict.md`: reviewer scored all six resolved, disposition `ship`. Verdict covers the fix list.
- Raster provenance scan: 4 academy rasters, 0 missing. Local fonts include source manifest and OFL licenses.

## Curriculum source and access

Local `docs/HSK1 3.0 Hanu 24.6.26.pdf`; visually inspected pages 4–7, 17–18, 27–29 (printed 2–5, 15–16, 25–27). Source references appear in lessons. The PDF is not a public frontend asset. Progress and authorization remain server-owned; client storage contains only validated reading preferences. Pronunciation completion records study steps, not automated pronunciation proficiency. Device speech is optional and explains its availability.

Word art uses explicit supported-word mappings; unsupported vocabulary has no unrelated fallback image. The admin retains its existing content-management capabilities.
