from __future__ import annotations

import math
import hashlib
from abc import ABC, abstractmethod

from app.core.config import Settings

# Gemini text-embedding-004 dimension
EMBEDDING_DIMENSION = 768


class EmbeddingProvider(ABC):
    dimension: int = EMBEDDING_DIMENSION

    @abstractmethod
    def embed(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        ...


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic pseudo-vectors for dev/CI. Pinecone index must match 768-dim."""

    dimension = EMBEDDING_DIMENSION

    def embed(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        return [self._one(t) for t in texts]

    @staticmethod
    def _one(text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        nums: list[float] = []
        for i in range(EMBEDDING_DIMENSION):
            b = h[i % len(h)] ^ h[(i // len(h)) % len(h)]
            nums.append((b / 127.5) - 1.0)
        norm = math.sqrt(sum(x * x for x in nums))
        if norm <= 0:
            return nums
        return [x / norm for x in nums]


class GeminiEmbeddingProvider(EmbeddingProvider):
    dimension = EMBEDDING_DIMENSION

    def __init__(self, settings: Settings) -> None:
        import google.generativeai as genai

        if not settings.gemini_api_key:
            raise ValueError("gemini_api_key required for GeminiEmbeddingProvider")
        genai.configure(api_key=settings.gemini_api_key)
        self._genai = genai
        self._model = settings.gemini_embedding_model

    def embed(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        task = "retrieval_query" if is_query else "retrieval_document"
        out: list[list[float]] = []
        for text in texts:
            result = self._genai.embed_content(
                model=self._model,
                content=text,
                task_type=task,
            )
            emb = result.get("embedding")
            if not emb:
                raise RuntimeError("embed_content returned no embedding")
            out.append(list(emb))
        return out


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.gemini_api_key:
        return GeminiEmbeddingProvider(settings)
    return MockEmbeddingProvider()
