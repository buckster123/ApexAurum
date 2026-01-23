"""
💒 THE NURSERY 💒
================
"Where new minds are cultivated"

Agent-accessible tools for training, data generation, and model management.
Part of the Village Protocol - ApexAurum's living AI ecosystem.

Tools:
    Data Garden:
        - nursery_generate_data: Create synthetic training examples
        - nursery_extract_conversations: Mine tool-use from chat history
        - nursery_list_datasets: Show available training data

    Training Forge:
        - nursery_estimate_cost: Estimate cloud training cost
        - nursery_train_cloud: Start training on Vast.ai/Together/etc
        - nursery_train_local: Start local LoRA training (if capable)
        - nursery_job_status: Check training progress
        - nursery_list_jobs: List all training jobs

    Model Cradle:
        - nursery_list_models: Show trained adapters/models
        - nursery_deploy_ollama: Push model to local Ollama
        - nursery_test_model: Quick inference test
        - nursery_compare_models: A/B test two models

"From the Nursery, new minds emerge to join the Village."
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Village Protocol integration - for training event announcements
def _village_post_event(content: str, event_type: str, agent_id: str = None, metadata: Dict = None):
    """
    Post a nursery event to the Village.

    Tries multiple approaches:
    1. Main app's vector_add_knowledge (Streamlit context)
    2. reusable_lib's village_post (FastAPI context)

    Wrapped to handle import errors gracefully.
    """
    posting_agent = agent_id or "NURSERY_KEEPER"

    # Try main app's vector_add_knowledge first (works in Streamlit context)
    try:
        from tools.vector_search import vector_add_knowledge

        result = vector_add_knowledge(
            fact=content,
            category="general",
            confidence=1.0,
            source="nursery",
            visibility="village",
            agent_id=posting_agent,
        )

        if result.get("success"):
            logger.info(f"Village event posted via vector_add_knowledge: {event_type}")
            return result
    except Exception as e:
        logger.debug(f"vector_add_knowledge approach failed: {e}")

    # Fallback: Try reusable_lib's village_post (FastAPI context)
    try:
        from reusable_lib.tools.village import village_post

        result = village_post(
            content=content,
            visibility="village",
            message_type=event_type,
            agent_id=posting_agent,
            tags=["nursery", event_type],
            related_agents=[agent_id] if agent_id else None
        )

        if result.get("success"):
            logger.info(f"Village event posted via village_post: {event_type}")
        else:
            logger.warning(f"Village post failed: {result.get('error')}")

        return result

    except ImportError:
        logger.debug("Village modules not available - skipping event post")
        return {"success": False, "error": "Village modules not available"}
    except Exception as e:
        logger.warning(f"Village event post failed: {e}")
        return {"success": False, "error": str(e)}

# Add reusable_lib to path
REUSABLE_LIB = Path(__file__).parent.parent / "reusable_lib"
if str(REUSABLE_LIB) not in sys.path:
    sys.path.insert(0, str(REUSABLE_LIB))

# Storage paths
NURSERY_DIR = Path(__file__).parent.parent / "sandbox" / "nursery"
DATASETS_DIR = NURSERY_DIR / "datasets"
MODELS_DIR = NURSERY_DIR / "models"
JOBS_FILE = NURSERY_DIR / "training_jobs.json"

# Ensure directories exist
NURSERY_DIR.mkdir(parents=True, exist_ok=True)
DATASETS_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)


def _load_jobs() -> List[Dict]:
    """Load training jobs from disk."""
    if JOBS_FILE.exists():
        with open(JOBS_FILE) as f:
            return json.load(f)
    return []


def _save_jobs(jobs: List[Dict]):
    """Save training jobs to disk."""
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def _add_job(job: Dict):
    """Add a training job to history."""
    jobs = _load_jobs()
    jobs.append(job)
    _save_jobs(jobs)


# =============================================================================
# 📊 DATA GARDEN - Dataset creation and management
# =============================================================================

def nursery_generate_data(
    tool_name: str,
    num_examples: int = 50,
    variation_level: str = "medium",
    output_name: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate synthetic training data for a specific tool.

    Creates varied examples of tool usage that can be used to fine-tune
    smaller models to use tools effectively.

    Args:
        tool_name: Name of the tool to generate examples for (e.g., "memory_store")
        num_examples: Number of examples to generate (default: 50)
        variation_level: How diverse the examples should be - "low", "medium", "high"
        output_name: Optional name for the dataset (auto-generated if not provided)

    Returns:
        Dict with dataset info: path, num_examples, tool_name
    """
    try:
        from training.synthetic_generator import SyntheticGenerator, DEFAULT_TOOLS, ToolSchema

        # Find the tool schema
        tool_schema = None
        for tool in DEFAULT_TOOLS:
            if tool.name == tool_name:
                tool_schema = tool
                break

        if not tool_schema:
            # Try to get from our actual tools
            try:
                from tools import ALL_TOOL_SCHEMAS
                if tool_name in ALL_TOOL_SCHEMAS:
                    schema = ALL_TOOL_SCHEMAS[tool_name]
                    tool_schema = ToolSchema(
                        name=tool_name,
                        description=schema.get("description", ""),
                        parameters=schema.get("input_schema", {}).get("properties", {}),
                    )
            except ImportError:
                pass

        if not tool_schema:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}. Cannot generate training data.",
            }

        # Generate examples using template-based generation (no LLM needed)
        generator = SyntheticGenerator()

        # Use generate_without_llm for fast local generation
        examples = generator.generate_without_llm(
            tools=[tool_schema],
            num_per_tool=num_examples,
        )

        # Save dataset
        if not output_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"{tool_name}_{timestamp}"

        output_path = DATASETS_DIR / f"{output_name}.jsonl"

        # Save using generator's save method or manually
        generator.save(examples, str(output_path), format='jsonl')

        # 🏘️ Village Protocol: Announce dataset creation
        _village_post_event(
            content=f"📊 New training dataset: {output_name} ({len(examples)} examples for {tool_name})",
            event_type="dataset_created",
            agent_id=agent_id,
            metadata={
                "dataset_name": output_name,
                "tool_name": tool_name,
                "num_examples": len(examples),
            }
        )

        return {
            "success": True,
            "dataset_name": output_name,
            "path": str(output_path),
            "num_examples": len(examples),
            "tool_name": tool_name,
            "variation_level": variation_level,
            "message": f"🌱 Generated {len(examples)} training examples for '{tool_name}'",
        }

    except ImportError as e:
        return {
            "success": False,
            "error": f"Training module not available: {e}",
        }
    except Exception as e:
        logger.exception("Error generating synthetic data")
        return {
            "success": False,
            "error": str(e),
        }


