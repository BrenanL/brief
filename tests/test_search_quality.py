"""Search quality benchmark tests.

These tests are excluded from the default pytest run because they require
an OpenAI API key and make API calls for embeddings.

Run with: pytest -m search_quality -v -s
"""
import json
import pytest
import sys
from pathlib import Path

# Add search-quality tool to path
SEARCH_QUALITY_DIR = Path(__file__).parent.parent / "performance-testing" / "search-quality"
sys.path.insert(0, str(SEARCH_QUALITY_DIR))

from scoring import precision_at_k, recall_at_k, mrr, hit_at_k, score_query, aggregate_scores


# ============================================================
# Unit tests for scoring (always run, no API key needed)
# ============================================================

class TestScoring:
    """Tests for scoring functions — no API key required."""

    def test_precision_perfect(self):
        results = ["a.py", "b.py", "c.py"]
        expected = ["a.py", "b.py"]
        assert precision_at_k(results, expected, k=3) == pytest.approx(2 / 3)

    def test_precision_none(self):
        results = ["x.py", "y.py"]
        expected = ["a.py"]
        assert precision_at_k(results, expected, k=2) == 0.0

    def test_recall_perfect(self):
        results = ["a.py", "b.py", "x.py"]
        expected = ["a.py", "b.py"]
        assert recall_at_k(results, expected, k=5) == 1.0

    def test_recall_partial(self):
        results = ["a.py", "x.py", "y.py"]
        expected = ["a.py", "b.py"]
        assert recall_at_k(results, expected, k=5) == 0.5

    def test_mrr_first(self):
        results = ["a.py", "b.py", "c.py"]
        expected = ["a.py"]
        assert mrr(results, expected) == 1.0

    def test_mrr_third(self):
        results = ["x.py", "y.py", "a.py"]
        expected = ["a.py"]
        assert mrr(results, expected) == pytest.approx(1 / 3)

    def test_mrr_miss(self):
        results = ["x.py", "y.py"]
        expected = ["a.py"]
        assert mrr(results, expected) == 0.0

    def test_hit_true(self):
        results = ["x.py", "a.py"]
        expected = ["a.py"]
        assert hit_at_k(results, expected, k=5) is True

    def test_hit_false(self):
        results = ["x.py", "y.py"]
        expected = ["a.py"]
        assert hit_at_k(results, expected, k=5) is False

    def test_aggregate(self):
        scores = [
            {"precision": 1.0, "recall": 1.0, "mrr": 1.0, "hit": True},
            {"precision": 0.0, "recall": 0.0, "mrr": 0.0, "hit": False},
        ]
        agg = aggregate_scores(scores)
        assert agg["precision@5"] == pytest.approx(0.5)
        assert agg["hit_rate"] == pytest.approx(0.5)


# ============================================================
# Benchmark tests (require API key, excluded by default)
# ============================================================

@pytest.mark.search_quality
class TestKeywordBaseline:
    """Keyword search quality — no API key needed for this config."""

    def test_keyword_code_terms_hit_rate(self):
        """Keyword search should find most code-term queries."""
        from runner import run_benchmark
        data = run_benchmark(
            configs_to_run=["keyword-only"],
            tiers_to_run=["code_terms"],
        )
        hit_rate = data["results"]["keyword-only"]["by_tier"]["code_terms"]["hit_rate"]
        assert hit_rate >= 0.7, f"Keyword hit rate on code terms too low: {hit_rate:.3f}"


@pytest.mark.search_quality
class TestLiteEmbeddings:
    """Lite embedding search quality — requires OPENAI_API_KEY."""

    def test_lite_improves_natural_language(self):
        """Lite embeddings should beat keyword on natural language queries."""
        from runner import run_benchmark
        data = run_benchmark(
            configs_to_run=["keyword-only", "lite-embeddings"],
            tiers_to_run=["natural_language"],
        )
        if "lite-embeddings" not in data["results"]:
            pytest.skip("OPENAI_API_KEY not set")

        kw_mrr = data["results"]["keyword-only"]["by_tier"]["natural_language"]["mrr"]
        lite_mrr = data["results"]["lite-embeddings"]["by_tier"]["natural_language"]["mrr"]
        assert lite_mrr >= kw_mrr, (
            f"Lite ({lite_mrr:.3f}) should beat keyword ({kw_mrr:.3f}) on natural language"
        )
