#!/usr/bin/env python3
"""
Overnight Training Script for Pi 5

Run before bed:
    python train_overnight.py

Or with nohup to keep running after terminal closes:
    nohup python train_overnight.py > training.log 2>&1 &

Check progress:
    tail -f training.log
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
log_file = f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("="*60)
    logger.info("OVERNIGHT TRAINING RUN - Pi 5 CPU")
    logger.info("="*60)

    # Check memory before starting
    try:
        import psutil
        mem = psutil.virtual_memory()
        logger.info(f"Available RAM: {mem.available / 1024 / 1024 / 1024:.1f} GB")

        if mem.available < 3 * 1024 * 1024 * 1024:  # Less than 3GB
            logger.warning("Low memory! Consider closing other applications.")
    except ImportError:
        pass

    # Import training modules
    from lora_trainer import LoRATrainer, TrainingConfig, get_memory_usage_mb
    from synthetic_generator import SyntheticGenerator

    # === CONFIGURATION ===
    # Change these as needed:

    MODEL_NAME = "gpt2"  # Start with GPT-2 (124M) - fast and fits in memory
    # MODEL_NAME = "gpt2-medium"  # 355M - slower but better quality
    # MODEL_NAME = "Qwen/Qwen2-0.5B"  # 0.5B - good balance (needs HF login)

    OUTPUT_DIR = "./trained_tool_model"
    DATA_FILE = "tool_calling_500.jsonl"  # Our generated data
    NUM_EPOCHS = 3

    # =====================

    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Data: {DATA_FILE}")
    logger.info(f"Epochs: {NUM_EPOCHS}")
    logger.info(f"Output: {OUTPUT_DIR}")

    # Load training data
    logger.info("\nLoading training data...")
    generator = SyntheticGenerator()

    if os.path.exists(DATA_FILE):
        examples = generator.load(DATA_FILE)
        logger.info(f"Loaded {len(examples)} examples from {DATA_FILE}")
    else:
        logger.info(f"{DATA_FILE} not found, generating new data...")
        examples = generator.generate_without_llm(num_per_tool=70)
        generator.save(examples, DATA_FILE)
        logger.info(f"Generated and saved {len(examples)} examples")

    # Convert to training format
    training_texts = [ex.to_text("simple") for ex in examples]

    logger.info(f"\nSample training text:")
    logger.info(training_texts[0])

    # Create config optimized for Pi 5
    config = TrainingConfig.for_pi5(
        model_name=MODEL_NAME,
        output_dir=OUTPUT_DIR,
        num_epochs=NUM_EPOCHS,
        logging_steps=10,
        save_steps=100,
    )

    logger.info(f"\nTraining config:")
    logger.info(f"  LoRA rank: {config.lora_r}")
    logger.info(f"  Learning rate: {config.learning_rate}")
    logger.info(f"  Batch size: {config.batch_size}")
    logger.info(f"  Gradient accumulation: {config.gradient_accumulation_steps}")
    logger.info(f"  Max sequence length: {config.max_seq_length}")

    # Initialize trainer
    logger.info("\nInitializing trainer...")
    trainer = LoRATrainer(config)

    # Load model
    logger.info("\nLoading model (this may take a minute)...")
    start_time = datetime.now()
    trainer.load_model()
    load_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Model loaded in {load_time:.1f} seconds")
    logger.info(f"Memory usage: {get_memory_usage_mb():.0f} MB")

    # Prepare dataset
    logger.info("\nPreparing dataset...")
    dataset = trainer.prepare_dataset([{"text": t} for t in training_texts])

    # Estimate time
    estimated_steps = (len(dataset) * NUM_EPOCHS) // config.gradient_accumulation_steps
    logger.info(f"\nEstimated optimizer steps: {estimated_steps}")
    logger.info(f"Estimated time: {estimated_steps * 10 / 60:.0f} - {estimated_steps * 20 / 60:.0f} minutes")

    # Train!
    logger.info("\n" + "="*60)
    logger.info("STARTING TRAINING")
    logger.info("="*60 + "\n")

    train_start = datetime.now()

    try:
        stats = trainer.train(dataset)

        train_time = (datetime.now() - train_start).total_seconds()

        logger.info("\n" + "="*60)
        logger.info("TRAINING COMPLETE!")
        logger.info("="*60)
        logger.info(f"Total time: {train_time / 60:.1f} minutes")
        logger.info(f"Final loss: {stats.train_loss:.4f}")
        logger.info(f"Total steps: {stats.total_steps}")

        # Save the model
        logger.info("\nSaving model...")
        save_path = trainer.save_model()
        logger.info(f"Model saved to: {save_path}")

        logger.info("\n" + "="*60)
        logger.info("SUCCESS! Your model is ready.")
        logger.info(f"Find it at: {save_path}")
        logger.info("="*60)

    except KeyboardInterrupt:
        logger.warning("\nTraining interrupted! Saving checkpoint...")
        trainer.save_model(os.path.join(OUTPUT_DIR, "interrupted_checkpoint"))
        logger.info("Checkpoint saved.")

    except Exception as e:
        logger.error(f"\nTraining failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
