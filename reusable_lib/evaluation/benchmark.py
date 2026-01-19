"""
Model Benchmarking Framework

Run systematic evaluations across multiple models, prompts, and test cases.
Track performance over time and compare before/after fine-tuning.

Usage:
    from reusable_lib.evaluation import (
        ModelBenchmark,
        TestCase,
        TestSuite,
        ToolCallEvaluator
    )
    from reusable_lib.api import create_ollama_client

    # Create test suite
    suite = TestSuite("tool_routing")
    suite.add_case(TestCase(
        name="memory_store",
        prompt="Remember that my name is Bob",
        expected={"tool": "memory_store", "arguments": {"key": "name"}}
    ))

    # Run benchmark
    client = create_ollama_client()
    bench = ModelBenchmark(client)

    results = bench.run_suite(
        suite,
        models=["llama3:8b", "qwen2:0.5b", "phi3:mini"],
        evaluator=ToolCallEvaluator()
    )

    # Compare
    report = bench.compare_models(results)
    print(report.summary())
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from .evaluators import Evaluator, ToolCallEvaluator, EvaluationResult
from .metrics import (
    calculate_accuracy,
    calculate_latency_stats,
    aggregate_results,
    compare_metrics,
    AccuracyMetrics,
    LatencyMetrics
)

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """A single test case for evaluation."""
    name: str                           # Unique identifier
    prompt: str                         # User prompt to send
    expected: Any                       # Expected output (format depends on evaluator)
    system_prompt: Optional[str] = None  # Optional system prompt
    tags: List[str] = field(default_factory=list)  # For filtering/grouping
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestSuite:
    """Collection of test cases."""
    name: str
    description: str = ""
    cases: List[TestCase] = field(default_factory=list)
    default_system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_case(self, case: TestCase) -> None:
        """Add a test case to the suite."""
        self.cases.append(case)

    def add_cases(self, cases: List[TestCase]) -> None:
        """Add multiple test cases."""
        self.cases.extend(cases)

    def filter_by_tag(self, tag: str) -> List[TestCase]:
        """Get cases with a specific tag."""
        return [c for c in self.cases if tag in c.tags]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "case_count": len(self.cases),
            "cases": [c.to_dict() for c in self.cases],
            "metadata": self.metadata
        }

    def save(self, path: str) -> None:
        """Save suite to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "TestSuite":
        """Load suite from JSON file."""
        with open(path) as f:
            data = json.load(f)

        suite = cls(
            name=data["name"],
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )

        for case_data in data.get("cases", []):
            suite.add_case(TestCase(
                name=case_data["name"],
                prompt=case_data["prompt"],
                expected=case_data.get("expected"),
                system_prompt=case_data.get("system_prompt"),
                tags=case_data.get("tags", []),
                metadata=case_data.get("metadata", {})
            ))

        return suite


@dataclass
class BenchmarkResult:
    """Result from running a single test case."""
    test_name: str
    model: str
    prompt: str
    output: str
    expected: Any
    evaluation: EvaluationResult
    latency_ms: float
    timestamp: str
    tokens: Optional[Dict[str, int]] = None
    cost: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "model": self.model,
            "prompt": self.prompt[:100] + "..." if len(self.prompt) > 100 else self.prompt,
            "output": self.output[:200] + "..." if len(self.output) > 200 else self.output,
            "expected": self.expected,
            "score": self.evaluation.score,
            "passed": self.evaluation.passed,
            "evaluation_details": self.evaluation.details,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp,
            "tokens": self.tokens,
            "cost": self.cost,
            "error": self.error
        }


