# Context Package Ruleset

This document defines the rules and configuration for context package generation in Brief.

## Current Behavior

### File Retrieval Limits

**Current**: Variable based on search mode
- Hybrid search returns top 10 results by default
- Related files are unlimited (all imports/imported-by)

**Configurable**: `--limit` flag on search command

### Similarity Thresholds

**Current**: No threshold - returns top N by score
- Semantic search: cosine similarity (0-1 scale)
- Keyword search: BM25-style scoring

**Proposed**: Add minimum threshold option for precision over recall

### Query Expansion

**Current**: Single query passed directly to search
- No query rewriting or expansion
- No synonym generation

**Proposed for future**:
- LLM-based query expansion for ambiguous queries
- Generate 2-3 query variations and merge results

## Package Contents

### What We Return

| Content Type | Description | Source |
|--------------|-------------|--------|
| Primary files | Directly matching files | Search results |
| Related files | Import dependencies | relationships.jsonl |
| File descriptions | LLM-generated summaries | context/files/*.md |
| Function signatures | Code signatures | manifest.jsonl |
| Patterns | Remembered conventions | memory.jsonl |
| Contracts | Detected conventions | ContractDetector |
| Execution paths | Call flow traces | PathTracer |

### What We Don't Return (Yet)

| Content Type | Why Missing | Priority |
|--------------|-------------|----------|
| Code snippets | Size concern | Medium |
| Test files for matched code | Not implemented | Low |
| Similar files by structure | No structural similarity | Low |
| Change history | No git integration | Low |
| Related documentation | Doc search not integrated | Medium |

## Rendering Options

### Full Mode (default)
- Complete file descriptions
- Full signatures for undescribed files
- All patterns and contracts

### Compact Mode (`--compact`)
- File list with one-line summaries
- Section counts only
- Good for quick orientation

### Signature Control
- `--show-signatures`: Force signatures even with descriptions
- Default: Show signatures only when no description exists

## BLUF (Bottom Line Up Front) Implementation

**Current status**: Partial
- File descriptions now start with "WHEN to use" guidance (via optimized prompts)
- Package structure puts primary files first

**Proposed additions**:
1. Add executive summary at top of package:
   ```markdown
   ## Quick Summary
   - Most relevant file: src/foo.py (handles X)
   - Key classes: FooManager, BarHandler
   - Key functions: process_data(), validate_input()
   ```

2. Add table of contents for large packages:
   ```markdown
   ## Contents
   - 5 primary files (3 with descriptions)
   - 2 related files
   - 4 relevant patterns
   - 1 execution flow
   ```

## Configuration Options

### Current Configurable Settings

```json
{
  "auto_generate_descriptions": true
}
```

### Proposed Additional Settings

```json
{
  "context_package": {
    "max_primary_files": 10,
    "max_related_files": 20,
    "include_contracts": true,
    "include_patterns": true,
    "include_paths": true,
    "similarity_threshold": 0.3
  }
}
```

## Quality Verification

### Execution Path Validation

**Current**: Paths are generated from call graph analysis
- Static analysis only
- May not reflect runtime behavior

**Verification approaches**:
1. Mark paths as "static analysis" vs "runtime traced"
2. Add confidence scores based on call graph completeness
3. Flag paths that include unanalyzed files

### Relevance Scoring

**Current**: Based on search score only

**Proposed enhancements**:
1. Boost files that are frequently co-edited
2. Boost files that appear in related tasks
3. Penalize test files when not testing-related query

## Token Budget Management

The `--tokens` flag shows estimated token counts:
- Primary files: ~X tokens
- Related files: ~Y tokens
- Patterns: ~Z tokens
- Total: ~N tokens

**Proposed**: Token budget option
```bash
brief context get "query" --max-tokens 4000
```
Would truncate or omit sections to fit budget.

## Future Enhancements

### Priority 1 (Near-term)
- [ ] Executive summary at package top
- [ ] Configurable file limits
- [ ] Minimum similarity threshold

### Priority 2 (Medium-term)
- [ ] Query expansion via LLM
- [ ] Related documentation inclusion
- [ ] Token budget management

### Priority 3 (Longer-term)
- [ ] Structural similarity matching
- [ ] Test file association
- [ ] Change history integration

## Usage Examples

### Basic Query
```bash
brief context get "add user authentication"
```

### Limited Results
```bash
brief context get "auth" --limit 5
```

### Quick Overview
```bash
brief context get "database" --compact
```

### With Token Count
```bash
brief context get "api endpoints" --tokens
```

### Semantic Search Only
```bash
brief context search "handle errors gracefully" --mode semantic
```
