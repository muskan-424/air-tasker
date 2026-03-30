"""
Run from repo: set USE_PINECONE_RAG, PINECONE_API_KEY, PINECONE_INDEX, GEMINI_API_KEY (recommended).
Uses same chunking as LocalRAGService / hybrid RAG.

  conda run -n airtasker_fastapi python scripts/index_docs_to_pinecone.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# backend_fastapi as cwd
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.services.doc_index_service import reindex_project_docs  # noqa: E402


def main() -> None:
    project_root = ROOT.parent
    n = reindex_project_docs(project_root, app_settings=settings)
    print(f"Upserted {n} vectors into namespace {settings.pinecone_namespace!r}")


if __name__ == "__main__":
    main()
