"""
Evaluators - Scoring Functions for Model Outputs

Different evaluators for measuring various aspects of model performance:
- Tool call accuracy (did it call the right tool with right args?)
- JSON validity (is the output valid JSON?)
- Exact match (does output match expected?)
- Response quality (length, coherence heuristics)
- Semantic similarity (meaning match, requires embeddings)

Usage:
    from reusable_lib.evaluation import ToolCallEvaluator, CompositeEvaluator

    # Single evaluator
    evaluator = ToolCallEvaluator()
    score = evaluator.evaluate(
        output='{"tool": "memory_store", "arguments": {"key": "name", "value": "Bob"}}',
        expected={"tool": "memory_store", "arguments": {"key": "name"}}
    )
    print(score)  # {"score": 1.0, "tool_correct": True, "args_correct": True}

    # Combine multiple evaluators
    combo = CompositeEvaluator([
        (ToolCallEvaluator(), 0.7),      # 70% weight
        (JSONValidityEvaluator(), 0.3),  # 30% weight
    ])
"""

import json
import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result from an evaluator."""
    score: float                    # 0.0 to 1.0
    passed: bool                    # Binary pass/fail
    details: Dict[str, Any]         # Evaluator-specific details
    evaluator_name: str             # Which evaluator produced this

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "details": self.details,
            "evaluator": self.evaluator_name
        }


class Evaluator(ABC):
    """Base class for all evaluators."""

    name: str = "base"
    description: str = "Base evaluator"

    @abstractmethod
    def evaluate(
        self,
        output: str,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        Evaluate a model output.

        Args:
            output: The model's output string
            expected: Expected output (format depends on evaluator)
            context: Additional context (prompt, tools, etc.)

        Returns:
            EvaluationResult with score and details
        """
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class ToolCallEvaluator(Evaluator):
    """
    Evaluate tool/function calling accuracy.

    Checks:
    - Did the model output valid JSON?
    - Did it call the correct tool?
    - Did it provide the required arguments?
    - Are argument values correct (if expected values provided)?
    """

    name = "tool_call"
    description = "Evaluates tool calling accuracy"

    def __init__(
        self,
        strict_args: bool = False,
        required_args_only: bool = True
    ):
        """
        Args:
            strict_args: If True, argument values must match exactly
            required_args_only: If True, only check required args are present
        """
        self.strict_args = strict_args
        self.required_args_only = required_args_only

    def evaluate(
        self,
        output: str,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        Evaluate tool call output.

        Expected format:
            {"tool": "tool_name", "arguments": {"arg1": "val1", ...}}
        Or:
            {"tool": "tool_name"}  # Just check tool name
        """
        details = {
            "json_valid": False,
            "tool_correct": False,
            "args_present": False,
            "args_correct": False,
            "parsed_output": None,
            "errors": []
        }

        # Parse output JSON
        parsed = self._parse_json(output)
        if parsed is None:
            details["errors"].append("Invalid JSON output")
            return EvaluationResult(
                score=0.0,
                passed=False,
                details=details,
                evaluator_name=self.name
            )

        details["json_valid"] = True
        details["parsed_output"] = parsed

        # No expected value - just check JSON validity
        if expected is None:
            return EvaluationResult(
                score=1.0 if details["json_valid"] else 0.0,
                passed=details["json_valid"],
                details=details,
                evaluator_name=self.name
            )

        # Check tool name
        expected_tool = expected.get("tool") if isinstance(expected, dict) else expected
        actual_tool = parsed.get("tool") or parsed.get("name") or parsed.get("function")

        if actual_tool == expected_tool:
            details["tool_correct"] = True

        # Check arguments if expected
        expected_args = expected.get("arguments", {}) if isinstance(expected, dict) else {}
        actual_args = parsed.get("arguments") or parsed.get("input") or parsed.get("args") or {}

        if expected_args:
            # Check required args are present
            missing_args = []
            for key in expected_args.keys():
                if key not in actual_args:
                    missing_args.append(key)

            details["args_present"] = len(missing_args) == 0
            details["missing_args"] = missing_args

            # Check arg values if strict mode
            if self.strict_args and details["args_present"]:
                incorrect_args = []
                for key, expected_val in expected_args.items():
                    if actual_args.get(key) != expected_val:
                        incorrect_args.append(key)
                details["args_correct"] = len(incorrect_args) == 0
                details["incorrect_args"] = incorrect_args
            else:
                details["args_correct"] = details["args_present"]
        else:
            details["args_present"] = True
            details["args_correct"] = True

        # Calculate score
        score = 0.0
        if details["tool_correct"]:
            score += 0.5  # 50% for correct tool
        if details["args_present"]:
            score += 0.25  # 25% for args present
        if details["args_correct"]:
            score += 0.25  # 25% for args correct

        passed = details["tool_correct"] and details["args_present"]

        return EvaluationResult(
            score=score,
            passed=passed,
            details=details,
            evaluator_name=self.name
        )

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Try to extract and parse JSON from text."""
        # Try direct parse
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON in text (model might add explanation)
        json_patterns = [
            r'\{[^{}]*"tool"[^{}]*\}',
            r'\{[^{}]*"function"[^{}]*\}',
            r'\{[^{}]*"name"[^{}]*\}',
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1) if match.lastindex else match.group(0)
                    return json.loads(json_str)
                except (json.JSONDecodeError, IndexError):
                    continue

        return None


class JSONValidityEvaluator(Evaluator):
    """Evaluate if output is valid JSON."""

    name = "json_validity"
    description = "Checks if output is valid JSON"

    def __init__(self, schema: Optional[Dict] = None):
        """
        Args:
            schema: Optional JSON schema to validate against
        """
        self.schema = schema

    def evaluate(
        self,
        output: str,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        details = {
            "is_valid": False,
            "parsed": None,
            "error": None
        }

        try:
            parsed = json.loads(output.strip())
            details["is_valid"] = True
            details["parsed"] = parsed

            # Schema validation if provided
            if self.schema:
                schema_valid, schema_errors = self._validate_schema(parsed)
                details["schema_valid"] = schema_valid
                details["schema_errors"] = schema_errors
                if not schema_valid:
                    return EvaluationResult(
                        score=0.5,  # Valid JSON but wrong schema
                        passed=False,
                        details=details,
                        evaluator_name=self.name
                    )

            return EvaluationResult(
                score=1.0,
                passed=True,
                details=details,
                evaluator_name=self.name
            )

        except json.JSONDecodeError as e:
            details["error"] = str(e)
            return EvaluationResult(
                score=0.0,
                passed=False,
                details=details,
                evaluator_name=self.name
            )

    def _validate_schema(self, data: Any) -> Tuple[bool, List[str]]:
        """Basic schema validation (type checking)."""
        errors = []
        # Simple type checking - extend with jsonschema if needed
        if "type" in self.schema:
            expected_type = self.schema["type"]
            type_map = {
                "object": dict,
                "array": list,
                "string": str,
                "number": (int, float),
                "boolean": bool
            }
            if expected_type in type_map:
                if not isinstance(data, type_map[expected_type]):
                    errors.append(f"Expected {expected_type}, got {type(data).__name__}")

        if "required" in self.schema and isinstance(data, dict):
            for field in self.schema["required"]:
                if field not in data:
                    errors.append(f"Missing required field: {field}")

        return len(errors) == 0, errors


class ExactMatchEvaluator(Evaluator):
    """Evaluate exact string match."""

    name = "exact_match"
    description = "Checks for exact string match"

    def __init__(
        self,
        case_sensitive: bool = True,
        strip_whitespace: bool = True
    ):
        self.case_sensitive = case_sensitive
        self.strip_whitespace = strip_whitespace

    def evaluate(
        self,
        output: str,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        if expected is None:
            return EvaluationResult(
                score=1.0,
                passed=True,
                details={"note": "No expected value provided"},
                evaluator_name=self.name
            )

        actual = output
        exp = str(expected)

        if self.strip_whitespace:
            actual = actual.strip()
            exp = exp.strip()

        if not self.case_sensitive:
            actual = actual.lower()
            exp = exp.lower()

        match = actual == exp

        return EvaluationResult(
            score=1.0 if match else 0.0,
            passed=match,
            details={
                "match": match,
                "actual_length": len(actual),
                "expected_length": len(exp)
            },
            evaluator_name=self.name
        )


class ResponseQualityEvaluator(Evaluator):
    """
    Evaluate response quality using heuristics.

    Checks:
    - Response length (not too short, not too long)
    - No error indicators
    - Coherence (basic sentence structure)
    """

    name = "response_quality"
    description = "Evaluates response quality heuristics"

    def __init__(
        self,
        min_length: int = 10,
        max_length: int = 5000,
        error_patterns: Optional[List[str]] = None
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.error_patterns = error_patterns or [
            r"i cannot",
            r"i can't",
            r"i am unable",
            r"error:",
            r"exception:",
            r"sorry,? i",
            r"as an ai",
        ]

    def evaluate(
        self,
        output: str,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        details = {
            "length": len(output),
            "length_ok": False,
            "no_errors": True,
            "error_matches": [],
            "has_content": False
        }

        score = 0.0

        # Length check
        if self.min_length <= len(output) <= self.max_length:
            details["length_ok"] = True
            score += 0.4

        # Error pattern check
        output_lower = output.lower()
        for pattern in self.error_patterns:
            if re.search(pattern, output_lower):
                details["no_errors"] = False
                details["error_matches"].append(pattern)

        if details["no_errors"]:
            score += 0.3

        # Content check (not just whitespace or repeated chars)
        stripped = output.strip()
        if stripped and len(set(stripped)) > 5:
            details["has_content"] = True
            score += 0.3

        passed = details["length_ok"] and details["no_errors"] and details["has_content"]

        return EvaluationResult(
            score=score,
            passed=passed,
            details=details,
            evaluator_name=self.name
        )


class SemanticSimilarityEvaluator(Evaluator):
    """
    Evaluate semantic similarity using embeddings.

    Requires sentence-transformers or similar embedding model.
    Falls back to simple word overlap if embeddings unavailable.
    """

    name = "semantic_similarity"
    description = "Evaluates meaning similarity"

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = 0.7
    ):
        self.model_name = model_name
        self.threshold = threshold
        self.model = None
        self._load_model()

    def _load_model(self):
        """Try to load embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, using word overlap")
            self.model = None

    def evaluate(
        self,
        output: str,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        if expected is None:
            return EvaluationResult(
                score=1.0,
                passed=True,
                details={"note": "No expected value for comparison"},
                evaluator_name=self.name
            )

        expected_str = str(expected)

        if self.model is not None:
            similarity = self._embedding_similarity(output, expected_str)
            method = "embedding"
        else:
            similarity = self._word_overlap_similarity(output, expected_str)
            method = "word_overlap"

        passed = similarity >= self.threshold

        return EvaluationResult(
            score=similarity,
            passed=passed,
            details={
                "similarity": similarity,
                "threshold": self.threshold,
                "method": method
            },
            evaluator_name=self.name
        )

    def _embedding_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity using embeddings."""
        import numpy as np

        embeddings = self.model.encode([text1, text2])
        cos_sim = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(cos_sim)

    def _word_overlap_similarity(self, text1: str, text2: str) -> float:
        """Simple word overlap similarity (fallback)."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)  # Jaccard similarity


class CompositeEvaluator(Evaluator):
    """
    Combine multiple evaluators with weights.

    Usage:
        combo = CompositeEvaluator([
            (ToolCallEvaluator(), 0.6),
            (JSONValidityEvaluator(), 0.2),
            (ResponseQualityEvaluator(), 0.2),
        ])
    """

    name = "composite"
    description = "Combines multiple evaluators"

    def __init__(self, evaluators: List[Tuple[Evaluator, float]]):
        """
        Args:
            evaluators: List of (evaluator, weight) tuples
                       Weights should sum to 1.0
        """
        self.evaluators = evaluators

        # Normalize weights
        total_weight = sum(w for _, w in evaluators)
        if abs(total_weight - 1.0) > 0.01:
            self.evaluators = [(e, w/total_weight) for e, w in evaluators]

    def evaluate(
        self,
        output: str,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        weighted_score = 0.0
        all_passed = True
        sub_results = {}

        for evaluator, weight in self.evaluators:
            result = evaluator.evaluate(output, expected, context)
            weighted_score += result.score * weight
            all_passed = all_passed and result.passed
            sub_results[evaluator.name] = result.to_dict()

        return EvaluationResult(
            score=weighted_score,
            passed=all_passed,
            details={
                "sub_evaluators": sub_results,
                "weights": {e.name: w for e, w in self.evaluators}
            },
            evaluator_name=self.name
        )


class ContainsEvaluator(Evaluator):
    """Check if output contains expected substring(s)."""

    name = "contains"
    description = "Checks if output contains expected text"

    def __init__(self, case_sensitive: bool = False):
        self.case_sensitive = case_sensitive

    def evaluate(
        self,
        output: str,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        if expected is None:
            return EvaluationResult(
                score=1.0, passed=True,
                details={}, evaluator_name=self.name
            )

        # Handle list of substrings
        if isinstance(expected, list):
            substrings = expected
        else:
            substrings = [str(expected)]

        check_output = output if self.case_sensitive else output.lower()
        found = []
        missing = []

        for s in substrings:
            check_s = s if self.case_sensitive else s.lower()
            if check_s in check_output:
                found.append(s)
            else:
                missing.append(s)

        score = len(found) / len(substrings) if substrings else 1.0
        passed = len(missing) == 0

        return EvaluationResult(
            score=score,
            passed=passed,
            details={"found": found, "missing": missing},
            evaluator_name=self.name
        )
