#!/usr/bin/env python3
"""
Quick LoRA Training Script for Vast.ai
TinyLlama 1.1B with tool-calling data
"""

import json
import torch
from pathlib import Path
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

print("🔥 ApexAurum Nursery - LoRA Training")
print("=" * 50)

# Config
BASE_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
DATA_FILE = "/workspace/training_data.jsonl"
OUTPUT_DIR = "/workspace/lora_output"

# Load tokenizer
print(f"Loading tokenizer from {BASE_MODEL}...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
tokenizer.pad_token = tokenizer.eos_token

# Load and prepare data
print(f"Loading training data from {DATA_FILE}...")
with open(DATA_FILE) as f:
    raw_data = [json.loads(line) for line in f]

# Format for training
def format_example(ex):
    query = ex["user_query"]
    tool_name = ex["tool_name"]
    tool_args = json.dumps(ex["tool_arguments"])

    # ChatML format
    text = f"<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n<tool_call>{tool_name}({tool_args})</tool_call><|im_end|>"
    return {"text": text}

formatted = [format_example(ex) for ex in raw_data]
dataset = Dataset.from_list(formatted)

print(f"Dataset size: {len(dataset)} examples")

# Tokenize
def tokenize(examples):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=256,
        padding="max_length",
    )

tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])
tokenized = tokenized.map(lambda x: {"labels": x["input_ids"].copy()})

print(f"Tokenized: {len(tokenized)} examples")

# Load model with 4-bit quantization for speed
print("Loading model with 4-bit quantization...")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.float16,
    device_map="auto",
    load_in_4bit=True,
)

# LoRA config
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Training args (quick test)
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=2,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=2,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=5,
    save_steps=50,
    save_total_limit=1,
    report_to="none",
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

# Train!
print("\n🔥 Starting training...")
trainer.train()

# Save
print(f"\n💾 Saving adapter to {OUTPUT_DIR}...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n✅ Training complete!")
print(f"Adapter saved to: {OUTPUT_DIR}")
