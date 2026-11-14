---
name: Chinese Learning
description: An illustrated academy for readable Vietnamese-first Chinese study.
colors:
  jade: "#296747"
  jade-hover: "#1e5338"
  pine: "#173f36"
  cinnabar: "#b73c34"
  cinnabar-hover: "#9f302a"
  paper: "#f3f5ee"
  ivory: "#fffef8"
  sage: "#edf2df"
  ink: "#243e34"
  ink-soft: "#37523b"
  muted: "#596f54"
  border: "#e3eae7"
  border-strong: "#b8cbc7"
  reading-border: "#dbe3d1"
  nav-active: "#e4edcf"
  nav-text: "#cadac4"
  focus-gold: "#a56c26"
  white: "#ffffff"
  success: "#17663b"
  success-soft: "#eef8f2"
  warning: "#8a5a12"
  warning-soft: "#fff9e9"
  danger: "#9d3434"
  danger-soft: "#fff1f1"
  info: "#066970"
  info-soft: "#e7f7f1"
typography:
  journey-plaque:
    fontFamily: "Noto Serif, serif"
    fontSize: "25px"
    fontWeight: 700
    lineHeight: 1
  headline:
    fontFamily: "Noto Sans, sans-serif"
    fontSize: "32px"
    fontWeight: 650
    lineHeight: 1.4
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Noto Sans, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Noto Sans, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.8
  reading:
    fontFamily: "Noto Sans, sans-serif"
    fontSize: "19px"
    fontWeight: 400
    lineHeight: 1.9
  control:
    fontFamily: "Noto Sans, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0em"
  hanzi:
    fontFamily: "Noto Sans SC, sans-serif"
    fontSize: "64px"
    fontWeight: 550
    lineHeight: 1.5
    letterSpacing: "0em"
  pinyin:
    fontFamily: "Noto Sans, sans-serif"
    fontSize: "23px"
    lineHeight: 1.7
rounded:
  sm: ".375rem"
  md: ".625rem"
  lg: ".875rem"
  pill: "999px"
spacing:
  "1": ".25rem"
  "2": ".5rem"
  "3": ".75rem"
  "4": "1rem"
  "6": "1.5rem"
  "8": "2rem"
  "12": "3rem"
components:
  button-primary:
    backgroundColor: "{colors.jade}"
    textColor: "{colors.white}"
    typography: "{typography.control}"
    rounded: "{rounded.md}"
    padding: ".55rem .9rem"
  button-primary-hover:
    backgroundColor: "{colors.jade-hover}"
  button-secondary:
    backgroundColor: "{colors.ivory}"
    textColor: "{colors.jade}"
    typography: "{typography.control}"
    rounded: "{rounded.md}"
    padding: ".55rem .9rem"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.jade}"
    typography: "{typography.control}"
    rounded: "{rounded.md}"
    padding: ".55rem .9rem"
  reading-card:
    backgroundColor: "{colors.ivory}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.lg}"
    padding: "25px"
  status-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success}"
    rounded: "{rounded.pill}"
    padding: "4px 9px"
  nav-current:
    backgroundColor: "{colors.nav-active}"
    textColor: "#214a34"
    rounded: "8px"
    padding: "12px"
---

# Design System: Chinese Learning

## Overview

**Creative North Star: "Bo's Illustrated Academy"**

A calm painted academy frames practical study. Pine navigation, pale paper and ivory reading surfaces make room for an expressive dragon named Bo. Local Noto Sans keeps Vietnamese explanations direct and comfortable; Noto Sans SC gives Chinese learning material a distinct, larger voice.

Illustration accompanies the task: Bo welcomes, guides and responds; Trúc explains; Bút supports practice. Reading surfaces remain quiet so the learner can distinguish a sound, Hanzi, pinyin, meaning and evidence. Public authentication and administration share the palette and type identity while retaining their existing workflows. This records the production academy adoption, not a comprehensive redesign of every administrative component.

**Key Characteristics:**

- Painted academy scenery with a contextual companion cast.
- Large Chinese learning content and adjustable Vietnamese reading text.
- Pine navigation, ivory reading cards and restrained tonal boundaries.
- Explicit progress, availability, source references and action states.

Implementation evidence: `frontend/src/styles/tokens.css`, the final overrides in `frontend/src/styles/academy.css`, imports in `frontend/src/index.css`, learner layout, academy components, pronunciation study and lesson theory sections. The approved production direction is recorded separately in `.impeccable/surfaces/bo-production.md`.

