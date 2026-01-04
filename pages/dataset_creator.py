# pages/dataset_creator.py
"""
Tiny Vector Dataset Creator & Manager

Creates lightweight, persistent ChromaDB vector datasets from documents.
Agents can query these via dataset_query() and dataset_list() tools.

Storage: sandbox/datasets/{dataset_name}/
"""

import streamlit as st
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from pypdf import PdfReader
import docx2txt
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Optional OCR support
try:
    import ocrmypdf
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


# Constants
DATASETS_PATH = Path("sandbox/datasets")
METADATA_FILE = "dataset_meta.json"

# Embedding model options (Pi-5 friendly)
MODEL_OPTIONS = {
    "all-MiniLM-L6-v2": {"dim": 384, "desc": "Fast, good quality (recommended)"},
    "all-MiniLM-L12-v2": {"dim": 384, "desc": "Slightly better, still fast"},
    "paraphrase-MiniLM-L6-v2": {"dim": 384, "desc": "Good for paraphrase/similarity"},
    "all-mpnet-base-v2": {"dim": 768, "desc": "Highest quality (slower on Pi-5)"},
}


def get_datasets() -> list[dict]:
    """Scan for all datasets with metadata."""
    datasets = []
    if not DATASETS_PATH.exists():
        return datasets

    for item in DATASETS_PATH.iterdir():
        if item.is_dir():
            meta_path = item / METADATA_FILE
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                except:
                    pass

            # Get collection info
            try:
                client = chromadb.PersistentClient(path=str(item))
                collections = client.list_collections()
                for col in collections:
                    count = client.get_collection(col.name).count()
                    datasets.append({
                        "name": item.name,
                        "collection": col.name,
                        "path": item,
                        "count": count,
                        "description": meta.get("description", ""),
                        "tags": meta.get("tags", []),
                        "model": meta.get("model", "unknown"),
                        "created_at": meta.get("created_at", ""),
                        "source_files": meta.get("source_files", []),
                    })
            except Exception as e:
                st.warning(f"Error reading {item.name}: {e}")

    return sorted(datasets, key=lambda d: d.get("created_at", ""), reverse=True)


def save_dataset_metadata(path: Path, metadata: dict):
    """Save dataset metadata to JSON file."""
    meta_path = path / METADATA_FILE
    meta_path.write_text(json.dumps(metadata, indent=2))


def extract_text_from_file(file_path: Path, file_name: str, use_ocr: bool = False) -> list[tuple[str, dict]]:
    """Extract text chunks from a file. Returns list of (text, metadata) tuples."""
    ext = Path(file_name).suffix.lower()
    chunks = []

    try:
        if ext == ".pdf":
            pdf_path = file_path

            # Apply OCR if enabled (for scanned/image PDFs)
            if use_ocr and HAS_OCR:
                ocr_path = file_path.parent / f"ocr_{file_path.name}"
                try:
                    ocrmypdf.ocr(
                        str(file_path),
                        str(ocr_path),
                        jobs=os.cpu_count() or 2,
                        skip_text=True,  # Skip pages that already have text
                        optimize=1
                    )
                    pdf_path = ocr_path
                    st.caption(f"OCR applied to {file_name}")
                except Exception as e:
                    st.warning(f"OCR failed on {file_name}: {e} - using original")

            reader = PdfReader(str(pdf_path))
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    chunks.append((text, {"source": file_name, "page": page_num, "type": "pdf"}))

        elif ext in [".txt", ".md", ".markdown"]:
            text = file_path.read_text(encoding="utf-8")
            if text.strip():
                chunks.append((text, {"source": file_name, "type": "text"}))

        elif ext == ".docx":
            text = docx2txt.process(str(file_path))
            if text.strip():
                chunks.append((text, {"source": file_name, "type": "docx"}))

        elif ext in [".html", ".htm"]:
            soup = BeautifulSoup(file_path.read_text(encoding="utf-8"), "html.parser")
            text = soup.get_text(separator="\n")
            if text.strip():
                chunks.append((text, {"source": file_name, "type": "html"}))

    except Exception as e:
        st.warning(f"Failed to extract from {file_name}: {e}")

    return chunks


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - chunk_overlap if chunk_overlap else end
    return chunks


# ============================================================================
# STREAMLIT PAGE
# ============================================================================

st.title("Dataset Creator")
st.caption("Create lightweight vector datasets for agent access")

# Tabs for Creator and Manager
tab_create, tab_manage = st.tabs(["Create Dataset", "Manage Datasets"])


