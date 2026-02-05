"""Search quality benchmark configurations.

Each config defines a search method to test. The runner queries directly
against the source .brief directory — descriptions and embeddings must
already exist there before running.

Setup before running:
  1. brief init && brief analyze all     (creates manifest)
  2. Generate descriptions (lite or full) into .brief/context/files/
  3. brief context embed                  (creates embeddings.db)

Adding new configs is just adding entries to the CONFIGS dict.
"""

CONFIGS = {
    "keyword-only": {
        "description": "Keyword search on manifest data only (no embeddings)",
        "search_fn": "keyword",
        "needs_embeddings": False,
    },
    "hybrid": {
        "description": "Hybrid search (semantic + keyword) using whatever embeddings exist in .brief",
        "search_fn": "hybrid",
        "needs_embeddings": True,
    },
    "semantic-only": {
        "description": "Pure semantic search (embeddings only, no keyword blending)",
        "search_fn": "semantic",
        "needs_embeddings": True,
    },
}
