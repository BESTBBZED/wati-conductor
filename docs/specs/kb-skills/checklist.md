# KB & Skills Implementation Checklist

> Progress tracker for the Knowledge Base and Skills Management feature.

## Phase 1: Database & API Infrastructure

- [x] **1.1** Add dependencies (asyncpg, pgvector, sqlalchemy[asyncio], fastapi, uvicorn, sentence-transformers)
- [x] **1.2** Docker Compose — PostgreSQL + pgvector service with healthcheck
- [x] **1.3** Configuration — postgres, KB, skills settings in `conductor/config.py`
- [x] **1.4** SQLAlchemy models — KBDocument, KBChunk, Skill in `conductor/db/models.py`
- [x] **1.5** Database session — async engine + pool + `get_session()` + `init_db()` in `conductor/db/session.py`
- [x] **1.6** FastAPI skeleton — app with lifespan, routers, health endpoint in `conductor/api/main.py`

## Phase 2: KB & Skills Business Logic

- [x] **2.1** Document ingestion — parse, chunk, embed, store in `conductor/kb/ingestion.py`
- [x] **2.2** KB retriever — `embed_text`, `embed_batch`, `search_similar`, `get_always_inject_guardrails` in `conductor/kb/retriever.py`
- [x] **2.3** KB API routes — full CRUD + search + guardrails in `conductor/api/routes/kb.py`
- [x] **2.4** Skills registry — CRUD + tool resolution + enable/disable in `conductor/skills/registry.py`
- [x] **2.5** Built-in skills seeding — 5 skills (contacts, messaging, templates, operators, tickets)
- [x] **2.6** Skills API routes — full CRUD + active tools in `conductor/api/routes/skills.py`
- [x] **2.7** Sample KB content — `data/kb/` with SOPs, guardrails, domain docs

## Phase 3: Agent Integration

- [x] **3.1** Context builder — `conductor/agent/context_builder.py`
  - Assembles enriched system prompt from KB + active skills
  - Graceful fallback when DB unavailable
- [x] **3.2** Agent node integration — modify `conductor/agent/react_nodes.py`
  - Use ContextBuilder in `_build_system_message()`
  - Only enrich on first iteration
- [x] **3.3** Tool registry integration — modify `conductor/tools/registry.py`
  - `get_active_tools()` queries skill registry
  - Fallback to hardcoded list when DB unavailable
- [x] **3.4** KB agent tools — `conductor/tools/kb_tools.py`
  - `search_knowledge(query, category)` tool
  - `get_guardrails()` tool
  - Included when `kb_enabled=True` (18 tools total)
- [x] **3.5** CLI commands — `conductor kb` and `conductor skills` groups
  - `conductor kb add/list/search/remove/stats`
  - `conductor skills list/enable/disable/info`
  - `conductor serve` — start FastAPI server
  - `conductor run "instruction"` — single-shot mode
- [x] **3.6** End-to-end testing — `tests/test_kb_skills.py`
  - 14 tests: ingestion, retrieval, skills CRUD, context builder, API endpoints
  - Auto-skips when PostgreSQL unavailable
  - 2 non-DB tests always run (tool registry)
- [x] **3.7** Documentation update

## Status Summary

| Phase | Progress | Notes |
|-------|----------|-------|
| Phase 1 | 6/6 ✅ | Infrastructure complete |
| Phase 2 | 7/7 ✅ | Business logic complete |
| Phase 3 | 7/7 ✅ | All complete |

## Key Design Notes

- Embedding model: `all-MiniLM-L6-v2` (384 dims) — lightweight, fast
- Vector column: `Vector(384)` in KBChunk
- DB: PostgreSQL 16 + pgvector via `pgvector/pgvector:pg16` Docker image
- Session pool: `pool_size=5`, `max_overflow=10`
- Chunking: `RecursiveCharacterTextSplitter`, 512 tokens, 64 overlap
