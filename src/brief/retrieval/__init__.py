"""Context retrieval system for Brief."""
from .context import (
    ContextPackage,
    get_file_description,
    get_file_context,
    build_context_for_file,
    build_context_for_query,
)
from .embeddings import (
    init_embeddings_db,
    store_embedding,
    get_embedding,
    get_all_embeddings,
    cosine_similarity,
    search_similar,
)
from .search import (
    keyword_search,
    hybrid_search,
)

__all__ = [
    "ContextPackage",
    "get_file_description",
    "get_file_context",
    "build_context_for_file",
    "build_context_for_query",
    "init_embeddings_db",
    "store_embedding",
    "get_embedding",
    "get_all_embeddings",
    "cosine_similarity",
    "search_similar",
    "keyword_search",
    "hybrid_search",
]
