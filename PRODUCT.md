# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Vietnamese-speaking learners of Chinese, and administrators managing curriculum and learning materials. The user confirmed equal attention to self-study, reference reading, and administration for the redesign proposals.

## Product Purpose

Support structured Chinese study and reference reading through pronunciation lessons, an HSK curriculum, lesson content, exercises, assessments, progress/history, and a lesson-aware AI assistant.

## Operating Context

Learners resume their current learning step, study pronunciation and HSK lessons, work through vocabulary, grammar and exercises, ask lesson-related questions, and review assessment results. Administrators manage curriculum, lessons, assessments, and source documents.

## Capabilities and Constraints

The existing React/TypeScript/Vite frontend and FastAPI backend provide the implementation context. Preserve actual curriculum progression rules, account roles, learning records, source citations, and assessment states. AI chat already displays lesson/document/external citations; a visual redesign must keep these distinctions understandable.

The user approved the illustrated academy prototype for production on 2026-11-03, with more readable fonts and larger text, and named the dragon Bo. Adopt the approved layout in the main application. Teach initials, finals and tones from the local HSK1 textbook as an ordered prerequisite; completing all three sections and explicitly finishing the pronunciation lesson unlocks HSK1. Server records govern progress and access. No new search, bookmarking, scheduling, or analytics capability is confirmed.

## Brand Commitments

The user chose Hanfolio as the public product name on 2026-11-11. Preserve an academic, trustworthy character with room for creativity, with Bo, Trúc and Bút as contextual learning companions.

## Evidence on Hand

README.md describes the Vietnamese-first product. frontend/src/app/router/routes.tsx lists public authentication, learner, and administrator routes. The approved academy assets and locally served Noto Sans / Noto Sans SC fonts live under frontend/public/academy. Bo has six expressions, Trúc supports explanations, and Bút supports practice. docs/HSK1 3.0 Hanu 24.6.26.pdf supplies the pronunciation content; page references remain visible in lessons. The source PDF is not redistributed as a public asset.

## Product Principles

- Balance daily self-study with clear access to learning material.
- Make curriculum position, available actions, and completion state understandable.
- Keep source evidence and AI feedback distinguishable from authoritative lesson content.
- Give administrators efficient tools consistent with the learner-facing identity.
