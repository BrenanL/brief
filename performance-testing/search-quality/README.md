# Search Quality Benchmark

Measures search result quality across different Brief configurations using benchmark queries with known expected results.

## Quick Start

```bash
# Run all configs (requires OPENAI_API_KEY for embedding configs)
python performance-testing/search-quality/runner.py run

# Run keyword-only (no API key needed)
python performance-testing/search-quality/runner.py run --configs keyword-only

# Run specific tiers
python performance-testing/search-quality/runner.py run --tiers code_terms natural_language
```

## Configurations

| Config | Search Method | Descriptions | Embeddings | API Key? |
|--------|--------------|-------------|------------|----------|
| `keyword-only` | keyword_search | None | None | No |
| `lite-embeddings` | hybrid_search | AST-derived (no LLM) | OpenAI | Yes |
| `full-embeddings` | hybrid_search | LLM-generated | OpenAI | Yes |

### Adding New Configurations

Edit `configs.py` and add an entry:

```python
"my-new-config": {
    "description": "What this tests",
    "search_fn": "hybrid",        # keyword, hybrid, or semantic
    "needs_descriptions": "lite",  # False, "lite", or "full"
    "needs_embeddings": True,
    "needs_api_key": True,
}
```

## Benchmark Queries

Queries are defined in `benchmark.json` organized by difficulty tier:

- **code_terms** (~10 queries): Direct code terminology that keyword search should handle
- **natural_language** (~10 queries): Natural language descriptions where semantic search helps
- **abstract** (~5 queries): Conceptual queries — the hardest tier

Each query has `expected` files — the files that should appear in top-k results.

### Adding New Queries

Add entries to the appropriate tier in `benchmark.json`:

```json
{
  "query": "your natural language query",
  "expected": ["src/brief/path/to/expected_file.py"],
  "notes": "Why this file should match"
}
```

## Metrics

- **Precision@k**: What fraction of top-k results are expected files
- **Recall@k**: What fraction of expected files appear in top-k
- **MRR**: Mean Reciprocal Rank — how high is the first correct result (1.0 = first position)
- **Hit Rate**: Did ANY expected file appear in top-k (binary per query, averaged)

## Results

Results are saved as timestamped JSON in `results/`. Compare two runs:

```bash
python runner.py compare results/2026-02-01_143000.json results/2026-02-02_100000.json
```

## Interpreting Results

- **MRR > 0.8**: Excellent — correct files consistently in top 1-2 positions
- **MRR 0.5-0.8**: Good — correct files usually in top 3-5
- **MRR < 0.5**: Needs improvement — correct files often ranked low or missing
- **Hit Rate < 0.8**: Significant coverage gap — many queries return no relevant files

The key comparison is **lite-embeddings vs keyword-only**: if lite descriptions provide a meaningful MRR improvement (>0.1), they're worth generating during setup. The **full-embeddings vs lite** delta shows the marginal value of LLM descriptions.

## Cost

~$0.01-0.02 per full run (OpenAI text-embedding-3-small for embeddings + query vectors).
Keyword-only config is free.

## Pytest Integration

Run as a pytest test (excluded from default test suite):

```bash
pytest -m search_quality -v -s
```