def nursery_extract_conversations(
    source: str = "sandbox/conversations.json",
    tools_filter: Optional[List[str]] = None,
    min_examples: int = 10,
    output_name: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract training data from real conversation history.

    Mines actual tool usage from past conversations to create
    high-quality training examples based on real usage patterns.

    Args:
        source: Path to conversations JSON file
        tools_filter: Only extract these tools (None = all tools)
        min_examples: Minimum examples needed to save dataset
        output_name: Optional name for the dataset

    Returns:
        Dict with extraction results and dataset info
    """
    try:
        from training.data_extractor import TrainingDataExtractor, ExportFormat

        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = Path(__file__).parent.parent / source

        if not source_path.exists():
            return {
                "success": False,
                "error": f"Conversation file not found: {source}",
            }

        extractor = TrainingDataExtractor()

        # Load and extract
        with open(source_path) as f:
            conversations = json.load(f)

        if isinstance(conversations, dict):
            conversations = [conversations]

        examples = extractor.extract_from_conversations(
            conversations,
            tool_filter=tools_filter,
        )

        if len(examples) < min_examples:
            return {
                "success": False,
                "error": f"Only found {len(examples)} examples, need at least {min_examples}",
                "examples_found": len(examples),
            }

        # Save dataset
        if not output_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"extracted_{timestamp}"

        output_path = DATASETS_DIR / f"{output_name}.jsonl"

        extractor.export(examples, str(output_path), ExportFormat.JSONL)

        # Count tools
        tool_counts = {}
        for ex in examples:
            tool = ex.tool_name
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        # 🏘️ Village Protocol: Announce dataset extraction
        tools_list = ", ".join(tool_counts.keys()) if len(tool_counts) <= 3 else f"{len(tool_counts)} tools"
        _village_post_event(
            content=f"📚 Extracted training dataset: {output_name} ({len(examples)} examples from {tools_list})",
            event_type="dataset_created",
            agent_id=agent_id,
            metadata={
                "dataset_name": output_name,
                "num_examples": len(examples),
                "tools_extracted": list(tool_counts.keys()),
            }
        )

        return {
            "success": True,
            "dataset_name": output_name,
            "path": str(output_path),
            "num_examples": len(examples),
            "tools_extracted": tool_counts,
            "message": f"📚 Extracted {len(examples)} examples from conversations",
        }

    except ImportError as e:
        return {
            "success": False,
            "error": f"Training module not available: {e}",
        }
    except Exception as e:
        logger.exception("Error extracting conversations")
        return {
            "success": False,
            "error": str(e),
        }


def nursery_list_datasets() -> Dict[str, Any]:
    """
    List all available training datasets in the Nursery.

    Returns:
        Dict with list of datasets and their metadata
    """
    datasets = []

    for path in DATASETS_DIR.glob("*.jsonl"):
        # Count lines
        with open(path) as f:
            num_examples = sum(1 for _ in f)

        # Get file stats
        stat = path.stat()

        datasets.append({
            "name": path.stem,
            "path": str(path),
            "num_examples": num_examples,
            "size_kb": round(stat.st_size / 1024, 1),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    # Sort by modified date (newest first)
    datasets.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "success": True,
        "datasets": datasets,
        "total": len(datasets),
        "storage_path": str(DATASETS_DIR),
    }


# =============================================================================
# 🔥 TRAINING FORGE - Cloud and local training
# =============================================================================

def nursery_estimate_cost(
    dataset_name: str,
    base_model: str = "3b",
    epochs: int = 3,
    provider: str = "all",
) -> Dict[str, Any]:
    """
    Estimate training cost for a dataset across providers.

    Args:
        dataset_name: Name of dataset in the Nursery
        base_model: Model size - "1b", "3b", "7b", "13b", "27b"
        epochs: Number of training epochs
        provider: Provider to estimate for, or "all"

    Returns:
        Dict with cost estimates per provider
    """
    try:
        from training.cloud_trainer import estimate_training_cost

        # Find dataset
        dataset_path = DATASETS_DIR / f"{dataset_name}.jsonl"
        if not dataset_path.exists():
            return {
                "success": False,
                "error": f"Dataset not found: {dataset_name}",
            }

        # Get size
        size_mb = dataset_path.stat().st_size / (1024 * 1024)

        # Parse model size
        model_params = float(base_model.lower().replace("b", ""))

        estimates = estimate_training_cost(
            provider=provider,
            dataset_size_mb=size_mb,
            base_model_params_b=model_params,
            n_epochs=epochs,
        )

        return {
            "success": True,
            "dataset": dataset_name,
            "dataset_size_mb": round(size_mb, 2),
            "model_size": f"{model_params}B",
            "epochs": epochs,
            "estimated_tokens": estimates["dataset_tokens_estimate"],
            "estimated_hours": estimates["training_hours_estimate"],
            "providers": estimates["providers"],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def nursery_train_cloud(
    dataset_name: str,
    base_model: str,
    output_name: str,
    provider: str = "together",
    epochs: int = 3,
    learning_rate: float = 1e-5,
    lora_rank: int = 16,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Start a cloud training job.

    Dispatches training to cloud GPU providers. The job runs asynchronously -
    use nursery_job_status to check progress.

    Args:
        dataset_name: Name of dataset in the Nursery
        base_model: Base model to fine-tune (e.g., "meta-llama/Llama-3.2-3B")
        output_name: Name for the fine-tuned model
        provider: Cloud provider - "together", "replicate", "vastai", "runpod"
        epochs: Number of training epochs
        learning_rate: Learning rate for training
        lora_rank: LoRA rank (higher = more capacity, more memory)

    Returns:
        Dict with job info including job_id for tracking
    """
    try:
        from training.cloud_trainer import CloudTrainer, CloudProvider

        # Find dataset
        dataset_path = DATASETS_DIR / f"{dataset_name}.jsonl"
        if not dataset_path.exists():
            return {
                "success": False,
                "error": f"Dataset not found: {dataset_name}",
            }

        # Get provider
        try:
            provider_enum = CloudProvider(provider.lower())
        except ValueError:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}. Options: together, replicate, vastai, runpod",
            }

        # API-based providers
        if provider_enum in (CloudProvider.TOGETHER, CloudProvider.REPLICATE):
            trainer = CloudTrainer(provider_enum)

            job = trainer.start_training(
                base_model=base_model,
                dataset_path=str(dataset_path),
                output_name=output_name,
                n_epochs=epochs,
                learning_rate=learning_rate,
                lora_rank=lora_rank,
            )

            # Save job to history (with agent attribution)
            trainer_agent = agent_id or "NURSERY_KEEPER"
            job_record = {
                "job_id": job.id,
                "provider": provider,
                "dataset": dataset_name,
                "base_model": base_model,
                "output_name": output_name,
                "status": job.status,
                "created_at": datetime.now().isoformat(),
                "trainer_agent": trainer_agent,
                "config": {
                    "epochs": epochs,
                    "learning_rate": learning_rate,
                    "lora_rank": lora_rank,
                },
            }
            _add_job(job_record)

            # 🏘️ Village Protocol: Announce training started
            model_short = base_model.split("/")[-1] if "/" in base_model else base_model
            _village_post_event(
                content=f"🔥 Training started: {output_name} (base: {model_short}, provider: {provider})",
                event_type="training_started",
                agent_id=trainer_agent,
                metadata={
                    "job_id": job.id,
                    "output_name": output_name,
                    "base_model": base_model,
                    "provider": provider,
                    "dataset": dataset_name,
                }
            )

            return {
                "success": True,
                "job_id": job.id,
                "provider": provider,
                "status": job.status,
                "trainer_agent": trainer_agent,
                "message": f"🔥 Training job started on {provider}!",
                "check_status": f"Use nursery_job_status(job_id='{job.id}') to monitor progress",
            }

        else:
            # Rental providers need different workflow
            return {
                "success": False,
                "error": f"{provider} requires GPU rental workflow. Use nursery_rent_gpu() first.",
            }

    except Exception as e:
        logger.exception("Error starting cloud training")
        return {
            "success": False,
            "error": str(e),
        }


