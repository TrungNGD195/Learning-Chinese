# Step 5.3 — Parsing & Cleaning

## Goal

Implement deterministic parsing and conservative cleaning for raw knowledge artifacts produced by Step 5.2.

The step must:

- select the correct parser for each supported raw format;
- extract text while preserving useful source structure;
- normalize technical text noise conservatively;
- preserve provenance-relevant boundaries such as PDF pages;
- validate and parse Raw Lesson Snapshots;
- persist a structured Parsed/Cleaned Artifact;
- record parser and cleaning versions;
- surface explicit parsing failures without deleting the raw source;
- provide a stable input for Step 5.4.

Do not implement document transformation, chunking, embedding, retrieval, or pipeline orchestration in this step.

---

# Supported Inputs

Support raw artifacts from Step 5.2:

```text
DOCUMENT
├── PDF
├── DOCX
├── TXT
└── MD

LESSON
└── deterministic Raw Lesson Snapshot JSON
```

Do not add:

```text
OCR
URL ingestion
HTML crawling
image captioning
VLM extraction
```

---

# Parser Abstraction

Use a parser boundary equivalent to:

```text
DocumentParser
├── PdfParser
├── DocxParser
├── TxtParser
└── MarkdownParser
```

The ingestion/parsing service should select the parser from the validated raw source type.

Do not put all format-specific logic into one giant conditional parser function.

Exact filenames/classes may differ if the same separation is preserved.

---

# PDF Parsing

Use:

```text
PyMuPDF
```

for text-based PDF extraction in V0.

Requirements:

- extract text by page;
- preserve page boundaries;
- retain source page numbers;
- do not flatten the whole PDF into one giant untraceable string;
- do not invoke OCR automatically;
- do not attempt complex layout reconstruction;
- do not add dedicated table-extraction frameworks.

If the PDF has no meaningful extractable text, return an explicit parsing failure.

---

# PDF Page Boundary

Parsed PDF output must preserve a mapping equivalent to:

```text
page_number
→ extracted text
```

This is required so later transformation/chunking/citation can remain source-traceable.

Do not remove page identity during parsing.

---

# No OCR

V0 does not support scanned-image OCR.

A practical scanned/no-text condition may be inferred when:

```text
PDF has pages
AND
extracted text is empty or near-empty
```

Return a stable failure equivalent to:

```text
NO_EXTRACTABLE_TEXT
```

Do not silently accept an empty parse result.

Do not add OCR libraries or OCR services.

---

# DOCX Parsing

Use:

```text
python-docx
```

for DOCX.

Preserve document order between:

```text
paragraph
table
paragraph
...
```

Do not parse:

```text
all paragraphs first
then all tables
```

because that destroys semantic order.

Preserve basic table structure:

```text
rows
cells
cell text
```

when practical.

Do not attempt pixel-perfect Word layout reconstruction.

---

# TXT Parsing

Canonical text output must be Unicode UTF-8.

Decode strategy:

```text
UTF-8
→ UTF-8 BOM handling
→ limited fallback detection if genuinely needed
```

Do not implement a large legacy-encoding compatibility system.

If decoding cannot be performed reliably:

```text
PARSING_FAILED
```

rather than silently persisting corrupted text.

---

# Markdown Parsing

Do not convert Markdown to HTML and then strip HTML.

Parse/preserve the original Markdown structure directly.

Preserve useful block-level meaning such as:

```text
heading
paragraph
list
code block when present
```

The parser representation may retain heading/block information for Step 5.4.

Do not render Markdown as a presentation concern.

---

# Raw Lesson Snapshot Parsing

Lesson parsing consumes the immutable/deterministic snapshot from Step 5.2.

Do not reread live Lesson/Vocabulary/Grammar database state as the source for this stage.

Flow:

```text
Raw Lesson Snapshot JSON
→ validate snapshot schema
→ preserve source ordering
→ clean textual fields
→ Parsed Lesson Artifact
```

The parser must reject malformed/incompatible snapshots explicitly.

---

# Cleaning Philosophy

Cleaning must be:

```text
deterministic
conservative
technical
non-semantic
```

The purpose is to remove extraction noise, not rewrite knowledge.

---

# Basic Text Cleaning

Apply safe normalization equivalent to:

```text
normalize line endings
remove null/control artifacts
trim trailing whitespace
collapse pathological repeated spaces
collapse excessive blank lines
```

Preserve:

```text
paragraph boundaries
heading boundaries
list boundaries
Chinese punctuation
meaningful spacing
source order
```

Do not collapse the whole document into one line.

---

# Unicode Normalization

Normalize extracted text using:

```text
Unicode NFC
```

Do not use NFKC globally by default.

The system contains Vietnamese, Chinese, and English text; normalization must not aggressively alter lexical content.

---

# No Linguistic Auto-correction

Do not automatically:

