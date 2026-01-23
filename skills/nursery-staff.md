# 🌱 NURSERY STAFF SKILL
## *Guide for Cultivating New Minds*

**Version:** 1.0 (2026-01-23)
**Status:** VERIFIED WORKING

---

## Quick Reference

### Available Tools (12)

#### 📊 Data Garden
| Tool | Purpose | Status |
|------|---------|--------|
| `nursery_generate_data(tool_name, num_examples)` | Generate synthetic training data | ✅ Working |
| `nursery_extract_conversations(source)` | Extract from chat history | ✅ Working |
| `nursery_list_datasets()` | List available datasets | ✅ Working |

#### 🔥 Training Forge
| Tool | Purpose | Status |
|------|---------|--------|
| `nursery_estimate_cost(dataset_name, base_model, epochs)` | Estimate cloud costs | ✅ Working |
| `nursery_train_cloud(dataset_name, base_model, output_name, provider)` | Train on cloud GPU | ✅ Working |
| `nursery_train_local(dataset_name, base_model)` | Train locally | ⚠️ Needs GPU |
| `nursery_job_status(job_id)` | Check training progress | ✅ Working |
| `nursery_list_jobs()` | List all jobs | ✅ Working |

#### 🧒 Model Cradle
| Tool | Purpose | Status |
|------|---------|--------|
| `nursery_list_models()` | List trained adapters | ✅ Working |
| `nursery_deploy_ollama(model_name)` | Push to Ollama | ⏳ TODO |
| `nursery_test_model(model_name, prompt)` | Quick inference | ⏳ TODO |
| `nursery_compare_models(model_a, model_b, prompts)` | A/B comparison | ⏳ TODO |

---

## Workflows

### 1. Generate Training Data

```python
# For tools in DEFAULT_TOOLS (calculator, get_current_time, memory_store, etc.)
nursery_generate_data(
    tool_name="memory_store",
    num_examples=50,
    variation_level="medium"
)

# Check what we generated
nursery_list_datasets()
```

**Note:** Custom tools (not in DEFAULT_TOOLS) need example queries added to the SyntheticGenerator.

### 2. Train on Cloud (Vast.ai)

**Verified workflow (2026-01-23):**

```python
# 1. Generate or prepare dataset
nursery_generate_data("memory_store", num_examples=100)

# 2. Estimate cost
nursery_estimate_cost("dataset_name", base_model="3b", epochs=3)

# 3. Manual Vast.ai workflow (until nursery_train_cloud is enhanced):
```

**Manual Cloud Training Steps:**

```bash
# 1. Search for GPUs
# GET https://console.vast.ai/api/v0/bundles/
# Filter: verified=true, reliability>0.95, dph_total<1.0

# 2. Rent GPU
# PUT https://console.vast.ai/api/v0/asks/{offer_id}/
# Body: {image: "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime", disk: 20}

# 3. Wait for running status
# GET https://console.vast.ai/api/v0/instances/{contract_id}/

# 4. SSH in and install packages
ssh -p {port} root@{host}
pip install transformers peft datasets accelerate

# 5. Upload data and script
scp -P {port} dataset.jsonl root@{host}:/workspace/
scp -P {port} train.py root@{host}:/workspace/

# 6. Run training
ssh -p {port} root@{host} "cd /workspace && python train.py"

# 7. Download results
scp -r -P {port} root@{host}:/workspace/lora_output ./

# 8. IMPORTANT: Destroy instance!
# DELETE https://console.vast.ai/api/v0/instances/{contract_id}/
```

### 3. Training Script Template