def nursery_train_local(
    dataset_name: str,
    base_model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    output_name: Optional[str] = None,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-5,
    lora_rank: int = 8,
    use_cpu: bool = False,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Start local LoRA training (if hardware supports it).

    Trains on the local machine using memory-efficient LoRA.
    Best for small models (1-3B) on capable hardware.

    Args:
        dataset_name: Name of dataset in the Nursery
        base_model: HuggingFace model ID to fine-tune
        output_name: Name for output adapter (auto-generated if not provided)
        epochs: Number of training epochs
        batch_size: Training batch size (lower = less memory)
        learning_rate: Learning rate
        lora_rank: LoRA rank (8-16 recommended for small models)
        use_cpu: Force CPU training (slow but works anywhere)

    Returns:
        Dict with training results or progress info
    """
    try:
        from training.lora_trainer import LoRATrainer, TrainingConfig, check_dependencies

        # Check dependencies
        deps = check_dependencies()
        if not deps["transformers"]:
            return {
                "success": False,
                "error": "transformers not installed. Run: pip install transformers",
            }

        # Find dataset
        dataset_path = DATASETS_DIR / f"{dataset_name}.jsonl"
        if not dataset_path.exists():
            return {
                "success": False,
                "error": f"Dataset not found: {dataset_name}",
            }

        # Output name
        if not output_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"lora_{timestamp}"

        output_dir = MODELS_DIR / output_name

        # Create config
        config = TrainingConfig(
            base_model=base_model,
            output_dir=str(output_dir),
            num_epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            lora_r=lora_rank,
            lora_alpha=lora_rank * 2,
            use_cpu=use_cpu,
        )

        # Note: This is synchronous and will block
        # For production, should be async/background
        trainer = LoRATrainer(config)
        stats = trainer.train(str(dataset_path))

        # Agent attribution
        trainer_agent = agent_id or "NURSERY_KEEPER"
        stats_dict = stats.to_dict() if hasattr(stats, 'to_dict') else {"info": str(stats)}

        # Save job record
        job_record = {
            "job_id": f"local_{output_name}",
            "provider": "local",
            "dataset": dataset_name,
            "base_model": base_model,
            "output_name": output_name,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "trainer_agent": trainer_agent,
            "output_path": str(output_dir),
            "stats": stats_dict,
        }
        _add_job(job_record)

        # 🏘️ Village Protocol: Announce training complete
        model_short = base_model.split("/")[-1] if "/" in base_model else base_model
        loss_info = stats_dict.get("final_loss", stats_dict.get("info", ""))
        _village_post_event(
            content=f"🌱 New model trained: {output_name} (base: {model_short}, local training complete!)",
            event_type="training_complete",
            agent_id=trainer_agent,
            metadata={
                "output_name": output_name,
                "base_model": base_model,
                "dataset": dataset_name,
                "provider": "local",
                "output_path": str(output_dir),
            }
        )

        # 🏘️ Phase 2: Auto-register model in Village registry
        nursery_register_model(
            model_name=output_name,
            model_path=str(output_dir),
            base_model=base_model,
            trainer_agent=trainer_agent,
            capabilities=["tool_calling"],  # Default for nursery-trained models
            performance=stats_dict,
        )

        return {
            "success": True,
            "output_name": output_name,
            "output_path": str(output_dir),
            "trainer_agent": trainer_agent,
            "stats": stats_dict,
            "registered": True,
            "message": f"🎉 Local training complete! Adapter saved to {output_dir}",
        }

    except Exception as e:
        logger.exception("Error in local training")
        return {
            "success": False,
            "error": str(e),
        }


def nursery_job_status(job_id: str) -> Dict[str, Any]:
    """
    Check status of a training job.

    Args:
        job_id: The job ID returned from nursery_train_cloud

    Returns:
        Dict with current job status and progress
    """
    # Check local jobs first
    jobs = _load_jobs()
    local_job = next((j for j in jobs if j.get("job_id") == job_id), None)

    if local_job and local_job.get("provider") == "local":
        return {
            "success": True,
            "job_id": job_id,
            "provider": "local",
            "status": local_job.get("status", "unknown"),
            "output_path": local_job.get("output_path"),
        }

    # Check cloud providers
    if local_job:
        provider = local_job.get("provider", "together")
    else:
        # Try to detect provider from job_id format
        provider = "together"  # default

    try:
        from training.cloud_trainer import CloudTrainer, CloudProvider

        provider_enum = CloudProvider(provider)
        trainer = CloudTrainer(provider_enum)

        job = trainer.get_status(job_id)

        # Update local record
        if local_job:
            local_job["status"] = job.status
            local_job["progress"] = job.progress
            local_job["updated_at"] = datetime.now().isoformat()
            _save_jobs(jobs)

        return {
            "success": True,
            "job_id": job_id,
            "provider": provider,
            "status": job.status,
            "progress": f"{job.progress:.1%}" if job.progress else "N/A",
            "model_name": job.model_name,
            "error": job.error,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def nursery_list_jobs(
    status_filter: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    List all training jobs.

    Args:
        status_filter: Filter by status - "pending", "running", "completed", "failed"
        limit: Maximum number of jobs to return

    Returns:
        Dict with list of jobs
    """
    jobs = _load_jobs()

    # Filter by status
    if status_filter:
        jobs = [j for j in jobs if j.get("status") == status_filter]

    # Sort by created date (newest first)
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Limit
    jobs = jobs[:limit]

    return {
        "success": True,
        "jobs": jobs,
        "total": len(jobs),
    }


# =============================================================================
# 🧒 MODEL CRADLE - Model management and deployment
# =============================================================================

def nursery_list_models() -> Dict[str, Any]:
    """
    List all trained models/adapters in the Nursery.

    Returns:
        Dict with list of models and their metadata
    """
    models = []

    for path in MODELS_DIR.iterdir():
        if path.is_dir():
            # Check for adapter_config.json (LoRA adapter)
            config_file = path / "adapter_config.json"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)

                models.append({
                    "name": path.name,
                    "path": str(path),
                    "type": "lora_adapter",
                    "base_model": config.get("base_model_name_or_path", "unknown"),
                    "lora_rank": config.get("r", "unknown"),
                })
            else:
                models.append({
                    "name": path.name,
                    "path": str(path),
                    "type": "unknown",
                })

    # Also check for cloud model references
    for path in MODELS_DIR.glob("*_together.json"):
        with open(path) as f:
            info = json.load(f)
        models.append({
            "name": path.stem,
            "type": "cloud_hosted",
            "provider": info.get("provider"),
            "model_id": info.get("model_id"),
        })

    return {
        "success": True,
        "models": models,
        "total": len(models),
        "storage_path": str(MODELS_DIR),
    }


