"""
Cloud Training Integration for ApexAurum
=========================================

Supports multiple cloud GPU providers for training from Pi or PC:
- Vast.ai - Cheap GPU rentals, SSH access
- RunPod - GPU pods with API
- Modal - Serverless GPU, Python-native
- Together.ai - Fine-tuning API
- Replicate - Training API with hosting

Usage:
    from reusable_lib.training import CloudTrainer, CloudProvider

    # Together.ai (easiest)
    trainer = CloudTrainer(CloudProvider.TOGETHER)
    job = trainer.start_training(
        base_model="meta-llama/Llama-3.2-3B",
        dataset_path="training_data.jsonl",
        output_name="my-finetuned-model"
    )
    trainer.wait_for_completion(job.id)
    trainer.download_model(job.id, "models/")

    # Vast.ai (cheapest)
    trainer = CloudTrainer(CloudProvider.VASTAI)
    instance = trainer.rent_gpu(gpu_type="RTX_4090", max_price=0.50)
    trainer.upload_and_train(instance, dataset_path, training_script)
    trainer.download_results(instance, "models/")
"""

import os
import json
import time
import subprocess
import tempfile
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class CloudProvider(Enum):
    """Supported cloud training providers."""
    VASTAI = "vastai"
    RUNPOD = "runpod"
    MODAL = "modal"
    TOGETHER = "together"
    REPLICATE = "replicate"
    LAMBDA = "lambda"


@dataclass
class TrainingJob:
    """Represents a cloud training job."""
    id: str
    provider: CloudProvider
    status: str = "pending"
    model_name: str = ""
    base_model: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    progress: float = 0.0
    cost: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider.value,
            "status": self.status,
            "model_name": self.model_name,
            "base_model": self.base_model,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": self.progress,
            "cost": self.cost,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class GPUInstance:
    """Represents a rented GPU instance."""
    id: str
    provider: CloudProvider
    gpu_type: str
    gpu_count: int = 1
    status: str = "pending"
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_user: str = "root"
    hourly_cost: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CloudTrainerBase(ABC):
    """Base class for cloud training providers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._http_client = None

    @property
    def http_client(self):
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.Client(timeout=60.0)
            except ImportError:
                raise ImportError("httpx required: pip install httpx")
        return self._http_client

    @abstractmethod
    def start_training(self, **kwargs) -> TrainingJob:
        """Start a training job."""
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> TrainingJob:
        """Get training job status."""
        pass

    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a training job."""
        pass

    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: int = 30,
        timeout: int = 7200,
        callback: Optional[Callable[[TrainingJob], None]] = None
    ) -> TrainingJob:
        """Wait for training job to complete."""
        start_time = time.time()
        while True:
            job = self.get_status(job_id)

            if callback:
                callback(job)

            if job.status in ("completed", "succeeded", "ready"):
                return job

            if job.status in ("failed", "error", "cancelled"):
                raise RuntimeError(f"Training failed: {job.error}")

            if time.time() - start_time > timeout:
                raise TimeoutError(f"Training timed out after {timeout}s")

            time.sleep(poll_interval)


