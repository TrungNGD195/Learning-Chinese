# Admin workspace layout — 2026-11-04

User approved direction1: prioritize Bài học and Luyện tập, place Lộ trình HSK and Tài liệu underneath, and make statistics secondary. Local application: http://127.0.0.1:5173/admin.

## Delivered behavior

- A single dashboard heading, Quản trị học liệu, and a create-lesson action opening the existing form directly.
- Primary2:1 lesson/exercise layout, actual lesson-draft continuation, real exercise titles/statuses/thresholds. Drafts are labeled drafts, not recent activity, because the existing endpoint exposes no update timestamps.
- Secondary curriculum/source-document sections using actual HSK metadata and document totals.
- Compact bottom statistics strip; detailed HSK table and aggregate data now live at `/admin/stats`, with a return link.
- Independent loading, empty, stale and failure states; errors do not remove the management actions. Empty draft copy does not imply no published lessons exist.
- Responsive primary collapse at1000px and secondary collapse at700px, matching DOM and keyboard order. Existing editor and publication behavior are retained.

## Evidence

- Initial full frontend suite:401passed. After the bounded review-copy correction, the73-test admin suite passed again. The final TypeScript/Vite build completed. Existing admin state-in-effect, verification-script lint and bundle-size warnings remain outside this layout change.
- `verification.json`:11full-page captures across1440/1024/768/390px, keyboard focus and200%equivalent layout zoom. Core views use actual local Docker backend data with a short-lived in-memory review cookie. Only the named empty/failure/long scenarios intercept read APIs. No JavaScript errors, horizontal overflow or mutation requests.
- Browser checks cover direct lesson creation, AI generation form, real draft continuation, statistics detail/return, task priority and recovery paths.
- Before/after layout detector returned `[]`; automatic hooks reported no deterministic quality issues. Existing academy raster assets are reused.
- Before captures document how the previous full statistics block pushed management links below the first viewport. Final images show the approved new order.
- Fresh finish review: one bounded empty-state copy correction, applied before the final recapture and verdict. Design-system documentation preserves the academy world and records the approved administration layout.

Deployment recreated only the frontend service. Backend records, draft publication states and learner progress were not modified.
