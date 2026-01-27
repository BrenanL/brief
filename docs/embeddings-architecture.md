# Embeddings Architecture

This document explains the relationship between `embeddings.db` and `.brief/context/files/` and when each is used.

## Overview

Brief uses two storage mechanisms for semantic content:

1. **`.brief/context/files/`** - Markdown files containing LLM-generated descriptions
2. **`.brief/embeddings.db`** - SQLite database containing vector embeddings for semantic search

These serve different purposes and are used at different stages of the workflow.

## Storage Structure

### Context Files (`context/files/`)

**Format**: Markdown files with naming pattern `path__to__file.py.md`

**Content**: Full LLM-generated descriptions including:
- Purpose (what the file does)
- Contents (classes, functions)
- Role (how it fits in the system)
- Dependencies and exports

**When written**:
- `brief describe file <path>` - generates single file description
- `brief describe batch` - generates descriptions for multiple files
- Auto-generation when context is requested (if enabled)

**When read**:
- `brief context get` - loads descriptions for context packages
- `brief describe file --show` - displays existing description
- Coverage reporting - checks which files have descriptions

### Embeddings Database (`embeddings.db`)

**Format**: SQLite database with schema:
```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    content_type TEXT NOT NULL,
    content_hash TEXT,
    embedding BLOB NOT NULL,  -- JSON-encoded float array
    metadata TEXT,
    created_at TIMESTAMP
)
```

**Content**: Vector embeddings (1536-dim for OpenAI text-embedding-3-small)

**When written**:
- `brief context embed` - generates embeddings for all descriptions
- `embed_file_description()` - embeds a single file's description

**When read**:
- `brief context search --mode semantic` - semantic similarity search
- `brief context search --mode hybrid` - combined keyword + semantic search

## Workflow

```
Source Files
     │
     ▼
┌────────────┐     ┌──────────────────┐
│  Analysis  │────▶│  manifest.jsonl  │  (AST parsing)
└────────────┘     └──────────────────┘
     │
     ▼
┌────────────┐     ┌──────────────────┐
│  Describe  │────▶│  context/files/  │  (LLM descriptions)
└────────────┘     └──────────────────┘
     │
     ▼
┌────────────┐     ┌──────────────────┐
│   Embed    │────▶│  embeddings.db   │  (Vector embeddings)
└────────────┘     └──────────────────┘
```

## Search Modes

| Mode | Uses Embeddings | Uses Descriptions | How It Works |
|------|-----------------|-------------------|--------------|
| `keyword` | No | Yes | Text matching in descriptions |
| `semantic` | Yes | No | Cosine similarity of embeddings |
| `hybrid` | Yes | Yes | Combines both, weights results |

## Cost Considerations

| Resource | Generation Cost | Regeneration Time |
|----------|-----------------|-------------------|
| manifest.jsonl | Free (local AST) | Fast |
| context/files/ | LLM API calls ($) | Medium |
| embeddings.db | Embedding API calls ($) | Fast once descriptions exist |

The `brief reset` command preserves expensive LLM content by default:
- Clears: manifest.jsonl, relationships.jsonl (cheap to rebuild)
- Preserves: context/files/, embeddings.db (expensive to regenerate)

## Current Gaps

1. **Embeddings not auto-generated**: Must run `brief context embed` manually after `describe batch`
2. **No incremental embedding updates**: Embed command regenerates all embeddings
3. **Single embedding per file**: Could benefit from per-function/class embeddings

## Future Improvements

1. Auto-embed when descriptions are generated
2. Incremental embedding updates (hash-based staleness check)
3. Finer-grained embeddings (class/function level)
4. Support for multiple embedding models

## Related Commands

```bash
# Generate descriptions
brief describe batch              # Generate all missing descriptions
brief describe file <path>        # Generate single description

# Generate embeddings
brief context embed               # Embed all descriptions

# Search
brief context search "query" --mode keyword   # Text search
brief context search "query" --mode semantic  # Vector search
brief context search "query" --mode hybrid    # Combined search

# Check status
brief coverage                    # See description coverage
brief config show                 # Check if embedding API available
```
