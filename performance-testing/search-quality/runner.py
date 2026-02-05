#!/usr/bin/env python3
"""Search quality benchmark runner for Brief.

Measures search result quality across different configurations
(keyword-only, lite embeddings, full LLM embeddings) using a
set of benchmark queries with known expected results.

Supports multiple corpora — each corpus has its own benchmark file
and source .brief directory. Results are permanently archived with
a master index for tracking improvement over time.

Usage:
    python runner.py run                           # Run all configs on default corpus
    python runner.py run --corpus langchain         # Run on a specific corpus
    python runner.py run --configs keyword-only     # Run specific config
    python runner.py run --tiers code_terms         # Run specific tier
    python runner.py list-configs                   # Show available configs
    python runner.py list-queries                   # Show benchmark queries
    python runner.py list-queries --corpus langchain
    python runner.py compare results/a.json results/b.json
    python runner.py index                          # Show results index
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path so we can import brief
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Load .env if present (for API keys)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from scoring import aggregate_scores, score_query
from configs import CONFIGS

BENCHMARKS_DIR = Path(__file__).parent / "benchmarks"
RESULTS_DIR = Path(__file__).parent / "results"
INDEX_FILE = RESULTS_DIR / "index.json"

# Registry of known corpora — maps corpus name to its .brief directory
# Add new corpora here as they are set up
CORPUS_REGISTRY = {
    "brief": {
        "brief_path": PROJECT_ROOT / ".brief",
        "description": "Brief's own codebase (~55 Python files)",
    },
    "langchain": {
        "brief_path": Path.home() / "experimental" / "langchain" / ".brief",
        "description": "LangChain framework (~1600 source files)",
    },
}


def load_benchmark(corpus: str | None = None, benchmark_path: Path | None = None) -> dict:
    """Load benchmark queries from JSON file.

    Looks in benchmarks/ directory by corpus name, or uses explicit path.
    Falls back to legacy benchmark.json for backwards compatibility.
    """
    if benchmark_path is not None:
        with open(benchmark_path) as f:
            return json.load(f)

    if corpus is not None:
        corpus_path = BENCHMARKS_DIR / f"{corpus}.json"
        if corpus_path.exists():
            with open(corpus_path) as f:
                return json.load(f)
        raise FileNotFoundError(f"No benchmark file for corpus '{corpus}' at {corpus_path}")

    # Legacy fallback
    legacy_path = Path(__file__).parent / "benchmark.json"
    if legacy_path.exists():
        with open(legacy_path) as f:
            return json.load(f)

    raise FileNotFoundError("No benchmark file found. Specify --corpus or --benchmark.")


def check_brief_ready(source_brief: Path, config: dict, config_name: str) -> bool:
    """Check if source .brief has what this config needs.

    Returns True if ready, prints warnings and returns False if not.
    """
    if not source_brief.exists():
        print(f"  [{config_name}] ERROR: .brief not found at {source_brief}")
        return False

    if not (source_brief / "manifest.jsonl").exists():
        print(f"  [{config_name}] ERROR: No manifest. Run 'brief analyze all' first.")
        return False

    if config["needs_embeddings"]:
        if not (source_brief / "embeddings.db").exists():
            print(f"  [{config_name}] ERROR: No embeddings.db. Generate descriptions and run 'brief context embed' first.")
            return False

    return True


def run_search(config: dict, brief_path: Path, query: str, top_k: int = 10) -> list[dict]:
    """Run a search against a configured .brief directory."""
    search_fn = config["search_fn"]

    if search_fn == "keyword":
        from brief.retrieval.search import keyword_search
        return keyword_search(brief_path, query, top_k)
    elif search_fn == "hybrid":
        from brief.retrieval.search import hybrid_search
        return hybrid_search(brief_path, query, top_k)
    elif search_fn == "semantic":
        from brief.retrieval.search import semantic_search
        return semantic_search(brief_path, query, top_k)
    else:
        raise ValueError(f"Unknown search function: {search_fn}")


def run_benchmark(
    configs_to_run: list[str] | None = None,
    tiers_to_run: list[str] | None = None,
    corpus: str | None = None,
    benchmark_path: Path | None = None,
    source_brief: Path | None = None,
) -> dict:
    """Run the full benchmark and return results.

    Args:
        configs_to_run: List of config names, or None for all
        tiers_to_run: List of tier names, or None for all
        corpus: Corpus name (looks up benchmark and .brief path from registry)
        benchmark_path: Explicit path to benchmark JSON (overrides corpus)
        source_brief: Explicit path to .brief directory (overrides corpus)

    Returns:
        Full results dict with per-config, per-tier, and per-query scores
    """
    # Resolve corpus -> benchmark file and .brief path
    if corpus and source_brief is None:
        if corpus in CORPUS_REGISTRY:
            source_brief = CORPUS_REGISTRY[corpus]["brief_path"]
        else:
            print(f"WARNING: Corpus '{corpus}' not in registry, using default .brief path")

    benchmark = load_benchmark(corpus=corpus, benchmark_path=benchmark_path)
    corpus_name = benchmark.get("corpus", corpus or "unknown")
    k = benchmark.get("k", 5)

    if source_brief is None:
        source_brief = PROJECT_ROOT / ".brief"

    if not source_brief.exists():
        print(f"ERROR: Source .brief directory not found at {source_brief}")
        print("Run 'brief analyze all' first.")
        sys.exit(1)

    print(f"Corpus: {corpus_name}")
    print(f"Source: {source_brief}")

    # Filter configs
    if configs_to_run is None:
        configs_to_run = list(CONFIGS.keys())
    else:
        for c in configs_to_run:
            if c not in CONFIGS:
                print(f"ERROR: Unknown config '{c}'. Available: {', '.join(CONFIGS.keys())}")
                sys.exit(1)

    # Filter tiers
    all_tiers = benchmark["tiers"]
    if tiers_to_run is None:
        tiers_to_run = list(all_tiers.keys())
    else:
        for t in tiers_to_run:
            if t not in all_tiers:
                print(f"ERROR: Unknown tier '{t}'. Available: {', '.join(all_tiers.keys())}")
                sys.exit(1)

    # Collect all queries to run
    queries: list[dict] = []
    for tier_name in tiers_to_run:
        tier = all_tiers[tier_name]
        for q in tier["queries"]:
            queries.append({**q, "tier": tier_name})

    print(f"Running {len(queries)} queries across {len(configs_to_run)} configs")
    print(f"Tiers: {', '.join(tiers_to_run)}")
    print()

    # Run queries directly against the source .brief
    results = {}

    for config_name in configs_to_run:
        config = CONFIGS[config_name]

        if not check_brief_ready(source_brief, config, config_name):
            continue

        print(f"Running queries for: {config_name}")
        config_results = {"per_query": [], "by_tier": {}, "overall": {}}

        for q in queries:
            search_results = run_search(config, source_brief, q["query"], top_k=k * 2)
            result_paths = [r["path"] for r in search_results]

            scores = score_query(result_paths, q["expected"], k)
            config_results["per_query"].append({
                "query": q["query"],
                "tier": q["tier"],
                "expected": q["expected"],
                "got": result_paths[:k],
                **scores,
            })

        # Aggregate by tier
        for tier_name in tiers_to_run:
            tier_scores = [
                q for q in config_results["per_query"]
                if q["tier"] == tier_name
            ]
            config_results["by_tier"][tier_name] = aggregate_scores(tier_scores)

        # Overall aggregate
        config_results["overall"] = aggregate_scores(config_results["per_query"])

        results[config_name] = config_results
        print(f"  Done: {config_name} — MRR={config_results['overall']['mrr']:.3f}")
        print()

    # Build comparison deltas
    comparison = {}
    config_names = list(results.keys())
    for i in range(len(config_names)):
        for j in range(i + 1, len(config_names)):
            a_name, b_name = config_names[i], config_names[j]
            a_scores, b_scores = results[a_name]["overall"], results[b_name]["overall"]
            key = f"{b_name}_vs_{a_name}"
            comparison[key] = {
                metric: round(b_scores[metric] - a_scores[metric], 4)
                for metric in a_scores
            }

    return {
        "timestamp": datetime.now().isoformat(),
        "corpus": corpus_name,
        "corpus_description": benchmark.get("corpus_description", ""),
        "source_brief": str(source_brief),
        "k": k,
        "configs_run": list(results.keys()),
        "query_count": len(queries),
        "tiers_run": tiers_to_run,
        "results": results,
        "comparison": comparison,
    }


def print_results(data: dict) -> None:
    """Print formatted results table to console."""
    results = data["results"]
    configs = data["configs_run"]

    print()
    print(f"Search Quality Benchmark Results — {data['timestamp'][:16]}")
    print(f"Corpus: {data['corpus']} | Queries: {data['query_count']} | k={data['k']}")
    print("=" * 70)
    print()

    # Header
    col_width = 16
    header = f"{'':25s}"
    for c in configs:
        # Shorten config names for display
        short = c.replace("-embeddings", "-embed").replace("-only", "")
        header += f"{short:>{col_width}s}"
    print(header)
    print("-" * (25 + col_width * len(configs)))

    # Overall
    print("OVERALL")
    for metric in ["precision@5", "recall@5", "mrr", "hit_rate"]:
        row = f"  {metric:23s}"
        for c in configs:
            val = results[c]["overall"][metric]
            row += f"{val:>{col_width}.3f}"
        print(row)

    print()
    print("BY TIER")
    tiers = data["tiers_run"]
    for tier in tiers:
        display_name = tier.replace("_", " ").title()
        row = f"  {display_name:23s}"
        for c in configs:
            val = results[c]["by_tier"].get(tier, {}).get("mrr", 0)
            row += f"{val:>{col_width}.3f}"
        print(row)

    # Deltas
    if data.get("comparison"):
        print()
        print("DELTAS (MRR)")
        for key, deltas in data["comparison"].items():
            delta_mrr = deltas["mrr"]
            sign = "+" if delta_mrr >= 0 else ""
            print(f"  {key:23s} {sign}{delta_mrr:.3f}")

    print()
    print("=" * 70)

    # Per-query failures (queries where best config still missed)
    print()
    print("MISSED QUERIES (hit=False in all configs):")
    all_queries = set()
    for c in configs:
        for q in results[c]["per_query"]:
            all_queries.add(q["query"])

    missed_count = 0
    for query in sorted(all_queries):
        all_miss = True
        for c in configs:
            for q in results[c]["per_query"]:
                if q["query"] == query and q["hit"]:
                    all_miss = False
                    break
        if all_miss:
            missed_count += 1
            # Find what was expected vs got
            for q in results[configs[0]]["per_query"]:
                if q["query"] == query:
                    print(f"  [{q['tier']}] \"{query}\"")
                    print(f"    Expected: {q['expected']}")
                    print(f"    Got:      {q['got'][:3]}")
                    break

    if missed_count == 0:
        print("  (none)")


def save_results(data: dict, output_dir: Path | None = None) -> Path:
    """Save results to a corpus-prefixed timestamped JSON file and update index."""
    if output_dir is None:
        output_dir = RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    corpus = data.get("corpus", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_path = output_dir / f"{corpus}_{timestamp}.json"

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    # Update the results index
    update_index(output_path, data)

    print(f"Results saved: {output_path}")
    return output_path


def load_index() -> dict:
    """Load the results index, creating it if it doesn't exist."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            return json.load(f)
    return {"runs": []}


