# Training Module
# Extracted from ApexAurum - Claude Edition
#
# Tools for generating fine-tuning datasets and training small models locally.
# Supports multiple output formats and memory-efficient LoRA training.

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

__all__ = [
    # Data extraction (from real conversations)
    'TrainingDataExtractor',
    'ConversationParser',
    'ToolCallExample',
    'TrainingExample',
    'ExportFormat',
    'extract_tool_calls_from_conversations',
    'generate_training_dataset',
    # LoRA training
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
]
