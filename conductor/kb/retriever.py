"""KB retriever — local embedding via sentence-transformers + pgvector search."""

import logging

from sentence_transformers import SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from conductor.config import settings
from conductor.db.models import KBChunk, KBDocument

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy-load embedding model (cached after first call)."""
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", settings.kb_embedding_model)
        _model = SentenceTransformer(settings.kb_embedding_model)
        logger.info("Embedding model loaded.")
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single text string.

    Args:
        text: Input text to embed.

    Returns:
        Normalized embedding vector (1024 dims for bge-m3).
    """
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single batch.

    Args:
        texts: List of text strings.

    Returns:
        List of normalized embedding vectors.
    """
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


async def search_similar(
    session: AsyncSession,
    query_embedding: list[float],
    top_k: int = 5,
    category: str | None = None,
) -> list[dict]:
    """Semantic search using pgvector cosine distance.

    Args:
        session: Async DB session.
        query_embedding: Query vector (1024 dims).
        top_k: Number of results.
        category: Optional category filter.

    Returns:
        List of {content, title, category, similarity} dicts.
    """
    stmt = (
        select(
            KBChunk.content,
            KBDocument.title,
            KBDocument.category,
            (1 - KBChunk.embedding.cosine_distance(query_embedding)).label("similarity"),
        )
        .join(KBDocument, KBChunk.document_id == KBDocument.id)
        .order_by(KBChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    if category:
        stmt = stmt.where(KBDocument.category == category)

    result = await session.execute(stmt)
    return [dict(row._mapping) for row in result]


async def get_always_inject_guardrails(session: AsyncSession) -> list[str]:
    """Get content of all always-inject documents.

    Args:
        session: Async DB session.

    Returns:
        List of guardrail content strings.
    """
    stmt = select(KBDocument.content).where(KBDocument.always_inject.is_(True))
    result = await session.execute(stmt)
    return [row[0] for row in result]
