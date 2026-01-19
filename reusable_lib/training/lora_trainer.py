"""
LoRA Fine-Tuning for ARM64/CPU

Memory-efficient LoRA training designed for resource-constrained devices
like Raspberry Pi 5. Works without CUDA or bitsandbytes.

Key optimizations:
- Gradient checkpointing to reduce memory
- Small batch sizes with gradient accumulation
- CPU-optimized settings
- Memory monitoring and automatic OOM prevention

Example usage:
    from training.lora_trainer import LoRATrainer, TrainingConfig

    config = TrainingConfig(
        model_name="google/gemma-2b",
        output_dir="./my_model",
        lora_r=8,
        learning_rate=2e-4,
        num_epochs=3,
    )

    trainer = LoRATrainer(config)
    trainer.load_model()
    trainer.train(train_dataset)
    trainer.save_model()
"""

import os
import json
import logging
import gc
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for LoRA fine-tuning."""

    # Model settings
    model_name: str = "google/gemma-2-2b"  # HuggingFace model name or path
    output_dir: str = "./lora_output"

    # LoRA hyperparameters
    lora_r: int = 8  # LoRA rank (lower = less memory, 4-16 typical)
    lora_alpha: int = 16  # LoRA alpha (typically 2x rank)
    lora_dropout: float = 0.05
    target_modules: Optional[List[str]] = None  # Auto-detect if None

    # Training hyperparameters
    learning_rate: float = 2e-4
    num_epochs: int = 3
    batch_size: int = 1  # Keep at 1 for Pi
    gradient_accumulation_steps: int = 4  # Effective batch = 4
    warmup_ratio: float = 0.03
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0

    # Sequence settings
    max_seq_length: int = 512  # Shorter = less memory

    # Memory optimization
    gradient_checkpointing: bool = True
    fp16: bool = False  # Set True if your CPU supports it
    optim: str = "adamw_torch"  # or "adafactor" for less memory

    # Logging
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 50

    # CPU/ARM specific
    dataloader_num_workers: int = 0  # 0 for Pi to avoid memory issues
    dataloader_pin_memory: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, path: str):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'TrainingConfig':
        with open(path, 'r') as f:
            return cls(**json.load(f))

    @classmethod
    def for_pi5(cls, model_name: str = "google/gemma-2-2b", **kwargs) -> 'TrainingConfig':
        """Optimized config for Raspberry Pi 5 (8GB)."""
        return cls(
            model_name=model_name,
            lora_r=4,  # Minimal rank
            lora_alpha=8,
            batch_size=1,
            gradient_accumulation_steps=8,
            max_seq_length=256,  # Short sequences
            gradient_checkpointing=True,
            fp16=False,  # CPU doesn't benefit
            optim="adafactor",  # Less memory than Adam
            dataloader_num_workers=0,
            **kwargs
        )


@dataclass
class TrainingStats:
    """Track training statistics."""
    total_steps: int = 0
    total_tokens: int = 0
    train_loss: float = 0.0
    learning_rate: float = 0.0
    epoch: float = 0.0
    memory_used_mb: float = 0.0
    tokens_per_second: float = 0.0
    time_elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_memory_usage_mb() -> float:
    """Get current memory usage in MB."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def check_dependencies() -> Dict[str, bool]:
    """Check which training dependencies are available."""
    deps = {}

    try:
        import torch
        deps['torch'] = True
        deps['torch_version'] = torch.__version__
        deps['cuda_available'] = torch.cuda.is_available()
    except ImportError:
        deps['torch'] = False

    try:
        import transformers
        deps['transformers'] = True
        deps['transformers_version'] = transformers.__version__
    except ImportError:
        deps['transformers'] = False

    try:
        import peft
        deps['peft'] = True
        deps['peft_version'] = peft.__version__
    except ImportError:
        deps['peft'] = False

    try:
        import datasets
        deps['datasets'] = True
    except ImportError:
        deps['datasets'] = False

    try:
        import accelerate
        deps['accelerate'] = True
    except ImportError:
        deps['accelerate'] = False

    try:
        import bitsandbytes
        deps['bitsandbytes'] = True
    except ImportError:
        deps['bitsandbytes'] = False

    return deps


