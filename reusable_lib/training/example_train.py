#!/usr/bin/env python3
"""
Example: Fine-tune a tiny model on Raspberry Pi 5

This script demonstrates LoRA fine-tuning on CPU with minimal resources.
Uses a small GPT-2 model for testing (124M params).

Usage:
    python example_train.py --test      # Quick functionality test
    python example_train.py --train     # Actually train (takes time)
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Example tool-calling training data
TOOL_CALLING_EXAMPLES = [
    # Calculator examples
    "User: What is 5 plus 3?\nAssistant: I'll calculate that for you.\n<tool_call>calculator(operation='add', a=5, b=3)</tool_call>\nThe result is 8.",
    "User: Multiply 7 by 9\nAssistant: Let me compute that.\n<tool_call>calculator(operation='multiply', a=7, b=9)</tool_call>\nThe answer is 63.",
    "User: What's 100 divided by 4?\nAssistant: I'll calculate the division.\n<tool_call>calculator(operation='divide', a=100, b=4)</tool_call>\nThe result is 25.",
    "User: Calculate 15 minus 8\nAssistant: <tool_call>calculator(operation='subtract', a=15, b=8)</tool_call>\nThat equals 7.",

    # Time examples
    "User: What time is it?\nAssistant: Let me check the current time.\n<tool_call>get_current_time(format='human')</tool_call>",
    "User: What's today's date?\nAssistant: I'll get that for you.\n<tool_call>get_current_time(format='date')</tool_call>",
    "User: Give me the timestamp\nAssistant: <tool_call>get_current_time(format='timestamp')</tool_call>",

    # Memory examples
    "User: Remember my name is Alice\nAssistant: I'll store that.\n<tool_call>memory_store(key='user_name', value='Alice')</tool_call>\nGot it, I'll remember your name is Alice.",
    "User: What's my name?\nAssistant: Let me check my memory.\n<tool_call>memory_retrieve(key='user_name')</tool_call>",
    "User: Save that my favorite color is blue\nAssistant: <tool_call>memory_store(key='favorite_color', value='blue')</tool_call>\nSaved! Your favorite color is blue.",
    "User: Store my email as bob@example.com\nAssistant: <tool_call>memory_store(key='email', value='bob@example.com')</tool_call>\nI've stored your email.",
    "User: What did I say my email was?\nAssistant: <tool_call>memory_retrieve(key='email')</tool_call>",

    # Random number
    "User: Give me a random number between 1 and 100\nAssistant: <tool_call>random_number(min_value=1, max_value=100)</tool_call>",
    "User: Pick a random number from 1 to 10\nAssistant: <tool_call>random_number(min_value=1, max_value=10)</tool_call>",

    # Word count
    "User: Count the words in 'Hello world how are you'\nAssistant: <tool_call>count_words(text='Hello world how are you')</tool_call>",
]


def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")

    try:
        import torch
        print(f"  ✓ torch {torch.__version__}")
    except ImportError as e:
        print(f"  ✗ torch: {e}")
        return False

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        print(f"  ✓ transformers")
    except ImportError as e:
        print(f"  ✗ transformers: {e}")
        return False

    try:
        from peft import LoraConfig, get_peft_model
        print(f"  ✓ peft")
    except ImportError as e:
        print(f"  ✗ peft: {e}")
        return False

    try:
        from lora_trainer import LoRATrainer, TrainingConfig, get_memory_usage_mb
        print(f"  ✓ lora_trainer")
    except ImportError as e:
        print(f"  ✗ lora_trainer: {e}")
        return False

    print(f"\nMemory usage: {get_memory_usage_mb():.1f} MB")
    return True


def test_model_load():
    """Test loading a tiny model with LoRA."""
    from lora_trainer import LoRATrainer, TrainingConfig, get_memory_usage_mb

    print("\n" + "="*50)
    print("Testing model load with LoRA...")
    print("="*50)

    # Use GPT-2 small for testing (124M params, ~500MB)
    # Note: for_pi5() already sets optimized defaults for lora_r, max_seq_length
    config = TrainingConfig.for_pi5(
        model_name="gpt2",  # Smallest common model
        output_dir="./test_output",
        num_epochs=1,
    )

    print(f"\nConfig:")
    print(f"  Model: {config.model_name}")
    print(f"  LoRA rank: {config.lora_r}")
    print(f"  Max seq length: {config.max_seq_length}")

    trainer = LoRATrainer(config)

    print(f"\nMemory before load: {get_memory_usage_mb():.1f} MB")

    try:
        trainer.load_model()
        print(f"Memory after load: {get_memory_usage_mb():.1f} MB")
        print("\n✓ Model loaded successfully!")
        return trainer
    except Exception as e:
        print(f"\n✗ Model load failed: {e}")
        return None


def test_training(trainer, num_examples=5):
    """Test a few training steps."""
    from lora_trainer import get_memory_usage_mb

    print("\n" + "="*50)
    print(f"Testing training with {num_examples} examples...")
    print("="*50)

    # Use subset of examples
    examples = TOOL_CALLING_EXAMPLES[:num_examples]
    dataset = trainer.prepare_dataset([{"text": t} for t in examples])

    print(f"\nDataset size: {len(dataset)}")
    print(f"Memory before training: {get_memory_usage_mb():.1f} MB")

    # Just do a few steps
    trainer.config.num_epochs = 1
    trainer.config.logging_steps = 1
    trainer.config.save_steps = 999999  # Don't save during test

    try:
        stats = trainer.train(dataset)
        print(f"\nMemory after training: {get_memory_usage_mb():.1f} MB")
        print(f"Training loss: {stats.train_loss:.4f}")
        print("\n✓ Training test passed!")
        return True
    except Exception as e:
        print(f"\n✗ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def full_training():
    """Run full training on all examples."""
    from lora_trainer import LoRATrainer, TrainingConfig, get_memory_usage_mb

    print("\n" + "="*50)
    print("Full Training Run")
    print("="*50)

    config = TrainingConfig.for_pi5(
        model_name="gpt2",
        output_dir="./tool_calling_lora",
        lora_r=8,
        lora_alpha=16,
        max_seq_length=256,
        num_epochs=3,
        learning_rate=2e-4,
        logging_steps=5,
        save_steps=50,
    )

    print(f"\nConfiguration:")
    print(f"  Model: {config.model_name}")
    print(f"  LoRA rank: {config.lora_r}")
    print(f"  Epochs: {config.num_epochs}")
    print(f"  Examples: {len(TOOL_CALLING_EXAMPLES)}")

    trainer = LoRATrainer(config)
    trainer.load_model()

    dataset = trainer.prepare_dataset([{"text": t} for t in TOOL_CALLING_EXAMPLES])

    print(f"\nStarting training...")
    print(f"Memory: {get_memory_usage_mb():.1f} MB")

    stats = trainer.train(dataset)

    print(f"\n" + "="*50)
    print("Training Complete!")
    print("="*50)
    print(f"  Total steps: {stats.total_steps}")
    print(f"  Final loss: {stats.train_loss:.4f}")
    print(f"  Time: {stats.time_elapsed_seconds:.1f}s")

    # Save model
    save_path = trainer.save_model()
    print(f"\nModel saved to: {save_path}")

    return save_path


def main():
    parser = argparse.ArgumentParser(description="Test LoRA training on Pi 5")
    parser.add_argument("--test", action="store_true", help="Quick functionality test")
    parser.add_argument("--train", action="store_true", help="Full training run")
    args = parser.parse_args()

    if not args.test and not args.train:
        parser.print_help()
        print("\nExample:")
        print("  python example_train.py --test   # Quick test")
        print("  python example_train.py --train  # Full training")
        return

    if args.test:
        print("="*50)
        print("LoRA Training Test Suite")
        print("="*50)

        if not test_imports():
            print("\n✗ Import test failed!")
            sys.exit(1)

        trainer = test_model_load()
        if trainer is None:
            print("\n✗ Model load test failed!")
            sys.exit(1)

        if not test_training(trainer, num_examples=3):
            print("\n✗ Training test failed!")
            sys.exit(1)

        print("\n" + "="*50)
        print("All tests passed! ✓")
        print("="*50)

    if args.train:
        full_training()


if __name__ == "__main__":
    main()
