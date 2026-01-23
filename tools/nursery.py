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

            # Save job to history
            job_record = {
                "job_id": job.id,
                "provider": provider,
                "dataset": dataset_name,
                "base_model": base_model,
                "output_name": output_name,
                "status": job.status,
                "created_at": datetime.now().isoformat(),
                "config": {
                    "epochs": epochs,
                    "learning_rate": learning_rate,
                    "lora_rank": lora_rank,
                },
            }
            _add_job(job_record)

            return {
                "success": True,
                "job_id": job.id,
                "provider": provider,
                "status": job.status,
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

        # Save job record
        job_record = {
            "job_id": f"local_{output_name}",
            "provider": "local",
            "dataset": dataset_name,
            "base_model": base_model,
            "output_name": output_name,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "output_path": str(output_dir),
            "stats": stats.to_dict() if hasattr(stats, 'to_dict') else str(stats),
        }
        _add_job(job_record)

        return {
            "success": True,
            "output_name": output_name,
            "output_path": str(output_dir),
            "stats": stats.to_dict() if hasattr(stats, 'to_dict') else {"info": str(stats)},
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
    "description": "Generate synthetic training data for a specific tool. Creates varied examples of tool usage for fine-tuning smaller models.",
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
        },
        "required": ["tool_name"],
    },
}

NURSERY_EXTRACT_CONVERSATIONS_SCHEMA = {
    "name": "nursery_extract_conversations",
    "description": "Extract training data from real conversation history. Mines actual tool usage patterns from past conversations.",
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
    "description": "Start a cloud training job on Vast.ai, Together.ai, etc. Returns a job_id for tracking.",
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
        },
        "required": ["dataset_name", "base_model", "output_name"],
    },
}

NURSERY_TRAIN_LOCAL_SCHEMA = {
    "name": "nursery_train_local",
    "description": "Start local LoRA training. Best for small models (1-3B) on capable hardware.",
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
