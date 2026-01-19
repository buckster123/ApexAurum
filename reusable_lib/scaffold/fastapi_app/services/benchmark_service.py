"""
Benchmark Service

Run model evaluations using reusable_lib evaluation module.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import from reusable_lib
import sys

lib_path = Path(__file__).parent.parent.parent.parent
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from reusable_lib.evaluation import (
    ModelBenchmark,
    TestCase,
    TestSuite,
    ComparisonReport,
    ToolCallEvaluator,
    JSONValidityEvaluator,
    ExactMatchEvaluator,
    CompositeEvaluator,
    compare_models
)

from services.llm_service import get_llm_client
from app_config import settings

logger = logging.getLogger(__name__)


class BenchmarkService:
    """
    Service for running model benchmarks.
    """

    def __init__(self):
        """Initialize benchmark service."""
        self.suites_dir = settings.DATA_DIR / "benchmark_suites"
        self.results_dir = settings.DATA_DIR / "benchmark_results"
        self.suites_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self._benchmark: Optional[ModelBenchmark] = None

    @property
    def benchmark(self) -> ModelBenchmark:
        """Get or create benchmark instance."""
        if self._benchmark is None:
            client = get_llm_client()
            self._benchmark = ModelBenchmark(client)
        return self._benchmark

    def _get_evaluator(self, evaluator_type: str):
        """Get evaluator by type name."""
        evaluators = {
            "tool_call": ToolCallEvaluator(),
            "json": JSONValidityEvaluator(),
            "exact_match": ExactMatchEvaluator(),
            "composite": CompositeEvaluator([
                (ToolCallEvaluator(), 0.6),
                (JSONValidityEvaluator(), 0.4)
            ])
        }
        return evaluators.get(evaluator_type, ToolCallEvaluator())

    def quick_compare(
        self,
        prompts: List[str],
        models: List[str],
        expected: Optional[List[Any]] = None,
        evaluator_type: str = "tool_call"
    ) -> ComparisonReport:
        """
        Run a quick model comparison.

        Args:
            prompts: Test prompts
            models: Models to compare
            expected: Expected outputs (parallel to prompts)
            evaluator_type: Evaluator to use

        Returns:
            ComparisonReport with results
        """
        client = get_llm_client()
        evaluator = self._get_evaluator(evaluator_type)

        report = compare_models(
            prompts=prompts,
            models=models,
            client=client,
            evaluator=evaluator,
            expected=expected
        )

        # Save results
        self._save_result(report, "quick_compare")

        return report

    # === Test Suites ===

    def list_suites(self) -> List[Dict]:
        """List all saved test suites."""
        suites = []
        for path in self.suites_dir.glob("*.json"):
            try:
                suite = TestSuite.load(str(path))
                suites.append({
                    "name": suite.name,
                    "description": suite.description,
                    "case_count": len(suite.cases),
                    "file": path.name
                })
            except Exception as e:
                logger.warning(f"Error loading suite {path}: {e}")
        return suites

    def create_suite(
        self,
        name: str,
        description: str = "",
        cases: List[Dict] = None
    ) -> str:
        """Create a new test suite."""
        suite = TestSuite(name=name, description=description)

        if cases:
            for case_data in cases:
                suite.add_case(TestCase(
                    name=case_data.get("name", f"case_{len(suite.cases)}"),
                    prompt=case_data["prompt"],
                    expected=case_data.get("expected"),
                    tags=case_data.get("tags", [])
                ))

        # Save
        path = self.suites_dir / f"{name}.json"
        suite.save(str(path))

        logger.info(f"Created suite: {name} with {len(suite.cases)} cases")
        return name

    def get_suite(self, name: str) -> Optional[Dict]:
        """Get a test suite by name."""
        path = self.suites_dir / f"{name}.json"
        if not path.exists():
            return None

        suite = TestSuite.load(str(path))
        return suite.to_dict()

    def delete_suite(self, name: str) -> bool:
        """Delete a test suite."""
        path = self.suites_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def run_suite(
        self,
        suite_name: str,
        models: List[str],
        evaluator_type: str = "tool_call"
    ) -> ComparisonReport:
        """
        Run a test suite against models.

        Args:
            suite_name: Name of the suite to run
            models: Models to test
            evaluator_type: Evaluator to use

        Returns:
            ComparisonReport with results
        """
        path = self.suites_dir / f"{suite_name}.json"
        if not path.exists():
            raise ValueError(f"Suite not found: {suite_name}")

        suite = TestSuite.load(str(path))
        evaluator = self._get_evaluator(evaluator_type)

        results = self.benchmark.run_suite(
            suite,
            models=models,
            evaluator=evaluator
        )

        report = self.benchmark.compare_models(results, suite_name)

        # Save results
        self._save_result(report, f"suite_{suite_name}")

        return report

    # === Results History ===

    def _save_result(self, report: ComparisonReport, prefix: str):
        """Save a benchmark result."""
        run_id = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        path = self.results_dir / f"{run_id}.json"
        report.save(str(path))
        logger.info(f"Saved benchmark result: {run_id}")
        return run_id

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent benchmark results."""
        results = []
        paths = sorted(self.results_dir.glob("*.json"), reverse=True)

        for path in paths[:limit]:
            try:
                with open(path) as f:
                    data = json.load(f)
                results.append({
                    "id": path.stem,
                    "timestamp": data.get("timestamp"),
                    "suite": data.get("test_suite"),
                    "models": data.get("models"),
                    "winner": data.get("winner")
                })
            except Exception as e:
                logger.warning(f"Error loading result {path}: {e}")

        return results

    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get a specific benchmark run."""
        path = self.results_dir / f"{run_id}.json"
        if not path.exists():
            return None

        with open(path) as f:
            return json.load(f)
