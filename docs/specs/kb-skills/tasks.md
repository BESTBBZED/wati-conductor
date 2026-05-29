# Implementation Tasks: Knowledge Base & Skills Management

> Ordered task breakdown following the 3-phase migration path. PostgreSQL + pgvector + FastAPI + SQLAlchemy async.

## Phase 1: Database & API Infrastructure

### Task 1.1: Add Dependencies

**Deliverable**: Updated `pyproject.toml` with new packages installed.

**Steps**:
1. Add to `[tool.poetry.dependencies]`:
   - `asyncpg = "^0.30"`
   - `pgvector = "^0.3"`
   - `sqlalchemy = {version = "^2.0", extras = ["asyncio"]}`
   - `fastapi = "^0.115"`
   - `uvicorn = "^0.30"`
   - `sentence-transformers = "^3.0"`
   - `pyyaml = "^6.0"`
2. Run `poetry lock && poetry install`
3. Verify: `python -c "import asyncpg; import pgvector; import sqlalchemy; import fastapi; import sentence_transformers"`

**Verification**: `poetry show asyncpg` shows installed version.

---

### Task 1.2: Docker Compose — PostgreSQL + pgvector

**Deliverable**: Updated `docker-compose.yaml` with pgvector service.

**Steps**:
1. Add `postgres` service using `pgvector/pgvector:pg16` image
2. Configure: `POSTGRES_DB=wati_conductor`, `POSTGRES_USER=conductor`, `POSTGRES_PASSWORD` from env
3. Add healthcheck (`pg_isready`)
4. Add `pgdata` volume for persistence
5. Add `depends_on` with `condition: service_healthy` to conductor service
6. Update `.env.example` with postgres connection vars

**Verification**: `docker compose up postgres` → `psql -h localhost -U conductor -d wati_conductor -c "SELECT 1"`

---

### Task 1.3: Configuration — Database Settings

**Deliverable**: New settings in `conductor/config.py`.

**Steps**:
1. Add PostgreSQL fields:
   - `postgres_host: str = "localhost"`
   - `postgres_port: int = 5432`
   - `postgres_user: str = "conductor"`
   - `postgres_password: str = "conductor"`
   - `postgres_db: str = "wati_conductor"`
2. Add `database_url` property (builds `postgresql+asyncpg://...` URL)
3. Add KB fields: `kb_enabled`, `kb_embedding_model` (default `BAAI/bge-m3`), `kb_top_k`, `kb_chunk_size`, `kb_chunk_overlap`
4. Add Skills field: `skills_enabled`
5. Update `.env.example`

**Verification**: `from conductor.config import settings; print(settings.database_url)`

---

### Task 1.4: SQLAlchemy Models

**Deliverable**: `conductor/db/models.py` — ORM models for KB and Skills.

**Steps**:
1. Create `conductor/db/__init__.py`
2. Define `Base(AsyncAttrs, DeclarativeBase)`
3. Define `KBDocument` model (id, title, category, tags, content, source_path, skill_id, always_inject, timestamps)
4. Define `KBChunk` model (id, document_id FK, chunk_index, content, embedding Vector(1536), timestamp)
5. Define `Skill` model (id, name unique, version, description, enabled, tool_names, instructions, depends_on, builtin, timestamps)
6. Define relationships: KBDocument.chunks, KBDocument.skill, Skill.kb_documents

**Verification**: Import models, no errors. `Base.metadata.tables` shows 3 tables.

---

### Task 1.5: Database Session Management

**Deliverable**: `conductor/db/session.py` — async engine + session factory.

**Steps**:
1. Create `ENGINE = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)`
2. Create `async_session = async_sessionmaker(bind=ENGINE, expire_on_commit=False)`
3. Implement `get_session() -> AsyncGenerator[AsyncSession, None]` for DI
4. Implement `init_db()` — creates pgvector extension + all tables (called in lifespan)

**Verification**: `await init_db()` succeeds against running postgres container.

---

### Task 1.6: FastAPI Application Skeleton

**Deliverable**: `conductor/api/main.py` + route stubs.

**Steps**:
1. Create `conductor/api/__init__.py`
2. Create `conductor/api/main.py`:
   - FastAPI app with lifespan (calls `init_db()`)
   - Include routers: `/api/kb`, `/api/skills`
3. Create `conductor/api/routes/__init__.py`
4. Create `conductor/api/routes/kb.py` — router with stub endpoints
5. Create `conductor/api/routes/skills.py` — router with stub endpoints
6. Add uvicorn startup to docker-compose or as CLI command (`conductor serve`)

**Verification**: `uvicorn conductor.api.main:app --port 8000` → `curl localhost:8000/docs` shows Swagger UI.

---

## Phase 2: KB & Skills Business Logic

### Task 2.1: Document Ingestion

**Deliverable**: `conductor/kb/ingestion.py` — parse, chunk, embed, store.