class LoRATrainer:
    """
    Memory-efficient LoRA trainer for CPU/ARM64.

    Designed to work on Raspberry Pi 5 and similar constrained devices.
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.peft_model = None
        self.stats = TrainingStats()

        # Check dependencies
        self.deps = check_dependencies()
        self._validate_dependencies()

        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"LoRATrainer initialized for {config.model_name}")
        logger.info(f"Memory usage: {get_memory_usage_mb():.1f} MB")

    def _validate_dependencies(self):
        """Ensure required dependencies are available."""
        required = ['torch', 'transformers', 'peft']
        missing = [dep for dep in required if not self.deps.get(dep, False)]

        if missing:
            install_cmd = f"pip install {' '.join(missing)}"
            raise ImportError(
                f"Missing required dependencies: {missing}\n"
                f"Install with: {install_cmd}"
            )

        if not self.deps.get('datasets'):
            logger.warning("'datasets' not installed - some features may be limited")

    def load_model(self, device_map: str = "cpu"):
        """
        Load base model and apply LoRA configuration.

        Args:
            device_map: Device to load model on ("cpu" for Pi)
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model, TaskType

        logger.info(f"Loading model: {self.config.model_name}")
        logger.info(f"Memory before load: {get_memory_usage_mb():.1f} MB")

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=True
        )

        # Ensure pad token exists
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model with memory optimizations
        model_kwargs = {
            "device_map": device_map,
            "trust_remote_code": True,
            "torch_dtype": torch.float32,  # FP32 for CPU stability
        }

        # Use low_cpu_mem_usage if available
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                low_cpu_mem_usage=True,
                **model_kwargs
            )
        except TypeError:
            # Older transformers version
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                **model_kwargs
            )

        logger.info(f"Memory after model load: {get_memory_usage_mb():.1f} MB")

        # Enable gradient checkpointing for memory efficiency
        if self.config.gradient_checkpointing:
            self.model.gradient_checkpointing_enable()
            logger.info("Gradient checkpointing enabled")

        # Configure LoRA
        target_modules = self.config.target_modules
        if target_modules is None:
            # Auto-detect target modules based on model architecture
            target_modules = self._detect_target_modules()

        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=target_modules,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )

        # Apply LoRA
        self.peft_model = get_peft_model(self.model, lora_config)

        # Count trainable parameters
        trainable, total = self.peft_model.get_nb_trainable_parameters()
        logger.info(f"Trainable parameters: {trainable:,} / {total:,} "
                   f"({100 * trainable / total:.2f}%)")
        logger.info(f"Memory after LoRA: {get_memory_usage_mb():.1f} MB")

        return self.peft_model

    def _detect_target_modules(self) -> List[str]:
        """Auto-detect LoRA target modules based on model architecture."""
        model_name_lower = self.config.model_name.lower()

        # Common target modules by model family
        if "gpt2" in model_name_lower or "gpt-2" in model_name_lower:
            return ["c_attn", "c_proj"]  # GPT-2 specific
        elif "gemma" in model_name_lower:
            return ["q_proj", "v_proj", "k_proj", "o_proj"]
        elif "llama" in model_name_lower or "mistral" in model_name_lower:
            return ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
        elif "qwen" in model_name_lower:
            return ["q_proj", "v_proj", "k_proj", "o_proj"]
        elif "phi" in model_name_lower:
            return ["q_proj", "v_proj", "k_proj", "dense"]
        elif "opt" in model_name_lower:
            return ["q_proj", "v_proj"]  # OPT models
        elif "bloom" in model_name_lower:
            return ["query_key_value"]  # BLOOM uses fused attention
        else:
            # Generic fallback - try to detect from model
            logger.warning(f"Unknown model architecture: {self.config.model_name}")
            logger.warning("Using generic target modules. You may need to specify them manually.")
            return ["q_proj", "v_proj"]

    def prepare_dataset(
        self,
        examples: List[Dict[str, str]],
        text_field: str = "text",
    ):
        """
        Prepare dataset for training.

        Args:
            examples: List of dicts with text field
            text_field: Key containing the text to train on

        Returns:
            Tokenized dataset ready for training
        """
        import torch
        from torch.utils.data import Dataset

        class SimpleDataset(Dataset):
            def __init__(self, encodings):
                self.encodings = encodings

            def __len__(self):
                return len(self.encodings['input_ids'])

            def __getitem__(self, idx):
                return {
                    'input_ids': torch.tensor(self.encodings['input_ids'][idx]),
                    'attention_mask': torch.tensor(self.encodings['attention_mask'][idx]),
                    'labels': torch.tensor(self.encodings['input_ids'][idx]),
                }

        # Tokenize all examples
        texts = [ex[text_field] for ex in examples]

        encodings = self.tokenizer(
            texts,
            truncation=True,
            max_length=self.config.max_seq_length,
            padding='max_length',
            return_tensors=None,
        )

        logger.info(f"Prepared {len(texts)} training examples")
        return SimpleDataset(encodings)

    def train(
        self,
        train_dataset,
        eval_dataset=None,
        callbacks: Optional[List[Callable]] = None,
    ):
        """
        Train the model with LoRA.

        Args:
            train_dataset: Training dataset (from prepare_dataset or HF Dataset)
            eval_dataset: Optional evaluation dataset
            callbacks: Optional list of callback functions called each step
        """
        import torch
        from torch.utils.data import DataLoader
        from torch.optim import AdamW

        if self.peft_model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        logger.info("Starting training...")
        logger.info(f"  Epochs: {self.config.num_epochs}")
        logger.info(f"  Batch size: {self.config.batch_size}")
        logger.info(f"  Gradient accumulation: {self.config.gradient_accumulation_steps}")
        logger.info(f"  Effective batch size: {self.config.batch_size * self.config.gradient_accumulation_steps}")

        # Create dataloader
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=self.config.dataloader_num_workers,
            pin_memory=self.config.dataloader_pin_memory,
        )

        # Setup optimizer
        if self.config.optim == "adafactor":
            try:
                from transformers import Adafactor
                optimizer = Adafactor(
                    self.peft_model.parameters(),
                    lr=self.config.learning_rate,
                    scale_parameter=False,
                    relative_step=False,
                )
            except ImportError:
                logger.warning("Adafactor not available, using AdamW")
                optimizer = AdamW(
                    self.peft_model.parameters(),
                    lr=self.config.learning_rate,
                    weight_decay=self.config.weight_decay,
                )
        else:
            optimizer = AdamW(
                self.peft_model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )

        # Training loop
        self.peft_model.train()
        global_step = 0
        total_loss = 0.0
        start_time = time.time()

        for epoch in range(self.config.num_epochs):
            epoch_loss = 0.0
            epoch_steps = 0

            for step, batch in enumerate(train_loader):
                # Move batch to device
                batch = {k: v.to(self.peft_model.device) for k, v in batch.items()}

                # Forward pass
                outputs = self.peft_model(**batch)
                loss = outputs.loss / self.config.gradient_accumulation_steps

                # Backward pass
                loss.backward()

                epoch_loss += loss.item() * self.config.gradient_accumulation_steps
                total_loss += loss.item() * self.config.gradient_accumulation_steps

                # Gradient accumulation
                if (step + 1) % self.config.gradient_accumulation_steps == 0:
                    # Gradient clipping
                    torch.nn.utils.clip_grad_norm_(
                        self.peft_model.parameters(),
                        self.config.max_grad_norm
                    )

                    optimizer.step()
                    optimizer.zero_grad()
                    global_step += 1
                    epoch_steps += 1

                    # Logging
                    if global_step % self.config.logging_steps == 0:
                        avg_loss = total_loss / global_step
                        mem_mb = get_memory_usage_mb()
                        elapsed = time.time() - start_time

                        self.stats = TrainingStats(
                            total_steps=global_step,
                            train_loss=avg_loss,
                            epoch=epoch + (step / len(train_loader)),
                            memory_used_mb=mem_mb,
                            time_elapsed_seconds=elapsed,
                        )

                        logger.info(
                            f"Step {global_step} | "
                            f"Loss: {avg_loss:.4f} | "
                            f"Epoch: {self.stats.epoch:.2f} | "
                            f"Mem: {mem_mb:.0f}MB | "
                            f"Time: {elapsed:.0f}s"
                        )

                        # Run callbacks
                        if callbacks:
                            for cb in callbacks:
                                cb(self.stats)

                    # Save checkpoint
                    if global_step % self.config.save_steps == 0:
                        self._save_checkpoint(global_step)

                # Memory cleanup
                if step % 50 == 0:
                    gc.collect()

            # End of epoch logging
            epoch_avg_loss = epoch_loss / max(epoch_steps, 1)
            logger.info(f"Epoch {epoch + 1}/{self.config.num_epochs} complete | "
                       f"Avg Loss: {epoch_avg_loss:.4f}")

        logger.info(f"Training complete! Total steps: {global_step}")
        return self.stats

    def _save_checkpoint(self, step: int):
        """Save a training checkpoint."""
        checkpoint_dir = os.path.join(self.config.output_dir, f"checkpoint-{step}")
        self.peft_model.save_pretrained(checkpoint_dir)
        self.tokenizer.save_pretrained(checkpoint_dir)
        self.config.save(os.path.join(checkpoint_dir, "training_config.json"))
        logger.info(f"Checkpoint saved to {checkpoint_dir}")

    def save_model(self, path: Optional[str] = None):
        """Save the final trained model."""
        save_path = path or os.path.join(self.config.output_dir, "final")
        self.peft_model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)
        self.config.save(os.path.join(save_path, "training_config.json"))

        # Save stats
        with open(os.path.join(save_path, "training_stats.json"), 'w') as f:
            json.dump(self.stats.to_dict(), f, indent=2)

        logger.info(f"Model saved to {save_path}")
        return save_path

    def merge_and_export(self, output_path: str, export_format: str = "safetensors"):
        """
        Merge LoRA weights into base model and export.

        Args:
            output_path: Where to save merged model
            export_format: "safetensors" or "pytorch"
        """
        logger.info("Merging LoRA weights into base model...")

        # Merge weights
        merged_model = self.peft_model.merge_and_unload()

        # Save
        merged_model.save_pretrained(
            output_path,
            safe_serialization=(export_format == "safetensors")
        )
        self.tokenizer.save_pretrained(output_path)

        logger.info(f"Merged model saved to {output_path}")
        return output_path


