"""SQLAlchemy ORM models for Knowledge Base and Skills."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all WATI Conductor models."""


class KBDocument(Base):
    """Knowledge base document metadata.

    Fields:
        id: UUID primary key
        title: Human-readable document title
        category: sop | guardrail | domain | faq
        tags: Free-form tags for filtering
        content: Full raw document content
        source_path: Original file path (if ingested from file)
        skill_id: Associated skill (nullable)
        always_inject: If True, always included in system prompt
        created_at: Ingestion timestamp
        updated_at: Last modification timestamp
    """

    __tablename__ = "kb_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str | None] = mapped_column(String)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL")
    )
    always_inject: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    chunks: Mapped[list["KBChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    skill: Mapped["Skill | None"] = relationship(back_populates="kb_documents")


class KBChunk(Base):
    """Embedded chunk of a KB document for vector search.

    Fields:
        id: UUID primary key
        document_id: Parent document reference
        chunk_index: Position within the document
        content: Chunk text content
        embedding: pgvector embedding (1024 dimensions for BAAI/bge-m3)
        created_at: Embedding timestamp
    """

    __tablename__ = "kb_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kb_documents.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    document: Mapped["KBDocument"] = relationship(back_populates="chunks")


class Skill(Base):
    """Registered skill with tools, instructions, and KB associations.

    Fields:
        id: UUID primary key
        name: Unique skill identifier
        version: Semantic version string
        description: Human-readable description
        enabled: Whether skill is active
        tool_names: List of tool function names this skill provides
        instructions: Skill-specific system prompt additions
        depends_on: List of skill names this depends on
        builtin: True for built-in skills (cannot be deleted)
        created_at: Registration timestamp
        updated_at: Last modification timestamp
    """

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String, default="1.0")
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tool_names: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    instructions: Mapped[str] = mapped_column(Text, default="")
    depends_on: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    kb_documents: Mapped[list["KBDocument"]] = relationship(back_populates="skill")