The administration workspace extends this world through `frontend/src/styles/admin-dashboard.css` and the dashboard, statistics summary and statistics detail components. Its scoped direction is recorded in `.impeccable/surfaces/admin-workspace.md`. The library and authoring extension uses `frontend/src/styles/admin-library-studio.css`, `AdminLibrary`, `AuthoringSession`, `LessonContentSection` and `QuestionEditor`, with lesson and assessment editor navigation. Its approved scope is recorded in `.impeccable/surfaces/admin-library-studio.md`; it preserves the academy identity and dashboard management priority.

The contextual artwork extension is recorded in `.impeccable/surfaces/academy-visuals-vi.md`. It adds watercolor scenes, semantic outlined icons and activity companions across learner and administration surfaces, while keeping the incumbent identity and content workflows. Administration interface copy is Vietnamese; this presentation scope does not change authored content or public and learner interface copy.

## Colors

The palette takes its character from forest greens and warm reading paper, with a small cinnabar action accent.

### Primary

- **Jade** carries shared primary buttons, text controls and interaction cues; **Pine** anchors the navigation shell.
- **Jade Hover** darkens the shared primary action on hover.

### Secondary

- **Cinnabar** and **Cinnabar Hover** distinguish existing learner continuation and public authentication actions from ordinary green controls. The painted dashboard's resume action has a local earth-red treatment; it is not a second global primary palette.
- **Focus Gold** marks academy button, navigation and summary keyboard focus.

### Neutral

- **Paper** is the workspace ground; **Ivory** is the reading surface; **Sage** groups lesson and journey introductions.
- **Ink**, **Ink Soft** and **Muted** separate headings, reading text and supporting text.
- **Reading Border** outlines academy reading cards; the shared **Border** and **Border Strong** support tables, fields and other UI primitives.
- **Nav Text** and **Nav Active** provide the learner rail's resting and selected states. Admin rail foregrounds are explicitly adapted to the same pine ground.

Semantic success, warning, danger and information pairs communicate state alongside text. Keep these distinct from the illustrated world and preserve their existing meanings.

**The Quiet Page Rule.** Keep explanatory and vocabulary surfaces ivory or pale sage; place painted scenery in the surrounding academy and dedicated scene regions.

Within `.admin-shell.admin-academy-workspace`, the administration ground is warm paper (`#f4f3eb`) with decorative background pseudo-elements removed. Library cards and editing surfaces use near-ivory (`#fffef9`); sage groups filters, outlines and preview frames. Contextual watercolor scenes belong to compact page headers and category covers with quiet color variations; they identify lesson topics, practice or documents rather than depicting an uploaded file.

## Typography

**Display and Body Font:** locally served Noto Sans, with sans-serif fallback.
**Chinese Font:** locally served Noto Sans SC, with sans-serif fallback.

Both families ship under `frontend/public/academy/fonts`; retain Vietnamese accents, pinyin marks and full Chinese font coverage. The default UI body uses the frontmatter body role. The headline and title roles describe the recurring academy hierarchy; individual lesson headings keep their contextual sizes.

### Hierarchy

- **Headline:** page titles; mobile page titles usually reduce to 28px, with lesson titles at 26px.
- **Title:** section headings, generally 23–26px depending on context.
- **Reading:** explanations and expanded notes use `--reader-font-size`, selectable at 19, 21 or 23px. Reading line height is generally 1.85–1.9; vocabulary meanings use 1.8.
- **Control:** shared buttons retain the frontmatter control role and a 46px minimum height. Compact shell utilities have existing smaller variants; they do not set the reading scale.
- **Hanzi:** vocabulary identity; 58px at widths up to 1250px, 49px up to 600px and 43px up to 370px. Chinese examples use 30px on desktop and 26px on mobile.
- **Pinyin:** vocabulary pronunciation; 21px on mobile. It can be hidden by the learner's reading preference.
- Pronunciation study gives the current sound its own larger stage: 82px desktop, 67px mobile; the adjacent Hanzi example is 68px desktop and 56px mobile.

**The Chinese First Rule.** Make Hanzi the vocabulary entry's strongest text, followed by pinyin and Vietnamese meaning; keep the example and explanatory note adjacent when details expand.