@dataclass
class ComparisonReport:
    """Report comparing multiple models."""
    models: List[str]
    test_suite: str
    results_by_model: Dict[str, List[BenchmarkResult]]
    metrics_by_model: Dict[str, Dict[str, Any]]
    winner: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"=== Model Comparison Report ===",
            f"Test Suite: {self.test_suite}",
            f"Models: {', '.join(self.models)}",
            f"Timestamp: {self.timestamp}",
            "",
            "Results by Model:",
            "-" * 50
        ]

        for model in self.models:
            metrics = self.metrics_by_model.get(model, {})
            acc = metrics.get("accuracy", {})
            lat = metrics.get("latency", {})

            lines.append(f"\n{model}:")
            lines.append(f"  Accuracy: {acc.get('accuracy', 0):.1%} ({acc.get('passed', 0)}/{acc.get('total', 0)})")
            lines.append(f"  Mean Score: {acc.get('mean_score', 0):.3f}")
            if lat:
                lines.append(f"  Latency: {lat.get('mean_ms', 0):.0f}ms (p95: {lat.get('p95_ms', 0):.0f}ms)")

        if self.winner:
            lines.append(f"\n🏆 Best Overall: {self.winner}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "models": self.models,
            "test_suite": self.test_suite,
            "metrics_by_model": self.metrics_by_model,
            "winner": self.winner,
            "timestamp": self.timestamp,
            "result_count": {m: len(r) for m, r in self.results_by_model.items()}
        }

    def save(self, path: str) -> None:
        """Save report to JSON."""
        data = self.to_dict()
        data["full_results"] = {
            model: [r.to_dict() for r in results]
            for model, results in self.results_by_model.items()
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


class ModelBenchmark:
    """
    Main benchmarking class.

    Runs test suites against models and collects metrics.
    """

    def __init__(
        self,
        client: Any = None,
        chat_fn: Optional[Callable] = None,
        default_evaluator: Optional[Evaluator] = None
    ):
        """
        Initialize benchmark.

        Args:
            client: OpenAI-compatible client (with .chat() method)
            chat_fn: Alternative: direct function(prompt, model, system) -> str
            default_evaluator: Default evaluator to use
        """
        self.client = client
        self.chat_fn = chat_fn
        self.default_evaluator = default_evaluator or ToolCallEvaluator()
        self.results: List[BenchmarkResult] = []

    def _get_response(
        self,
        prompt: str,
        model: str,
        system_prompt: Optional[str] = None
    ) -> tuple[str, float, Optional[Dict]]:
        """
        Get response from model.

        Returns: (output, latency_ms, usage_info)
        """
        start = time.perf_counter()

        if self.chat_fn:
            output = self.chat_fn(prompt, model, system_prompt)
            usage = None
        elif self.client:
            response = self.client.chat(
                prompt,
                model=model,
                system=system_prompt
            )
            output = response.content
            usage = response.usage
        else:
            raise ValueError("No client or chat_fn provided")

        latency_ms = (time.perf_counter() - start) * 1000
        return output, latency_ms, usage

    def run_case(
        self,
        case: TestCase,
        model: str,
        evaluator: Optional[Evaluator] = None,
        system_prompt: Optional[str] = None
    ) -> BenchmarkResult:
        """
        Run a single test case.

        Args:
            case: Test case to run
            model: Model identifier
            evaluator: Evaluator to use (default if None)
            system_prompt: Override system prompt

        Returns:
            BenchmarkResult
        """
        evaluator = evaluator or self.default_evaluator
        sys_prompt = system_prompt or case.system_prompt

        try:
            output, latency_ms, usage = self._get_response(
                case.prompt, model, sys_prompt
            )

            evaluation = evaluator.evaluate(
                output,
                expected=case.expected,
                context={"prompt": case.prompt, "model": model}
            )

            tokens = None
            cost = None
            if usage:
                tokens = {
                    "input": usage.get("prompt_tokens", 0),
                    "output": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0)
                }

            result = BenchmarkResult(
                test_name=case.name,
                model=model,
                prompt=case.prompt,
                output=output,
                expected=case.expected,
                evaluation=evaluation,
                latency_ms=latency_ms,
                timestamp=datetime.now().isoformat(),
                tokens=tokens,
                cost=cost
            )

        except Exception as e:
            logger.error(f"Error running case {case.name} on {model}: {e}")
            result = BenchmarkResult(
                test_name=case.name,
                model=model,
                prompt=case.prompt,
                output="",
                expected=case.expected,
                evaluation=EvaluationResult(
                    score=0.0,
                    passed=False,
                    details={"error": str(e)},
                    evaluator_name=evaluator.name
                ),
                latency_ms=0,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )

        self.results.append(result)
        return result

    def run_suite(
        self,
        suite: TestSuite,
        models: List[str],
        evaluator: Optional[Evaluator] = None,
        parallel: bool = False,
        max_workers: int = 3,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, List[BenchmarkResult]]:
        """
        Run a test suite across multiple models.

        Args:
            suite: Test suite to run
            models: List of model identifiers
            evaluator: Evaluator to use
            parallel: Run models in parallel
            max_workers: Max parallel workers
            progress_callback: Optional callback(current, total, status)

        Returns:
            Dict mapping model -> list of results
        """
        evaluator = evaluator or self.default_evaluator
        results_by_model: Dict[str, List[BenchmarkResult]] = {m: [] for m in models}

        total = len(models) * len(suite.cases)
        current = 0

        def run_model(model: str) -> List[BenchmarkResult]:
            nonlocal current
            model_results = []

            for case in suite.cases:
                result = self.run_case(
                    case, model, evaluator,
                    system_prompt=suite.default_system_prompt
                )
                model_results.append(result)

                current += 1
                if progress_callback:
                    progress_callback(current, total, f"{model}: {case.name}")

                logger.info(
                    f"[{current}/{total}] {model} | {case.name}: "
                    f"{'✓' if result.evaluation.passed else '✗'} "
                    f"({result.evaluation.score:.2f})"
                )

            return model_results

        if parallel and len(models) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(run_model, m): m for m in models}
                for future in as_completed(futures):
                    model = futures[future]
                    results_by_model[model] = future.result()
        else:
            for model in models:
                results_by_model[model] = run_model(model)

        return results_by_model

    def compare_models(
        self,
        results_by_model: Dict[str, List[BenchmarkResult]],
        suite_name: str = "benchmark"
    ) -> ComparisonReport:
        """
        Generate comparison report from benchmark results.

        Args:
            results_by_model: Dict from run_suite()
            suite_name: Name for the report

        Returns:
            ComparisonReport with metrics and winner
        """
        metrics_by_model = {}
        best_score = -1
        winner = None

        for model, results in results_by_model.items():
            result_dicts = [r.to_dict() for r in results]

            accuracy = calculate_accuracy(result_dicts)
            latencies = [r.latency_ms for r in results if r.latency_ms > 0]
            latency = calculate_latency_stats(latencies) if latencies else None

            metrics_by_model[model] = {
                "accuracy": accuracy.to_dict(),
                "latency": latency.to_dict() if latency else None,
                "total_tests": len(results),
                "errors": sum(1 for r in results if r.error)
            }

            # Determine winner (highest accuracy, latency as tiebreaker)
            if accuracy.accuracy > best_score:
                best_score = accuracy.accuracy
                winner = model
            elif accuracy.accuracy == best_score and latency:
                current_latency = metrics_by_model.get(winner, {}).get("latency", {}).get("mean_ms", float("inf"))
                if latency.mean_ms < current_latency:
                    winner = model

        return ComparisonReport(
            models=list(results_by_model.keys()),
            test_suite=suite_name,
            results_by_model=results_by_model,
            metrics_by_model=metrics_by_model,
            winner=winner
        )

    def get_results_df(self) -> Any:
        """
        Get results as pandas DataFrame (if pandas available).

        Returns:
            DataFrame or list of dicts if pandas unavailable
        """
        data = [r.to_dict() for r in self.results]

        try:
            import pandas as pd
            return pd.DataFrame(data)
        except ImportError:
            return data

    def clear_results(self) -> None:
        """Clear accumulated results."""
        self.results = []


