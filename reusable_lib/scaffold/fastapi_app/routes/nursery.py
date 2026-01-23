"""
🌱 THE NURSERY - FastAPI Routes
================================
Training Studio API - Where New Minds Are Cultivated

Phase 5 of Nursery Village Integration:
Full FastAPI parity with Streamlit Nursery features.

Endpoints:
- Datasets: List, generate, extract
- Training: Estimate cost, start jobs, monitor progress
- Models: List, register, discover
- Apprentices: Create, list, manage
- Village Activity: Training events feed
"""

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
import logging
import sys

# Add project root to path (same as tool_service.py)
project_root = Path(__file__).parent.parent.parent.parent.parent  # Go up to ApexAurum
lib_path = project_root / "reusable_lib"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(lib_path) not in sys.path:
    sys.path.insert(1, str(lib_path))

# Import nursery tools
from tools.nursery import (
    # Data Garden
    nursery_generate_data,
    nursery_list_datasets,
    nursery_extract_conversations,
    # Training Forge
    nursery_estimate_cost,
    nursery_train_cloud,
    nursery_train_local,
    nursery_job_status,
    nursery_list_jobs,
    # Model Cradle
    nursery_list_models,
    nursery_deploy_ollama,
    nursery_test_model,
    nursery_compare_models,
    # Phase 2: Village Registry
    nursery_register_model,
    nursery_discover_models,
    # Phase 3: Apprentice Protocol
    nursery_create_apprentice,
    nursery_list_apprentices,
)

# Village search for activity feed
try:
    from tools.vector_search import vector_search_village
    VILLAGE_AVAILABLE = True
except ImportError:
    VILLAGE_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nursery", tags=["Nursery"])


# =============================================================================
# Request/Response Models
# =============================================================================

class GenerateDataRequest(BaseModel):
    """Request to generate synthetic training data."""
    tool_name: str = Field(..., description="Name of the tool to generate examples for")
    num_examples: int = Field(default=50, ge=5, le=500, description="Number of examples")
    variation_level: str = Field(default="medium", description="low|medium|high")
    output_name: Optional[str] = Field(default=None, description="Custom dataset name")
    agent_id: Optional[str] = Field(default=None, description="Agent attribution")


class ExtractConversationsRequest(BaseModel):
    """Request to extract training data from conversations."""
    source: str = Field(default="sandbox/conversations.json", description="Path to conversations file")
    tools_filter: Optional[List[str]] = Field(default=None, description="Filter specific tools")
    min_examples: int = Field(default=10, description="Minimum examples required")
    output_name: Optional[str] = Field(default=None, description="Custom dataset name")
    agent_id: Optional[str] = Field(default=None, description="Agent attribution")


class EstimateCostRequest(BaseModel):
    """Request to estimate training cost."""
    dataset_name: str = Field(..., description="Dataset name in Nursery")
    base_model: str = Field(default="3b", description="Model size: 1b, 3b, 7b, 13b, 27b")
    epochs: int = Field(default=3, ge=1, le=20, description="Training epochs")
    provider: str = Field(default="all", description="Provider or 'all'")


class TrainCloudRequest(BaseModel):
    """Request to start cloud training."""
    dataset_name: str = Field(..., description="Dataset name in Nursery")
    base_model: str = Field(..., description="Base model to fine-tune")
    output_name: str = Field(..., description="Name for fine-tuned model")
    provider: str = Field(default="together", description="Cloud provider")
    epochs: int = Field(default=3, ge=1, le=20)
    learning_rate: float = Field(default=1e-5)
    lora_rank: int = Field(default=16, ge=4, le=64)
    agent_id: Optional[str] = Field(default=None, description="Trainer agent")