The scoped administration workspace uses `Noto Sans, Noto Sans SC, sans-serif` at 16px/1.7. Its headings use the same family stack, and inputs, textareas, selects and buttons inherit it. Workspace fields use 16px/1.6; labels use 14px/1.6 at weight 600. Keep these administration overrides scoped. The student-style vocabulary preview gives Hanzi a 56px identity, followed by 18px pinyin and 17px meaning; the compact library quick glimpse uses 34px Noto Sans SC Hanzi beside its illustration.

## Layout

The learner workspace has a fixed pine rail (226px), a quiet topbar and a centered main area (maximum 1400px, 32px side gutters). At 1250px the rail narrows to 200px and gutters to 24px. At 800px the rail becomes a 78px icon rail. At 600px it gives way to a fixed four-item bottom navigation with safe-area padding, and the content uses 16px side gutters with room beneath it for navigation.

Wide dashboards pair the main academy scene with a narrow progress/context column. The columns stack at 1050px. Pronunciation similarly pairs a flexible study card with contextual help, then stacks at 1050px. Lesson reading uses a narrow section index beside one column of cards; the final index width is 125px, with English and Chinese labels deliberately stacked and kept whole. At 800px the index becomes a wrapping horizontal row.

The administration workspace uses a separate content-management layout: lessons and practice share an unequal row (2:1 above 1250px; 1.65:1 from 1001–1250px), followed by equal HSK and source-document panels, then a compact statistics strip. At 1000px and below, lessons and practice stack in document order; the secondary pair stays in two columns until 700px, then stacks. Panel gaps are 24px, reducing to 20px at 700px; panel padding steps from 26px to 22px at 1250px and 21px at 700px. The create-lesson action sits beside the page heading on wider screens and spans the heading's width at 700px and below. Preserve the same reading and keyboard order through reflow.

Administration libraries pair results with a 240?300px quick-preview column and a 24px gap inside a maximum 1600px container. Card results use two columns, reduce to one at 1250px, return to two when the preview stacks at 800px, and become one horizontal cover-and-copy row at 480px. A sole result also uses a horizontal card. Tables keep a labeled, keyboard-focusable horizontal scroll region. Quick previews are sticky on wide screens and enter document flow at 800px. Container gutters use `clamp(18px, 3vw, 44px)`, then 18px at 800px.

Authoring pairs a 200px outline with the selected content stage. The stage divides into editor and student preview at a 1.15:0.85 ratio with a 240px preview minimum. At 1250px the outline narrows to 160px and editor/preview stack; at 800px the outline becomes a wrapping row above the stage and explicit Edit/Preview controls choose the visible pane. Wider outlines and previews may be sticky; narrower layouts use document flow. Preserve the same mounted drafts through every pane and area switch.

Use the shared spacing scale for ordinary controls and component rhythm. Academy reading cards use contextual padding around 25–30px on desktop and 15–22px on mobile. Reading explanations cap near 70ch where the pronunciation card allows it. Keep `min-width: 0` on flexible text columns; allow long Hanzi entries to wrap without pushing the illustration beyond its available width.

Contextual page headers pair flexible copy with a 180px artwork column on desktop. The artwork region is 180×144px, with a 150px square scene and a 76px square companion overlapping its lower right corner. Actions occupy a separate full-width row beneath the copy and art. At 700px and below, use a 100px artwork column, a 96px scene and a 50px companion; at 440px and below, stack artwork, copy and actions in that order, preserving title and control wrapping. The administration dashboard heading uses its existing dedicated grid: its artwork is 164×132px, reducing to 120×112px at 1100px, when the create action moves to the following row; at 440px, art precedes copy and the create action.

Scene cells and word previews preserve a square aspect ratio without stretching or borrowing an adjacent atlas cell. Administration student-style word art is 144px wide with automatic height, a square aspect ratio and no inherited minimum height; the quick glimpse places a 92px square picture beside flexible Hanzi, pinyin and meaning. Topic scenes remain compact in covers and curriculum rows; they never set the reading column's width.

## Elevation & Depth

Reading cards are flat, using a fine border and pale tonal grouping. Depth belongs to overlays and small contextual speech surfaces. The reading settings popover uses `0 12px 28px #21422a16`; Bo's speech surface uses `0 5px 15px #22442a16`. Shared dialogs retain `--shadow-overlay`. The shared surface shadow remains available outside the flat academy reading cards.