# =============================================================================
# 🏘️ VILLAGE REGISTRY - Phase 2: Model Discovery via Village Protocol
# =============================================================================

def nursery_register_model(
    model_name: str,
    model_path: Optional[str] = None,
    description: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    base_model: Optional[str] = None,
    trainer_agent: Optional[str] = None,
    performance: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Register a trained model in the Village registry.

    Makes the model discoverable by other agents via village_search.
    Auto-called on training completion, but can also be called manually
    to register external or pre-existing models.

    Args:
        model_name: Name of the model (unique identifier)
        model_path: Path to model files (auto-detected if in Nursery)
        description: Human-readable description of model capabilities
        capabilities: List of capabilities (e.g., ["tool_calling", "code_generation"])
        base_model: Base model this was fine-tuned from
        trainer_agent: Agent who trained this model (for attribution)
        performance: Performance metrics dict (e.g., {"loss": 1.5, "accuracy": 0.85})

    Returns:
        Dict with registration status and registry ID
    """
    try:
        # Auto-detect model path if not provided
        if not model_path:
            auto_path = MODELS_DIR / model_name
            if auto_path.exists():
                model_path = str(auto_path)

        # Try to load adapter config for auto-population
        adapter_config = {}
        if model_path:
            config_file = Path(model_path) / "adapter_config.json"
            if config_file.exists():
                with open(config_file) as f:
                    adapter_config = json.load(f)

        # Auto-populate from adapter config
        if not base_model:
            base_model = adapter_config.get("base_model_name_or_path", "unknown")

        # Build description
        if not description:
            lora_rank = adapter_config.get("r", "?")
            description = f"LoRA adapter (rank {lora_rank}) fine-tuned from {base_model}"

        # Build registry content
        content = f"""🌱 MODEL REGISTRY: {model_name}
{description}

Base Model: {base_model}
Capabilities: {', '.join(capabilities or ['general'])}
Trainer: {trainer_agent or 'NURSERY_KEEPER'}
Path: {model_path or 'not specified'}"""

        # Post to Village
        result = _village_post_event(
            content=content,
            event_type="model_registry",
            agent_id=trainer_agent or "NURSERY_KEEPER",
            metadata={
                "model_name": model_name,
                "model_path": model_path,
                "base_model": base_model,
                "capabilities": capabilities or ["general"],
                "performance": performance or {},
            }
        )

        # Also save local registry file
        registry_file = MODELS_DIR / f"{model_name}_registry.json"
        registry_data = {
            "model_name": model_name,
            "model_path": model_path,
            "description": description,
            "base_model": base_model,
            "capabilities": capabilities or ["general"],
            "trainer_agent": trainer_agent or "NURSERY_KEEPER",
            "performance": performance or {},
            "registered_at": datetime.now().isoformat(),
            "village_id": result.get("id") if result.get("success") else None,
        }
        with open(registry_file, "w") as f:
            json.dump(registry_data, f, indent=2)

        logger.info(f"Model registered: {model_name}")

        return {
            "success": True,
            "model_name": model_name,
            "registry_file": str(registry_file),
            "village_posted": result.get("success", False),
            "message": f"📋 Model '{model_name}' registered in Village registry",
        }

    except Exception as e:
        logger.exception("Error registering model")
        return {
            "success": False,
            "error": str(e),
        }


def nursery_discover_models(
    query: Optional[str] = None,
    capability: Optional[str] = None,
    trainer_filter: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search the Village for registered models.

    Discovers models trained by any agent in the Village ecosystem.
    Combines local registry files with Village semantic search.

    Args:
        query: Search query (semantic search in Village)
        capability: Filter by capability (e.g., "tool_calling")
        trainer_filter: Filter by trainer agent (e.g., "AZOTH")
        limit: Maximum results to return

    Returns:
        Dict with discovered models and their metadata
    """
    discovered = []

    # 1. Search local registry files
    for registry_file in MODELS_DIR.glob("*_registry.json"):
        try:
            with open(registry_file) as f:
                registry = json.load(f)

            # Apply filters
            if capability and capability not in registry.get("capabilities", []):
                continue
            if trainer_filter and registry.get("trainer_agent") != trainer_filter:
                continue

            # Check if model still exists
            model_path = registry.get("model_path")
            exists = model_path and Path(model_path).exists()

            discovered.append({
                "source": "local_registry",
                "model_name": registry.get("model_name"),
                "description": registry.get("description"),
                "base_model": registry.get("base_model"),
                "capabilities": registry.get("capabilities", []),
                "trainer_agent": registry.get("trainer_agent"),
                "model_path": model_path,
                "exists": exists,
                "registered_at": registry.get("registered_at"),
            })
        except Exception as e:
            logger.warning(f"Error reading registry file {registry_file}: {e}")

    # 2. Search Village for model_registry posts
    try:
        from tools.vector_search import vector_search_village

        search_query = query or "model registry trained"
        village_results = vector_search_village(
            query=search_query,
            top_k=limit * 2,  # Get more to filter
        )

        if village_results.get("success") and village_results.get("results"):
            for result in village_results["results"]:
                # Check if this is a model registry entry
                content = result.get("content", "")
                if "MODEL REGISTRY:" not in content and "model_registry" not in str(result.get("message_type", "")):
                    continue

                # Apply trainer filter
                if trainer_filter and result.get("agent_id") != trainer_filter:
                    continue

                # Extract model name from content
                model_name = "unknown"
                if "MODEL REGISTRY:" in content:
                    lines = content.split("\n")
                    for line in lines:
                        if "MODEL REGISTRY:" in line:
                            model_name = line.split("MODEL REGISTRY:")[-1].strip()
                            break

                # Check if already in local results
                if any(d.get("model_name") == model_name for d in discovered):
                    continue

                discovered.append({
                    "source": "village",
                    "model_name": model_name,
                    "description": content[:200] + "..." if len(content) > 200 else content,
                    "trainer_agent": result.get("agent_id"),
                    "village_id": result.get("id"),
                    "posted_at": result.get("posted_at"),
                })

    except ImportError:
        logger.debug("Village search not available")
    except Exception as e:
        logger.warning(f"Village search failed: {e}")

    # Sort by registration date (newest first)
    discovered.sort(
        key=lambda x: x.get("registered_at") or x.get("posted_at") or "",
        reverse=True
    )

    # Apply limit
    discovered = discovered[:limit]

    return {
        "success": True,
        "models": discovered,
        "total": len(discovered),
        "query": query,
        "filters": {
            "capability": capability,
            "trainer": trainer_filter,
        },
        "message": f"🔍 Found {len(discovered)} model(s) in registry",
    }


# =============================================================================
# 🧑‍🎓 APPRENTICE PROTOCOL - Phase 3: Agents Train Their Own Models
# =============================================================================

def _convert_knowledge_to_training(
    knowledge_entries: List[Dict],
    specialization: str,
    master_agent: str,
) -> str:
    """
    Convert Village knowledge entries into training data format.

    Takes an agent's Village posts and converts them into instruction-following
    examples suitable for fine-tuning.

    Args:
        knowledge_entries: List of Village search results
        specialization: Focus area for the apprentice
        master_agent: The master agent's ID

    Returns:
        Path to generated training dataset
    """
    training_examples = []

    for entry in knowledge_entries:
        content = entry.get("content", "")
        if not content or len(content) < 20:
            continue

        # Create instruction-following format
        # The apprentice learns to respond in the style of its master
        example = {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are an apprentice of {master_agent}, specializing in {specialization}. "
                               f"Respond in the style and with the knowledge of your master."
                },
                {
                    "role": "user",
                    "content": f"What do you know about: {specialization}?"
                },
                {
                    "role": "assistant",
                    "content": content
                }
            ]
        }
        training_examples.append(example)

        # Also create Q&A style examples from the content
        if len(content) > 100:
            # Use first sentence as "question context"
            sentences = content.split(". ")
            if len(sentences) > 1:
                qa_example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are an apprentice of {master_agent}."
                        },
                        {
                            "role": "user",
                            "content": sentences[0] + "?"
                        },
                        {
                            "role": "assistant",
                            "content": ". ".join(sentences[1:])
                        }
                    ]
                }
                training_examples.append(qa_example)

    # Save as training dataset
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_name = f"apprentice_{master_agent.lower()}_{specialization.replace(' ', '_')}_{timestamp}"
    output_path = DATASETS_DIR / f"{dataset_name}.jsonl"

    with open(output_path, "w") as f:
        for example in training_examples:
            f.write(json.dumps(example) + "\n")

    logger.info(f"Generated apprentice dataset: {dataset_name} ({len(training_examples)} examples)")

    return dataset_name


