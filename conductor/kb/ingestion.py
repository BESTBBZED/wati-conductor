"""KB ingestion — parse files, chunk, embed, and store in PostgreSQL."""

import logging
import uuid
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession

from conductor.config import settings
from conductor.db.models import KBChunk, KBDocument
from conductor.kb.retriever import embed_batch

logger = logging.getLogger(__name__)


def _read_file(path: Path) -> str:
    """Read file content as text."""
    return path.read_text(encoding="utf-8")


def _chunk_text(text: str) -> list[str]:
    """Split text into chunks using recursive character splitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.kb_chunk_size,
        chunk_overlap=settings.kb_chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    return splitter.split_text(text)


async def ingest_file(
    session: AsyncSession,
    file_path: str,
    category: str,
    tags: list[str] | None = None,
    always_inject: bool = False,
    skill_id: uuid.UUID | None = None,
) -> KBDocument:
    """Ingest a file into the knowledge base.

    Args:
        session: Async DB session.
        file_path: Path to the file to ingest.
        category: Document category (sop, guardrail, domain, faq).
        tags: Optional tags for filtering.
        always_inject: If True, always include in system prompt.
        skill_id: Optional associated skill ID.

    Returns:
        Created KBDocument with chunks.
    """
    path = Path(file_path)
    content = _read_file(path)
    title = path.stem.replace("-", " ").replace("_", " ").title()

    return await ingest_text(
        session=session,
        title=title,
        content=content,
        category=category,
        tags=tags,
        source_path=str(path),
        always_inject=always_inject,
        skill_id=skill_id,
    )


async def ingest_text(
    session: AsyncSession,
    title: str,
    content: str,
    category: str,
    tags: list[str] | None = None,
    source_path: str | None = None,
    always_inject: bool = False,
    skill_id: uuid.UUID | None = None,
) -> KBDocument:
    """Ingest raw text into the knowledge base.

    Args:
        session: Async DB session.
        title: Document title.
        content: Raw text content.
        category: Document category.
        tags: Optional tags.
        source_path: Original file path (if from file).
        always_inject: If True, always include in system prompt.
        skill_id: Optional associated skill ID.

    Returns:
        Created KBDocument with chunks.
    """
    # Create document record
    doc = KBDocument(
        title=title,
        category=category,
        tags=tags or [],
        content=content,
        source_path=source_path,
        always_inject=always_inject,
        skill_id=skill_id,
    )
    session.add(doc)
    await session.flush()  # Get doc.id

    # Chunk and embed
    chunks_text = _chunk_text(content)
    if not chunks_text:
        chunks_text = [content]

    logger.info("Embedding %d chunks for '%s'...", len(chunks_text), title)
    embeddings = embed_batch(chunks_text)

    # Create chunk records
    for i, (text, embedding) in enumerate(zip(chunks_text, embeddings)):
        chunk = KBChunk(
            document_id=doc.id,
            chunk_index=i,
            content=text,
            embedding=embedding,
        )
        session.add(chunk)

    await session.commit()
    await session.refresh(doc)
    logger.info("Ingested '%s': %d chunks stored.", title, len(chunks_text))
    return doc


async def ingest_directory(
    session: AsyncSession,
    dir_path: str,
    category: str,
    tags: list[str] | None = None,
    always_inject: bool = False,
) -> list[KBDocument]:
    """Ingest all markdown/text files from a directory.

    Args:
        session: Async DB session.
        dir_path: Directory path to scan.
        category: Category for all documents.
        tags: Tags applied to all documents.
        always_inject: If True for all documents.

    Returns:
        List of created KBDocuments.
    """
    path = Path(dir_path)
    docs = []
    for file in sorted(path.glob("**/*.md")):
        doc = await ingest_file(
            session=session,
            file_path=str(file),
            category=category,
            tags=tags,
            always_inject=always_inject,
        )
        docs.append(doc)

    for file in sorted(path.glob("**/*.txt")):
        doc = await ingest_file(
            session=session,
            file_path=str(file),
            category=category,
            tags=tags,
            always_inject=always_inject,
        )
        docs.append(doc)

    return docs