**The Flat Reading Rule.** Preserve the academy lesson and pronunciation cards' shadow-free reading plane; use elevation to explain an overlay or contextual floating surface.

Bo's dashboard breathing motion is a gentle 5-second vertical cycle enabled only when reduced motion is not requested. Reduced motion disables animation, transitions and smooth scrolling throughout learner, public and admin shells. Motion never carries completion or availability by itself.

## Shapes

Corners are gently rounded: shared controls use the medium radius; reading cards use the large radius; status badges use pills. Academy scene regions use slightly larger corners, while one-pixel boundaries distinguish reading surfaces. The Chinese brand tile and illustrative surfaces belong to this academy's materials.

Companion sprite cells remain square, preserve their native proportions and opt out of cross-axis stretching. Word illustrations are square, use a restrained corner radius and occupy at most 42% of the entry identity row. Counting illustrations use an exact number of dots inside a pale panel.

## Components

### Buttons

Shared buttons are compact, clear and rounded. Primary is jade with white text; secondary is ivory with jade text and a border; ghost removes the ground and border; danger retains the semantic danger pair. Shared buttons use the frontmatter padding and a 46px minimum height. Disabled controls use reduced opacity (0.58) and a not-allowed cursor. Academy keyboard focus has a gold outline (3px, 4px offset); retain existing contextual focus behavior elsewhere until explicitly reconciled.

### Status badges

Pill labels show state with explicit words. Success, information, warning and danger use their semantic pairs; neutral uses a pale ground and border. The academy base badge is 14px with line height 1.6; progress-dense contexts have compact variants.

### Cards / Containers

Academy vocabulary and pronunciation cards use ivory, a fine reading border, the large radius and no shadow. Vocabulary cards keep Hanzi, pinyin, meaning, view state and a detail action together. Expanded examples and Trúc's note remain part of that same card. Pending saves and errors stay beside the action they concern.

### Inputs / Fields

Use existing labeled field primitives with a visible border, pale or white ground, rounded corners, a visible focus treatment and adjacent help/error text. Public authentication uses 18px input text with at least 50px height. Existing administration field variants retain their source behavior; the `.admin-shell.admin-academy-workspace` override uses 16px/1.6 inherited Noto text, a near-ivory field ground (`#fffefb`), dark text (`#253c32`) and a muted border (`#bcc8ba`). Textareas have a 96px minimum height and resize vertically. The scoped workspace focus treatment is a 3px earth-colored outline (`#a95b2b`) with a 3px offset. Do not turn the retained per-page field variants into a newly invented universal component.

### Administration management panels

Management panels are quiet, flat containers with a fine border and gently rounded corners (14px). Ivory panels support a pale sage lesson panel; restrained Bo artwork sits beside its heading (84px, then 74px at 1000px and 66px at 700px). Noto headings and body text carry the hierarchy without adding a display face. Divided content rows lead to management links anchored at the panel foot; a lesson draft's continuation action stays beside its identity and moves beneath it as space narrows. Long titles wrap within the panel.

Lesson previews show actual drafts without implying recency. Practice previews show actual exercise titles, explicit status and pass thresholds. Empty, loading and retry feedback belongs inside the affected panel; a failed request does not replace unrelated content. Create and generate actions open the existing forms. The bottom statistics strip is a small supporting summary with a link to `/admin/stats`; its standalone detail page retains a return to `/admin` and uses the same flat ivory containers.

### Administration library

Lessons, assessments and source documents share a card/table switch with explicit pressed states, a result total and a separate current-page count. A title button selects the quick summary; a separate action opens the canonical editor or document. Keep the effective selection within the current page of filtered results: retain a matching selected record or fall back to the first visible record, and omit the summary when no record is visible. Pagination stays outside this shared presentation. Selected cards use a green boundary; selected table rows use a pale sage ground, alongside the title button's pressed state.

Quick summaries use actual record context, status and details. The lesson glimpse fetches actual vocabulary and grammar, shows a supported exact-match word illustration when available, and keeps loading, retry and empty feedback beside the preview. Category covers remain decorative. Long identities wrap within flexible columns; a quiet summary never substitutes for the canonical editor.

### Administration authoring workshop

