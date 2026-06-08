import pytest
from pathlib import Path

from app.services.rag_service import load_markdown_chunks


def test_load_markdown_chunks_includes_faq():
    project_root = Path(__file__).resolve().parents[2]
    chunks = load_markdown_chunks(project_root)
    sources = {source for source, _ in chunks}
    assert "vayutask_help_faq.md" in sources
    assert len(chunks) >= 5


def test_capabilities_rag_mode_local(client):
    res = client.get("/api/health/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert data["rag_mode"] in ("local", "pinecone")