```text
fix Chinese grammar
correct typos
rewrite punctuation semantically
translate
convert Simplified ↔ Traditional
paraphrase
rewrite examples
```

Parsing/Cleaning must not modify source knowledge based on linguistic guesses.

---

# No LLM Cleaning

Do not send parsed source text to an LLM for cleanup/repair.

Reasons include:

- non-determinism;
- hallucination risk;
- source corruption;
- cost;
- reproducibility loss.

Cleaning must remain deterministic code.

---

# Header / Footer Policy

Do not aggressively remove repeated PDF headers/footers in V0.

Preserve extracted text by default.

Only introduce a conservative deterministic rule if there is a concrete verified pattern and it cannot reasonably delete content.

Do not add source-specific heuristics prematurely.

---

# Page Number Policy

Do not remove isolated numeric lines globally.

A number may represent:

```text
page number
exercise number
lesson number
quantity
content
```

Prefer preserving source text over deleting uncertain content.

---

# Hyphenation Policy

Do not apply aggressive universal end-of-line dehyphenation.

Only use a conservative transformation if extraction behavior is known to be reliable.

Avoid introducing rules that may corrupt Chinese-learning examples or mixed-language content.

---

# Images

Image-only knowledge is not extracted in V0.

If an image has a text layer/caption already extractable by the parser, that text may remain.

Do not implement:

```text
OCR
image captioning
VLM
diagram understanding
```

---

# Structured Parsed Artifact

Persist a common intermediate representation equivalent to:

```text
ParsedDocument
├── source_type
├── source_id
├── parser_name
├── parser_version
├── cleaning_strategy
├── cleaning_version
└── units[]
    ├── order
    ├── text
    └── source_locator
```

This is a parser/cleaning artifact.

It is not yet the canonical transformed Knowledge Document of Step 5.4.

---

# Source Locator

Preserve source-specific location information.

Equivalent examples:

```text
PDF
→ page_number

DOCX
→ document/block order
→ paragraph/table locator

TXT
→ logical block/order

MD
→ heading/block/order

LESSON
→ lesson field/content identity + order
```

Exact representation may be refined in Step 5.4, but Step 5.3 must not discard the information.

---

# Intermediate Persistence

Persist the Step 5.3 Parsed/Cleaned Artifact.

Do not keep it only in memory between Step 5.3 and Step 5.4.

Benefits:

- parser debugging;
- transformation can rerun without reparsing;
- stage-level failure isolation;
- reproducibility.

V0 may persist the structured artifact as JSON/text in ingestion storage rather than introducing an unnecessary complex relational schema.

Follow existing storage abstractions where practical.

---

# Raw Extracted Text Duplication

Do not persist a separate full uncleaned extracted-text artifact by default.

V0 flow:

```text
immutable Raw Artifact
→ parse
→ clean
→ persist Parsed/Cleaned Artifact
```

The immutable raw source remains available if parsing must be repeated.

Add another extraction artifact only if a concrete later debugging/evaluation requirement justifies it.

---

# Parser Version Tracking

Persist:

```text
parser_name
parser_version
```

for every parsed artifact.

Examples:

```text
pymupdf
<installed/versioned parser identifier>

python-docx
<installed/versioned parser identifier>
```

Do not hard-code parser identity only in source code with no persisted trace.

---

# Cleaning Version Tracking

Persist simple cleaning identity:

```text
cleaning_strategy
cleaning_version
```

Equivalent initial values:

```text
basic_text_cleaning
v1
```

Do not build a plugin/version-management framework.

The goal is only to make later reprocessing decisions reproducible.

---

# Determinism

For the same:

```text
raw artifact
parser version
cleaning version
```

the logical parsed output should be deterministic.

Do not include unstable timestamps/random IDs inside content comparison semantics unless required as artifact metadata.

---

# Parsing Status

Represent parsing lifecycle with states equivalent to:

```text
PENDING
PROCESSING
SUCCEEDED
FAILED
```

A background job system is not required.

The status represents stage outcome, not orchestration infrastructure.

---

# Parsing Failure

If parsing fails:

```text
Raw Artifact
→ remains intact
```

Persist:

```text
FAILED
error code / safe diagnostic metadata
```

Do not delete the raw source.

Do not activate downstream knowledge from a failed parse.

---

# Empty / Near-empty Output

A parser must not report success when meaningful source text cannot be extracted.

For PDFs with no useful extractable text, return a stable error equivalent to:

```text
NO_EXTRACTABLE_TEXT
```

For other unreadable/invalid sources, use stable parser errors following project error conventions.

---

# Retry / Re-run

Parsing must be re-runnable.

Provide a primitive equivalent to:

```text
parse(raw_artifact)
```

that does not depend on one-time transient state.

Do not implement an automatic retry scheduler here.