Vocabulary, grammar and assessment questions use an outline, one visible selected editor and a live student-style preview. Lesson metadata and associated exercises have separate workspace areas; assessment metadata is separate from the question workshop. Hide inactive areas and item editors while retaining their mounted state, so an unfinished edit survives item selection, metadata switches and mobile Edit/Preview switches within the current record session. This draft retention is in memory; leaving or reloading can discard unsaved work.

Each item has its own explicit save, adjacent status and error feedback. Save failures preserve the entered draft; a successful save updates that item's baseline without resetting other mounted drafts. The session notice reflects unsaved work across areas. Unsaved drafts protect route departure and browser unload, and disable lesson publication and assessment review/publication. Pending item saves disable the affected fields. Preserve existing API lifecycle, read-only, detachment and deletion restrictions.

Canonical vocabulary or grammar content and its lesson association are separate field groups. Explain that editing shared canonical content affects every use, while order, note and example belong to its lesson placement. Detachment removes the association and retains the canonical record.

Student-style previews read the current draft and identify unsaved changes. Vocabulary and grammar previews show their content hierarchy, supported illustrations, examples and notes. Question previews use the learner question renderer for all seven existing types, with local interactive answers and an explicit explanation that interactions do not save learning results. Keep answer keys, accepted answers and grading rubrics in the editor. Previewing has no learner progress, submission or publication side effects; it represents the selected content rather than a complete learner session.

### Navigation

The learner now lands directly in Giáo trình (`/pronunciation`); the sidebar/mobile bar contain Giáo trình and Hồ sơ. Legacy `/dashboard` redirects to the curriculum and `/companions` to the profile's `#companions` section. Keep the real resume action at the curriculum heading and preserve logout/account access. The cast introduction is a compact, collapsed native details section inside Profile rather than a standalone destination. Reuse landscape artwork only in whitespace; study and password surfaces stay opaque and readable.

The learner rail uses outlined SVG icons and text, with a pale selected row against pine. Hover lightens text and adds a muted green ground. Preserve an accessible label when the rail collapses to icons; mobile navigation keeps both icons and text. The account and logout controls remain separate from course progress.

### Student curriculum and illustrated ascent

**Current direction (11 November 2026):** the user removed the 2D Great Wall. The main curriculum is list-only; omit map selectors, map artwork and walking controls. Earlier map details below describe the retired version. Existing `?view=map` links open the ordinary lesson list. Retain the illustrated foundation subjects and content-specific lesson covers.

Use the same cloud cover/hold/reveal for entering study as for returning. `LessonEntryLink` preserves native modified/new-tab clicks, guards repeat clicks and follows the shared provider's reduced-motion and Escape behavior. Place Bo in the curriculum introduction (guide), empty search (think), measure-word usage notes (think), practice preparation (encourage), passed results (celebrate) and retry guidance (encourage); never float Bo over reading content. Native dashboard/sidebar appearances remain.

The approved academy prototype now governs the main local curriculum at `/pronunciation` and `/hsk/:hskLevel`. The default list uses individual illustrated lesson blocks, three columns on wide screens, two on medium screens and one on phones. Keep real titles and learning states legible below the image. Choose supported cover artwork from meaningful title topics; use a neutral book for unmatched, unpublished, planned and assessment entries. Do not infer artwork topics from lesson ordinal numbers.

The optional `?view=map` view uses the painted bird's-eye 2D Great Wall, with gates aligned to measured stone landings, Bo at the current unit and a watchtower leading to the next HSK. Progress ascends from bottom to top. Keep HSK/view selectors, locate and state legend; omit the list summary and scenic introductory banner in map mode. Use ordinary vertical scrolling, direct gate links and reduced-motion support, without the former 3D camera or walking controls. Retain the native pine sidebar and account actions.

The real curriculum and progress APIs determine all states and destinations. Keep pronunciation accessible and required for HSK 1 only; HSK 2 and HSK 3 remain independently selectable. Preserve periodic assessments in backend order. Unpublished, locked and planned entries cannot open content; they explain their state. Planned counts of 15/10/15 describe intended lesson slots, never published content or completed progress. Generated map and tower asset provenance remains alongside `academy-2d-v1` artwork; production code does not import prototype learning records or storage.

Show the curriculum learning sequence above the foundation subjects as a compact ordered guide: pronunciation, lesson theory (vocabulary, grammar, reading), then practice at 80% to advance. Mark pronunciation complete only from its API completion state. Make the pronunciation cover the primary starting point; measure words remain explicitly supplementary. Explain that HSK 2–3 can be selected directly. On phones the sequence reads vertically. This guide communicates existing progression rules without adding gates.