def update_index(result_path: Path, data: dict) -> None:
    """Add a result to the index."""
    index = load_index()

    entry = {
        "file": result_path.name,
        "timestamp": data["timestamp"],
        "corpus": data.get("corpus", "unknown"),
        "corpus_description": data.get("corpus_description", ""),
        "configs_run": data["configs_run"],
        "query_count": data["query_count"],
        "tiers_run": data["tiers_run"],
        "summary": {},
    }

    # Add headline MRR per config
    for config_name, config_results in data.get("results", {}).items():
        overall = config_results.get("overall", {})
        entry["summary"][config_name] = {
            "mrr": overall.get("mrr", 0),
            "hit_rate": overall.get("hit_rate", 0),
        }

    index["runs"].append(entry)

    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def print_index() -> None:
    """Print the results index."""
    index = load_index()
    if not index["runs"]:
        print("No runs recorded in index.")
        return

    print(f"{'File':<45s} {'Corpus':<12s} {'Queries':>7s}  {'Configs + MRR'}")
    print("-" * 100)
    for run in index["runs"]:
        configs_str = "  ".join(
            f"{c}={run['summary'].get(c, {}).get('mrr', '?'):.3f}"
            if isinstance(run['summary'].get(c, {}).get('mrr', '?'), float)
            else f"{c}=?"
            for c in run["configs_run"]
        )
        print(f"{run['file']:<45s} {run['corpus']:<12s} {run['query_count']:>7d}  {configs_str}")


