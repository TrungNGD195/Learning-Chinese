# Step 6.6 — Context / Prompt Construction

## Objective

Convert successful, already-reranked Step-6.5 evidence into a deterministic, token-bounded, provider-independent `PromptPackage` without calling an LLM.

## Why

Retrieval and reranking decide relevance. Generation needs bounded evidence, trusted provenance, and a clear separation between system instructions, retrieved data, and the current user query. Keeping this logic outside provider code prevents a provider integration from silently changing RAG behavior.

## Mental Model

```text
Reranked evidence
→ whole-block packing
→ source labeling and provenance
→ provider-independent PromptPackage
→ Step 6.7 serialization and generation
```

## Core Knowledge

**MUST KNOW**

- Prompt capacity uses the injected model-token counter, never character count.
- Evidence blocks remain atomic; a block is included whole or omitted.
- Source labels are runtime-local and assigned only to selected evidence.
- System policy and retrieved data have different authority.
- `source_map` is trusted backend provenance, not model output.
- Empty retrieval differs from technical prompt-budget exhaustion.
- Frozen decision 6.6-D1 validates the base prompt before evaluating evidence state.

**SHOULD KNOW**

- Provider serialization adds token overhead supplied through `PromptBudget`.
- Step 6.7 supplies the real model-aware `TokenCounter` and budget.
- Greedy packing is deterministic but not globally token-optimal.

**AWARENESS ONLY**

- Semantic compression and MMR may be evaluated later.
- Conversation memory extends the prompt contract in Step 6.9.
- Citation behavior consumes `source_map` in Step 6.10.

## Data Flow

```text
query + reranked evidence + trusted learning context + budget
→ validate budget structure
→ count system, learning context, query, serialization overhead, and output reserve
→ reject base overflow as CONTEXT_BUDGET_EXHAUSTED
→ handle empty evidence as NO_RETRIEVAL_CONTEXT
→ greedily pack complete blocks in rerank order
→ assign contiguous S labels to selected blocks
→ build trusted source_map
→ PromptPackage
```

## Key Design Decisions

- Keep the package provider-independent; no provider or model is selected here.
- Validate `PromptBudget` structure, then validate the base token envelope before evidence-state handling (6.6-D1).
- Base prompt equal to the model input limit is valid; base prompt exceeding it returns `CONTEXT_BUDGET_EXHAUSTED`.
- Preserve successful Step-6.5 order and contiguous `rerank_rank` values.
- Do not add score thresholds or a semantic-rank fallback.
- Do not deduplicate, summarize, translate, compress, or truncate evidence.
- Continue packing later candidates after an oversized block.
- Assign source labels only to selected blocks and preserve provenance in an internal map.
- Keep all processing in memory, with no DB, persistence, network, or transaction dependency.
- Keep conversation history and citations out of this step.

## Reusable approach

```text
retrieve and rerank first
→ keep evidence selection separate from provider serialization
→ count with a target-model tokenizer boundary
→ preserve provenance alongside model-visible text
→ never let retrieved data become system authority
```

## Common mistakes

- Hard-coding a model context window in business logic.
- Treating characters as tokens.
- Truncating a chunk silently or stopping after one oversized block.
- Assigning labels before selection and leaving gaps.
- Logging queries, evidence, rendered prompts, or raw counter exceptions.
- Reconstructing provenance from generated prose.
- Mixing conversation history or citation output policy into this package.

## Definition of Done

- Frozen Step-6.6 contracts and test matrix are implemented.
- Focused tests, accepted regressions, full backend tests, compilation, and Alembic checks pass.
- No migration, persistent schema, or dependency changes are introduced.
- This Step Note reflects the implementation and used concepts/tools.
- The focused review ZIP is available for specialist review.
- Step 6.7 is not started.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Prompt Context Construction | AI | 6.6 | Converts selected RAG evidence into deterministic generation input. |
| Prompt Budget | AI | 6.6 | Separates model input capacity from reserved output and serialization costs. |
| Model-aware Token Counting | AI | 6.6 | Makes multilingual prompt capacity correct in model-token units. |
| Whole-block Greedy Packing | AI | 6.6 | Fits atomic evidence blocks without silent truncation. |
| Runtime Source Labels | BOTH | 6.6 | Links model-visible labels to trusted backend provenance. |
| Source Map | BOTH | 6.6 | Preserves citation-ready provenance separately from model prose. |
| Prompt Authority Separation | AI | 6.6 | Separates system instructions, retrieved data, and the current query. |
| Retrieved-content Prompt Injection Boundary | AI | 6.6 | Prevents instruction-like knowledge from becoming system authority. |
| Semantic Empty vs Technical Context Failure | BOTH | 6.6 | Distinguishes no evidence from budget/configuration failure. |
| Runtime DTO / Persistence Separation | SYSTEM | 6.6 | Keeps prompt construction out of persistent schema and DB transactions. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| Python | SYSTEM | 6.6 | Implements runtime DTOs, formatting, token-budget accounting, and packing. |
| pytest | SYSTEM | 6.6 | Runs deterministic unit and regression verification. |