Shared action affordances use a stronger jade edge, clear opening arrows, visible keyboard focus and restrained hover lift for whole-card links. Primary actions are filled; secondary actions have a sage surface. Reading panels remain flat. Locked and unpublished cards retain their explanatory action but do not lift like available lessons. Keep text-only exceptions such as password recovery, and distinguish selected navigation from available actions. Respect reduced motion.

The list header uses two illustrated subject blocks for pronunciation and measure words, followed by HSK/view selectors, compact progress and search. Avoid the former large green progress panel. Full-scene covers from `curriculum-v2/covers.png` give the five current lesson subjects distinct imagery; preserve the 3:2 tile ratio and match by title topic rather than sequence. Unknown, unpublished and assessment content uses neutral study artwork. The measure-word subject is supplementary reading, freely accessible from every HSK: ten entries, clear Hanzi/pinyin, usage, phrases, example sentences, notes and phrase audio. Use “Mục n/10” for position without implying completion or changing HSK progress.

### Pronunciation study stage

The current sound and example occupy two columns in a pale inset stage. Tones use a geometric pitch diagram rather than a decorative image. Articulation guidance, the source disclosure and device-voice availability stay adjacent to the learning material. Three section states show initials, finals and tones; completion and the final finish action reflect API state. The frontend must preserve ordered section completion and the server-controlled HSK1 gate.

### Academy cast and vocabulary art

Current cast allocation: Bo leads/resumes and celebrates passed results; Trúc explains technical material including pronunciation, vocabulary, grammar and measure words; Bút handles practice preparation, active-question advice and retry feedback, with its happy pose for successful-review advice. Avoid replacing every helper with Bo or repeating mascots across the same reading area.

Bo has six expressions: welcome, guide, think, encourage, celebrate and rest. Trúc supports explanations; Bút supports practice, with a happy practice pose. Decorative appearances are hidden from assistive technology; meaningful appearances have contextual text alternatives. Keep lesson content and action labels understandable without the image.

Word art is keyed to exact supported words: 茶, 水, 书, 山, 人, 朋友, 口, 马, 女, 大, 白, 你好, 你, 好 and 不. The lesson-1 extension adds the three-cell `vocabulary-hsk1-extra.png` atlas for 你, 好 and 不. The numeral panels render exactly one, five or eight dots for 一, 五 and 八. Unsupported vocabulary receives no substitute picture. The incumbent scenery, cast and word-art assets remain in use alongside the contextual scene atlas; this does not imply that every curriculum entry is illustrated.

### Contextual scenes and semantic icons

The transparent `learning-scenes-v1` atlas is a 1536×1024 image with three columns and two rows of 512px square cells, read left to right and then top to bottom. Keep the exact slot mapping:

| Cell | Scene key | Subject | Background position |
| --- | --- | --- | --- |
| 0, top left | `greeting` | Two adult learners greeting in a courtyard | `0% 0%` |
| 1, top center | `family` | Family of three | `50% 0%` |
| 2, top right | `study` | Scholarly reading desk | `100% 0%` |
| 3, bottom left | `path` | Garden path and academy arch | `0% 100%` |
| 4, bottom center | `practice` | Exercise notebook and paper tiles | `50% 100%` |
| 5, bottom right | `library` | Library shelf and source documents | `100% 100%` |

Render each scene as a square background with `background-size: 300% 200%`. Lesson covers and curriculum lesson rows choose `greeting` only for titles matching chào, greeting, 你好 or giao tiếp, and `family` only for gia đình, family or 家庭. All other lesson titles use the neutral `study` scene. Assessment covers and curriculum assessment rows use `practice`; document covers use `library`. These identify topic or category and make no claim about uploaded contents.

The shared artwork context chooses `library` for document and history routes, `practice` for assessment routes, `path` for pronunciation, curriculum and HSK routes, and `study` otherwise. `PageHeader` receives this context by default; an explicit artwork or scene can override it, and `artwork={false}` omits it. Header artwork pairs the scene with Bút for practice, Trúc for library and Bo's guide pose otherwise. A real lesson completion can choose Bo's celebration pose; unfinished lessons use the thinking pose. Preserve explicit progress-based pose choices rather than deriving completion from the picture. Contextual empty states show a small scene with the actual empty-state text and action, without inventing records or progress. Scene and header decoration remain hidden from assistive technology.

