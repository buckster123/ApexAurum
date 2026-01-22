"""
Prompts Routes

Load system prompts from files in data/prompts/
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException

from app_config import settings

router = APIRouter()

PROMPTS_DIR = settings.DATA_DIR / "prompts"


@router.get("")
async def list_prompts():
    """List available prompt files."""
    if not PROMPTS_DIR.exists():
        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    prompts = []
    for f in PROMPTS_DIR.iterdir():
        if f.suffix in [".md", ".txt"]:
            prompts.append({
                "name": f.stem,
                "filename": f.name,
                "type": f.suffix[1:]
            })

    # Sort alphabetically
    prompts.sort(key=lambda x: x["name"].lower())

    return {"prompts": prompts, "count": len(prompts)}


@router.get("/{filename}")
async def get_prompt(filename: str):
    """Load a prompt file's contents."""
    # Security: only allow .md and .txt
    if not filename.endswith((".md", ".txt")):
        raise HTTPException(400, "Only .md and .txt files allowed")

    filepath = PROMPTS_DIR / filename

    # Security: prevent path traversal
    if not filepath.resolve().is_relative_to(PROMPTS_DIR.resolve()):
        raise HTTPException(400, "Invalid path")

    if not filepath.exists():
        raise HTTPException(404, f"Prompt not found: {filename}")

    content = filepath.read_text(encoding="utf-8")

    return {
        "filename": filename,
        "name": filepath.stem,
        "content": content
    }
