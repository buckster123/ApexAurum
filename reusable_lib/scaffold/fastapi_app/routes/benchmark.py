"""
Benchmark Routes

Run model evaluations and comparisons.
"""

import logging
from typing import Optional, List, Any
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from services.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize benchmark service
benchmark_service = BenchmarkService()


class QuickBenchmarkRequest(BaseModel):
    """Quick benchmark request."""
    prompts: List[str]
    models: List[str]
    expected: Optional[List[Any]] = None
    evaluator: str = "tool_call"  # tool_call, json, exact_match


class TestCaseInput(BaseModel):
    """A single test case."""
    name: str
    prompt: str
    expected: Optional[Any] = None
    tags: List[str] = []


class SuiteRunRequest(BaseModel):
    """Request to run a test suite."""
    suite_name: str
    models: List[str]
    evaluator: str = "tool_call"


@router.post("/quick")
async def quick_benchmark(request: QuickBenchmarkRequest):
    """
    Run a quick benchmark comparing models.

    Returns accuracy and latency for each model.
    """
    try:
        report = benchmark_service.quick_compare(
            prompts=request.prompts,
            models=request.models,
            expected=request.expected,
            evaluator_type=request.evaluator
        )
        return {
            "summary": report.summary(),
            "metrics": report.metrics_by_model,
            "winner": report.winner
        }
    except Exception as e:
        logger.error(f"Benchmark error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick/stream")
async def quick_benchmark_stream(request: QuickBenchmarkRequest):
    """
    Run a quick benchmark with streaming progress updates.
    """
    import json

    async def generate():
        def progress_callback(current, total, status):
            data = {"current": current, "total": total, "status": status}
            # Note: This won't actually stream in sync mode
            # Would need to refactor for true async streaming

        try:
            report = benchmark_service.quick_compare(
                prompts=request.prompts,
                models=request.models,
                expected=request.expected,
                evaluator_type=request.evaluator
            )

            yield f"data: {json.dumps({'type': 'complete', 'summary': report.summary(), 'winner': report.winner})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# === Test Suites ===

@router.get("/suites")
async def list_suites():
    """List available test suites."""
    suites = benchmark_service.list_suites()
    return {"suites": suites}


@router.post("/suites")
async def create_suite(name: str, description: str = "", cases: List[TestCaseInput] = []):
    """Create a new test suite."""
    suite_id = benchmark_service.create_suite(name, description, cases)
    return {"message": f"Suite created: {name}", "id": suite_id}


@router.get("/suites/{suite_name}")
async def get_suite(suite_name: str):
    """Get a test suite by name."""
    suite = benchmark_service.get_suite(suite_name)
    if not suite:
        raise HTTPException(status_code=404, detail=f"Suite not found: {suite_name}")
    return suite


@router.post("/suites/{suite_name}/run")
async def run_suite(suite_name: str, request: SuiteRunRequest):
    """Run a test suite against specified models."""
    try:
        report = benchmark_service.run_suite(
            suite_name=suite_name,
            models=request.models,
            evaluator_type=request.evaluator
        )
        return {
            "suite": suite_name,
            "summary": report.summary(),
            "metrics": report.metrics_by_model,
            "winner": report.winner
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Suite run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/suites/{suite_name}")
async def delete_suite(suite_name: str):
    """Delete a test suite."""
    success = benchmark_service.delete_suite(suite_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Suite not found: {suite_name}")
    return {"message": f"Suite deleted: {suite_name}"}


# === Results History ===

@router.get("/history")
async def get_benchmark_history(limit: int = 20):
    """Get recent benchmark results."""
    history = benchmark_service.get_history(limit)
    return {"history": history, "count": len(history)}


@router.get("/history/{run_id}")
async def get_benchmark_run(run_id: str):
    """Get details of a specific benchmark run."""
    run = benchmark_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run