Outlined native SVG icons carry semantic meaning beside visible headings: vocabulary uses a book, grammar a structure diagram, practice a checked exercise sheet, curriculum a path, source documents a library and history a clock. The academy SVG set uses a 24px view box, no fill, current-color strokes at 1.7px and round caps and joins; section icons sit in 44px tonal tiles. Keep labels available without the artwork or icon.

The unmodified generated source is `/academy/learning-scenes-v1.png`. The delivered `/academy/learning-scenes-v1.webp` is a lossless derivative preserving identical alpha; retain the original PNG, exact generation prompt in `learning-scenes-v1.prompt.txt` and source provenance in `learning-scenes-v1.provenance.json`. Preserve watercolor transparency without thresholding, background removal or cropping into neighboring cells.

### Vietnamese administration presentation

Administration navigation, headings, labels, status names, question types, confirmations, errors, upload controls and local question-preview controls use Vietnamese. Shared status and date presentation lives in `frontend/src/features/admin/labels.ts`: map known API values to Vietnamese labels, retain unknown values rather than inventing a state, and show `—` for absent values. Format valid administration dates with `vi-VN`, medium date and short time; invalid dates show “Chưa xác định”. Keep API enums, payload fields, identifiers, lifecycle rules and authored lesson/source text unchanged. This scope also includes the administration logout label, while retaining the existing public and learner copy.

## Do's and Don'ts

### Do:

- **Do** keep Vietnamese explanations readable and Chinese content visually distinct with the locally served Noto families.
- **Do** preserve all three reading-size choices and the optional vocabulary pinyin preference.
- **Do** use Bo, Trúc and Bút according to their contextual roles and preserve sprite proportions.
- **Do** keep examples, notes, source references, save states and errors next to the material or action they explain.
- **Do** derive progress, completion and availability from the API; store only presentation preferences locally in the production academy.
- **Do** keep administration's lesson and practice actions ahead of supporting statistics, with real drafts and adjacent data-state feedback.
- **Do** keep library selection tied to the current result page and distinguish selecting a quick summary from opening its canonical editor.
- **Do** preserve mounted authoring drafts across item, area and mobile pane switches, with explicit per-item saves and honest unsaved preview labels.
- **Do** choose topic artwork only for supported title matches and use the reading desk as the neutral lesson fallback.
- **Do** keep scene and word-art cells square, preserve transparent edges and let narrow-screen header controls wrap beneath the content.
- **Do** present administration controls, status labels and dates in Vietnamese while preserving API values and authored content.

### Don't:

- **Don't** show an unrelated vocabulary picture or imply complete illustration coverage.
- **Don't** replace real completion or unlock rules with prototype sample progress.
- **Don't** reduce Chinese or Vietnamese font coverage to the prototype's limited subset.
- **Don't** promote legacy cascade artifacts, heading kickers, thick colored section stripes or inherited ornamental gradients into reusable academy rules.
- **Don't** treat the local textbook PDF as a public visual asset; keep concise source-page references visible in the lesson.
- **Don't** imply that category covers depict uploaded content, or that an administration preview records a learner result or publishes a draft.
- **Don't** apply the scoped administration workspace's typography, field or background overrides to learner and public surfaces.
- **Don't** infer completion from decorative scenes, translate authored lesson/source material automatically, or extend administration copy changes into public and learner surfaces.

Pronunciation study navigation: keep the four sections in one horizontal row above the workspace. Reserve the left column for a bounded, scrollable, grouped sound index (21 initials, 36 finals, 5 tones, 12 sandhi examples). Highlight the selected item and keep it visible within the index without scrolling the entire page. On phones the index sits above the reading panel, with two columns for short sounds and one column for sandhi phrases. Selecting an item previews it without writing progress; retain backend-owned sequential completion and return to the saved step through the primary action when previewing ahead. Keep existing audio sources unchanged.

Admin account directory: use the existing admin header and artwork, a labelled name/email search with explicit submit, role filter and a horizontally scrollable table on phones. Newest registrations come first; pagination remains server-owned. A dedicated detail route shows identity and stored learning activity. Keep this surface read-only: no password fields, delete controls or account mutations. Active status describes the account flag, not presence or last login.