def compare_results(path_a: Path, path_b: Path) -> None:
    """Compare two result files and show deltas."""
    with open(path_a) as f:
        data_a = json.load(f)
    with open(path_b) as f:
        data_b = json.load(f)

    print(f"Comparing:")
    print(f"  A: {path_a.name} ({data_a['timestamp'][:16]})")
    print(f"  B: {path_b.name} ({data_b['timestamp'][:16]})")
    print()

    # Find common configs
    configs_a = set(data_a["configs_run"])
    configs_b = set(data_b["configs_run"])
    common = sorted(configs_a & configs_b)

    if not common:
        print("No common configs to compare.")
        return

    col_width = 16
    header = f"{'':25s}{'A':>{col_width}s}{'B':>{col_width}s}{'Delta':>{col_width}s}"
    print(header)
    print("-" * (25 + col_width * 3))

    for config in common:
        print(f"\n{config}")
        a_overall = data_a["results"][config]["overall"]
        b_overall = data_b["results"][config]["overall"]

        for metric in ["precision@5", "recall@5", "mrr", "hit_rate"]:
            a_val = a_overall.get(metric, 0)
            b_val = b_overall.get(metric, 0)
            delta = b_val - a_val
            sign = "+" if delta >= 0 else ""
            print(f"  {metric:23s}{a_val:>{col_width}.3f}{b_val:>{col_width}.3f}{sign}{delta:>{col_width - 1}.3f}")


