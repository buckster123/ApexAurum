"""
Application Configuration

Load settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on environment variables


@dataclass
class Settings:
    """Application settings."""

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # LLM Configuration
    LLM_PROVIDER: str = "ollama"  # ollama, llamacpp, vllm, together, groq
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: Optional[str] = None
    DEFAULT_MODEL: str = "qwen2.5-instruct:1.5b"  # Available on Hailo-10H
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7

    # Claude (optional, for hybrid setups)
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-5-20250929"

    # Storage paths
    DATA_DIR: Path = Path("./data")
    MEMORY_FILE: Path = Path("./data/memory.json")
    CONVERSATIONS_FILE: Path = Path("./data/conversations.json")
    VECTOR_DIR: Path = Path("./data/vectors")

    # Features
    ENABLE_TOOLS: bool = True
    ENABLE_MEMORY: bool = True
    ENABLE_STREAMING: bool = True

    def __post_init__(self):
        """Load from environment and ensure directories exist."""
        # Override from environment
        self.HOST = os.getenv("HOST", self.HOST)
        self.PORT = int(os.getenv("PORT", self.PORT))
        self.DEBUG = os.getenv("DEBUG", "true").lower() == "true"

        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", self.LLM_PROVIDER)
        self.LLM_BASE_URL = os.getenv("LLM_BASE_URL", self.LLM_BASE_URL)
        self.LLM_API_KEY = os.getenv("LLM_API_KEY", self.LLM_API_KEY)
        self.DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", self.DEFAULT_MODEL)

        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", self.ANTHROPIC_API_KEY)

        # Ensure data directory exists
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
