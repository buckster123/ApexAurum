"""
Metrics - Statistical Calculations for Benchmark Results

Aggregate functions for calculating accuracy, precision, recall,
latency statistics, and cost efficiency metrics.

Usage:
    from reusable_lib.evaluation import (
        calculate_accuracy,
        calculate_precision_recall,
        calculate_latency_stats,
        aggregate_results
    )

    # From a list of evaluation results
    accuracy = calculate_accuracy(results)
    latency = calculate_latency_stats(latencies)
"""

import statistics
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AccuracyMetrics:
    """Accuracy-related metrics."""
    total: int
    passed: int
    failed: int
    accuracy: float
    mean_score: float
    std_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "accuracy": round(self.accuracy, 4),
            "mean_score": round(self.mean_score, 4),
            "std_score": round(self.std_score, 4)
        }


@dataclass
class LatencyMetrics:
    """Latency/timing metrics."""
    count: int
    mean_ms: float
    median_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "mean_ms": round(self.mean_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "std_ms": round(self.std_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "p90_ms": round(self.p90_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2)
        }


@dataclass
class PrecisionRecallMetrics:
    """Precision and recall metrics."""
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4)
        }


@dataclass
class CostMetrics:
    """Cost efficiency metrics."""
    total_cost: float
    cost_per_request: float
    cost_per_success: float
    tokens_per_request: float
    cost_efficiency: float  # score / cost ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cost": round(self.total_cost, 6),
            "cost_per_request": round(self.cost_per_request, 6),
            "cost_per_success": round(self.cost_per_success, 6),
            "tokens_per_request": round(self.tokens_per_request, 2),
            "cost_efficiency": round(self.cost_efficiency, 4)
        }


def calculate_accuracy(
    results: List[Dict[str, Any]],
    score_key: str = "score",
    passed_key: str = "passed"
) -> AccuracyMetrics:
    """
    Calculate accuracy metrics from evaluation results.

    Args:
        results: List of result dicts with score and passed fields
        score_key: Key for score value (0.0-1.0)
        passed_key: Key for pass/fail boolean

    Returns:
        AccuracyMetrics dataclass
    """
    if not results:
        return AccuracyMetrics(
            total=0, passed=0, failed=0,
            accuracy=0.0, mean_score=0.0, std_score=0.0
        )

    scores = [r.get(score_key, 0.0) for r in results]
    passed_count = sum(1 for r in results if r.get(passed_key, False))
    failed_count = len(results) - passed_count

    mean_score = statistics.mean(scores)
    std_score = statistics.stdev(scores) if len(scores) > 1 else 0.0
    accuracy = passed_count / len(results)

    return AccuracyMetrics(
        total=len(results),
        passed=passed_count,
        failed=failed_count,
        accuracy=accuracy,
        mean_score=mean_score,
        std_score=std_score
    )


def calculate_latency_stats(latencies_ms: List[float]) -> LatencyMetrics:
    """
    Calculate latency statistics.

    Args:
        latencies_ms: List of latency values in milliseconds

    Returns:
        LatencyMetrics dataclass
    """
    if not latencies_ms:
        return LatencyMetrics(
            count=0, mean_ms=0, median_ms=0, std_ms=0,
            min_ms=0, max_ms=0, p90_ms=0, p95_ms=0, p99_ms=0
        )

    sorted_latencies = sorted(latencies_ms)
    n = len(sorted_latencies)

    def percentile(p: float) -> float:
        idx = int(n * p / 100)
        return sorted_latencies[min(idx, n - 1)]

    return LatencyMetrics(
        count=n,
        mean_ms=statistics.mean(latencies_ms),
        median_ms=statistics.median(latencies_ms),
        std_ms=statistics.stdev(latencies_ms) if n > 1 else 0.0,
        min_ms=min(latencies_ms),
        max_ms=max(latencies_ms),
        p90_ms=percentile(90),
        p95_ms=percentile(95),
        p99_ms=percentile(99)
    )


def calculate_precision_recall(
    results: List[Dict[str, Any]],
    expected_positive: bool = True
) -> PrecisionRecallMetrics:
    """
    Calculate precision and recall metrics.

    For tool calling:
    - True Positive: Correct tool called
    - False Positive: Wrong tool called
    - False Negative: Should have called tool but didn't
    - True Negative: Correctly didn't call tool

    Args:
        results: List of result dicts with 'passed' and 'expected' fields
        expected_positive: What value indicates a positive case

    Returns:
        PrecisionRecallMetrics dataclass
    """
    tp = fp = fn = tn = 0

    for r in results:
        actual_positive = r.get("passed", False)
        expected = r.get("expected_positive", expected_positive)

        if actual_positive and expected:
            tp += 1
        elif actual_positive and not expected:
            fp += 1
        elif not actual_positive and expected:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return PrecisionRecallMetrics(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        precision=precision,
        recall=recall,
        f1_score=f1
    )


