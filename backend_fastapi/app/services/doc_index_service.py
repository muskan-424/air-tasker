from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import Settings, settings
from app.services.embeddings import get_embedding_provider
from app.services.pinecone_store import PineconeVectorStore
from app.services.rag_service import load_markdown_chunks


def reindex_project_docs(project_root: Path, app_settings: Settings | None = None) -> int:
    """Chunk local markdown, embed, upsert into Pinecone namespace. Requires vector index with 768 dimensions."""
    cfg = app_settings or settings
    chunks = load_markdown_chunks(project_root)
    embedder = get_embedding_provider(cfg)
    store = PineconeVectorStore(cfg, embedder)
    if not store.is_configured:
        raise RuntimeError("Set USE_PINECONE_RAG=true and PINECONE_API_KEY, PINECONE_INDEX")
    items: list[tuple[str, str, str]] = []
    for idx, (source, text) in enumerate(chunks):
        vid = hashlib.sha256(f"{source}:{idx}:{text[:120]}".encode()).hexdigest()[:32]
        items.append((vid, text, source))
    return store.upsert_vectors(items)