def cmd_list_configs(args: argparse.Namespace) -> None:
    """List available configurations."""
    print("Available configurations:")
    print()
    for name, config in CONFIGS.items():
        emb = " (requires embeddings in .brief)" if config["needs_embeddings"] else ""
        print(f"  {name:25s} {config['description']}{emb}")


def cmd_list_queries(args: argparse.Namespace) -> None:
    """List benchmark queries."""
    corpus = getattr(args, "corpus", None)
    benchmark = load_benchmark(corpus=corpus)
    print(f"Corpus: {benchmark.get('corpus', 'unknown')}")
    for tier_name, tier in benchmark["tiers"].items():
        print(f"\n[{tier_name}] {tier['description']}")
        for q in tier["queries"]:
            expected_short = ", ".join(Path(p).name for p in q["expected"])
            print(f"  \"{q['query']}\"")
            print(f"    -> {expected_short}")


def cmd_run(args: argparse.Namespace) -> None:
    """Run the benchmark."""
    configs = args.configs if args.configs else None
    tiers = args.tiers if args.tiers else None
    corpus = getattr(args, "corpus", None)
    source_brief = Path(args.source_brief) if getattr(args, "source_brief", None) else None
    benchmark_path = Path(args.benchmark) if getattr(args, "benchmark", None) else None

    data = run_benchmark(
        configs_to_run=configs,
        tiers_to_run=tiers,
        corpus=corpus,
        benchmark_path=benchmark_path,
        source_brief=source_brief,
    )
    print_results(data)
    save_results(data)