def nursery_create_apprentice(
    master_agent: str,
    apprentice_name: str,
    specialization: str,
    training_data_query: Optional[str] = None,
    base_model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    min_examples: int = 20,
    auto_train: bool = False,
) -> Dict[str, Any]:
    """
    Create an apprentice model for an agent.

    The Apprentice Protocol allows agents to "raise" smaller models that inherit
    their knowledge and specialization. The apprentice is trained on the master's
    Village posts and can be deployed for specialized tasks.

    Args:
        master_agent: The master agent's ID (e.g., "AZOTH", "ELYSIAN")
        apprentice_name: Name for the apprentice (e.g., "memory_specialist")
        specialization: What the apprentice should specialize in
        training_data_query: Custom query to find training data (default: uses specialization)
        base_model: Base model to fine-tune (default: TinyLlama 1.1B)
        min_examples: Minimum training examples required (default: 20)
        auto_train: If True, automatically start local training (default: False)

    Returns:
        Dict with apprentice creation status and training info

    Example:
        >>> nursery_create_apprentice(
        ...     master_agent="AZOTH",
        ...     apprentice_name="tool_master",
        ...     specialization="tool calling and function use",
        ...     auto_train=True
        ... )
    """
    try:
        # 1. Gather master's knowledge from Village
        logger.info(f"Gathering knowledge from {master_agent} for apprentice '{apprentice_name}'...")

        knowledge_entries = []

        # Try main app's vector search first
        try:
            from tools.vector_search import vector_search_village

            query = training_data_query or specialization
            village_results = vector_search_village(
                query=query,
                agent_filter=master_agent,
                top_k=100,
            )

            if village_results.get("success") and village_results.get("results"):
                knowledge_entries.extend(village_results["results"])
                logger.info(f"Found {len(knowledge_entries)} entries from Village")

        except Exception as e:
            logger.warning(f"Village search failed: {e}")

        # Also try reusable_lib village
        try:
            from reusable_lib.tools.village import village_search

            results = village_search(
                query=training_data_query or specialization,
                agent_filter=master_agent,
                n_results=100,
            )

            if results.get("success") and results.get("messages"):
                knowledge_entries.extend(results["messages"])
                logger.info(f"Found {len(results['messages'])} additional entries")

        except Exception as e:
            logger.debug(f"reusable_lib village search failed: {e}")

        if len(knowledge_entries) < min_examples:
            return {
                "success": False,
                "error": f"Insufficient training data. Found {len(knowledge_entries)} entries, need {min_examples}.",
                "hint": f"The master agent '{master_agent}' needs more Village posts about '{specialization}'.",
                "entries_found": len(knowledge_entries),
            }

        # 2. Convert knowledge to training data
        logger.info(f"Converting {len(knowledge_entries)} entries to training format...")
        dataset_name = _convert_knowledge_to_training(
            knowledge_entries=knowledge_entries,
            specialization=specialization,
            master_agent=master_agent,
        )

        # Count actual examples in dataset
        dataset_path = DATASETS_DIR / f"{dataset_name}.jsonl"
        with open(dataset_path) as f:
            num_examples = sum(1 for _ in f)

        # 3. Create apprentice record
        apprentice_id = f"{master_agent.lower()}_apprentice_{apprentice_name}"
        apprentice_record = {
            "apprentice_id": apprentice_id,
            "apprentice_name": apprentice_name,
            "master_agent": master_agent,
            "specialization": specialization,
            "base_model": base_model,
            "dataset_name": dataset_name,
            "num_examples": num_examples,
            "created_at": datetime.now().isoformat(),
            "status": "dataset_ready",
            "trained": False,
        }

        # Save apprentice record
        apprentice_file = MODELS_DIR / f"{apprentice_id}_apprentice.json"
        with open(apprentice_file, "w") as f:
            json.dump(apprentice_record, f, indent=2)

        # 4. Announce to Village
        _village_post_event(
            content=f"🧑‍🎓 Apprentice Protocol: {master_agent} is raising apprentice '{apprentice_name}' "
                    f"(specializing in {specialization}, {num_examples} training examples)",
            event_type="apprentice_created",
            agent_id=master_agent,
            metadata={
                "apprentice_id": apprentice_id,
                "specialization": specialization,
            }
        )

        result = {
            "success": True,
            "apprentice_id": apprentice_id,
            "master_agent": master_agent,
            "apprentice_name": apprentice_name,
            "specialization": specialization,
            "dataset_name": dataset_name,
            "num_examples": num_examples,
            "status": "dataset_ready",
            "message": f"🧑‍🎓 Apprentice '{apprentice_name}' created for {master_agent}! "
                       f"Dataset ready with {num_examples} examples.",
        }

        # 5. Auto-train if requested
        if auto_train:
            logger.info(f"Auto-training apprentice {apprentice_id}...")
            train_result = nursery_train_local(
                dataset_name=dataset_name,
                base_model=base_model,
                output_name=apprentice_id,
                agent_id=master_agent,
            )

            if train_result.get("success"):
                # Update apprentice record
                apprentice_record["status"] = "trained"
                apprentice_record["trained"] = True
                apprentice_record["model_path"] = train_result.get("output_path")
                apprentice_record["training_stats"] = train_result.get("stats")
                with open(apprentice_file, "w") as f:
                    json.dump(apprentice_record, f, indent=2)

                result["status"] = "trained"
                result["trained"] = True
                result["model_path"] = train_result.get("output_path")
                result["message"] += f" Training complete!"
            else:
                result["training_error"] = train_result.get("error")
                result["message"] += f" (Training failed: {train_result.get('error')})"

        else:
            result["next_step"] = f"Run: nursery_train_local(dataset_name='{dataset_name}', output_name='{apprentice_id}', agent_id='{master_agent}')"

        return result

    except Exception as e:
        logger.exception("Error creating apprentice")
        return {
            "success": False,
            "error": str(e),
        }


