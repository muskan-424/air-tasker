from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import Settings, settings
from app.services.embeddings import get_embedding_provider
from app.services.pinecone_store import PineconeVectorStore
from app.services.rag_service import LocalRAGService, RetrievedChunk

logger = logging.getLogger(__name__)


class HybridRAGService:
    """
    Tries Pinecone vector search when configured; falls back to local token-overlap RAG.
    """

    def __init__(self, project_root: Path, app_settings: Settings | None = None) -> None:
        self._settings = app_settings or settings
        self._local = LocalRAGService(project_root=project_root)
        self._embedder = get_embedding_provider(self._settings)
        self._pinecone = PineconeVectorStore(self._settings, self._embedder)

    def retrieve(self, query: str, top_k: int = 3) -> tuple[list[RetrievedChunk], str]:
        if self._pinecone.is_configured:
            try:
                chunks = self._pinecone.query(query, top_k=top_k)
                if chunks:
                    return chunks, "pinecone"
            except Exception as e:
                logger.warning("Hybrid RAG: Pinecone path failed: %s", e)
        return self._local.retrieve(query, top_k=top_k), "local"