def cmd_compare(args: argparse.Namespace) -> None:
    """Compare two result files."""
    compare_results(Path(args.file_a), Path(args.file_b))


def cmd_index(args: argparse.Namespace) -> None:
    """Show results index."""
    print_index()


def cmd_index_rebuild(args: argparse.Namespace) -> None:
    """Rebuild the index from existing result files."""
    rebuild_index()


def rebuild_index() -> None:
    """Rebuild index.json from all result JSON files in the results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    index = {"runs": []}

    for result_file in sorted(RESULTS_DIR.glob("*.json")):
        if result_file.name == "index.json":
            continue
        try:
            with open(result_file) as f:
                data = json.load(f)
            entry = {
                "file": result_file.name,
                "timestamp": data.get("timestamp", ""),
                "corpus": data.get("corpus", "unknown"),
                "corpus_description": data.get("corpus_description", ""),
                "configs_run": data.get("configs_run", []),
                "query_count": data.get("query_count", 0),
                "tiers_run": data.get("tiers_run", []),
                "summary": {},
            }
            for config_name, config_results in data.get("results", {}).items():
                overall = config_results.get("overall", {})
                entry["summary"][config_name] = {
                    "mrr": overall.get("mrr", 0),
                    "hit_rate": overall.get("hit_rate", 0),
                }
            index["runs"].append(entry)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Skipping {result_file.name}: {e}")

    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Index rebuilt with {len(index['runs'])} runs.")


def main():
    parser = argparse.ArgumentParser(
        description="Search quality benchmark for Brief",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    run_parser = subparsers.add_parser("run", help="Run benchmark")
    run_parser.add_argument(
        "--corpus",
        help="Corpus name (e.g. 'brief', 'langchain'). Looks up benchmark file and .brief path."
    )
    run_parser.add_argument(
        "--source-brief",
        help="Explicit path to .brief directory (overrides corpus registry)"
    )
    run_parser.add_argument(
        "--benchmark",
        help="Explicit path to benchmark JSON file (overrides corpus lookup)"
    )
    run_parser.add_argument(
        "--configs", nargs="+",
        help="Configs to run (default: all)"
    )
    run_parser.add_argument(
        "--tiers", nargs="+",
        help="Tiers to run (default: all)"
    )
    run_parser.set_defaults(func=cmd_run)

    # list-configs
    lc_parser = subparsers.add_parser("list-configs", help="List configurations")
    lc_parser.set_defaults(func=cmd_list_configs)

    # list-queries
    lq_parser = subparsers.add_parser("list-queries", help="List benchmark queries")
    lq_parser.add_argument("--corpus", help="Corpus name")
    lq_parser.set_defaults(func=cmd_list_queries)

    # compare
    cmp_parser = subparsers.add_parser("compare", help="Compare two result files")
    cmp_parser.add_argument("file_a", help="First results file")
    cmp_parser.add_argument("file_b", help="Second results file")
    cmp_parser.set_defaults(func=cmd_compare)

    # index
    idx_parser = subparsers.add_parser("index", help="Show results index")
    idx_parser.set_defaults(func=cmd_index)

    # index-rebuild
    idxr_parser = subparsers.add_parser("index-rebuild", help="Rebuild index from result files")
    idxr_parser.set_defaults(func=cmd_index_rebuild)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