# ============================================================================
# TAB 1: CREATE DATASET
# ============================================================================
with tab_create:
    st.markdown("""
    Upload documents to create a searchable vector dataset.
    Agents can query these via the `dataset_query` tool.
    """)

    # Dataset settings
    col1, col2 = st.columns(2)
    with col1:
        dataset_name = st.text_input(
            "Dataset name",
            value="",
            placeholder="e.g., python_docs, research_papers",
            help="Alphanumeric and underscores only"
        )
    with col2:
        dataset_desc = st.text_input(
            "Description (optional)",
            value="",
            placeholder="What is this dataset about?"
        )

    dataset_tags = st.text_input(
        "Tags (comma-separated, optional)",
        value="",
        placeholder="e.g., documentation, python, reference"
    )

    # Processing settings in expander
    with st.expander("Processing Settings", expanded=False):
        model_name = st.selectbox(
            "Embedding model",
            options=list(MODEL_OPTIONS.keys()),
            index=0,
            format_func=lambda m: f"{m} - {MODEL_OPTIONS[m]['desc']}"
        )

        col1, col2 = st.columns(2)
        with col1:
            chunk_size = st.slider("Chunk size (chars)", 500, 4000, 1500, 100)
        with col2:
            chunk_overlap = st.slider("Chunk overlap (chars)", 0, 500, 150, 50)

        st.caption(f"Model dimension: {MODEL_OPTIONS[model_name]['dim']}")

        # OCR option
        st.divider()
        if HAS_OCR:
            use_ocr = st.checkbox(
                "Enable OCR for scanned PDFs",
                value=False,
                help="Use OCR to extract text from image-based/scanned PDFs. Slower but handles scans."
            )
        else:
            use_ocr = False
            st.caption("OCR unavailable (install ocrmypdf + tesseract-ocr)")

    # File uploader
    uploaded_files = st.file_uploader(
        "Upload documents",
        accept_multiple_files=True,
        type=["pdf", "txt", "md", "markdown", "docx", "html", "htm"],
        key="dataset_uploader"
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) selected")
        with st.expander("Files to process"):
            for f in uploaded_files:
                st.text(f"  {f.name} ({f.size:,} bytes)")

    # Create button
    create_disabled = not dataset_name or not uploaded_files
    if st.button("Create Dataset", type="primary", disabled=create_disabled):
        # Validate name
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in dataset_name)
        if safe_name != dataset_name:
            st.warning(f"Name sanitized to: {safe_name}")
            dataset_name = safe_name

        dataset_path = DATASETS_PATH / dataset_name

        # Check if exists
        if dataset_path.exists():
            st.error(f"Dataset '{dataset_name}' already exists. Delete it first or choose another name.")
            st.stop()

        # Create directory
        dataset_path.mkdir(parents=True, exist_ok=True)

        progress = st.progress(0, text="Initializing...")

        try:
            # Phase 1: Extract text from files
            progress.progress(0.1, text="Extracting text from files...")
            all_chunks = []
            source_files = []

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                for i, up_file in enumerate(uploaded_files):
                    progress.progress(0.1 + 0.2 * (i / len(uploaded_files)),
                                     text=f"Processing {up_file.name}...")

                    # Save to temp
                    saved = temp_path / up_file.name
                    saved.write_bytes(up_file.getbuffer())
                    source_files.append(up_file.name)

                    # Extract text (with OCR if enabled)
                    raw_chunks = extract_text_from_file(saved, up_file.name, use_ocr=use_ocr)

                    # Apply chunking
                    for text, meta in raw_chunks:
                        text_chunks = chunk_text(text, chunk_size, chunk_overlap)
                        for j, chunk in enumerate(text_chunks):
                            chunk_meta = meta.copy()
                            chunk_meta["chunk_index"] = j
                            all_chunks.append((chunk, chunk_meta))

            if not all_chunks:
                st.error("No text content extracted from files!")
                import shutil
                shutil.rmtree(dataset_path)
                st.stop()

            st.info(f"Extracted {len(all_chunks)} chunks from {len(source_files)} files")

            # Phase 2: Create embeddings and store
            progress.progress(0.4, text=f"Loading {model_name}...")

            embedding_function = SentenceTransformerEmbeddingFunction(model_name=model_name)
            client = chromadb.PersistentClient(path=str(dataset_path))
            collection = client.create_collection(
                name="main",
                embedding_function=embedding_function
            )

            # Batch add
            progress.progress(0.5, text="Embedding and indexing...")
            batch_size = 32
            total = len(all_chunks)

            for start_idx in range(0, total, batch_size):
                end_idx = min(start_idx + batch_size, total)
                batch = all_chunks[start_idx:end_idx]

                documents = [c[0] for c in batch]
                metadatas = [c[1] for c in batch]
                ids = [f"chunk_{start_idx + i}" for i in range(len(batch))]

                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )

                progress.progress(0.5 + 0.4 * (end_idx / total),
                                 text=f"Indexed {end_idx}/{total} chunks...")

            # Phase 3: Save metadata
            progress.progress(0.95, text="Saving metadata...")

            tags = [t.strip() for t in dataset_tags.split(",") if t.strip()]
            metadata = {
                "name": dataset_name,
                "description": dataset_desc,
                "tags": tags,
                "model": model_name,
                "model_dim": MODEL_OPTIONS[model_name]["dim"],
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "ocr_enabled": use_ocr,
                "source_files": source_files,
                "chunk_count": len(all_chunks),
                "created_at": datetime.now().isoformat(),
            }
            save_dataset_metadata(dataset_path, metadata)

            progress.progress(1.0, text="Complete!")
            st.success(f"Dataset '{dataset_name}' created with {len(all_chunks)} chunks!")
            st.balloons()

            st.info("""
            **Next steps:**
            - Agents can query via: `dataset_query("{0}", "your question")`
            - View all datasets: `dataset_list()`
            - Manage in the "Manage Datasets" tab
            """.format(dataset_name))

        except Exception as e:
            st.error(f"Error creating dataset: {e}")
            # Cleanup on failure
            if dataset_path.exists():
                import shutil
                shutil.rmtree(dataset_path)
            raise


