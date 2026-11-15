# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Vietnamese-speaking learners of Chinese, and administrators managing curriculum and learning materials. The user confirmed equal attention to self-study, reference reading, and administration for the redesign proposals.

## Product Purpose

Support structured Chinese study and reference reading through pronunciation lessons, HSK curricula, vocabulary, grammar, readings, exercises, assessments and saved progress. Current architecture and invariants are documented in [docs/architecture.md](docs/architecture.md).

## Operating Context

Learners choose an HSK level, study its lessons, work through vocabulary, grammar and readings, complete exercises and review results. Administrators manage lessons, assessments, users and source documents. The HSK selection flow is currently a local change awaiting an explicitly requested deployment.

## Capabilities and Constraints

The existing React/TypeScript/Vite frontend and FastAPI backend provide the implementation context. Preserve server-owned progression rules, account roles, learning records and assessment states. The student AI assistant and journey maps have been removed. Backend AI/evaluation modules remain, with document AI disabled on the deployed learning-only configuration. Teacher/classroom functionality remains a future proposal, not an active role.

The user approved the illustrated academy direction, readable fonts and larger text, and named the dragon Bo. Pronunciation covers initials, finals, tones and tone sandhi; completion unlocks HSK1, while HSK2/3 are independently selectable. Existing pronunciation graduates retain their valid completion. Server records govern progress and access. Lesson exercises pass at 80% by default; existing explicit thresholds remain authoritative. Do not add bookmarking, scheduling or analytics without a separate product request.

## Brand Commitments

The user chose Hanfolio as the public product name on 2026-11-11. Preserve an academic, trustworthy character with room for creativity, with Bo, Trúc and Bút as contextual learning companions.

## Evidence on Hand

README.md describes the Vietnamese-first product. frontend/src/app/router/routes.tsx lists public authentication, learner and administrator routes. Approved academy assets and self-hosted fonts are in frontend/public/academy. Bo guides learners, Trúc supports explanations and Bút supports practice. Textbook sources and checksums are documented in docs/learning-sources.md; local PDFs are not redistributed as public assets. Source notices remain documented without requiring source blocks in every lesson UI.

## Product Principles

- Balance daily self-study with clear access to learning material.
- Make curriculum position, available actions, and completion state understandable.
- Keep reviewed lesson content and optional machine-generated material distinguishable; never auto-publish AI drafts.
- Give administrators efficient tools consistent with the learner-facing identity.
