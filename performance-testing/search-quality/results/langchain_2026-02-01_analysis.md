# Search Quality Benchmark — LangChain Corpus Analysis

**Date:** 2026-02-01
**Run:** `results/langchain_2026-02-01_173702.json`
**Corpus:** LangChain framework (1,665 Python files, monorepo with core/langchain/partners packages)
**Comparison corpus:** Brief (55 Python files) — `results/2026-02-01_145607.json`

---

## Headline Results

| Metric | Keyword Only | Lite Embeddings | Delta |
|--------|-------------|----------------|-------|
| **MRR** | 0.575 | **0.737** | **+0.162** |
| Recall@5 | 0.600 | 0.800 | +0.200 |
| Hit Rate | 0.600 | 0.800 | +0.200 |
| Precision@5 | 0.144 | 0.160 | +0.016 |

**By tier (MRR):**

| Tier | Keyword | Lite | Delta |
|------|---------|------|-------|
| Code Terms (10 queries) | **1.000** | **1.000** | 0.000 |
| Natural Language (10 queries) | 0.341 | **0.617** | **+0.276** |
| Abstract (5 queries) | 0.195 | **0.453** | **+0.258** |

---

## Cross-Corpus Comparison: LangChain vs Brief

| Metric | Brief (55 files) | LangChain (1,665 files) |
|--------|-------------------|------------------------|
| **Keyword MRR** | 0.628 | 0.575 |
| **Lite MRR** | 0.747 | 0.737 |
| **Lite vs Keyword delta** | +0.119 | **+0.162** |

**By tier — Keyword MRR:**

| Tier | Brief | LangChain |
|------|-------|-----------|
| Code Terms | 0.850 | **1.000** |
| Natural Language | 0.617 | 0.341 |
| Abstract | 0.207 | 0.195 |

**By tier — Lite MRR:**

| Tier | Brief | LangChain |
|------|-------|-----------|
| Code Terms | 0.925 | **1.000** |
| Natural Language | 0.838 | 0.617 |
| Abstract | 0.209 | **0.453** |

---

## Per-Query Breakdown

Out of 25 queries:
- **10 queries improved** with lite embeddings vs keyword-only
- **1 query regressed** ("how to split documents into chunks" — keyword 0.143 → lite 0.000)
- **14 queries tied** (all 10 code-term queries + 4 others already correct)

### Where Lite Embeddings Beat Keyword

| Query | KW MRR | Lite MRR | Delta |
|-------|--------|----------|-------|
| "generate multiple search queries from one question" | 0.000 | **1.000** | +1.000 |
| "parse output into pydantic models" | 0.143 | **1.000** | +0.857 |
| "run chains in sequence with outputs feeding to inputs" | 0.000 | **0.500** | +0.500 |
| "store vectors in chroma database" | 0.500 | **1.000** | +0.500 |
| "conditional branching in runnable chains" | 0.125 | **0.500** | +0.375 |
| "evaluate model outputs against criteria" | 0.143 | **0.500** | +0.357 |
| "embed text into vectors" | 0.000 | **0.167** | +0.167 |
| "create tools that accept structured arguments" | 0.000 | **0.167** | +0.167 |
| "provide dynamic examples in prompts" | 0.333 | **0.500** | +0.167 |
| "add metadata and track individual documents" | 0.000 | **0.100** | +0.100 |

### Where Keyword Beat Lite

| Query | KW MRR | Lite MRR | Delta |
|-------|--------|----------|-------|
| "how to split documents into chunks" | 0.143 | 0.000 | -0.143 |

The one regression: keyword found `character.py` at position 7 (outside k=5 but scored via MRR), while lite found related text-splitter files (html, base, markdown) but not `character.py`. The word "split" plus "chunks" matched HTML and markdown splitters more strongly in the embedding space.

### Queries Both Configs Miss (hit=False)

| Query | Tier | Expected | Best Result |
|-------|------|----------|-------------|
| "how to split documents into chunks" | natural_language | character.py | html.py (close, wrong file) |
| "question answering over documents" | natural_language | retrieval_qa/base.py | vectorstores/base.py (different layer) |
| "embed text into vectors" | natural_language | embeddings/embeddings.py | vectorstores/base.py (consumer not provider) |
| "add metadata and track individual documents" | abstract | documents/base.py | callbacks/base.py (wrong domain) |
| "create tools that accept structured arguments" | abstract | tools/structured.py | tools/base.py (parent class, close) |

---

## What These Results Mean

### Finding 1: Embeddings matter MORE on larger corpora

The lite embeddings improvement over keyword is **+0.162 MRR on langchain vs +0.119 on Brief**. This confirms our earlier hypothesis: on a small corpus (55 files), keyword search often gets lucky because there's less ambiguity. On a 1,665-file corpus, there are many more competing files with similar names, and semantic similarity from embeddings helps disambiguate.

### Finding 2: Keyword search degrades on natural language queries at scale

Keyword natural language MRR dropped from **0.617 on Brief → 0.341 on langchain**. With 30x more files, keyword search increasingly returns files that contain the right words but aren't the right files (e.g., "question answering" → vectorstores/base.py instead of retrieval_qa/base.py). This is the disambiguation problem.

