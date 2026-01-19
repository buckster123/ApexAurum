# Evaluation - Model Benchmarking and Quality Assessment
# Extracted from ApexAurum - Claude Edition
#
# Tools for evaluating model performance, comparing models,
# and tracking quality over time.

from .benchmark import (
    ModelBenchmark,
    BenchmarkResult,
    TestCase,
    TestSuite,
    ComparisonReport,
    run_benchmark,
    compare_models
)

from .evaluators import (
    Evaluator,
    ToolCallEvaluator,
    ExactMatchEvaluator,
    JSONValidityEvaluator,
    ResponseQualityEvaluator,
    CompositeEvaluator,
    SemanticSimilarityEvaluator
)

from .metrics import (
    calculate_accuracy,
    calculate_precision_recall,
    calculate_latency_stats,
    calculate_cost_efficiency,
    aggregate_results
)

__all__ = [
    # Benchmark
    'ModelBenchmark',
    'BenchmarkResult',
    'TestCase',
    'TestSuite',
    'ComparisonReport',
    'run_benchmark',
    'compare_models',
    # Evaluators
    'Evaluator',
    'ToolCallEvaluator',
    'ExactMatchEvaluator',
    'JSONValidityEvaluator',
    'ResponseQualityEvaluator',
    'CompositeEvaluator',
    'SemanticSimilarityEvaluator',
    # Metrics
    'calculate_accuracy',
    'calculate_precision_recall',
    'calculate_latency_stats',
    'calculate_cost_efficiency',
    'aggregate_results',
]
