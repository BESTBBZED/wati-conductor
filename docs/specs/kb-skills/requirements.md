# Requirements: Knowledge Base Management & Skills Management

> Add a queryable knowledge base for SOPs/guardrails/domain knowledge, and a skills registry for dynamically managing agent capabilities — enabling the agent to be context-aware and extensible without code changes.

## Problem Statement

### Knowledge Base

The agent's system prompt is a static 15-line string in `react_nodes.py`. As business rules grow (SOP procedures, guardrails, template usage policies, contact segment definitions), this approach doesn't scale:

- Adding rules bloats the prompt → increases cost per LLM call in the ReAct loop
- All rules are injected regardless of relevance → dilutes attention
- Updating rules requires code deployment
- No audit trail of what knowledge the agent used for a decision

### Skills Management

The tool registry (`tools/registry.py`) is a hardcoded list of 16 tools. Adding new capabilities requires:

- Writing Python code for the tool
- Manually adding it to `get_all_tools()`
- Redeploying the application

There's no way to:

- Enable/disable tools per tenant or use case
- Group tools into logical "skills" (e.g., "marketing skill" = template tools + batch messaging)
- Add tool-specific instructions that the agent sees only when that skill is active
- Version or rollback skill configurations

## Functional Requirements

### Knowledge Base Management

#### FR-KB-1: Document Ingestion

The system MUST support ingesting knowledge documents in these formats:

- Markdown (`.md`) — primary format for SOPs and guidelines
- Plain text (`.txt`) — for simple rules
- JSON (`.json`) — for structured data (template catalogs, segment definitions)

Documents MUST be chunked and embedded for semantic retrieval.

#### FR-KB-2: Semantic Retrieval

Given a user instruction, the system MUST retrieve the top-K most relevant knowledge chunks (configurable, default K=5) and inject them into the agent's system prompt before reasoning begins.

#### FR-KB-3: Knowledge Categories

Documents MUST be tagged with a category:

| Category | Purpose | Retrieval Behavior |
|---|---|---|
| `sop` | Standard operating procedures | Retrieved by semantic similarity to user instruction |
| `guardrail` | Hard constraints and limits | Always injected (small set) OR retrieved when relevant |
| `domain` | Reference data (templates, segments, teams) | Retrieved by semantic similarity |
| `faq` | Common questions and answers | Retrieved by semantic similarity |

#### FR-KB-4: CRUD Operations

The system MUST provide tools/commands for:

- **Create**: Add a new document to the KB with metadata (title, category, tags)
- **Read**: List documents, view document content, search by metadata
- **Update**: Replace or append to existing documents
- **Delete**: Remove documents from the KB (soft delete with audit)

#### FR-KB-5: CLI Management Interface

KB management MUST be accessible via CLI commands:

```
conductor kb add <file_or_dir> --category sop --tags "marketing,templates"
conductor kb list [--category sop] [--tag marketing]
conductor kb search "how to handle VIP contacts"
conductor kb remove <doc_id>
conductor kb sync <directory>  # bulk ingest/update from a folder
```

#### FR-KB-6: Agent-Accessible KB Tools

The agent MUST have tools to query the KB at runtime:

- `search_knowledge(query: str, category: str | None) → list[str]` — semantic search
- `get_guardrails(tool_name: str | None) → list[str]` — retrieve applicable guardrails

These tools allow the agent to self-serve additional context mid-conversation when the pre-retrieved context is insufficient.

#### FR-KB-7: Pre-Retrieval Enrichment

Before the first `agent_node` invocation in a ReAct cycle, the system MUST:

1. Embed the user's instruction
2. Retrieve top-K relevant documents
3. Retrieve all active guardrails (always-on subset)
4. Inject retrieved content into the system message

This happens transparently — no new graph node required for V4.

### Skills Management

#### FR-SK-1: Skill Definition

A "skill" is a named, versioned bundle of:

- **Tools**: One or more LangChain tools
- **Instructions**: Skill-specific system prompt additions (injected when skill is active)
- **KB documents**: Associated knowledge documents (auto-retrieved when skill is active)
- **Metadata**: Name, description, version, author, enabled/disabled status

#### FR-SK-2: Skill Registry

The system MUST maintain a skill registry that:

- Lists all available skills with their status (enabled/disabled)
- Resolves which tools are active for the current session
- Provides skill metadata to the agent (so it knows what it can do)

#### FR-SK-3: Skill Enable/Disable

Skills MUST be toggleable without code changes:

```
conductor skills list
conductor skills enable marketing
conductor skills disable marketing
conductor skills info marketing
```

When a skill is disabled:

