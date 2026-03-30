from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RetrievedChunk:
    source: str
    text: str
    score: float


def _doc_paths(project_root: Path) -> list[Path]:
    return [
        project_root / "ai_airtasker_india_proposal.md",
        project_root / "implementation_plan_india.md",
        project_root / "agentic_chatbot_implementation_checklist.md",
    ]


def load_markdown_chunks(project_root: Path) -> list[tuple[str, str]]:
    """Return (source_filename, chunk_text) for Pinecone indexing; same chunking as LocalRAGService."""
    out: list[tuple[str, str]] = []
    for path in _doc_paths(project_root):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        raw_parts = re.split(r"\n{2,}", text)
        for part in raw_parts:
            cleaned = part.strip()
            if len(cleaned) < 30:
                continue
            out.append((path.name, cleaned))
    return out


class LocalRAGService:
    """
    Lightweight RAG service for MVP.
    - Loads local markdown docs
    - Splits into chunks
    - Retrieves by token overlap scoring
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._chunks: list[RetrievedChunk] = []
        self._load_docs()

    def _load_docs(self) -> None:
        chunks: list[RetrievedChunk] = []
        for source, cleaned in load_markdown_chunks(self.project_root):
            chunks.append(RetrievedChunk(source=source, text=cleaned, score=0.0))
        self._chunks = chunks

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []
        ranked: list[RetrievedChunk] = []
        for chunk in self._chunks:
            c_tokens = self._tokenize(chunk.text)
            overlap = len(q_tokens.intersection(c_tokens))
            if overlap == 0:
                continue
            score = overlap / max(len(q_tokens), 1)
            ranked.append(RetrievedChunk(source=chunk.source, text=chunk.text, score=score))
        ranked.sort(key=lambda x: x.score, reverse=True)
        return ranked[:top_k]