def calculate_cost_efficiency(
    results: List[Dict[str, Any]],
    cost_key: str = "cost",
    tokens_key: str = "total_tokens",
    score_key: str = "score"
) -> CostMetrics:
    """
    Calculate cost efficiency metrics.

    Args:
        results: List of result dicts with cost and token info
        cost_key: Key for cost value
        tokens_key: Key for total tokens
        score_key: Key for score value

    Returns:
        CostMetrics dataclass
    """
    if not results:
        return CostMetrics(
            total_cost=0, cost_per_request=0,
            cost_per_success=0, tokens_per_request=0,
            cost_efficiency=0
        )

    total_cost = sum(r.get(cost_key, 0) for r in results)
    total_tokens = sum(r.get(tokens_key, 0) for r in results)
    total_score = sum(r.get(score_key, 0) for r in results)

    n = len(results)
    successes = sum(1 for r in results if r.get("passed", False))

    cost_per_request = total_cost / n if n > 0 else 0
    cost_per_success = total_cost / successes if successes > 0 else 0
    tokens_per_request = total_tokens / n if n > 0 else 0
    cost_efficiency = total_score / total_cost if total_cost > 0 else 0

    return CostMetrics(
        total_cost=total_cost,
        cost_per_request=cost_per_request,
        cost_per_success=cost_per_success,
        tokens_per_request=tokens_per_request,
        cost_efficiency=cost_efficiency
    )


def aggregate_results(
    results: List[Dict[str, Any]],
    group_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Aggregate benchmark results with optional grouping.

    Args:
        results: List of benchmark result dicts
        group_by: Optional field to group by (e.g., "model", "evaluator")

    Returns:
        Aggregated statistics dict
    """
    if not results:
        return {"total": 0, "groups": {}}

    if group_by:
        # Group results
        groups = {}
        for r in results:
            key = r.get(group_by, "unknown")
            if key not in groups:
                groups[key] = []
            groups[key].append(r)

        # Calculate metrics per group
        group_metrics = {}
        for key, group_results in groups.items():
            group_metrics[key] = {
                "count": len(group_results),
                "accuracy": calculate_accuracy(group_results).to_dict(),
                "scores": {
                    "mean": statistics.mean(r.get("score", 0) for r in group_results),
                    "min": min(r.get("score", 0) for r in group_results),
                    "max": max(r.get("score", 0) for r in group_results),
                }
            }

            # Add latency if available
            latencies = [r.get("latency_ms") for r in group_results if r.get("latency_ms")]
            if latencies:
                group_metrics[key]["latency"] = calculate_latency_stats(latencies).to_dict()

        return {
            "total": len(results),
            "groups": group_metrics,
            "overall": calculate_accuracy(results).to_dict()
        }

    else:
        # No grouping - just overall stats
        accuracy = calculate_accuracy(results)

        latencies = [r.get("latency_ms") for r in results if r.get("latency_ms")]
        latency = calculate_latency_stats(latencies) if latencies else None

        return {
            "total": len(results),
            "accuracy": accuracy.to_dict(),
            "latency": latency.to_dict() if latency else None
        }


def compare_metrics(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
    metrics: List[str] = ["accuracy", "mean_score", "mean_ms"]
) -> Dict[str, Any]:
    """
    Compare metrics between baseline and candidate.

    Args:
        baseline: Baseline metrics dict
        candidate: Candidate metrics dict
        metrics: List of metric keys to compare

    Returns:
        Comparison dict with deltas and improvement flags
    """
    comparisons = {}

    for metric in metrics:
        base_val = _get_nested(baseline, metric, 0)
        cand_val = _get_nested(candidate, metric, 0)

        delta = cand_val - base_val
        pct_change = (delta / base_val * 100) if base_val != 0 else 0

        # For latency, lower is better; for others, higher is better
        if "latency" in metric or "_ms" in metric:
            improved = delta < 0
        else:
            improved = delta > 0

        comparisons[metric] = {
            "baseline": base_val,
            "candidate": cand_val,
            "delta": round(delta, 4),
            "pct_change": round(pct_change, 2),
            "improved": improved
        }

    return comparisons


def _get_nested(d: Dict, key: str, default: Any = None) -> Any:
    """Get value from potentially nested dict using dot notation."""
    keys = key.split(".")
    val = d
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, default)
        else:
            return default
    return val
