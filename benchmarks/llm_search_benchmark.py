"""Benchmark LLM search quality, latency, and cost across providers/models.

Usage:
    cd folio-api
    uv run python benchmarks/llm_search_benchmark.py

Outputs a markdown table comparing models on FOLIO ontology search.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from alea_llm_client import (
    AnthropicModel,
    GoogleModel,
    GrokModel,
    OpenAIModel,
    get_llm_kwargs,
)
from folio import FOLIO


@dataclass
class BenchmarkResult:
    provider: str
    model: str
    effort: str
    tier: str
    query: str
    latency_ms: float
    num_results: int
    top_result: str
    top_score: int | float
    all_results: list[tuple[str, int | float]]
    error: str | None = None


# Models to benchmark — (provider_class, model_name, effort, tier)
MODELS = [
    # OpenAI - GPT-5.x flagship
    (OpenAIModel, "gpt-5.4", "low", "flex"),
    (OpenAIModel, "gpt-5.4", "medium", "flex"),
    (OpenAIModel, "gpt-5.4", "high", "flex"),
    # OpenAI - GPT-5.x cheap/fast
    (OpenAIModel, "gpt-5-mini", None, None),
    (OpenAIModel, "gpt-5-nano", None, None),
    # OpenAI - GPT-4.x
    (OpenAIModel, "gpt-4.1-mini", None, None),
    (OpenAIModel, "gpt-4.1-nano", None, None),
    # Anthropic
    (AnthropicModel, "claude-sonnet-4-6", "low", None),
    (AnthropicModel, "claude-sonnet-4-6", "high", None),
    (AnthropicModel, "claude-haiku-4-5", None, None),
    # Google
    (GoogleModel, "gemini-3.1-pro-preview", "low", None),
    (GoogleModel, "gemini-3.1-pro-preview", "high", None),
    (GoogleModel, "gemini-3-flash-preview", "low", None),
    (GoogleModel, "gemini-3-flash-preview", "high", None),
    (GoogleModel, "gemini-2.5-flash", "low", None),
    # Grok
    (GrokModel, "grok-4-fast-non-reasoning", None, None),
    (GrokModel, "grok-4-fast-reasoning", None, None),
    (GrokModel, "grok-3-mini", None, None),
]

# Test queries covering different FOLIO domains
QUERIES = [
    "landlord tenant eviction",
    "intellectual property patent infringement",
    "employment discrimination wrongful termination",
    "securities fraud insider trading",
    "environmental regulation pollution",
]


def load_folio() -> FOLIO:
    """Load FOLIO ontology."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    return FOLIO(
        source_type=config["folio"]["source"],
        github_repo_owner=config["folio"]["repository"].split("/")[0],
        github_repo_name=config["folio"]["repository"].split("/")[1],
        github_repo_branch=config["folio"]["branch"],
        use_cache=True,
    )


async def benchmark_model(
    folio: FOLIO,
    model_cls,
    model_name: str,
    effort: str | None,
    tier: str | None,
    query: str,
    search_set: list,
) -> BenchmarkResult:
    """Run a single benchmark."""
    try:
        model = model_cls(model=model_name)
        kwargs = get_llm_kwargs(model, effort=effort, tier=tier)

        # Temporarily set the model and kwargs on folio
        folio.llm = model
        folio.llm_kwargs = kwargs

        start = time.perf_counter()
        results = await folio.search_by_llm(
            query=query,
            search_set=search_set,
            limit=5,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        all_results = [(cls.label, score) for cls, score in results]

        return BenchmarkResult(
            provider=model_cls.__name__.replace("Model", ""),
            model=model_name,
            effort=effort or "-",
            tier=tier or "-",
            query=query,
            latency_ms=elapsed_ms,
            num_results=len(results),
            top_result=all_results[0][0] if all_results else "(none)",
            top_score=all_results[0][1] if all_results else 0,
            all_results=all_results,
        )
    except Exception as e:
        return BenchmarkResult(
            provider=model_cls.__name__.replace("Model", ""),
            model=model_name,
            effort=effort or "-",
            tier=tier or "-",
            query=query,
            latency_ms=0,
            num_results=0,
            top_result="",
            top_score=0,
            all_results=[],
            error=str(e)[:80],
        )


async def run_benchmarks():
    print("Loading FOLIO ontology...")
    folio = load_folio()
    search_set = folio.get_areas_of_law()
    print(f"Loaded {len(folio.classes)} classes, {len(search_set)} areas of law\n")

    results: list[BenchmarkResult] = []

    for model_cls, model_name, effort, tier in MODELS:
        for query in QUERIES:
            provider = model_cls.__name__.replace("Model", "")
            effort_str = effort or "-"
            print(f"  {provider:>10} {model_name:<30} effort={effort_str:<6}  query={query[:40]}...", end="", flush=True)

            result = await benchmark_model(
                folio, model_cls, model_name, effort, tier, query, search_set
            )
            results.append(result)

            if result.error:
                print(f"  ERROR: {result.error[:50]}")
            else:
                print(f"  {result.latency_ms:>6.0f}ms  {result.num_results} results  top: {result.top_result}")

        print()  # blank line between models

    # Print summary table
    print("\n" + "=" * 120)
    print("SUMMARY: Average across all queries")
    print("=" * 120)

    # Group by model
    model_groups: dict[str, list[BenchmarkResult]] = {}
    for r in results:
        key = f"{r.provider}|{r.model}|{r.effort}|{r.tier}"
        model_groups.setdefault(key, []).append(r)

    print(f"\n| {'Provider':<12} | {'Model':<30} | {'Effort':<6} | {'Tier':<8} | {'Avg ms':>8} | {'Avg Results':>11} | {'Errors':>6} |")
    print(f"|{'-'*14}|{'-'*32}|{'-'*8}|{'-'*10}|{'-'*10}|{'-'*13}|{'-'*8}|")

    for key, group in model_groups.items():
        provider, model, effort, tier = key.split("|")
        successes = [r for r in group if r.error is None]
        errors = len(group) - len(successes)

        if successes:
            avg_ms = sum(r.latency_ms for r in successes) / len(successes)
            avg_results = sum(r.num_results for r in successes) / len(successes)
        else:
            avg_ms = 0
            avg_results = 0

        print(f"| {provider:<12} | {model:<30} | {effort:<6} | {tier:<8} | {avg_ms:>7.0f}ms | {avg_results:>11.1f} | {errors:>6} |")

    # Print detailed results per query
    print(f"\n\n{'=' * 120}")
    print("DETAILED: Results per query")
    print("=" * 120)

    for query in QUERIES:
        print(f"\n### Query: \"{query}\"")
        print(f"| {'Provider':<12} | {'Model':<30} | {'Effort':<6} | {'ms':>7} | {'Results':<50} |")
        print(f"|{'-'*14}|{'-'*32}|{'-'*8}|{'-'*9}|{'-'*52}|")

        query_results = [r for r in results if r.query == query]
        for r in query_results:
            if r.error:
                result_str = f"ERROR: {r.error[:45]}"
            else:
                result_str = ", ".join(f"{label}({score})" for label, score in r.all_results[:3])
                if len(result_str) > 50:
                    result_str = result_str[:47] + "..."
            print(f"| {r.provider:<12} | {r.model:<30} | {r.effort:<6} | {r.latency_ms:>6.0f}ms | {result_str:<50} |")


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
