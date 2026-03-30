from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.embeddings import EmbeddingProvider
from app.services.rag_service import RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)


class PineconeVectorStore:
    def __init__(self, settings: Settings, embedder: EmbeddingProvider) -> None:
        self._settings = settings
        self._embedder = embedder
        self._pc = None
        self._index = None

    @property
    def is_configured(self) -> bool:
        return bool(
            self._settings.use_pinecone_rag
            and self._settings.pinecone_api_key
            and self._settings.pinecone_index
        )

    def _ensure_index(self):
        if self._index is not None:
            return self._index
        if not self.is_configured:
            raise RuntimeError("Pinecone not configured")
        from pinecone import Pinecone

        self._pc = Pinecone(api_key=self._settings.pinecone_api_key)
        self._index = self._pc.Index(self._settings.pinecone_index)
        return self._index

    def query(self, query_text: str, top_k: int = 3) -> list[RetrievedChunk]:
        if not self.is_configured:
            return []
        try:
            index = self._ensure_index()
            vec = self._embedder.embed([query_text], is_query=True)[0]
            ns = self._settings.pinecone_namespace
            res = index.query(vector=vec, top_k=top_k, namespace=ns, include_metadata=True)
            matches = getattr(res, "matches", None) or []
            out: list[RetrievedChunk] = []
            for m in matches:
                if isinstance(m, dict):
                    score = float(m.get("score", 0.0))
                    meta = m.get("metadata") or {}
                else:
                    score = float(getattr(m, "score", 0.0) or 0.0)
                    meta = getattr(m, "metadata", None) or {}
                text = (meta or {}).get("text") or ""
                source = (meta or {}).get("source") or "unknown"
                if text:
                    out.append(RetrievedChunk(source=str(source), text=str(text), score=score))
            return out
        except Exception as e:
            logger.warning("Pinecone query failed, will fall back to local RAG: %s", e)
            return []

    def upsert_vectors(
        self,
        items: list[tuple[str, str, str]],
        *,
        batch_size: int = 16,
    ) -> int:
        """
        items: list of (vector_id, text, source_filename)
        """
        if not self.is_configured:
            raise RuntimeError("Pinecone not configured")
        index = self._ensure_index()
        ns = self._settings.pinecone_namespace
        total = 0
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            texts = [t for _, t, _ in batch]
            vectors = self._embedder.embed(texts, is_query=False)
            upsert_payload = []
            for j, (vid, text, source) in enumerate(batch):
                meta = {"source": source[:500], "text": text[:35000]}
                upsert_payload.append({"id": vid, "values": vectors[j], "metadata": meta})
            index.upsert(vectors=upsert_payload, namespace=ns)
            total += len(upsert_payload)
        return total
