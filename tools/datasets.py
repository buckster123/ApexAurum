# tools/datasets.py
"""
Dataset Tools for Agent Access

Provides agents with access to user-created vector datasets.
Datasets are created via the Dataset Creator page (pages/dataset_creator.py).

Tools:
- dataset_list: List all available datasets with metadata
- dataset_query: Semantic search within a specific dataset
"""

import json
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


# Constants
DATASETS_PATH = Path("sandbox/datasets")
METADATA_FILE = "dataset_meta.json"


# ============================================================================
# TOOL FUNCTIONS
# ============================================================================

def dataset_list() -> dict:
    """
    List all available datasets with their metadata.

    Returns information about each dataset including name, description,
    tags, chunk count, and the embedding model used.

    Returns:
        dict: {
            "success": bool,
            "datasets": list of dataset info dicts,
            "count": total number of datasets
        }
    """
    try:
        datasets = []

        if not DATASETS_PATH.exists():
            return {
                "success": True,
                "datasets": [],
                "count": 0,
                "message": "No datasets directory found. Create datasets via the Dataset Creator page."
            }

        for item in DATASETS_PATH.iterdir():
            if not item.is_dir():
                continue

            # Load metadata
            meta_path = item / METADATA_FILE
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                except:
                    pass

            # Get collection stats
            try:
                client = chromadb.PersistentClient(path=str(item))
                collections = client.list_collections()

                for col in collections:
                    count = client.get_collection(col.name).count()
                    datasets.append({
                        "name": item.name,
                        "description": meta.get("description", ""),
                        "tags": meta.get("tags", []),
                        "chunk_count": count,
                        "model": meta.get("model", "unknown"),
                        "source_files": meta.get("source_files", []),
                        "created_at": meta.get("created_at", ""),
                    })
            except Exception as e:
                # Include errored datasets with warning
                datasets.append({
                    "name": item.name,
                    "error": str(e),
                    "chunk_count": 0
                })

        # Sort by creation date (newest first)
        datasets.sort(key=lambda d: d.get("created_at", ""), reverse=True)

        return {
            "success": True,
            "datasets": datasets,
            "count": len(datasets)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "datasets": [],
            "count": 0
        }


def dataset_query(
    dataset_name: str,
    query: str,
    top_k: int = 5
) -> dict:
    """
    Search a dataset using semantic similarity.

    Performs vector similarity search on the specified dataset and returns
    the most relevant chunks with their metadata.

    Args:
        dataset_name: Name of the dataset to search
        query: Search query (will be embedded and matched against dataset)
        top_k: Number of results to return (default: 5, max: 20)

    Returns:
        dict: {
            "success": bool,
            "results": list of {text, source, page, distance, metadata},
            "query": the original query,
            "dataset": dataset name
        }
    """
    try:
        # Validate
        if not dataset_name:
            return {"success": False, "error": "dataset_name is required"}
        if not query:
            return {"success": False, "error": "query is required"}

        top_k = min(max(1, top_k), 20)  # Clamp 1-20

        dataset_path = DATASETS_PATH / dataset_name

        if not dataset_path.exists():
            available = [d.name for d in DATASETS_PATH.iterdir() if d.is_dir()] if DATASETS_PATH.exists() else []
            return {
                "success": False,
                "error": f"Dataset '{dataset_name}' not found",
                "available_datasets": available
            }

        # Load metadata to get model
        meta_path = dataset_path / METADATA_FILE
        model_name = "all-MiniLM-L6-v2"  # Default fallback

        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                model_name = meta.get("model", model_name)
            except:
                pass

        # Connect to dataset
        client = chromadb.PersistentClient(path=str(dataset_path))
        embedding_function = SentenceTransformerEmbeddingFunction(model_name=model_name)

        try:
            collection = client.get_collection("main", embedding_function=embedding_function)
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not load collection: {e}"
            }

        # Perform search
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted_results = []
        if results["ids"][0]:
            for i in range(len(results["ids"][0])):
                doc = results["documents"][0][i]
                meta = results["metadatas"][0][i]
                dist = results["distances"][0][i]

                formatted_results.append({
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "page": meta.get("page"),
                    "distance": round(dist, 4),
                    "metadata": meta
                })

        return {
            "success": True,
            "results": formatted_results,
            "result_count": len(formatted_results),
            "query": query,
            "dataset": dataset_name,
            "model": model_name
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "dataset": dataset_name
        }


# ============================================================================
# TOOL SCHEMAS
# ============================================================================

DATASET_LIST_SCHEMA = {
    "name": "dataset_list",
    "description": """List all available vector datasets with their metadata.

Returns information about each dataset including:
- name: Dataset identifier (used in dataset_query)
- description: What the dataset contains
- tags: Categorization tags
- chunk_count: Number of searchable chunks
- source_files: Original files used to create the dataset
- model: Embedding model used

Use this to discover what datasets are available before querying.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

DATASET_QUERY_SCHEMA = {
    "name": "dataset_query",
    "description": """Search a vector dataset using semantic similarity.

Performs embedding-based search on user-created datasets. Returns the most
relevant text chunks with source information and similarity scores.

Use dataset_list() first to see available datasets.

Example usage:
- dataset_query("python_docs", "how to handle exceptions")
- dataset_query("research_papers", "neural network architecture", top_k=10)

Lower distance = more similar (0 = exact match).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "dataset_name": {
                "type": "string",
                "description": "Name of the dataset to search (from dataset_list)"
            },
            "query": {
                "type": "string",
                "description": "Search query - will be semantically matched against dataset contents"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (1-20, default: 5)",
                "default": 5
            }
        },
        "required": ["dataset_name", "query"]
    }
}
