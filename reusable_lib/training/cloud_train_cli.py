#!/usr/bin/env python3
"""
Cloud Training CLI for ApexAurum
================================

Simple command-line interface for cloud training operations.

Usage:
    python -m reusable_lib.training.cloud_train_cli providers
    python -m reusable_lib.training.cloud_train_cli estimate --dataset data.jsonl --model 3b
    python -m reusable_lib.training.cloud_train_cli train --provider together --model meta-llama/Llama-3.2-3B --dataset data.jsonl
    python -m reusable_lib.training.cloud_train_cli status --provider together --job-id ft-xxxxx
    python -m reusable_lib.training.cloud_train_cli gpus --provider vastai --max-price 0.50
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reusable_lib.training.cloud_trainer import (
    CloudTrainer,
    CloudProvider,
    estimate_training_cost,
)


def cmd_providers(args):
    """List available cloud training providers."""
    providers = CloudTrainer.list_providers()

    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║              Cloud Training Providers                          ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    for p in providers:
        status = "✓" if os.getenv(p["env_key"]) else "○"
        print(f"  [{status}] {p['name']:<15} ({p['type']})")
        print(f"      {p['description']}")
        print(f"      Env: {p['env_key']}")
        print(f"      Pricing: {p['pricing']}")
        print()

    print("  Legend: [✓] API key configured  [○] Not configured\n")


def cmd_estimate(args):
    """Estimate training costs."""
    # Get dataset size
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset not found: {args.dataset}")
        sys.exit(1)

    dataset_size_mb = dataset_path.stat().st_size / (1024 * 1024)

    # Parse model size (e.g., "3b" -> 3.0)
    model_size = args.model.lower().replace("b", "")
    try:
        model_params = float(model_size)
    except ValueError:
        print(f"Error: Invalid model size: {args.model}. Use format like '3b' or '7b'")
        sys.exit(1)

    estimates = estimate_training_cost(
        provider="all",
        dataset_size_mb=dataset_size_mb,
        base_model_params_b=model_params,
        n_epochs=args.epochs,
    )

    print("\n╔═══════════════════════════════════════════════════════════════╗")
    print("║              Training Cost Estimates                           ║")
    print("╚═══════════════════════════════════════════════════════════════╝\n")

    print(f"  Dataset:        {args.dataset}")
    print(f"  Dataset Size:   {dataset_size_mb:.2f} MB")
    print(f"  Est. Tokens:    {estimates['dataset_tokens_estimate']:,}")
    print(f"  Model Size:     {model_params}B parameters")
    print(f"  Epochs:         {args.epochs}")
    print(f"  Est. Time:      {estimates['training_hours_estimate']} hours")
    print()

    print("  Provider Estimates:")
    print("  ───────────────────────────────────────────────────────────────")
    for name, info in estimates["providers"].items():
        print(f"    {name:<12} ${info['cost_estimate']:<8} - {info['notes']}")
    print()


def cmd_train(args):
    """Start a cloud training job."""
    try:
        provider = CloudProvider(args.provider.lower())
    except ValueError:
        print(f"Error: Unknown provider: {args.provider}")
        print("Use 'providers' command to see available providers")
        sys.exit(1)

    trainer = CloudTrainer(provider)

    print(f"\nStarting training on {args.provider}...")
    print(f"  Model:   {args.model}")
    print(f"  Dataset: {args.dataset}")
    print(f"  Name:    {args.name}")
    print()

    try:
        job = trainer.start_training(
            base_model=args.model,
            dataset_path=args.dataset,
            output_name=args.name,
            n_epochs=args.epochs,
            learning_rate=args.lr,
        )

        print(f"✓ Training job started!")
        print(f"  Job ID: {job.id}")
        print(f"  Status: {job.status}")
        print()
        print(f"  Monitor with: python -m reusable_lib.training.cloud_train_cli status --provider {args.provider} --job-id {job.id}")

        if args.wait:
            print("\nWaiting for completion...")
            job = trainer.wait_for_completion(
                job.id,
                callback=lambda j: print(f"  Progress: {j.progress:.1%} - {j.status}")
            )
            print(f"\n✓ Training complete!")
            print(f"  Final status: {job.status}")

    except Exception as e:
        print(f"✗ Training failed: {e}")
        sys.exit(1)


def cmd_status(args):
    """Check training job status."""
    try:
        provider = CloudProvider(args.provider.lower())
    except ValueError:
        print(f"Error: Unknown provider: {args.provider}")
        sys.exit(1)

    trainer = CloudTrainer(provider)

    try:
        job = trainer.get_status(args.job_id)

        print(f"\n  Job ID:    {job.id}")
        print(f"  Provider:  {job.provider.value}")
        print(f"  Status:    {job.status}")
        print(f"  Progress:  {job.progress:.1%}")
        if job.model_name:
            print(f"  Model:     {job.model_name}")
        if job.error:
            print(f"  Error:     {job.error}")
        print()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_gpus(args):
    """Search for available GPUs (Vast.ai / RunPod)."""
    try:
        provider = CloudProvider(args.provider.lower())
    except ValueError:
        print(f"Error: Unknown provider: {args.provider}")
        sys.exit(1)

    if provider == CloudProvider.VASTAI:
        trainer = CloudTrainer(provider)

        print(f"\nSearching Vast.ai for {args.gpu} under ${args.max_price}/hr...\n")

        try:
            offers = trainer.search_gpus(
                gpu_type=args.gpu,
                max_price=args.max_price,
                num_gpus=args.num_gpus,
            )

            if not offers:
                print("  No matching GPUs found.")
                return

            print(f"  {'ID':<10} {'GPU':<20} {'VRAM':<8} {'$/hr':<8} {'Location'}")
            print("  " + "─" * 60)

            for offer in offers[:10]:  # Top 10
                print(f"  {offer.get('id', 'N/A'):<10} "
                      f"{offer.get('gpu_name', 'N/A'):<20} "
                      f"{offer.get('gpu_ram', 'N/A'):<8} "
                      f"${offer.get('dph_total', 0):<7.3f} "
                      f"{offer.get('geolocation', 'N/A')}")

            print()
            print(f"  To rent: python -m reusable_lib.training.cloud_train_cli rent --provider vastai --offer-id <ID>")

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print(f"GPU search not supported for {args.provider}. Try vastai or runpod.")


def cmd_rent(args):
    """Rent a GPU instance."""
    try:
        provider = CloudProvider(args.provider.lower())
    except ValueError:
        print(f"Error: Unknown provider: {args.provider}")
        sys.exit(1)

    trainer = CloudTrainer(provider)

    print(f"\nRenting GPU on {args.provider}...")

    try:
        if provider == CloudProvider.VASTAI:
            instance = trainer.rent_gpu(
                offer_id=args.offer_id,
                gpu_type=args.gpu,
                max_price=args.max_price,
            )
        elif provider == CloudProvider.RUNPOD:
            instance = trainer.create_pod(
                gpu_type=args.gpu,
                name=args.name or "apex-training",
            )
        else:
            print(f"Rent not supported for {args.provider}")
            sys.exit(1)

        print(f"\n✓ Instance created!")
        print(f"  ID:     {instance.id}")
        print(f"  GPU:    {instance.gpu_type}")
        print(f"  Status: {instance.status}")
        print(f"  Cost:   ${instance.hourly_cost:.3f}/hr")
        print()

        if args.wait:
            print("Waiting for instance to be ready...")
            instance = trainer.wait_for_instance(instance.id)
            print(f"\n✓ Instance ready!")
            print(f"  SSH: ssh -p {instance.ssh_port} {instance.ssh_user}@{instance.ssh_host}")

    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ApexAurum Cloud Training CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # providers
    subparsers.add_parser("providers", help="List available cloud providers")

    # estimate
    est_parser = subparsers.add_parser("estimate", help="Estimate training costs")
    est_parser.add_argument("--dataset", "-d", required=True, help="Path to training dataset (JSONL)")
    est_parser.add_argument("--model", "-m", required=True, help="Model size (e.g., 3b, 7b, 13b)")
    est_parser.add_argument("--epochs", "-e", type=int, default=3, help="Number of epochs")

    # train
    train_parser = subparsers.add_parser("train", help="Start a training job")
    train_parser.add_argument("--provider", "-p", required=True, help="Cloud provider")
    train_parser.add_argument("--model", "-m", required=True, help="Base model to fine-tune")
    train_parser.add_argument("--dataset", "-d", required=True, help="Path to training dataset")
    train_parser.add_argument("--name", "-n", default="apex-finetuned", help="Output model name")
    train_parser.add_argument("--epochs", "-e", type=int, default=3, help="Number of epochs")
    train_parser.add_argument("--lr", type=float, default=1e-5, help="Learning rate")
    train_parser.add_argument("--wait", "-w", action="store_true", help="Wait for completion")

    # status
    status_parser = subparsers.add_parser("status", help="Check training job status")
    status_parser.add_argument("--provider", "-p", required=True, help="Cloud provider")
    status_parser.add_argument("--job-id", "-j", required=True, help="Job ID")

    # gpus
    gpu_parser = subparsers.add_parser("gpus", help="Search available GPUs")
    gpu_parser.add_argument("--provider", "-p", default="vastai", help="Provider (vastai, runpod)")
    gpu_parser.add_argument("--gpu", "-g", default="RTX_4090", help="GPU type")
    gpu_parser.add_argument("--max-price", type=float, default=1.0, help="Max $/hr")
    gpu_parser.add_argument("--num-gpus", type=int, default=1, help="Number of GPUs")

    # rent
    rent_parser = subparsers.add_parser("rent", help="Rent a GPU instance")
    rent_parser.add_argument("--provider", "-p", required=True, help="Provider")
    rent_parser.add_argument("--offer-id", type=int, help="Specific offer ID (Vast.ai)")
    rent_parser.add_argument("--gpu", "-g", default="RTX_4090", help="GPU type")
    rent_parser.add_argument("--max-price", type=float, default=0.50, help="Max $/hr")
    rent_parser.add_argument("--name", "-n", help="Instance name")
    rent_parser.add_argument("--wait", "-w", action="store_true", help="Wait for ready")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "providers": cmd_providers,
        "estimate": cmd_estimate,
        "train": cmd_train,
        "status": cmd_status,
        "gpus": cmd_gpus,
        "rent": cmd_rent,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
