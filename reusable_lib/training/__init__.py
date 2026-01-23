# Training Module
# Extracted from ApexAurum - Claude Edition
#
# Tools for generating fine-tuning datasets and training small models locally.
# Supports multiple output formats and memory-efficient LoRA training.
# Cloud training integration for Vast.ai, RunPod, Modal, Together.ai, Replicate.

from .data_extractor import (
    TrainingDataExtractor,
    ConversationParser,
    ToolCallExample,
    TrainingExample,
    ExportFormat,
    extract_tool_calls_from_conversations,
    generate_training_dataset
)

from .lora_trainer import (
    LoRATrainer,
    TrainingConfig,
    TrainingStats,
    check_dependencies,
    get_memory_usage_mb,
    quick_train,
)

from .synthetic_generator import (
    SyntheticGenerator,
    ToolSchema,
    TrainingExample as SyntheticExample,
    DEFAULT_TOOLS,
    generate_training_data,
)

from .cloud_trainer import (
    CloudTrainer,
    CloudProvider,
    TrainingJob,
    GPUInstance,
    TogetherTrainer,
    ReplicateTrainer,
    VastAITrainer,
    RunPodTrainer,
    ModalTrainer,
    quick_cloud_train,
    estimate_training_cost,
)

__all__ = [
    # Data extraction (from real conversations)
    'TrainingDataExtractor',
    'ConversationParser',
    'ToolCallExample',
    'TrainingExample',
    'ExportFormat',
    'extract_tool_calls_from_conversations',
    'generate_training_dataset',
    # LoRA training (local)
    'LoRATrainer',
    'TrainingConfig',
    'TrainingStats',
    'check_dependencies',
    'get_memory_usage_mb',
    'quick_train',
    # Synthetic data generation
    'SyntheticGenerator',
    'ToolSchema',
    'SyntheticExample',
    'DEFAULT_TOOLS',
    'generate_training_data',
    # Cloud training
    'CloudTrainer',
    'CloudProvider',
    'TrainingJob',
    'GPUInstance',
    'TogetherTrainer',
    'ReplicateTrainer',
    'VastAITrainer',
    'RunPodTrainer',
    'ModalTrainer',
    'quick_cloud_train',
    'estimate_training_cost',
]