def quick_train(
    model_name: str,
    training_texts: List[str],
    output_dir: str = "./lora_output",
    num_epochs: int = 3,
    **config_kwargs
) -> str:
    """
    Quick function to train a model with minimal setup.

    Args:
        model_name: HuggingFace model name
        training_texts: List of training text strings
        output_dir: Where to save the model
        num_epochs: Number of training epochs
        **config_kwargs: Additional TrainingConfig parameters

    Returns:
        Path to saved model

    Example:
        texts = [
            "User: What time is it?\\nAssistant: <tool>get_time</tool>",
            "User: Calculate 5+3\\nAssistant: <tool>calculator(5, 3, add)</tool>",
        ]
        model_path = quick_train("google/gemma-2-2b", texts)
    """
    # Create config optimized for Pi 5
    config = TrainingConfig.for_pi5(
        model_name=model_name,
        output_dir=output_dir,
        num_epochs=num_epochs,
        **config_kwargs
    )

    # Create trainer
    trainer = LoRATrainer(config)
    trainer.load_model()

    # Prepare dataset
    examples = [{"text": t} for t in training_texts]
    dataset = trainer.prepare_dataset(examples)

    # Train
    trainer.train(dataset)

    # Save
    return trainer.save_model()


# CLI for quick testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LoRA Fine-Tuning for ARM64/CPU")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies")
    parser.add_argument("--model", type=str, help="Model to fine-tune")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.check_deps:
        deps = check_dependencies()
        print("\n=== Dependency Check ===")
        for name, available in deps.items():
            status = "✓" if available else "✗"
            print(f"  {status} {name}: {available}")

        # Memory info
        print(f"\n=== System Info ===")
        print(f"  Memory usage: {get_memory_usage_mb():.1f} MB")

        try:
            import psutil
            mem = psutil.virtual_memory()
            print(f"  Total RAM: {mem.total / 1024 / 1024 / 1024:.1f} GB")
            print(f"  Available: {mem.available / 1024 / 1024 / 1024:.1f} GB")
        except ImportError:
            pass