# Convenience functions

def run_benchmark(
    prompts: List[str],
    models: List[str],
    client: Any,
    evaluator: Optional[Evaluator] = None,
    expected: Optional[List[Any]] = None
) -> Dict[str, List[BenchmarkResult]]:
    """
    Quick benchmark of prompts across models.

    Args:
        prompts: List of prompts to test
        models: List of model identifiers
        client: OpenAI-compatible client
        evaluator: Evaluator to use
        expected: Optional list of expected outputs (parallel to prompts)

    Returns:
        Dict mapping model -> results
    """
    suite = TestSuite("quick_benchmark")

    for i, prompt in enumerate(prompts):
        exp = expected[i] if expected and i < len(expected) else None
        suite.add_case(TestCase(
            name=f"test_{i+1}",
            prompt=prompt,
            expected=exp
        ))

    bench = ModelBenchmark(client, default_evaluator=evaluator)
    return bench.run_suite(suite, models)


def compare_models(
    prompts: List[str],
    models: List[str],
    client: Any,
    evaluator: Optional[Evaluator] = None,
    expected: Optional[List[Any]] = None
) -> ComparisonReport:
    """
    Quick comparison of models on prompts.

    Args:
        prompts: Test prompts
        models: Models to compare
        client: API client
        evaluator: Evaluator
        expected: Expected outputs

    Returns:
        ComparisonReport
    """
    results = run_benchmark(prompts, models, client, evaluator, expected)
    bench = ModelBenchmark(client)
    return bench.compare_models(results)


def create_tool_routing_suite(
    tool_examples: List[Dict[str, Any]],
    suite_name: str = "tool_routing"
) -> TestSuite:
    """
    Create a test suite from tool call examples.

    Args:
        tool_examples: List of {"prompt": str, "tool": str, "arguments": dict}
        suite_name: Name for the suite

    Returns:
        TestSuite ready for benchmarking
    """
    suite = TestSuite(
        name=suite_name,
        description="Tool routing accuracy test",
        default_system_prompt=(
            "You are an AI assistant with tools. "
            "When appropriate, respond with a tool call in JSON format: "
            '{"tool": "tool_name", "arguments": {...}}'
        )
    )

    for i, example in enumerate(tool_examples):
        suite.add_case(TestCase(
            name=f"tool_{i+1}_{example.get('tool', 'unknown')}",
            prompt=example["prompt"],
            expected={
                "tool": example["tool"],
                "arguments": example.get("arguments", {})
            },
            tags=[example.get("tool", "unknown")]
        ))

    return suite