# ============================================================================
# TAB 2: MANAGE DATASETS
# ============================================================================
with tab_manage:
    datasets = get_datasets()

    if not datasets:
        st.info("No datasets yet. Create one in the 'Create Dataset' tab!")
    else:
        st.markdown(f"**{len(datasets)} dataset(s) available**")

        # Dataset selector
        selected_idx = st.selectbox(
            "Select dataset",
            options=range(len(datasets)),
            format_func=lambda i: f"{datasets[i]['name']} ({datasets[i]['count']} chunks)"
        )

        ds = datasets[selected_idx]

        # Dataset info card
        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Chunks", ds["count"])
        with col2:
            st.metric("Model", ds["model"].split("-")[-1] if ds["model"] != "unknown" else "?")
        with col3:
            created = ds.get("created_at", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created)
                    created = dt.strftime("%Y-%m-%d")
                except:
                    pass
            st.metric("Created", created or "?")

        if ds["description"]:
            st.markdown(f"**Description:** {ds['description']}")

        if ds["tags"]:
            st.markdown(f"**Tags:** {', '.join(ds['tags'])}")

        if ds["source_files"]:
            with st.expander(f"Source files ({len(ds['source_files'])})"):
                for f in ds["source_files"]:
                    st.text(f"  {f}")

        # Quick search preview
        st.divider()
        st.subheader("Quick Search Preview")

        query = st.text_input("Test query", key="manage_query", placeholder="Search this dataset...")
        top_k = st.slider("Results to show", 1, 20, 5, key="manage_topk")

        if query:
            if st.button("Search", key="manage_search"):
                try:
                    client = chromadb.PersistentClient(path=str(ds["path"]))

                    # Need to recreate embedding function
                    model = ds.get("model", "all-MiniLM-L6-v2")
                    if model == "unknown":
                        model = "all-MiniLM-L6-v2"

                    embedding_function = SentenceTransformerEmbeddingFunction(model_name=model)
                    collection = client.get_collection("main", embedding_function=embedding_function)

                    results = collection.query(
                        query_texts=[query],
                        n_results=top_k,
                        include=["documents", "metadatas", "distances"]
                    )

                    if results["ids"][0]:
                        for i in range(len(results["ids"][0])):
                            doc = results["documents"][0][i]
                            meta = results["metadatas"][0][i]
                            dist = results["distances"][0][i]

                            # Format source info
                            source = meta.get("source", "?")
                            page = meta.get("page", "")
                            source_info = f"{source}"
                            if page:
                                source_info += f" (p.{page})"

                            with st.expander(f"Result {i+1} | {source_info} | dist: {dist:.3f}"):
                                st.text(doc[:500] + "..." if len(doc) > 500 else doc)
                                st.caption(f"Full length: {len(doc)} chars")
                    else:
                        st.info("No results found")

                except Exception as e:
                    st.error(f"Search error: {e}")

        # Delete section
        st.divider()
        with st.expander("Danger Zone", expanded=False):
            st.warning(f"Delete dataset '{ds['name']}' permanently?")

            confirm_name = st.text_input(
                "Type dataset name to confirm",
                key="delete_confirm",
                placeholder=ds["name"]
            )

            if st.button("Delete Dataset", type="secondary", key="delete_btn"):
                if confirm_name == ds["name"]:
                    try:
                        import shutil
                        shutil.rmtree(ds["path"])
                        st.success(f"Deleted '{ds['name']}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
                else:
                    st.error("Name doesn't match. Type the exact dataset name to confirm.")