class TrainLocalRequest(BaseModel):
    """Request to start local training."""
    dataset_name: str = Field(..., description="Dataset name in Nursery")
    base_model: str = Field(default="TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    output_name: Optional[str] = Field(default=None)
    epochs: int = Field(default=3, ge=1, le=20)
    batch_size: int = Field(default=4, ge=1, le=16)
    learning_rate: float = Field(default=2e-5)
    lora_rank: int = Field(default=8, ge=4, le=32)
    use_cpu: bool = Field(default=False)
    agent_id: Optional[str] = Field(default=None, description="Trainer agent")


class RegisterModelRequest(BaseModel):
    """Request to register a model in Village."""
    model_name: str = Field(..., description="Model name")
    model_path: Optional[str] = Field(default=None, description="Path to model files")
    description: Optional[str] = Field(default=None)
    capabilities: Optional[List[str]] = Field(default=None)
    base_model: Optional[str] = Field(default=None)
    trainer_agent: Optional[str] = Field(default=None)
    performance: Optional[Dict[str, Any]] = Field(default=None)


class DiscoverModelsRequest(BaseModel):
    """Request to search for models."""
    query: Optional[str] = Field(default=None, description="Search query")
    capability: Optional[str] = Field(default=None, description="Filter by capability")
    trainer_filter: Optional[str] = Field(default=None, description="Filter by trainer")
    limit: int = Field(default=10, ge=1, le=50)


class CreateApprenticeRequest(BaseModel):
    """Request to create an apprentice."""
    master_agent: str = Field(..., description="Master agent ID")
    apprentice_name: str = Field(..., description="Apprentice name")
    specialization: str = Field(..., description="Specialization focus")
    training_data_query: Optional[str] = Field(default=None)
    base_model: str = Field(default="TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    min_examples: int = Field(default=20)
    auto_train: bool = Field(default=False)


class DeployOllamaRequest(BaseModel):
    """Request to deploy model to Ollama."""
    model_name: str = Field(..., description="Model name in Nursery")
    ollama_name: Optional[str] = Field(default=None, description="Name in Ollama")
    quantize: str = Field(default="q4_k_m", description="Quantization level")


class TestModelRequest(BaseModel):
    """Request to test a model."""
    model_name: str = Field(..., description="Model name")
    prompt: str = Field(..., description="Test prompt")
    provider: str = Field(default="local", description="Where to run: local, together, ollama")


class CompareModelsRequest(BaseModel):
    """Request to compare two models."""
    model_a: str = Field(..., description="First model")
    model_b: str = Field(..., description="Second model")
    test_prompts: List[str] = Field(..., description="Test prompts")


# =============================================================================
# Data Garden Routes
# =============================================================================

@router.get("/datasets")
async def list_datasets():
    """List all training datasets in the Nursery."""
    return nursery_list_datasets()


@router.post("/datasets/generate")
async def generate_data(request: GenerateDataRequest):
    """Generate synthetic training data for a tool."""
    return nursery_generate_data(
        tool_name=request.tool_name,
        num_examples=request.num_examples,
        variation_level=request.variation_level,
        output_name=request.output_name,
        agent_id=request.agent_id,
    )


@router.post("/datasets/extract")
async def extract_conversations(request: ExtractConversationsRequest):
    """Extract training data from conversation history."""
    return nursery_extract_conversations(
        source=request.source,
        tools_filter=request.tools_filter,
        min_examples=request.min_examples,
        output_name=request.output_name,
        agent_id=request.agent_id,
    )


# =============================================================================
# Training Forge Routes
# =============================================================================

@router.post("/training/estimate")
async def estimate_cost(request: EstimateCostRequest):
    """Estimate training cost for a dataset."""
    return nursery_estimate_cost(
        dataset_name=request.dataset_name,
        base_model=request.base_model,
        epochs=request.epochs,
        provider=request.provider,
    )


@router.post("/training/cloud")
async def train_cloud(request: TrainCloudRequest):
    """Start a cloud training job."""
    return nursery_train_cloud(
        dataset_name=request.dataset_name,
        base_model=request.base_model,
        output_name=request.output_name,
        provider=request.provider,
        epochs=request.epochs,
        learning_rate=request.learning_rate,
        lora_rank=request.lora_rank,
        agent_id=request.agent_id,
    )


@router.post("/training/local")
async def train_local(request: TrainLocalRequest):
    """Start local LoRA training."""
    return nursery_train_local(
        dataset_name=request.dataset_name,
        base_model=request.base_model,
        output_name=request.output_name,
        epochs=request.epochs,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate,
        lora_rank=request.lora_rank,
        use_cpu=request.use_cpu,
        agent_id=request.agent_id,
    )


@router.get("/training/jobs")
async def list_jobs(
    status_filter: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List training jobs."""
    return nursery_list_jobs(status_filter=status_filter, limit=limit)


@router.get("/training/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific training job."""
    return nursery_job_status(job_id)


@router.websocket("/training/jobs/{job_id}/progress")
async def training_progress(websocket: WebSocket, job_id: str):
    """WebSocket for real-time training progress updates."""
    await websocket.accept()
    logger.info(f"WebSocket connected for job {job_id}")

    try:
        while True:
            status = nursery_job_status(job_id)
            await websocket.send_json(status)

            # Check if job is complete
            job_status = status.get("status", "unknown")
            if job_status in ("completed", "failed", "cancelled"):
                logger.info(f"Job {job_id} finished with status: {job_status}")
                break

            await asyncio.sleep(5)  # Poll every 5 seconds

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        await websocket.close()


# =============================================================================
# Model Cradle Routes
# =============================================================================

@router.get("/models")
async def list_models():
    """List all trained models in the Nursery."""
    return nursery_list_models()


@router.post("/models/register")
async def register_model(request: RegisterModelRequest):
    """Register a model in the Village registry."""
    return nursery_register_model(
        model_name=request.model_name,
        model_path=request.model_path,
        description=request.description,
        capabilities=request.capabilities,
        base_model=request.base_model,
        trainer_agent=request.trainer_agent,
        performance=request.performance,
    )


@router.post("/models/discover")
async def discover_models(request: DiscoverModelsRequest):
    """Search for registered models in the Village."""
    return nursery_discover_models(
        query=request.query,
        capability=request.capability,
        trainer_filter=request.trainer_filter,
        limit=request.limit,
    )


@router.get("/models/discover")
async def discover_models_get(
    query: Optional[str] = Query(default=None),
    capability: Optional[str] = Query(default=None),
    trainer_filter: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Search for registered models (GET version)."""
    return nursery_discover_models(
        query=query,
        capability=capability,
        trainer_filter=trainer_filter,
        limit=limit,
    )


@router.post("/models/deploy-ollama")
async def deploy_ollama(request: DeployOllamaRequest):
    """Deploy a model to local Ollama."""
    return nursery_deploy_ollama(
        model_name=request.model_name,
        ollama_name=request.ollama_name,
        quantize=request.quantize,
    )


@router.post("/models/test")
async def test_model(request: TestModelRequest):
    """Test a trained model with a prompt."""
    return nursery_test_model(
        model_name=request.model_name,
        prompt=request.prompt,
        provider=request.provider,
    )


@router.post("/models/compare")
async def compare_models(request: CompareModelsRequest):
    """A/B compare two models."""
    return nursery_compare_models(
        model_a=request.model_a,
        model_b=request.model_b,
        test_prompts=request.test_prompts,
    )


# =============================================================================
# Apprentice Protocol Routes
# =============================================================================

@router.get("/apprentices")
async def list_apprentices(
    master_filter: Optional[str] = Query(default=None, description="Filter by master agent"),
    trained_only: bool = Query(default=False, description="Only trained apprentices"),
):
    """List all apprentices in the Nursery."""
    return nursery_list_apprentices(
        master_filter=master_filter,
        trained_only=trained_only,
    )


@router.post("/apprentices")
async def create_apprentice(request: CreateApprenticeRequest):
    """Create an apprentice model for an agent."""
    return nursery_create_apprentice(
        master_agent=request.master_agent,
        apprentice_name=request.apprentice_name,
        specialization=request.specialization,
        training_data_query=request.training_data_query,
        base_model=request.base_model,
        min_examples=request.min_examples,
        auto_train=request.auto_train,
    )


# =============================================================================
# Village Activity Routes
# =============================================================================

@router.get("/village-activity")
async def get_village_activity(
    limit: int = Query(default=10, ge=1, le=50, description="Number of events"),
):
    """Get recent training activity from the Village."""
    if not VILLAGE_AVAILABLE:
        return {
            "success": False,
            "error": "Village module not available",
            "events": [],
        }

    try:
        results = vector_search_village(
            query="training dataset model nursery apprentice",
            top_k=limit,
        )

        if results.get("success"):
            events = []
            for r in results.get("results", []):
                events.append({
                    "agent_id": r.get("agent_id", "unknown"),
                    "content": r.get("content", "")[:200],
                    "posted_at": r.get("posted_at"),
                    "message_type": r.get("message_type"),
                })
            return {
                "success": True,
                "events": events,
                "total": len(events),
            }
        else:
            return {
                "success": False,
                "error": results.get("error", "Search failed"),
                "events": [],
            }

    except Exception as e:
        logger.error(f"Village activity error: {e}")
        return {
            "success": False,
            "error": str(e),
            "events": [],
        }


# =============================================================================
# Summary/Stats Endpoint
# =============================================================================

@router.get("/stats")
async def get_nursery_stats():
    """Get Nursery statistics summary."""
    datasets = nursery_list_datasets()
    models = nursery_list_models()
    jobs = nursery_list_jobs()
    apprentices = nursery_list_apprentices()

    jobs_list = jobs.get("jobs", [])
    completed_jobs = len([j for j in jobs_list if j.get("status") == "completed"])
    running_jobs = len([j for j in jobs_list if j.get("status") in ("pending", "running")])

    return {
        "success": True,
        "stats": {
            "datasets": datasets.get("total", 0),
            "models": models.get("total", 0),
            "jobs_completed": completed_jobs,
            "jobs_running": running_jobs,
            "apprentices": apprentices.get("total", 0),
        },
    }
