"""Knowledge Base API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from conductor.db.models import KBChunk, KBDocument
from conductor.db.session import get_session
from conductor.kb.ingestion import ingest_file, ingest_text, ingest_directory
from conductor.kb.retriever import embed_text, search_similar, get_always_inject_guardrails

router = APIRouter()


# --- Pydantic schemas ---


class IngestTextRequest(BaseModel):
    """Request body for ingesting raw text."""

    title: str
    content: str
    category: str
    tags: list[str] = []
    always_inject: bool = False


class IngestFileRequest(BaseModel):
    """Request body for ingesting a file by path."""

    file_path: str
    category: str
    tags: list[str] = []
    always_inject: bool = False


class IngestDirectoryRequest(BaseModel):
    """Request body for bulk ingesting a directory."""

    dir_path: str
    category: str
    tags: list[str] = []
    always_inject: bool = False


class SearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str
    top_k: int = 5
    category: str | None = None


class DocumentResponse(BaseModel):
    """Response for a single document."""

    id: UUID
    title: str
    category: str
    tags: list[str]
    source_path: str | None
    always_inject: bool
    chunk_count: int

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    """A single search result."""

    content: str
    title: str
    category: str
    similarity: float


# --- Routes ---


@router.get("/documents")
async def list_documents(
    category: str | None = None,
    tag: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """List KB documents with optional filters."""
    stmt = select(KBDocument)

    if category:
        stmt = stmt.where(KBDocument.category == category)
    if tag:
        stmt = stmt.where(KBDocument.tags.any(tag))

    stmt = stmt.order_by(KBDocument.created_at.desc())
    result = await session.execute(stmt)
    docs = result.scalars().all()

    # Get chunk counts
    response = []
    for doc in docs:
        count_stmt = select(func.count()).where(KBChunk.document_id == doc.id)
        count_result = await session.execute(count_stmt)
        chunk_count = count_result.scalar() or 0
        response.append({
            "id": str(doc.id),
            "title": doc.title,
            "category": doc.category,
            "tags": doc.tags,
            "source_path": doc.source_path,
            "always_inject": doc.always_inject,
            "chunk_count": chunk_count,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })

    return {"documents": response, "total": len(response)}


@router.post("/documents/text")
async def ingest_text_endpoint(
    request: IngestTextRequest,
    session: AsyncSession = Depends(get_session),
):
    """Ingest raw text into the knowledge base."""
    doc = await ingest_text(
        session=session,
        title=request.title,
        content=request.content,
        category=request.category,
        tags=request.tags,
        always_inject=request.always_inject,
    )
    count_stmt = select(func.count()).where(KBChunk.document_id == doc.id)
    count_result = await session.execute(count_stmt)
    chunk_count = count_result.scalar() or 0

    return {"id": str(doc.id), "title": doc.title, "chunk_count": chunk_count}


@router.post("/documents/file")
async def ingest_file_endpoint(
    request: IngestFileRequest,
    session: AsyncSession = Depends(get_session),
):
    """Ingest a file by path into the knowledge base."""
    doc = await ingest_file(
        session=session,
        file_path=request.file_path,
        category=request.category,
        tags=request.tags,
        always_inject=request.always_inject,
    )
    count_stmt = select(func.count()).where(KBChunk.document_id == doc.id)
    count_result = await session.execute(count_stmt)
    chunk_count = count_result.scalar() or 0

    return {"id": str(doc.id), "title": doc.title, "chunk_count": chunk_count}


@router.post("/documents/directory")
async def ingest_directory_endpoint(
    request: IngestDirectoryRequest,
    session: AsyncSession = Depends(get_session),
):
    """Bulk ingest all markdown/text files from a directory."""
    docs = await ingest_directory(
        session=session,
        dir_path=request.dir_path,
        category=request.category,
        tags=request.tags,
        always_inject=request.always_inject,
    )
    return {
        "ingested": len(docs),
        "documents": [{"id": str(d.id), "title": d.title} for d in docs],
    }


@router.get("/documents/{doc_id}")
async def get_document(doc_id: UUID, session: AsyncSession = Depends(get_session)):
    """Get a single document by ID with its content."""
    stmt = select(KBDocument).where(KBDocument.id == doc_id)
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    count_stmt = select(func.count()).where(KBChunk.document_id == doc.id)
    count_result = await session.execute(count_stmt)
    chunk_count = count_result.scalar() or 0

    return {
        "id": str(doc.id),
        "title": doc.title,
        "category": doc.category,
        "tags": doc.tags,
        "content": doc.content,
        "source_path": doc.source_path,
        "always_inject": doc.always_inject,
        "chunk_count": chunk_count,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: UUID, session: AsyncSession = Depends(get_session)):
    """Delete a document and its chunks (cascade)."""
    stmt = select(KBDocument).where(KBDocument.id == doc_id)
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await session.delete(doc)
    await session.commit()
    return {"deleted": str(doc_id), "title": doc.title}


@router.post("/search")
async def search_kb(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    """Semantic search across KB chunks."""
    query_embedding = embed_text(request.query)
    results = await search_similar(
        session=session,
        query_embedding=query_embedding,
        top_k=request.top_k,
        category=request.category,
    )
    return {"results": results, "total": len(results)}


@router.get("/guardrails")
async def get_guardrails(session: AsyncSession = Depends(get_session)):
    """Get all always-inject guardrail documents."""
    guardrails = await get_always_inject_guardrails(session)
    return {"guardrails": guardrails, "total": len(guardrails)}