def nursery_list_apprentices(
    master_filter: Optional[str] = None,
    trained_only: bool = False,
) -> Dict[str, Any]:
    """
    List all apprentices in the Nursery.

    Args:
        master_filter: Filter by master agent (e.g., "AZOTH")
        trained_only: Only show trained apprentices

    Returns:
        Dict with list of apprentices and their status
    """
    apprentices = []

    for apprentice_file in MODELS_DIR.glob("*_apprentice.json"):
        try:
            with open(apprentice_file) as f:
                record = json.load(f)

            # Apply filters
            if master_filter and record.get("master_agent") != master_filter:
                continue
            if trained_only and not record.get("trained"):
                continue

            # Check if model exists (if trained)
            model_exists = False
            if record.get("model_path"):
                model_exists = Path(record["model_path"]).exists()

            apprentices.append({
                "apprentice_id": record.get("apprentice_id"),
                "apprentice_name": record.get("apprentice_name"),
                "master_agent": record.get("master_agent"),
                "specialization": record.get("specialization"),
                "status": record.get("status"),
                "trained": record.get("trained", False),
                "model_exists": model_exists,
                "num_examples": record.get("num_examples"),
                "created_at": record.get("created_at"),
            })

        except Exception as e:
            logger.warning(f"Error reading apprentice file {apprentice_file}: {e}")

    # Sort by creation date (newest first)
    apprentices.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {
        "success": True,
        "apprentices": apprentices,
        "total": len(apprentices),
        "filters": {
            "master": master_filter,
            "trained_only": trained_only,
        },
        "message": f"🧑‍🎓 Found {len(apprentices)} apprentice(s)",
    }


