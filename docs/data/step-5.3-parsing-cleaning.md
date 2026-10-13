# Step 5.3 — Parsing & Cleaning

## Objective

Implement deterministic parsing and conservative cleaning over immutable raw sources.

## Why

Separating source acquisition from extraction and cleaning gives downstream transformation a reproducible, persisted input.

## Mental Model

```text
Raw Artifact
→ format parser
→ ordered extracted units
→ conservative cleaning
→ persisted Parsed/Cleaned Artifact
→ ParsedArtifactRef
```

## Core Knowledge

- Parsing, conservative cleaning, intermediate artifacts, source locators, parser and cleaning versioning, deterministic processing, stage lifecycle and data lineage are data engineering concepts used in this step.
- `RawArtifactRef` and `ParsedArtifactRef` are the typed boundary between raw storage, a specific parsing attempt and its output.
- `ParsingRun` stores lifecycle metadata in PostgreSQL. Parsed bytes live in the existing private `FileStorage`.
- Source locators retain PDF pages, DOCX body blocks/table rows, text blocks, Markdown blocks or stored Lesson fields.
- `basic_text_cleaning/v1` performs only technical normalization. It does not rewrite meaning.

## Concepts

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Parsing | DE | 5.3 | Extracts ordered content from stored raw source bytes. |
| Conservative Cleaning | DE | 5.3 | Removes technical noise without rewriting source meaning. |
| Intermediate Artifact | DE | 5.3 | Persists reproducible parsed input for the next stage. |
| Source Locator | DE | 5.3 | Preserves provenance to source pages, blocks, rows, or fields. |
| Parser Versioning | DE | 5.3 | Identifies parser behavior used for each run. |
| Cleaning Versioning | DE | 5.3 | Identifies cleanup behavior used for each run. |
| Deterministic Processing | DE | 5.3 | Produces equivalent artifact bytes for equivalent inputs and versions. |
| Stage Lifecycle | DE | 5.3 | Records parsing attempt status and safe failures. |
| Data Lineage | DE | 5.3 | Links raw source, ParsingRun, and parsed artifact. |
| Raw-to-Parsed Contract | BOTH | 5.3 | Gives Step 5.4 a specific persisted parsed artifact reference. |
| Unicode Normalization | SYSTEM | 5.3 | Applies deterministic NFC normalization to multilingual text. |
| Parser Abstraction | SYSTEM | 5.3 | Keeps format-specific extraction behind small parser boundaries. |
| Compensating Cleanup | SYSTEM | 5.3 | Deletes orphan parsed output after partial persistence failure. |

## Tools

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| PyMuPDF | DE | 5.3 | Extracts text by PDF page. |
| python-docx | DE | 5.3 | Reads DOCX body paragraphs and tables in source order. |
| PostgreSQL | DE | 5.3 | Persists ParsingRun lifecycle metadata and enforces constraints. |
| SQLAlchemy | DE | 5.3 | Maps and persists ParsingRun records. |
| Alembic | DE | 5.3 | Applies and verifies migration 0006. |
| Pydantic | SYSTEM | 5.3 | Validates typed artifact references. |
| Python `json` | SYSTEM | 5.3 | Serializes canonical parsed artifact JSON. |
| `unicodedata` | SYSTEM | 5.3 | Performs Unicode NFC normalization and control classification. |
| `importlib.metadata` | SYSTEM | 5.3 | Reads installed PyMuPDF and python-docx versions. |
| pytest | SYSTEM | 5.3 | Runs parser, lifecycle, schema, and regression tests. |
| uv | SYSTEM | 5.3 | Resolves parser dependencies and runs project commands. |

## Data Flow

### Document flow

The parser marks a Document `PROCESSING`, records a `ParsingRun`, reads immutable bytes through `FileStorage`, parses and cleans ordered units, writes deterministic JSON, and records `SUCCEEDED`. Success leaves the coarse Document status `PROCESSING`; later pipeline work owns readiness.

### Lesson snapshot flow

The parser reads only stored `raw_lesson_snapshot/v1` bytes. It does not reconstruct input from live Lesson, Vocabulary or Grammar rows.

### Success and failure

Each invocation creates a separate run. A failure records a stable error code and safe short detail, marks a Document `FAILED` when applicable, and leaves the raw artifact intact. If the parsed artifact was finalized but the success transaction fails, the service deletes the orphan artifact and makes a best effort to persist `FAILED`.

## Key Design Decisions

- One PostgreSQL `ParsingRun` per invocation; no current/latest/active run selection.
- `parsed_cleaned_artifact/v1` uses canonical compact UTF-8 JSON with sorted keys and no timestamps or run identifier.
- `ParsedArtifactRef` points to one run's immutable artifact.
- PDF uses PyMuPDF by page; DOCX uses python-docx while preserving body order and row cell order; TXT accepts UTF-8 and UTF-8 BOM; Markdown uses a narrow source scanner; Lesson uses the frozen stored snapshot.
- Every parser persists its identity/version. PyMuPDF and python-docx versions come from installed package metadata.
- Cleaning normalizes line endings, applies Unicode NFC, removes NUL and C0/C1 control characters except tab/newline, trims prose trailing whitespace, conservatively collapses excessive spaces/blank lines, and preserves code indentation and table delimiters.
- Source locators remain technical parser provenance, not Step-5.4 canonical Knowledge Blocks.
- Parsed files are stored separately from immutable raw files. Database transactions do not span parsing or file I/O.

## Reusable Approach

For another data pipeline, persist the raw input first, parse it through a format-specific boundary into ordered units with source locators, apply a versioned conservative cleanup, persist a deterministic intermediate artifact, and store lifecycle metadata separately. Return a specific artifact reference so a later stage can consume exactly that result.

## Common Mistakes

- Re-reading mutable source tables instead of the stored snapshot.
- Mixing extraction with semantic transformation.
- Flattening page/block provenance or changing source order.
- Over-cleaning multilingual text or code whitespace.
- Setting `PREVIEW_READY` before preview generation exists.
- Keeping parsed output only in memory or placing large JSON in lifecycle rows.
- Adding active/latest selection before a reprocessing policy exists.
- Deleting raw input when parsing fails.
- Holding a database transaction open during parsing or file I/O.

## Definition of Done

- `0006_parsing_runs` follows `0005_raw_document_metadata`, and the ORM matches it.
- PDF, DOCX, TXT, Markdown and stored Lesson snapshot parsing preserve ordered units and source locators.
- Cleaning and artifact serialization are deterministic and versioned.
- Parsing failures preserve raw files; partial finalization failures receive compensating cleanup.
- Focused parser, cleaning, service, migration/schema and full backend tests pass; Alembic reports head `0006_parsing_runs` with no schema drift.
