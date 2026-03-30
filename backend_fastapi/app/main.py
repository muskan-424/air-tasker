import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes.admin_jobs import router as admin_jobs_router
from app.api.routes.admin_rag import router as admin_rag_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.task_drafts import router as task_drafts_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.verification import router as verification_router
from app.api.routes.voice import router as voice_router
from app.core.config import settings
from app.core.limiter import limiter
from app.middleware.metrics_middleware import MetricsMiddleware
from app.workers.job_queue import start_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_worker = asyncio.Event()
    worker_task = start_worker(stop_worker)

    reindex_task: asyncio.Task | None = None
    if settings.rag_reindex_interval_hours > 0 and settings.use_pinecone_rag:
        from pathlib import Path

        from app.services.doc_index_service import reindex_project_docs

        project_root = Path(__file__).resolve().parents[2]

        async def reindex_loop() -> None:
            while True:
                await asyncio.sleep(settings.rag_reindex_interval_hours * 3600)
                try:
                    n = await asyncio.to_thread(reindex_project_docs, project_root)
                    logger.info("Scheduled RAG re-index upserted %s vectors", n)
                except Exception:
                    logger.exception("Scheduled RAG re-index failed")

        reindex_task = asyncio.create_task(reindex_loop())

    yield

    stop_worker.set()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    if reindex_task:
        reindex_task.cancel()
        try:
            await reindex_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(verification_router)
app.include_router(notifications_router)
app.include_router(metrics_router)
app.include_router(admin_jobs_router)
app.include_router(admin_rag_router)
app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(task_drafts_router)
app.include_router(tasks_router)


@app.get("/")
async def root():
    return {"name": settings.app_name, "status": "ok", "env": settings.environment}
