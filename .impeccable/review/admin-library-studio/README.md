# Admin library and authoring workshop verification

Main local product: http://127.0.0.1:5173/admin

The approved extension is implemented in the main frontend. `verification.json` records the final browser captures and interaction checks. Capture names identify real routes versus explicit fixture scenarios; the real document inventory is currently empty, so populated document cards and tables use isolated read fixtures.

The browser runner is `frontend/scripts/verify-admin-library-studio.mjs`. It uses a short-lived in-memory admin credential, blocks API writes by default, and overrides only specific write requests with isolated failure/delay fixtures. Previews never call learner submission or progress endpoints. No publishing action is tested against the real API.

The final frontend suite is recorded in `tmp/admin-library-ship-tests.json`: 401 passed, zero failed. Production build and lint completed; existing bundle-size and lint warnings remain. The layout detector returned an empty findings array. Independent source/visual review is in `finish-review.md`.

A preceding review attempt accidentally changed the first exercise prompt. It was restored through a guarded transaction to the original textbook manifest before the final protected run. A direct comparison of all 20 question prompts, types, reference answers, rubrics, configurations and option meanings/correctness returned no differences. The 12 vocabulary records also matched the manifest. Lesson and assessment remained DRAFT with an 80% pass threshold. This incident is recorded explicitly rather than describing all earlier review attempts as read-only.