class TogetherTrainer(CloudTrainerBase):
    """
    Together.ai fine-tuning API.

    Pros: Easy API, good model selection, managed infrastructure
    Cons: Limited customization, higher cost than self-managed

    Env: TOGETHER_API_KEY
    """

    BASE_URL = "https://api.together.xyz/v1"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("TOGETHER_API_KEY"))
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY required")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def upload_dataset(self, file_path: str) -> str:
        """Upload training dataset (JSONL format)."""
        with open(file_path, "rb") as f:
            response = self.http_client.post(
                f"{self.BASE_URL}/files",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": (Path(file_path).name, f, "application/jsonl")},
                data={"purpose": "fine-tune"},
            )
        response.raise_for_status()
        return response.json()["id"]

    def list_models(self) -> List[Dict[str, Any]]:
        """List available base models for fine-tuning."""
        response = self.http_client.get(
            f"{self.BASE_URL}/models",
            headers=self._headers(),
        )
        response.raise_for_status()
        # Filter to fine-tunable models
        models = response.json()
        return [m for m in models if m.get("fine_tuning_supported", False)]

    def start_training(
        self,
        base_model: str,
        dataset_path: str,
        output_name: str,
        n_epochs: int = 3,
        learning_rate: float = 1e-5,
        batch_size: int = 4,
        lora_rank: int = 16,
        lora_alpha: int = 32,
        **kwargs
    ) -> TrainingJob:
        """Start a fine-tuning job on Together.ai."""

        # Upload dataset first
        logger.info(f"Uploading dataset: {dataset_path}")
        file_id = self.upload_dataset(dataset_path)

        # Create fine-tuning job
        payload = {
            "training_file": file_id,
            "model": base_model,
            "suffix": output_name,
            "n_epochs": n_epochs,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "lora": True,
            "lora_r": lora_rank,
            "lora_alpha": lora_alpha,
        }
        payload.update(kwargs)

        response = self.http_client.post(
            f"{self.BASE_URL}/fine-tunes",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return TrainingJob(
            id=data["id"],
            provider=CloudProvider.TOGETHER,
            status=data.get("status", "pending"),
            model_name=output_name,
            base_model=base_model,
            metadata={"file_id": file_id, "response": data},
        )

    def get_status(self, job_id: str) -> TrainingJob:
        """Get fine-tuning job status."""
        response = self.http_client.get(
            f"{self.BASE_URL}/fine-tunes/{job_id}",
            headers=self._headers(),
        )
        response.raise_for_status()
        data = response.json()

        return TrainingJob(
            id=job_id,
            provider=CloudProvider.TOGETHER,
            status=data.get("status", "unknown"),
            model_name=data.get("output_name", ""),
            base_model=data.get("model", ""),
            progress=data.get("training_progress", 0.0),
            metadata=data,
        )

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a fine-tuning job."""
        response = self.http_client.post(
            f"{self.BASE_URL}/fine-tunes/{job_id}/cancel",
            headers=self._headers(),
        )
        return response.status_code == 200

    def download_model(self, job_id: str, output_dir: str) -> str:
        """
        Download the fine-tuned model.
        Note: Together.ai hosts models, so this gets the model ID for inference.
        """
        job = self.get_status(job_id)
        if job.status not in ("completed", "succeeded"):
            raise ValueError(f"Job not complete: {job.status}")

        # Save model info for later use
        output_path = Path(output_dir) / f"{job.model_name}_together.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        model_info = {
            "provider": "together",
            "model_id": job.metadata.get("fine_tuned_model"),
            "base_model": job.base_model,
            "job_id": job_id,
            "created_at": job.created_at,
        }

        with open(output_path, "w") as f:
            json.dump(model_info, f, indent=2)

        logger.info(f"Model info saved to {output_path}")
        return str(output_path)


class ReplicateTrainer(CloudTrainerBase):
    """
    Replicate training API.

    Pros: Easy deployment, versioned models, web UI
    Cons: Less control over training params

    Env: REPLICATE_API_TOKEN
    """

    BASE_URL = "https://api.replicate.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("REPLICATE_API_TOKEN"))
        if not self.api_key:
            raise ValueError("REPLICATE_API_TOKEN required")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    def start_training(
        self,
        base_model: str,
        dataset_url: str,
        destination: str,
        **kwargs
    ) -> TrainingJob:
        """
        Start training on Replicate.

        Args:
            base_model: Model to fine-tune (e.g., "meta/llama-2-7b")
            dataset_url: URL to training data (must be publicly accessible)
            destination: Your model destination (e.g., "username/model-name")
        """
        payload = {
            "destination": destination,
            "input": {
                "train_data": dataset_url,
                **kwargs
            },
        }

        response = self.http_client.post(
            f"{self.BASE_URL}/models/{base_model}/versions/latest/trainings",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return TrainingJob(
            id=data["id"],
            provider=CloudProvider.REPLICATE,
            status=data.get("status", "starting"),
            model_name=destination,
            base_model=base_model,
            metadata=data,
        )

    def get_status(self, job_id: str) -> TrainingJob:
        """Get training status."""
        response = self.http_client.get(
            f"{self.BASE_URL}/trainings/{job_id}",
            headers=self._headers(),
        )
        response.raise_for_status()
        data = response.json()

        return TrainingJob(
            id=job_id,
            provider=CloudProvider.REPLICATE,
            status=data.get("status", "unknown"),
            metadata=data,
        )

    def cancel_job(self, job_id: str) -> bool:
        """Cancel training."""
        response = self.http_client.post(
            f"{self.BASE_URL}/trainings/{job_id}/cancel",
            headers=self._headers(),
        )
        return response.status_code == 200


class VastAITrainer(CloudTrainerBase):
    """
    Vast.ai GPU rental with SSH access.

    Pros: Cheapest GPUs, full control, SSH access
    Cons: More setup required, variable availability

    Env: VASTAI_API_KEY
    Requires: vastai CLI (pip install vastai)
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("VASTAI_API_KEY"))
        self._check_cli()

    def _check_cli(self):
        """Check if vastai CLI is installed."""
        try:
            result = subprocess.run(
                ["vastai", "--help"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError("vastai CLI not working")
        except FileNotFoundError:
            raise ImportError("vastai CLI required: pip install vastai")

    def _run_vastai(self, *args) -> str:
        """Run vastai CLI command."""
        cmd = ["vastai"]
        if self.api_key:
            cmd.extend(["--api-key", self.api_key])
        cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"vastai error: {result.stderr}")
        return result.stdout

    def search_gpus(
        self,
        gpu_type: str = "RTX_4090",
        min_gpu_ram: int = 24,
        max_price: float = 1.0,
        num_gpus: int = 1,
    ) -> List[Dict[str, Any]]:
        """Search for available GPU instances."""
        query = f"gpu_name={gpu_type} gpu_ram>={min_gpu_ram} num_gpus>={num_gpus} dph<={max_price}"
        output = self._run_vastai("search", "offers", query, "--raw")
        return json.loads(output) if output.strip() else []

    def rent_gpu(
        self,
        offer_id: Optional[int] = None,
        gpu_type: str = "RTX_4090",
        max_price: float = 0.50,
        image: str = "pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime",
        disk_gb: int = 50,
    ) -> GPUInstance:
        """Rent a GPU instance."""

        # Find best offer if not specified
        if offer_id is None:
            offers = self.search_gpus(gpu_type=gpu_type, max_price=max_price)
            if not offers:
                raise ValueError(f"No {gpu_type} available under ${max_price}/hr")
            offer_id = offers[0]["id"]
            logger.info(f"Selected offer {offer_id}: {offers[0]}")

        # Create instance
        output = self._run_vastai(
            "create", "instance", str(offer_id),
            "--image", image,
            "--disk", str(disk_gb),
            "--raw"
        )
        data = json.loads(output)

        return GPUInstance(
            id=str(data.get("new_contract")),
            provider=CloudProvider.VASTAI,
            gpu_type=gpu_type,
            status="starting",
            hourly_cost=data.get("dph_total", 0),
            metadata=data,
        )

    def get_instance_status(self, instance_id: str) -> GPUInstance:
        """Get instance status and SSH details."""
        output = self._run_vastai("show", "instance", instance_id, "--raw")
        data = json.loads(output)

        return GPUInstance(
            id=instance_id,
            provider=CloudProvider.VASTAI,
            gpu_type=data.get("gpu_name", "unknown"),
            status=data.get("actual_status", "unknown"),
            ssh_host=data.get("ssh_host"),
            ssh_port=data.get("ssh_port", 22),
            hourly_cost=data.get("dph_total", 0),
            metadata=data,
        )

    def wait_for_instance(self, instance_id: str, timeout: int = 300) -> GPUInstance:
        """Wait for instance to be ready."""
        start = time.time()
        while time.time() - start < timeout:
            instance = self.get_instance_status(instance_id)
            if instance.status == "running" and instance.ssh_host:
                return instance
            if instance.status in ("error", "failed"):
                raise RuntimeError(f"Instance failed: {instance.metadata}")
            time.sleep(10)
        raise TimeoutError("Instance startup timed out")

    def destroy_instance(self, instance_id: str) -> bool:
        """Destroy a rented instance."""
        try:
            self._run_vastai("destroy", "instance", instance_id)
            return True
        except Exception as e:
            logger.error(f"Failed to destroy instance: {e}")
            return False

    def upload_file(self, instance: GPUInstance, local_path: str, remote_path: str):
        """Upload file to instance via SCP."""
        if not instance.ssh_host:
            raise ValueError("Instance not ready (no SSH host)")

        cmd = [
            "scp", "-P", str(instance.ssh_port),
            "-o", "StrictHostKeyChecking=no",
            local_path,
            f"{instance.ssh_user}@{instance.ssh_host}:{remote_path}"
        ]
        subprocess.run(cmd, check=True)

    def run_command(self, instance: GPUInstance, command: str) -> str:
        """Run command on instance via SSH."""
        if not instance.ssh_host:
            raise ValueError("Instance not ready")

        cmd = [
            "ssh", "-p", str(instance.ssh_port),
            "-o", "StrictHostKeyChecking=no",
            f"{instance.ssh_user}@{instance.ssh_host}",
            command
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout + result.stderr

    def download_file(self, instance: GPUInstance, remote_path: str, local_path: str):
        """Download file from instance via SCP."""
        if not instance.ssh_host:
            raise ValueError("Instance not ready")

        cmd = [
            "scp", "-P", str(instance.ssh_port),
            "-o", "StrictHostKeyChecking=no",
            f"{instance.ssh_user}@{instance.ssh_host}:{remote_path}",
            local_path
        ]
        subprocess.run(cmd, check=True)

    def start_training(self, **kwargs) -> TrainingJob:
        """
        For Vast.ai, training is done via SSH commands.
        Use rent_gpu() + run_command() + upload/download instead.
        """
        raise NotImplementedError(
            "Vast.ai uses SSH-based training. Use rent_gpu(), upload_file(), "
            "run_command(), and download_file() methods instead."
        )

    def get_status(self, job_id: str) -> TrainingJob:
        raise NotImplementedError("Use get_instance_status() for Vast.ai")

    def cancel_job(self, job_id: str) -> bool:
        return self.destroy_instance(job_id)


class RunPodTrainer(CloudTrainerBase):
    """
    RunPod GPU pods.

    Pros: Good availability, templates, serverless option
    Cons: Slightly higher cost than Vast.ai

    Env: RUNPOD_API_KEY
    """

    BASE_URL = "https://api.runpod.io/graphql"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("RUNPOD_API_KEY"))
        if not self.api_key:
            raise ValueError("RUNPOD_API_KEY required")

    def _graphql(self, query: str, variables: Dict = None) -> Dict:
        """Execute GraphQL query."""
        response = self.http_client.post(
            self.BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"query": query, "variables": variables or {}},
        )
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")
        return data["data"]

    def list_gpus(self) -> List[Dict[str, Any]]:
        """List available GPU types."""
        query = """
        query {
            gpuTypes {
                id
                displayName
                memoryInGb
            }
        }
        """
        return self._graphql(query)["gpuTypes"]

    def create_pod(
        self,
        gpu_type: str = "NVIDIA RTX 4090",
        gpu_count: int = 1,
        image: str = "runpod/pytorch:2.1.0-py3.10-cuda12.1.0-devel-ubuntu22.04",
        disk_gb: int = 50,
        volume_gb: int = 50,
        name: str = "apex-training",
    ) -> GPUInstance:
        """Create a GPU pod."""
        query = """
        mutation($input: PodFindAndDeployOnDemandInput!) {
            podFindAndDeployOnDemand(input: $input) {
                id
                name
                runtime {
                    uptimeInSeconds
                    ports {
                        ip
                        publicPort
                        privatePort
                    }
                }
            }
        }
        """
        variables = {
            "input": {
                "cloudType": "SECURE",
                "gpuTypeId": gpu_type,
                "gpuCount": gpu_count,
                "containerDiskInGb": disk_gb,
                "volumeInGb": volume_gb,
                "imageName": image,
                "name": name,
            }
        }

        data = self._graphql(query, variables)["podFindAndDeployOnDemand"]

        return GPUInstance(
            id=data["id"],
            provider=CloudProvider.RUNPOD,
            gpu_type=gpu_type,
            gpu_count=gpu_count,
            status="starting",
            metadata=data,
        )

    def get_pod_status(self, pod_id: str) -> GPUInstance:
        """Get pod status."""
        query = """
        query($podId: String!) {
            pod(input: { podId: $podId }) {
                id
                name
                desiredStatus
                runtime {
                    uptimeInSeconds
                    ports {
                        ip
                        publicPort
                        privatePort
                    }
                }
            }
        }
        """
        data = self._graphql(query, {"podId": pod_id})["pod"]

        # Extract SSH info from ports
        ssh_info = None
        if data.get("runtime", {}).get("ports"):
            for port in data["runtime"]["ports"]:
                if port["privatePort"] == 22:
                    ssh_info = port
                    break

        return GPUInstance(
            id=pod_id,
            provider=CloudProvider.RUNPOD,
            gpu_type="",
            status=data.get("desiredStatus", "unknown"),
            ssh_host=ssh_info["ip"] if ssh_info else None,
            ssh_port=ssh_info["publicPort"] if ssh_info else 22,
            metadata=data,
        )

    def terminate_pod(self, pod_id: str) -> bool:
        """Terminate a pod."""
        query = """
        mutation($podId: String!) {
            podTerminate(input: { podId: $podId })
        }
        """
        try:
            self._graphql(query, {"podId": pod_id})
            return True
        except Exception:
            return False

    def start_training(self, **kwargs) -> TrainingJob:
        raise NotImplementedError("Use create_pod() for RunPod")

    def get_status(self, job_id: str) -> TrainingJob:
        raise NotImplementedError("Use get_pod_status() for RunPod")

    def cancel_job(self, job_id: str) -> bool:
        return self.terminate_pod(job_id)


