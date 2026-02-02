"""Scoring functions for search quality benchmarks."""


def precision_at_k(result_paths: list[str], expected: list[str], k: int = 5) -> float:
    """What fraction of top-k results are in the expected set.

    Args:
        result_paths: Ordered list of file paths from search results
        expected: List of expected file paths
        k: Number of top results to consider

    Returns:
        Fraction of top-k that are expected (0.0 to 1.0)
    """
    top_k = result_paths[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for p in top_k if p in expected)
    return hits / len(top_k)


def recall_at_k(result_paths: list[str], expected: list[str], k: int = 5) -> float:
    """What fraction of expected files were found in top-k.

    Args:
        result_paths: Ordered list of file paths from search results
        expected: List of expected file paths
        k: Number of top results to consider

    Returns:
        Fraction of expected files found (0.0 to 1.0)
    """
    if not expected:
        return 1.0
    top_k = set(result_paths[:k])
    hits = sum(1 for p in expected if p in top_k)
    return hits / len(expected)


def mrr(result_paths: list[str], expected: list[str]) -> float:
    """Mean Reciprocal Rank — how high is the first correct result.

    Args:
        result_paths: Ordered list of file paths from search results
        expected: List of expected file paths

    Returns:
        1/rank of first expected file found (0.0 if none found)
    """
    for i, path in enumerate(result_paths):
        if path in expected:
            return 1.0 / (i + 1)
    return 0.0


def hit_at_k(result_paths: list[str], expected: list[str], k: int = 5) -> bool:
    """Did ANY expected file appear in top-k.

    Args:
        result_paths: Ordered list of file paths from search results
        expected: List of expected file paths
        k: Number of top results to consider

    Returns:
        True if at least one expected file is in top-k
    """
    top_k = set(result_paths[:k])
    return any(p in top_k for p in expected)


def score_query(result_paths: list[str], expected: list[str], k: int = 5) -> dict:
    """Compute all metrics for one query.

    Args:
        result_paths: Ordered list of file paths from search results
        expected: List of expected file paths
        k: Number of top results to consider

    Returns:
        Dict with precision, recall, mrr, hit metrics
    """
    return {
        "precision": precision_at_k(result_paths, expected, k),
        "recall": recall_at_k(result_paths, expected, k),
        "mrr": mrr(result_paths, expected),
        "hit": hit_at_k(result_paths, expected, k),
    }


def aggregate_scores(query_scores: list[dict]) -> dict:
    """Aggregate scores across multiple queries.

    Args:
        query_scores: List of score dicts from score_query()

    Returns:
        Dict with averaged metrics
    """
    if not query_scores:
        return {"precision@5": 0.0, "recall@5": 0.0, "mrr": 0.0, "hit_rate": 0.0}

    n = len(query_scores)
    return {
        "precision@5": sum(s["precision"] for s in query_scores) / n,
        "recall@5": sum(s["recall"] for s in query_scores) / n,
        "mrr": sum(s["mrr"] for s in query_scores) / n,
        "hit_rate": sum(1 for s in query_scores if s["hit"]) / n,
    }
