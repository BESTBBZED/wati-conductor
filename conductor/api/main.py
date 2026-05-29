"""FastAPI application for WATI Conductor KB and Skills management."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from conductor.db.session import async_session, init_db
from conductor.skills.registry import seed_builtin_skills
from conductor.api.routes import kb, skills

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, seed skills, pre-load embedding model."""
    logger.info("Initializing database...")
    await init_db()

    async with async_session() as session:
        await seed_builtin_skills(session)

    # Pre-load embedding model so first request isn't slow
    from conductor.kb.retriever import embed_text
    logger.info("Pre-loading embedding model...")
    embed_text("warmup")
    logger.info("Embedding model ready.")

    yield


app = FastAPI(
    title="WATI Conductor API",
    description="Knowledge Base and Skills management for WATI Conductor agent.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(kb.router, prefix="/api/kb", tags=["knowledge-base"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