### Finding 3: Lite embeddings substantially improve natural language and abstract queries

On langchain:
- Natural language: keyword 0.341 → lite **0.617** (+0.276)
- Abstract: keyword 0.195 → lite **0.453** (+0.258)

These are the exact query types that real users will use. Nobody searches their codebase for "BaseChatModel" — they search for "how to run chains in sequence" or "evaluate model outputs."

### Finding 4: Code term queries are solved — perfect 1.000 on both

This is expected: if you search for "ChatPromptTemplate" on a codebase that has a file with that exact class name, any search method will find it. Code term queries are the easy case and don't differentiate search approaches.

### Finding 5: Lite descriptions work well for search on large corpora

Lite descriptions (AST-derived, zero LLM cost) achieved **MRR 0.737** on a 1,665-file codebase. This validates the approach of using lite descriptions as the default setup path. The delta from keyword (+0.162) is meaningful and consistent.

---

## Comparison with Brief Analysis Conclusions

Our earlier Brief-corpus analysis said:
> "Lite descriptions are sufficient for file discovery"

The langchain results **strengthen this conclusion**. On a larger, more complex corpus:
- Lite embeddings provide a larger improvement over keyword-only (+0.162 vs +0.119)
- The improvement is concentrated in natural language and abstract tiers where real users search
- Code terms are already perfect, so embeddings add value exactly where it's needed

The earlier analysis also said:
> "This benchmark likely understates the value of both embeddings and LLM descriptions"

This is confirmed: the langchain corpus shows a **36% larger MRR improvement** from lite embeddings than the Brief corpus did.

---

## What We Still Don't Know

### 1. Would full LLM descriptions help more at this scale?

We only ran keyword-only and lite-embeddings on langchain (no full LLM descriptions because generating them for 1,665 files would cost ~$5-15 and take significant time). On the Brief corpus, the full vs lite delta was negligible (+0.002 MRR). At this scale, the gap might widen — particularly for abstract queries where the lite descriptions scored 0.453. Richer LLM descriptions capturing *what problems the code solves* could push this higher.

### 2. What happens beyond 5,000 files?

LangChain at 1,665 files is a medium-sized codebase. Production codebases at 5,000-10,000+ files would create even more ambiguity. The trend suggests embeddings would become increasingly important.

### 3. Context output quality

This test still only measures file discovery ranking. When the agent receives the search results, the context package from lite descriptions ("class MultiQueryRetriever, methods: ...") is less informative than what full LLM descriptions would provide ("Uses an LLM to generate multiple query variations to improve retrieval recall over a base retriever"). This quality difference isn't captured here.

---

## Infrastructure Notes

- **Corpus size:** 1,665 Python files, 751 classes, 5,293 functions
- **Lite description generation:** 1,665 descriptions in ~4 seconds
- **Embedding generation:** 1,665 descriptions embedded via OpenAI text-embedding-3-small
- **Embedding cost:** ~$0.02
- **Total run time:** ~2 minutes (including embedding generation)
- **Parser fix required:** Brief's AST parser hit an IndexError on langchain's use of positional-only parameters (`/` in function signatures). Fixed by adding `posonlyargs` and `kwonlyargs` handling to `parser.py`.
- **Gitignore issue:** LangChain's `.gitignore` has `lib/` which Brief's `fnmatch`-based exclusion matched against `libs/`, excluding ALL source files. Worked around by disabling `use_gitignore` for this corpus. This is a known issue in Brief's exclude pattern matching.

---

## Recommendations

### Immediate (validated by this test)

1. **Use lite descriptions + embeddings as the default setup path.** Results on a 1,665-file codebase confirm this provides meaningful search improvement (+0.162 MRR) at near-zero cost.
2. **Fix the gitignore pattern matching bug.** The `fnmatch(path, "*pattern*")` approach is too greedy — `lib` shouldn't match `libs`. This will affect real users.
3. **Fix the parser for positional-only and keyword-only args.** Already fixed in this session; needs to be committed.

### Short-term

4. **Run full LLM descriptions on langchain** to get the 3-config comparison at scale. This is the one remaining question: does the lite/full gap widen on larger corpora?
5. **Add more abstract queries** (10-15 instead of 5) — the abstract tier shows the biggest improvement opportunity but has the smallest sample size.
6. **Test with pure semantic search** (no keyword blending) to isolate description quality from keyword signal.

### Medium-term

7. **Run agent-based performance tests** on langchain to measure context output quality, not just search ranking.
8. **Build a query generator** — use an LLM to generate benchmark queries from file descriptions to reduce hand-authoring bias.

---

## Appendix: Test Infrastructure

- **Benchmark tool:** `performance-testing/search-quality/runner.py`
- **Langchain queries:** `performance-testing/search-quality/benchmarks/langchain.json`
- **Brief queries:** `performance-testing/search-quality/benchmarks/brief.json`
- **Results index:** `performance-testing/search-quality/results/index.json`
- **Full results:** `results/langchain_2026-02-01_173702.json`
- **Keyword-only run:** `results/langchain_2026-02-01_172242.json`
- **Corpus .brief:** `~/experimental/langchain/.brief/`
- **Cost of this run:** ~$0.02 (OpenAI embeddings for 1,665 files)