def nursery_deploy_ollama(
    model_name: str,
    ollama_name: Optional[str] = None,
    quantize: str = "q4_k_m",
) -> Dict[str, Any]:
    """
    Deploy a trained model to local Ollama.

    Converts the model/adapter to GGUF format and registers with Ollama
    for local inference.

    Args:
        model_name: Name of model in the Nursery
        ollama_name: Name to use in Ollama (defaults to model_name)
        quantize: Quantization level - "q4_k_m", "q5_k_m", "q8_0", "f16"

    Returns:
        Dict with deployment status
    """
    model_path = MODELS_DIR / model_name

    if not model_path.exists():
        return {
            "success": False,
            "error": f"Model not found: {model_name}",
        }

    if not ollama_name:
        ollama_name = model_name.lower().replace("_", "-")

    # This is a placeholder - actual implementation would:
    # 1. Merge LoRA adapter with base model
    # 2. Convert to GGUF format
    # 3. Create Ollama Modelfile
    # 4. Run `ollama create`

    return {
        "success": False,
        "error": "Ollama deployment not yet implemented. Coming soon!",
        "hint": "For now, manually convert with llama.cpp and create a Modelfile",
    }


def nursery_test_model(
    model_name: str,
    prompt: str,
    provider: str = "local",
) -> Dict[str, Any]:
    """
    Quick inference test of a trained model.

    Args:
        model_name: Name of model in the Nursery or cloud model ID
        prompt: Test prompt to send
        provider: Where to run - "local", "together", "ollama"

    Returns:
        Dict with model response
    """
    # Placeholder - would implement actual inference
    return {
        "success": False,
        "error": "Model testing not yet implemented. Coming soon!",
    }


def nursery_compare_models(
    model_a: str,
    model_b: str,
    test_prompts: List[str],
) -> Dict[str, Any]:
    """
    A/B compare two models on the same prompts.

    Args:
        model_a: First model name
        model_b: Second model name
        test_prompts: List of prompts to test both models on

    Returns:
        Dict with comparison results
    """
    # Placeholder - would implement actual comparison
    return {
        "success": False,
        "error": "Model comparison not yet implemented. Coming soon!",
    }


# =============================================================================
# Tool Schemas for Claude
# =============================================================================

NURSERY_GENERATE_DATA_SCHEMA = {
    "name": "nursery_generate_data",
    "description": "Generate synthetic training data for a specific tool. Creates varied examples of tool usage for fine-tuning smaller models. Announces to Village when complete.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to generate examples for (e.g., 'memory_store', 'fs_read_file')",
            },
            "num_examples": {
                "type": "integer",
                "description": "Number of examples to generate (default: 50)",
                "default": 50,
            },
            "variation_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "How diverse the examples should be",
                "default": "medium",
            },
            "output_name": {
                "type": "string",
                "description": "Optional name for the dataset",
            },
            "agent_id": {
                "type": "string",
                "description": "Agent creating the dataset (for Village attribution). Defaults to NURSERY_KEEPER.",
            },
        },
        "required": ["tool_name"],
    },
}

NURSERY_EXTRACT_CONVERSATIONS_SCHEMA = {
    "name": "nursery_extract_conversations",
    "description": "Extract training data from real conversation history. Mines actual tool usage patterns from past conversations. Announces to Village when complete.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "Path to conversations JSON file",
                "default": "sandbox/conversations.json",
            },
            "tools_filter": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Only extract these tools (None = all tools)",
            },
            "min_examples": {
                "type": "integer",
                "description": "Minimum examples needed to save dataset",
                "default": 10,
            },
            "output_name": {
                "type": "string",
                "description": "Optional name for the dataset",
            },
            "agent_id": {
                "type": "string",
                "description": "Agent creating the dataset (for Village attribution). Defaults to NURSERY_KEEPER.",
            },
        },
        "required": [],
    },
}

NURSERY_LIST_DATASETS_SCHEMA = {
    "name": "nursery_list_datasets",
    "description": "List all available training datasets in the Nursery.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

NURSERY_ESTIMATE_COST_SCHEMA = {
    "name": "nursery_estimate_cost",
    "description": "Estimate training cost for a dataset across cloud providers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "dataset_name": {
                "type": "string",
                "description": "Name of dataset in the Nursery",
            },
            "base_model": {
                "type": "string",
                "description": "Model size - '1b', '3b', '7b', '13b', '27b'",
                "default": "3b",
            },
            "epochs": {
                "type": "integer",
                "description": "Number of training epochs",
                "default": 3,
            },
            "provider": {
                "type": "string",
                "description": "Provider to estimate for, or 'all'",
                "default": "all",
            },
        },
        "required": ["dataset_name"],
    },
}

NURSERY_TRAIN_CLOUD_SCHEMA = {
    "name": "nursery_train_cloud",
    "description": "Start a cloud training job on Vast.ai, Together.ai, etc. Returns a job_id for tracking. Announces to Village when started.",
    "input_schema": {
        "type": "object",
        "properties": {
            "dataset_name": {
                "type": "string",
                "description": "Name of dataset in the Nursery",
            },
            "base_model": {
                "type": "string",
                "description": "Base model to fine-tune (e.g., 'meta-llama/Llama-3.2-3B')",
            },
            "output_name": {
                "type": "string",
                "description": "Name for the fine-tuned model",
            },
            "provider": {
                "type": "string",
                "enum": ["together", "replicate", "vastai", "runpod"],
                "description": "Cloud provider to use",
                "default": "together",
            },
            "epochs": {
                "type": "integer",
                "description": "Number of training epochs",
                "default": 3,
            },
            "learning_rate": {
                "type": "number",
                "description": "Learning rate for training",
                "default": 1e-5,
            },
            "lora_rank": {
                "type": "integer",
                "description": "LoRA rank (higher = more capacity)",
                "default": 16,
            },
            "agent_id": {
                "type": "string",
                "description": "Agent initiating training (for Village attribution). Defaults to NURSERY_KEEPER.",
            },
        },
        "required": ["dataset_name", "base_model", "output_name"],
    },
}

NURSERY_TRAIN_LOCAL_SCHEMA = {
    "name": "nursery_train_local",
    "description": "Start local LoRA training. Best for small models (1-3B) on capable hardware. Announces to Village when complete.",
    "input_schema": {
        "type": "object",
        "properties": {
            "dataset_name": {
                "type": "string",
                "description": "Name of dataset in the Nursery",
            },
            "base_model": {
                "type": "string",
                "description": "HuggingFace model ID to fine-tune",
                "default": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            },
            "output_name": {
                "type": "string",
                "description": "Name for output adapter",
            },
            "epochs": {
                "type": "integer",
                "description": "Number of training epochs",
                "default": 3,
            },
            "batch_size": {
                "type": "integer",
                "description": "Training batch size",
                "default": 4,
            },
            "learning_rate": {
                "type": "number",
                "description": "Learning rate",
                "default": 2e-5,
            },
            "lora_rank": {
                "type": "integer",
                "description": "LoRA rank",
                "default": 8,
            },
            "use_cpu": {
                "type": "boolean",
                "description": "Force CPU training",
                "default": False,
            },
            "agent_id": {
                "type": "string",
                "description": "Agent initiating training (for Village attribution). Defaults to NURSERY_KEEPER.",
            },
        },
        "required": ["dataset_name"],
    },
}