Step 5.6 and Step 5.7 determine orchestration/reprocessing policy.

---

# Table Handling

DOCX:

```text
preserve table row/cell content and source order
```

PDF:

```text
use the text ordering available from the selected parser
```

Do not add:

```text
Camelot
Tabula
OCR table extraction
special table ML models
```

solely for V0.

---

# Suggested Error Codes

Use the existing backend error contract.

Add stable codes where needed, equivalent to:

```text
PARSING_FAILED
NO_EXTRACTABLE_TEXT
UNSUPPORTED_PARSER
INVALID_LESSON_SNAPSHOT
TEXT_DECODING_FAILED
```

Do not expose raw library stack traces or internal exceptions to the client.

Persist safe internal diagnostics/logs according to existing backend practices.

---

# Suggested Module Boundaries

Equivalent structure:

```text
ingestion/
├── parsing/
│   ├── interface
│   ├── pdf
│   ├── docx
│   ├── txt
│   ├── markdown
│   └── lesson
├── cleaning/
│   └── basic
└── artifacts/
```

Exact filenames may differ.

Do not create a microservice for parsing.

---

# Tests

Add focused tests covering at least:

## Parser selection

- PDF selects PdfParser.
- DOCX selects DocxParser.
- TXT selects TxtParser.
- MD selects MarkdownParser.
- unsupported raw type fails explicitly.

## PDF

- text PDF extracts content successfully.
- page boundaries/page numbers are preserved.
- multiple pages remain ordered.
- near-empty/scanned PDF returns `NO_EXTRACTABLE_TEXT`.
- parser does not invoke OCR.
- raw source remains after failure.

## DOCX

- paragraphs preserve order.
- tables preserve row/cell content.
- paragraph/table interleaving remains in source order.

## TXT

- UTF-8 text parses correctly.
- UTF-8 BOM is handled.
- invalid/unreliable decoding fails explicitly.

## Markdown

- headings are preserved.
- paragraphs/lists preserve logical order.
- Markdown is not unnecessarily converted through HTML.

## Lesson

- valid Raw Lesson Snapshot parses successfully.
- malformed snapshot fails explicitly.
- parser reads snapshot rather than live lesson data.
- Vocabulary/Grammar ordering remains deterministic.

## Cleaning

- line endings normalize deterministically.
- Unicode is normalized to NFC.
- null/control noise is removed where defined.
- excessive blank lines are reduced.
- paragraph boundaries remain.
- Chinese punctuation/content is not rewritten.
- no linguistic correction occurs.

## Artifacts

- Parsed/Cleaned Artifact is persisted.
- parser name/version are recorded.
- cleaning strategy/version are recorded.
- source locators are retained.
- failed parsing does not produce a successful downstream artifact.
- rerunning with same input/version produces equivalent logical output.

---

# Out of Scope

Do not implement in Step 5.3:

```text
Document Transformation
canonical knowledge-document schema
metadata enrichment beyond parser/source locators
chunking
chunk size/overlap strategy
embedding
vector storage
semantic retrieval
filtering
reranking
prompt construction
LLM generation
OCR
image captioning
VLM
website parsing
URL crawling
automatic parser retry scheduling
pipeline orchestration
incremental/reprocessing policy
aggressive PDF layout reconstruction
specialized PDF table extraction
LLM text cleaning
linguistic correction
Simplified/Traditional conversion
```

---

# Acceptance Criteria

- [ ] Parser abstraction exists for PDF/DOCX/TXT/MD.
- [ ] PyMuPDF is used for text-based PDF parsing.
- [ ] python-docx is used for DOCX parsing.
- [ ] TXT output uses UTF-8-compatible Unicode handling.
- [ ] Markdown is parsed without unnecessary HTML conversion.
- [ ] Raw Lesson Snapshot is parsed independently of live Lesson state.
- [ ] PDF page boundaries are preserved.
- [ ] DOCX paragraph/table source order is preserved.
- [ ] Cleaning is deterministic and conservative.
- [ ] Unicode NFC normalization is applied.
- [ ] No linguistic auto-correction is performed.
- [ ] No LLM cleaning is used.
- [ ] No OCR/image/VLM extraction is added.
- [ ] Near-empty/scanned PDFs fail explicitly.
- [ ] Raw source survives parsing failure.
- [ ] Parsed/Cleaned Artifact is persisted.
- [ ] Source locators remain available.
- [ ] Parser name/version are persisted.
- [ ] Cleaning strategy/version are persisted.
- [ ] Parsing status distinguishes success/failure.
- [ ] Parsing is re-runnable.
- [ ] Step 5.4 can consume the persisted artifact without reparsing the raw source.

# Expected Deliverable

Parsing/Cleaning foundation plus documentation:

```text
docs/data/
└── step-5.3-parsing-cleaning.md
```

Next Step:

**Step 5.4 — Document Transformation**