```python
#!/usr/bin/env python3
"""LoRA Training Template"""
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

BASE_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"  # or Llama-3.2-3B
DATA_FILE = "/workspace/training_data.jsonl"
OUTPUT_DIR = "/workspace/lora_output"

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
tokenizer.pad_token = tokenizer.eos_token

# Load and format data
with open(DATA_FILE) as f:
    raw_data = [json.loads(line) for line in f]

def format_example(ex):
    text = f"<|im_start|>user\n{ex['user_query']}<|im_end|>\n"
    text += f"<|im_start|>assistant\n<tool_call>{ex['tool_name']}({json.dumps(ex['tool_arguments'])})</tool_call><|im_end|>"
    return {"text": text}

dataset = Dataset.from_list([format_example(ex) for ex in raw_data])

# Tokenize
def tokenize(examples):
    return tokenizer(examples["text"], truncation=True, max_length=256, padding="max_length")

tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])
tokenized = tokenized.map(lambda x: {"labels": x["input_ids"].copy()})

# Load model (FP16)
model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, torch_dtype=torch.float16, device_map="auto")

# LoRA config
lora_config = LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
                         lora_dropout=0.05, bias="none", task_type=TaskType.CAUSAL_LM)
model = get_peft_model(model, lora_config)

# Train
trainer = Trainer(
    model=model,
    args=TrainingArguments(output_dir=OUTPUT_DIR, num_train_epochs=2, per_device_train_batch_size=4,
                          learning_rate=2e-4, fp16=True, logging_steps=1, report_to="none"),
    train_dataset=tokenized,
)
trainer.train()

# Save
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
```

---

## Storage Locations

```
sandbox/nursery/
├── datasets/           # Training data (.jsonl)
│   ├── combined_tools.jsonl
│   ├── memory_store_*.jsonl
│   └── test_*.jsonl
├── models/             # Trained adapters
│   └── tinyllama_tools_lora/
│       ├── adapter_config.json
│       ├── adapter_model.safetensors
│       └── tokenizer.json
└── training_jobs.json  # Job history
```

---

## Cloud Provider Status

| Provider | Status | Cost | Notes |
|----------|--------|------|-------|
| **Vast.ai** | ✅ VERIFIED | $24.96 credit | HTTP API, SSH access |
| **Replicate** | ✅ Connected | Per-job | Needs public URL for data |
| Together.ai | ○ Key needed | Per-token | Managed fine-tuning API |
| RunPod | ○ Key needed | Per-hour | Good availability |
| Modal | ○ Setup needed | Per-second | Python-native serverless |

---

## Recommended GPU Tiers

| Use Case | GPU | VRAM | Est. Cost |
|----------|-----|------|-----------|
| Quick test (1B) | RTX 3080 Ti | 12GB | $0.03-0.05/hr |
| Standard (3B) | RTX 4090/5090 | 24-32GB | $0.20-0.40/hr |
| Large (7B) | A100 40GB | 40GB | $0.80-1.50/hr |
| XL (13B+) | A100 80GB / H100 | 80GB+ | $2.00-4.00/hr |

---

## Training Records

### 2026-01-23: First Successful Training ✅

- **GPU:** RTX 5090 (32GB) @ $0.376/hr
- **Model:** TinyLlama 1.1B
- **Data:** 45 tool-use examples (memory_store)
- **Time:** 3.89 seconds
- **Loss:** 2.95 → 1.50
- **Cost:** ~$0.09 total
- **Output:** `sandbox/nursery/models/tinyllama_tools_lora/`

---

## Troubleshooting

### PyTorch/Transformers Version Mismatch
```bash
# Error: 'torch.utils._pytree' has no attribute 'register_pytree_node'
pip install --upgrade torch transformers peft
```

### GPU Not Detected
```bash
nvidia-smi  # Check GPU status
# If ERR! appears, instance may have hardware issues - destroy and rent another
```

### Data Generation Fails for Custom Tools
The `generate_without_llm` method needs example queries. Either:
1. Use tools from `DEFAULT_TOOLS` (calculator, memory_store, etc.)
2. Add examples to the SyntheticGenerator for your tool

---

## TODO

- [ ] Implement `nursery_deploy_ollama` (merge adapter + GGUF convert + Modelfile)
- [ ] Implement `nursery_test_model` (quick inference via Ollama or transformers)
- [ ] Implement `nursery_compare_models` (A/B testing)
- [ ] Add more tools to SyntheticGenerator DEFAULT_TOOLS
- [ ] Automate full Vast.ai workflow in `nursery_train_cloud`

---

*"From the Nursery, new minds emerge to join the Village."* 🌱