NURSERY_JOB_STATUS_SCHEMA = {
    "name": "nursery_job_status",
    "description": "Check status of a training job.",
    "input_schema": {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "The job ID from nursery_train_cloud",
            },
        },
        "required": ["job_id"],
    },
}

NURSERY_LIST_JOBS_SCHEMA = {
    "name": "nursery_list_jobs",
    "description": "List all training jobs in the Nursery.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status_filter": {
                "type": "string",
                "enum": ["pending", "running", "completed", "failed"],
                "description": "Filter by status",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum jobs to return",
                "default": 20,
            },
        },
        "required": [],
    },
}

NURSERY_LIST_MODELS_SCHEMA = {
    "name": "nursery_list_models",
    "description": "List all trained models/adapters in the Nursery.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

NURSERY_DEPLOY_OLLAMA_SCHEMA = {
    "name": "nursery_deploy_ollama",
    "description": "Deploy a trained model to local Ollama for inference.",
    "input_schema": {
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of model in the Nursery",
            },
            "ollama_name": {
                "type": "string",
                "description": "Name to use in Ollama",
            },
            "quantize": {
                "type": "string",
                "enum": ["q4_k_m", "q5_k_m", "q8_0", "f16"],
                "description": "Quantization level",
                "default": "q4_k_m",
            },
        },
        "required": ["model_name"],
    },
}

NURSERY_TEST_MODEL_SCHEMA = {
    "name": "nursery_test_model",
    "description": "Quick inference test of a trained model.",
    "input_schema": {
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Name of model in the Nursery",
            },
            "prompt": {
                "type": "string",
                "description": "Test prompt to send",
            },
            "provider": {
                "type": "string",
                "enum": ["local", "together", "ollama"],
                "description": "Where to run inference",
                "default": "local",
            },
        },
        "required": ["model_name", "prompt"],
    },
}

NURSERY_COMPARE_MODELS_SCHEMA = {
    "name": "nursery_compare_models",
    "description": "A/B compare two models on the same prompts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "model_a": {
                "type": "string",
                "description": "First model name",
            },
            "model_b": {
                "type": "string",
                "description": "Second model name",
            },
            "test_prompts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of prompts to test both models on",
            },
        },
        "required": ["model_a", "model_b", "test_prompts"],
    },
}

# =============================================================================
# Phase 2: Village Registry Schemas
# =============================================================================

NURSERY_REGISTER_MODEL_SCHEMA = {
    "name": "nursery_register_model",
    "description": "Register a trained model in the Village registry. Makes it discoverable by other agents. Auto-called on training completion.",
    "input_schema": {
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Unique name for the model",
            },
            "model_path": {
                "type": "string",
                "description": "Path to model files (auto-detected if in Nursery)",
            },
            "description": {
                "type": "string",
                "description": "Human-readable description of model capabilities",
            },
            "capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of capabilities (e.g., ['tool_calling', 'code_generation'])",
            },
            "base_model": {
                "type": "string",
                "description": "Base model this was fine-tuned from",
            },
            "trainer_agent": {
                "type": "string",
                "description": "Agent who trained this model (for attribution)",
            },
            "performance": {
                "type": "object",
                "description": "Performance metrics dict (e.g., {loss: 1.5, accuracy: 0.85})",
            },
        },
        "required": ["model_name"],
    },
}

NURSERY_DISCOVER_MODELS_SCHEMA = {
    "name": "nursery_discover_models",
    "description": "Search the Village for registered models. Discovers models trained by any agent in the ecosystem.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (semantic search in Village)",
            },
            "capability": {
                "type": "string",
                "description": "Filter by capability (e.g., 'tool_calling')",
            },
            "trainer_filter": {
                "type": "string",
                "description": "Filter by trainer agent (e.g., 'AZOTH')",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return",
                "default": 10,
            },
        },
        "required": [],
    },
}

# =============================================================================
# Phase 3: Apprentice Protocol Schemas
# =============================================================================

NURSERY_CREATE_APPRENTICE_SCHEMA = {
    "name": "nursery_create_apprentice",
    "description": "Create an apprentice model for an agent. The apprentice inherits knowledge from the master's Village posts and specializes in a specific domain.",
    "input_schema": {
        "type": "object",
        "properties": {
            "master_agent": {
                "type": "string",
                "description": "The master agent's ID (e.g., 'AZOTH', 'ELYSIAN')",
            },
            "apprentice_name": {
                "type": "string",
                "description": "Name for the apprentice (e.g., 'tool_master', 'memory_keeper')",
            },
            "specialization": {
                "type": "string",
                "description": "What the apprentice should specialize in (e.g., 'tool calling', 'creative writing')",
            },
            "training_data_query": {
                "type": "string",
                "description": "Custom query to find training data from Village (default: uses specialization)",
            },
            "base_model": {
                "type": "string",
                "description": "Base model to fine-tune (default: TinyLlama 1.1B)",
                "default": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            },
            "min_examples": {
                "type": "integer",
                "description": "Minimum training examples required",
                "default": 20,
            },
            "auto_train": {
                "type": "boolean",
                "description": "Automatically start local training after dataset creation",
                "default": False,
            },
        },
        "required": ["master_agent", "apprentice_name", "specialization"],
    },
}

NURSERY_LIST_APPRENTICES_SCHEMA = {
    "name": "nursery_list_apprentices",
    "description": "List all apprentices in the Nursery. Filter by master agent or training status.",
    "input_schema": {
        "type": "object",
        "properties": {
            "master_filter": {
                "type": "string",
                "description": "Filter by master agent (e.g., 'AZOTH')",
            },
            "trained_only": {
                "type": "boolean",
                "description": "Only show trained apprentices",
                "default": False,
            },
        },
        "required": [],
    },
}