class ModalTrainer(CloudTrainerBase):
    """
    Modal serverless GPU compute.

    Pros: Python-native, no instance management, scales to zero
    Cons: Requires Modal account and setup

    Env: MODAL_TOKEN_ID, MODAL_TOKEN_SECRET
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self._check_modal()

    def _check_modal(self):
        """Check if Modal is installed and configured."""
        try:
            import modal
            self.modal = modal
        except ImportError:
            raise ImportError("Modal required: pip install modal")

    def create_training_function(
        self,
        base_model: str,
        dataset_path: str,
        output_dir: str = "/results",
        gpu: str = "A100",
        timeout: int = 3600,
    ) -> str:
        """
        Create a Modal training function.
        Returns the function code to be run with `modal run`.
        """
        code = f'''
import modal

app = modal.App("apex-training")

image = modal.Image.debian_slim().pip_install(
    "torch", "transformers", "peft", "datasets",
    "accelerate", "bitsandbytes", "wandb"
)

@app.function(
    gpu="{gpu}",
    timeout={timeout},
    image=image,
    volumes={{"/data": modal.Volume.from_name("training-data")}},
)
def train():
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from peft import LoraConfig, get_peft_model
    from datasets import load_dataset

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        "{base_model}",
        load_in_8bit=True,
        device_map="auto",
    )
    tokenizer = AutoTokenizer.from_pretrained("{base_model}")

    # LoRA config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    # Load dataset
    dataset = load_dataset("json", data_files="/data/training.jsonl")

    # Training args
    args = TrainingArguments(
        output_dir="{output_dir}",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-5,
        fp16=True,
        save_steps=100,
        logging_steps=10,
    )

    # Train
    from transformers import Trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset["train"],
    )
    trainer.train()

    # Save
    model.save_pretrained("{output_dir}")
    tokenizer.save_pretrained("{output_dir}")

    return "{output_dir}"

if __name__ == "__main__":
    with app.run():
        result = train.remote()
        print(f"Training complete: {{result}}")
'''
        return code

    def start_training(self, **kwargs) -> TrainingJob:
        raise NotImplementedError(
            "Modal uses Python decorators. Use create_training_function() "
            "to generate code, then run with `modal run script.py`"
        )

    def get_status(self, job_id: str) -> TrainingJob:
        raise NotImplementedError("Check Modal dashboard for status")

    def cancel_job(self, job_id: str) -> bool:
        raise NotImplementedError("Cancel via Modal dashboard or CLI")


# =============================================================================
# Main CloudTrainer facade
# =============================================================================

class CloudTrainer:
    """
    Unified interface for cloud training providers.

    Usage:
        trainer = CloudTrainer(CloudProvider.TOGETHER)
        job = trainer.start_training(...)
        trainer.wait_for_completion(job.id)
    """

    PROVIDERS = {
        CloudProvider.TOGETHER: TogetherTrainer,
        CloudProvider.REPLICATE: ReplicateTrainer,
        CloudProvider.VASTAI: VastAITrainer,
        CloudProvider.RUNPOD: RunPodTrainer,
        CloudProvider.MODAL: ModalTrainer,
    }

    def __init__(self, provider: CloudProvider, api_key: Optional[str] = None):
        self.provider = provider
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        self._trainer = self.PROVIDERS[provider](api_key)

    def __getattr__(self, name):
        """Delegate to underlying trainer."""
        return getattr(self._trainer, name)

    @classmethod
    def list_providers(cls) -> List[Dict[str, Any]]:
        """List available providers with descriptions."""
        return [
            {
                "id": CloudProvider.TOGETHER.value,
                "name": "Together.ai",
                "type": "api",
                "description": "Managed fine-tuning API, easy setup",
                "env_key": "TOGETHER_API_KEY",
                "pricing": "Per token, ~$0.0004/1K tokens training",
            },
            {
                "id": CloudProvider.REPLICATE.value,
                "name": "Replicate",
                "type": "api",
                "description": "Training API with model hosting",
                "env_key": "REPLICATE_API_TOKEN",
                "pricing": "Per training job",
            },
            {
                "id": CloudProvider.VASTAI.value,
                "name": "Vast.ai",
                "type": "rental",
                "description": "Cheapest GPU rentals, SSH access",
                "env_key": "VASTAI_API_KEY",
                "pricing": "~$0.20-1.50/hr depending on GPU",
            },
            {
                "id": CloudProvider.RUNPOD.value,
                "name": "RunPod",
                "type": "rental",
                "description": "GPU pods with good availability",
                "env_key": "RUNPOD_API_KEY",
                "pricing": "~$0.40-2.50/hr depending on GPU",
            },
            {
                "id": CloudProvider.MODAL.value,
                "name": "Modal",
                "type": "serverless",
                "description": "Serverless GPU, Python-native",
                "env_key": "MODAL_TOKEN_ID",
                "pricing": "Per second of GPU use",
            },
        ]


# =============================================================================
# Convenience functions
# =============================================================================

def quick_cloud_train(
    provider: str,
    base_model: str,
    dataset_path: str,
    output_name: str,
    **kwargs
) -> TrainingJob:
    """
    Quick cloud training with minimal setup.

    Args:
        provider: Provider name (together, replicate, vastai, runpod, modal)
        base_model: Base model to fine-tune
        dataset_path: Path to JSONL training data
        output_name: Name for the fine-tuned model
        **kwargs: Additional provider-specific arguments

    Returns:
        TrainingJob with status
    """
    provider_enum = CloudProvider(provider.lower())
    trainer = CloudTrainer(provider_enum)

    if provider_enum in (CloudProvider.TOGETHER, CloudProvider.REPLICATE):
        return trainer.start_training(
            base_model=base_model,
            dataset_path=dataset_path,
            output_name=output_name,
            **kwargs
        )
    else:
        raise ValueError(
            f"quick_cloud_train only supports API providers (together, replicate). "
            f"For {provider}, use CloudTrainer directly with rent_gpu() workflow."
        )


def estimate_training_cost(
    provider: str,
    dataset_size_mb: float,
    base_model_params_b: float,
    n_epochs: int = 3,
) -> Dict[str, Any]:
    """
    Estimate training cost for different providers.

    Args:
        provider: Provider name
        dataset_size_mb: Dataset size in MB
        base_model_params_b: Model parameters in billions (e.g., 3 for 3B)
        n_epochs: Number of training epochs

    Returns:
        Dict with cost estimates and recommendations
    """
    # Rough estimates based on typical training scenarios
    tokens_estimate = dataset_size_mb * 250_000  # ~250K tokens per MB of JSONL

    # Training time estimates (hours)
    # Rough: 1B params * 1M tokens * 3 epochs ≈ 1 hour on A100
    hours_estimate = (base_model_params_b * tokens_estimate / 1_000_000 * n_epochs) / 10

    estimates = {
        "dataset_tokens_estimate": int(tokens_estimate),
        "training_hours_estimate": round(hours_estimate, 1),
        "providers": {}
    }

    # Provider-specific estimates
    if provider in ("together", "all"):
        estimates["providers"]["together"] = {
            "cost_estimate": round(tokens_estimate * 0.0004 / 1000, 2),
            "notes": "Managed, no GPU management needed",
        }

    if provider in ("vastai", "all"):
        estimates["providers"]["vastai"] = {
            "cost_estimate": round(hours_estimate * 0.50, 2),  # Avg $0.50/hr
            "notes": "Cheapest, requires SSH setup",
        }

    if provider in ("runpod", "all"):
        estimates["providers"]["runpod"] = {
            "cost_estimate": round(hours_estimate * 0.80, 2),  # Avg $0.80/hr
            "notes": "Good availability, templates available",
        }

    if provider in ("modal", "all"):
        estimates["providers"]["modal"] = {
            "cost_estimate": round(hours_estimate * 1.10, 2),  # ~$1.10/hr A100
            "notes": "Serverless, scales to zero",
        }

    return estimates