**Steps**:
1. Create `conductor/kb/__init__.py`
2. Implement `ingest_document(session, file_path, category, tags) -> KBDocument`:
   - Read file content (md, txt, json)
   - Create `KBDocument` row
   - Split content using `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)`
   - Batch embed chunks locally via `sentence-transformers` (`embed_batch()`)
   - Create `KBChunk` rows with embeddings
   - `session.commit()`
   - Return document with chunk count
3. Implement `ingest_text(session, title, content, category, tags)` — same but from raw text
4. Handle duplicate detection (same `source_path` → update existing)

**Verification**: Ingest a test markdown file, query `SELECT count(*) FROM kb_chunks` confirms chunks created.

---

### Task 2.2: KB Retriever

**Deliverable**: `conductor/kb/retriever.py` — semantic search + guardrails.

**Steps**:
1. Implement `search_similar(session, query_embedding, top_k, category) -> list[dict]`:
   - pgvector cosine distance query with JOIN on kb_documents
   - Optional category filter
   - Returns `[{content, title, category, similarity}]`
2. Implement `get_always_inject_guardrails(session) -> list[str]`:
   - `SELECT content FROM kb_documents WHERE always_inject = true`
3. Implement `embed_text(text) -> list[float]`:
   - Local embedding via `SentenceTransformer("BAAI/bge-m3")`
   - Model loaded once (lazy singleton), stays in memory
4. Implement `embed_batch(texts) -> list[list[float]]`:
   - Batch embedding for ingestion (faster than one-by-one)

**Verification**: Ingest 3 docs, search with related query, verify top result is the most relevant.

---

### Task 2.3: KB API Routes

**Deliverable**: Full implementation of `conductor/api/routes/kb.py`.

**Steps**:
1. `POST /api/kb/documents` — ingest (file upload or JSON body with content)
2. `GET /api/kb/documents` — list with optional `?category=sop&tag=vip` filters
3. `GET /api/kb/documents/{id}` — get single document with metadata
4. `DELETE /api/kb/documents/{id}` — cascade delete document + chunks
5. `POST /api/kb/search` — body: `{query, top_k, category}` → semantic search results
6. `GET /api/kb/guardrails` — return all always-inject documents
7. Define Pydantic request/response schemas

**Verification**: Full CRUD cycle via Swagger UI or curl.

---

### Task 2.4: Skills Registry

**Deliverable**: `conductor/skills/registry.py` — CRUD + tool resolution.

**Steps**:
1. Create `conductor/skills/__init__.py`
2. Implement `get_active_skills(session) -> list[Skill]`:
   - `SELECT * FROM skills WHERE enabled = true`
3. Implement `resolve_active_tools(session) -> list`:
   - Collect `tool_names` from all enabled skills
   - Map to actual tool objects from existing tool modules
4. Implement `enable_skill(session, name)` / `disable_skill(session, name)`
5. Implement dependency resolution (enabling A enables its deps)

**Verification**: Disable `tickets` skill, `resolve_active_tools()` returns 14 tools.

---

### Task 2.5: Built-in Skills Seeding

**Deliverable**: `conductor/skills/builtin.py` — seed data for 5 built-in skills.

**Steps**:
1. Define built-in skill data:
   - `contacts`: 8 tools (search, get_info, add/remove tags, update attributes + batch variants)
   - `messaging`: 2 tools (send_session_message, send_template_message_batch)
   - `templates`: 2 tools (list_templates, get_template_details)
   - `operators`: 2 tools (assign_operator, assign_team)
   - `tickets`: 2 tools (create_ticket, resolve_ticket)
2. Implement `seed_builtin_skills(session)` — insert if not exists
3. Call from FastAPI lifespan (after table creation)

**Verification**: After startup, `SELECT count(*) FROM skills WHERE builtin = true` returns 5.

---

### Task 2.6: Skills API Routes

**Deliverable**: Full implementation of `conductor/api/routes/skills.py`.

**Steps**:
1. `GET /api/skills` — list all skills with status
2. `POST /api/skills` — create custom skill
3. `GET /api/skills/{name}` — get skill details (tools, instructions, KB docs)
4. `PATCH /api/skills/{name}` — update (enable/disable, edit instructions)
5. `DELETE /api/skills/{name}` — delete (reject if builtin)
6. `GET /api/skills/active/tools` — resolved tool names from enabled skills
7. Define Pydantic request/response schemas

**Verification**: `GET /api/skills` returns 5 built-in skills. `PATCH /api/skills/tickets {enabled: false}` works.

---

## Phase 3: Agent Integration

### Task 3.1: Context Builder

**Deliverable**: `conductor/agent/context_builder.py`.

**Steps**:
1. Implement `ContextBuilder` class:
   - Uses `async_session()` from pool (no extra connection cost)
   - `build_system_message(user_instruction) -> str`:
     1. Base SYSTEM_PROMPT
     2. Active skill instructions (from DB)
     3. Always-on guardrails (from DB)
     4. Semantic search results for instruction (pgvector)
     5. Conversation history (existing)
2. Graceful degradation: if DB unavailable, return base prompt only
3. Module-level `get_context_builder()` factory

**Verification**: Mock DB with SOP doc, verify it appears in assembled prompt.

---

### Task 3.2: Agent Node Integration

