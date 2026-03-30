from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_admin_user
from app.core.config import settings
from app.models.user import User
from app.services.doc_index_service import reindex_project_docs

router = APIRouter(prefix="/api/admin/rag", tags=["admin-rag"])


class RagReindexResponse(BaseModel):
    upserted: int
    namespace: str


@router.post("/reindex", response_model=RagReindexResponse)
async def reindex_rag_docs(_admin: User = Depends(get_current_admin_user)) -> RagReindexResponse:
    _ = _admin
    # app/api/routes -> parents[4] = workspace root (same docs as HybridRAGService)
    project_root = Path(__file__).resolve().parents[4]
    n = reindex_project_docs(project_root)
    return RagReindexResponse(upserted=n, namespace=settings.pinecone_namespace)