- Its tools are NOT bound to the LLM
- Its instructions are NOT injected into the system prompt
- Its KB documents are still in the store but NOT retrieved

#### FR-SK-4: Built-in Skills

The existing 16 tools MUST be organized into built-in skills:

| Skill | Tools | Description |
|---|---|---|
| `contacts` | search_contacts, get_contact_info, add/remove tags, update attributes | Contact management |
| `messaging` | send_session_message, send_template_message_batch | Message sending |
| `templates` | list_templates, get_template_details | Template browsing |
| `operators` | assign_operator, assign_team | Operator/team assignment |
| `tickets` | create_ticket, resolve_ticket | Ticket management |

All built-in skills are enabled by default.

#### FR-SK-5: Custom Skill Creation

Users MUST be able to create custom skills via:

- A skill manifest file (YAML/JSON) defining tools, instructions, and KB docs
- CLI commands for scaffolding and registration

```
conductor skills create <name>
conductor skills register <path_to_manifest>
```

#### FR-SK-6: Skill-Scoped Instructions

Each skill MAY define instructions that are injected into the system prompt ONLY when that skill is active. Example:

```yaml
# skills/marketing/manifest.yaml
name: marketing
instructions: |
  When sending marketing templates:
  - Always check contact's opt-in status before sending
  - Never send more than 1 marketing message per contact per day
  - Prefer the contact's language preference for template selection
```

#### FR-SK-7: Skill Dependencies

A skill MAY declare dependencies on other skills. If skill A depends on skill B, enabling A automatically enables B.

## Non-Functional Requirements

### NFR-1: Storage Backend

The KB vector store MUST support:

- **Default**: Local file-based store (ChromaDB or FAISS) for development/single-node
- **Production**: Pluggable backend interface for PostgreSQL+pgvector or cloud vector DBs

### NFR-2: Embedding Model

- Default: `BAAI/bge-m3` via `sentence-transformers` (local, free, multilingual)
- 1024 dimensions, normalized embeddings for cosine similarity
- Model downloaded once (~2GB), cached locally
- Configurable via `KB_EMBEDDING_MODEL` env var
- No API key required — zero cost per embedding

### NFR-3: Retrieval Latency

Pre-retrieval enrichment MUST add < 500ms to the first agent node invocation. This is acceptable since the LLM call itself takes 1-3s.

### NFR-4: KB Size Limits

- Initial target: up to 500 documents, ~50K chunks
- Chunk size: configurable, default 512 tokens with 64-token overlap
- Must not degrade retrieval quality as KB grows

### NFR-5: Backward Compatibility

- Existing CLI interface MUST remain unchanged
- Agent behavior with empty KB MUST be identical to current behavior
- All 16 existing tools MUST continue to work
- No breaking changes to `AgentState` schema

### NFR-6: Persistence

- KB documents and embeddings MUST persist across application restarts
- Skill configurations MUST persist (file-based config)
- Default storage location: `./data/kb/` and `./data/skills/`

### NFR-7: Observability

- Log which KB documents were retrieved for each instruction
- Log which skills are active per session
- Include retrieval metadata in verbose/debug output

### NFR-8: Cost Awareness

- Embeddings are free (local model) — no per-query or per-ingestion cost
- Retrieved context increases LLM prompt size → track token usage delta
- More context = more tokens per ReAct iteration = higher DeepSeek API cost
- Provide `--no-kb` flag to bypass retrieval for cost-sensitive usage

## Out of Scope (V4)

- Web UI for KB management (future)
- Multi-tenant KB isolation (future)
- Dedicated validation node / hard guardrail enforcement (V5 — Option B in roadmap)
- Real-time KB updates from conversation feedback (V5)
- Skill marketplace or sharing
- Parallel tool execution within a skill

## Success Criteria

1. **KB retrieval works**: Agent receives relevant context for instructions that match KB content
2. **Agent behavior improves**: Agent follows SOPs and respects guardrails from KB (vs. ignoring them when not in prompt)
3. **Skills are toggleable**: Disabling a skill removes its tools from the agent's capabilities
4. **Zero regression**: All existing functionality works identically with empty KB and all skills enabled
5. **CLI management works**: Users can add/remove/search KB documents and enable/disable skills without code changes
6. **Performance acceptable**: Pre-retrieval adds < 500ms, no noticeable degradation in agent response quality

## Constraints

- Must use LangGraph (existing dependency)
- Must use LangChain's tool-calling mechanism (existing pattern)
- Python 3.11+, Poetry for dependency management
- Storage must work in Docker container (no external services required for dev mode)
- Embedding model must be configurable (not hardcoded to a paid API)