**Deliverable**: Modified `conductor/agent/react_nodes.py`.

**Steps**:
1. Make `_build_system_message()` async, accept `user_instruction` param
2. Use `ContextBuilder` when `kb_enabled=True`
3. Fall back to original static prompt when KB disabled or DB unavailable
4. Modify `agent_node()`:
   - Extract user instruction from first HumanMessage
   - Call async `_build_system_message(user_instruction)`
   - Only build enriched prompt on first iteration (not every loop cycle)

**Verification**: Agent with KB containing "never send more than 100 messages" → agent mentions limit.

---

### Task 3.3: Tool Registry Integration

**Deliverable**: Modified `conductor/tools/registry.py`.

**Steps**:
1. Add async `get_active_tools() -> list` that queries skill registry
2. Modify `get_all_tools()` to call skill resolution when `skills_enabled=True`
3. Fallback: if DB unavailable, return legacy hardcoded list
4. Update `get_tool(name)` to respect active skills

**Verification**: Disable `tickets` skill → agent cannot call `create_ticket`.

---

### Task 3.4: KB Agent Tools

**Deliverable**: `conductor/tools/kb_tools.py`.

**Steps**:
1. `@tool search_knowledge(query: str, category: str | None = None) -> str`
   - Embeds query, calls `search_similar()`, formats results
2. `@tool get_guardrails(tool_name: str | None = None) -> str`
   - Returns applicable guardrails from DB
3. Add to a `knowledge` built-in skill (always enabled when KB enabled)

**Verification**: Agent can call `search_knowledge("batch limits")` mid-conversation.

---

### Task 3.5: KB CLI Commands

**Deliverable**: `conductor kb` command group calling the API.

**Steps**:
1. CLI commands call FastAPI endpoints via `httpx`:
   - `conductor kb add <path> --category <cat> --tags <tags>`
   - `conductor kb list [--category] [--tag]`
   - `conductor kb search <query> [--top-k 5]`
   - `conductor kb remove <doc_id>`
   - `conductor kb stats`
2. `conductor skills list/enable/disable/info/create`
3. `conductor serve` — start the FastAPI server
4. Rich-formatted output (tables, panels)

**Verification**: `conductor kb add ./test.md --category sop` → `conductor kb search "test"` returns it.

---

### Task 3.6: End-to-End Testing

**Deliverable**: Integration tests.

**Steps**:
1. Test: Empty DB → agent behaves identically to current (regression)
2. Test: KB with SOP → agent references SOP in reasoning
3. Test: KB with guardrail (always_inject) → agent respects constraint
4. Test: Skill disabled → tools removed from agent
5. Test: DB unavailable → graceful fallback to base prompt
6. Test: Retrieval latency < 500ms (with 100 docs)
7. Test: API CRUD cycle (ingest → search → delete)

**Verification**: All tests pass. `pytest tests/` green.

---

### Task 3.7: Documentation

**Deliverable**: Updated docs.

**Steps**:
1. Update `README.md` — KB and Skills sections
2. Create sample KB documents:
   - `docs/sample-kb/sops/batch-messaging.md`
   - `docs/sample-kb/guardrails/limits.md`
   - `docs/sample-kb/domain/template-guide.md`
3. Write `docs/kb-skills-guide.md` — usage guide
4. Update `docs/roadmap.md` — mark V4 features as in-progress

**Verification**: New user can follow guide end-to-end.

---

## Task Dependencies

```
Phase 1 (Infrastructure):
  1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6

Phase 2 (Business Logic):
  1.5 → 2.1 → 2.2 → 2.3
  1.5 → 2.4 → 2.5 → 2.6

Phase 3 (Integration):
  2.2 + 2.4 → 3.1 → 3.2
  2.4 → 3.3
  2.2 → 3.4
  2.3 + 2.6 → 3.5
  3.2 + 3.3 + 3.4 → 3.6 → 3.7
```

## Estimated Effort

| Phase | Tasks | Effort |
|---|---|---|
| Phase 1: DB + API Infrastructure | 1.1–1.6 | 2 days |
| Phase 2: KB + Skills Logic | 2.1–2.6 | 3 days |
| Phase 3: Agent Integration | 3.1–3.7 | 3 days |
| **Total** | **19 tasks** | **8 days** |

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| pgvector not available in base postgres image | Use `pgvector/pgvector:pg16` image (includes extension) |
| Embedding model large (~2GB download) | Downloaded once on first use, cached in `~/.cache/huggingface/` |
| Embedding slow on CPU | ~200ms/chunk on CPU is fine for ingestion; query embedding is single call (~50ms) |
| Connection pool exhaustion under load | Start with pool_size=5, max_overflow=10; monitor in production |
| Agent latency increase from DB queries | Pool reuse = ~1ms overhead; local embedding ~50ms; pgvector search ~10ms |
| Breaking existing tests | Feature-flagged via `KB_ENABLED`/`SKILLS_ENABLED`; tests run with flags off by default |
| Docker compose conflicts with existing services | Use unique port (5432) and volume name (pgdata) |
