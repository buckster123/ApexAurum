"""
Embedding Service

Generate text embeddings for vector search.
"""

from typing import Optional
import numpy as np


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service.

        Args:
            model_name: Sentence transformer model name
        """
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Returns:
            List of floats (embedding vector)
        """
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        More efficient than calling embed() multiple times.
        """
        embeddings = self.model.encode(texts)
        return [e.tolist() for e in embeddings]

    def similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        """
        a = np.array(embedding1)
        b = np.array(embedding2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    @property
    def dimension(self) -> int:
        """Get embedding dimension for the model."""
        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "paraphrase-MiniLM-L6-v2": 384,
        }
        return dimensions.get(self.model_name, 384)


# Singleton instance with 1536 dimensions for OpenAI compatibility
# We'll pad/project smaller embeddings if needed
_default_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the default embedding service."""
    global _default_service
    if _default_service is None:
        _default_service = EmbeddingService()
    return _default_service
