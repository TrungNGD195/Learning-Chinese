# Step 4.1 — Frontend Structure

## Objective

Establish the Vite React TypeScript single-page application, route tree, presentation layouts, and shallow product screens before API integration or detailed feature behavior.

## Why

Stable URL and layout boundaries let later feature work add behavior to the right screen without creating duplicate route families or moving backend responsibilities into React.

## Mental Model

```text
Browser
→ Router
→ Layout
→ Feature Page
```

Later, feature pages can consume frontend API/state layers while FastAPI remains authoritative for business rules, permissions, progression, grading, and AI behavior.

## Core Knowledge

- React Router Data Mode resolves client-side URLs into nested pages and shared layouts.
- `Outlet` composes page content inside the Public, Learner, or Admin presentation shell.
- Dynamic route parameters identify a structural screen; they do not supply or simulate domain data.
- Feature-oriented folders keep page structure near its product responsibility.
- Skeleton UI uses headings and reserved regions without fabricated learner or Admin state.
- Component tests verify rendered routes and visible behavior in jsdom.

## Data / UI Flow

```text
URL
→ Router match
→ Layout
→ Page component
```

Step 4.1 does not load backend data.

## Key Design Decisions

- D-027: Node.js `>=22.12`, npm, and `package-lock.json`, with a Vite React TypeScript application.
- D-028: React Router Data Mode using `createBrowserRouter()`, `RouterProvider`, and `Outlet`. `/` redirects to `/dashboard`; unknown paths render NotFoundPage. Learner navigation uses Dashboard, Learn (`/pronunciation`), Progress, History, and Profile. Lesson AI Chat stays inside the Lesson page.
- D-029: Vitest, jsdom, and React Testing Library test rendered route, layout, navigation, and screen behavior.
- Public, Learner, and Admin layouts are presentation-only. Admin routes stay beneath `/admin`.

## Reusable Approach

Bootstrap one SPA with a production route tree that can also be exercised through an in-memory router. Add a feature folder only when a real Step page or component lives there. Keep screen structure intentionally shallow until its implementation Step opens.

## Common Mistakes

- Moving authorization, progress, curriculum unlock, grading, or AI decisions into React.
- Adding unapproved routes such as `/learn` or standalone `/chat`.
- Creating empty architecture folders or API/state abstractions for later Steps.
- Installing future API, state, UI, or browser E2E tools before they are needed.
- Showing fabricated users, scores, progress, curriculum states, results, or chat messages.

## Definition of Done

The approved routes render under their intended layouts; structural screens remain free of fabricated data and feature behavior; route/component tests pass; and the production build and npm lockfile workflow work.

## Concepts Actually Used

| Concept | Category | Step | Role |
|---|---|---|---|
| Single Page Application | SYSTEM | 4.1 | One browser app resolves the product screens client-side. |
| Client-side routing | SYSTEM | 4.1 | Maps approved URL paths to React screens. |
| Nested routes | SYSTEM | 4.1 | Groups screens under shared layouts. |
| Layout | SYSTEM | 4.1 | Provides navigation and page shell through `Outlet`. |
| Route parameter | SYSTEM | 4.1 | Represents dynamic HSK, lesson, assessment, and attempt paths. |
| Feature-oriented structure | SYSTEM | 4.1 | Organizes code around product screen responsibilities. |
| Presentation vs business logic | SYSTEM | 4.1 | Keeps backend decisions authoritative. |
| Component composition | SYSTEM | 4.1 | Builds screens from layouts and small page regions. |
| Skeleton UI | SYSTEM | 4.1 | Defines visible screen areas without fake behavior or data. |
| Component testing | SYSTEM | 4.1 | Verifies rendered routes and user-visible structure. |

## Tools Actually Used

| Tool | Category | Step | Role |
|---|---|---|---|
| Node.js | SYSTEM | 4.1 | Frontend build and test runtime. |
| npm | SYSTEM | 4.1 | Dependency and lockfile workflow. |
| React | SYSTEM | 4.1 | UI component layer. |
| TypeScript | SYSTEM | 4.1 | Typed frontend implementation. |
| Vite | SYSTEM | 4.1 | SPA development and production build. |
| React Router | SYSTEM | 4.1 | Route tree, layouts, and navigation. |
| Vitest | SYSTEM | 4.1 | Frontend component test runner. |
| jsdom | SYSTEM | 4.1 | Browser-like DOM test environment. |
| React Testing Library | SYSTEM | 4.1 | Rendered user-facing component and route tests. |
