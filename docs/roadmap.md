# Roadmap

V2 vision and feature priorities for WATI Conductor. Consolidated from v1 build notes, v2 vision docs, and the interactive CLI refactor plan.

## V1 → V2 Summary

**V1** (current): Single-shot and basic REPL CLI agent with mock WATI client. 3-node LangGraph graph, 16 tools, LLM-first parsing. Production-ready for demos.

**V2** (target): Persistent interactive sessions with streaming, real WATI API integration, session memory, RAG-based knowledge base for SOPs and guardrails, and web UI.

**V3** (future): Hard guardrail validation node, self-updating KB from conversation feedback, admin dashboard for business-owned policy management.

## Feature Priorities

### High Priority

| Feature | Description | Effort |
|---|---|---|
| Real WATI API testing | Test real client against WATI sandbox, handle rate limits and error codes | 1-2 days |
| RAG knowledge base (Option A) | Pre-retrieval enrichment — inject SOPs, guardrails, domain knowledge into parser context | 3-4 days |
| Streaming responses | Token-by-token display for LLM thinking and responses | 2 days |
| Advanced error recovery | Per-tool retry, fallback strategies, partial success handling | 2 days |
| Rollback on failure | Undo completed steps when a later step fails (e.g., remove tag if message send fails) | 2 days |

### Medium Priority

| Feature | Description | Effort |
|---|---|---|
| RAG guardrail node (Option B) | Dedicated graph node that validates parsed intent against KB hard constraints | 3 days |
| Web UI | Chat interface with React/Next.js + shadcn/ui | 1 week |
| LangSmith tracing | Full trace visibility for debugging agent behavior | 1 day |
| Batch optimization | Parallel tool execution where tasks have no dependencies | 2 days |
| Session persistence | Save/resume sessions across restarts (SQLite checkpointer) | 1 day |
| REPL meta commands | `/help`, `/history`, `/clear`, `/sessions`, `/trust` | 1 day |
| Advanced scheduling | Cron-like triggers for recurring workflows | 3 days |

### Low Priority

| Feature | Description | Effort |
|---|---|---|
| Webhook handling | Process WATI webhook events (message status, delivery receipts) | 3 days |
| Multi-language output | i18n for CLI responses | 2 days |
| Admin dashboard | Visualize workflows, monitor executions | 1 week |
| RBAC / access control | User permissions, API key rotation | 3 days |
| Production deployment | k8s manifests, CI/CD pipeline, health checks | 1 week |

## Interactive CLI Refactor (V2 Core)

The main V2 effort is transforming the CLI from basic REPL to a persistent interactive session.

### Current vs Target

```
Current: User Input → Agent Graph → Execute → Output → (loop)
                      (no session state between turns beyond 2-turn history)

Target:  User Input → Session Context → Agent Graph → Execute → Output
              ↑                                           |
              └── Session State (memory, preferences) ←───┘
```

### New Components

```
conductor/
├── repl/                     # NEW
│   ├── session.py            # Session state management
│   ├── loop.py               # Main REPL loop
│   ├── commands.py           # Meta command handlers (/help, /history, etc.)
│   ├── streaming.py          # Token streaming utilities
│   └── ui.py                 # Rich UI components
```

### Session State

```python
class SessionState(BaseModel):
    session_id: str
    created_at: datetime
    last_active: datetime
    conversation_history: list[ConversationTurn]
    preferences: UserPreferences  # trust_mode, etc.
    execution_context: dict       # last plan, results
```

### Key Design Decisions

- **LangGraph checkpointer**: Use `MemorySaver` for in-memory sessions (v2.0), `SqliteSaver` for persistence (v2.1)
- **Thread ID = session ID**: Conversation continuity via LangGraph's built-in threading
- **Backward compatible**: `python -m conductor.cli "instruction"` still works as single-shot
- **Meta command prefix**: `/` (matches Slack/Kiro conventions)
- **Streaming granularity**: Token-level for thinking, sentence-level for final response

### Implementation Phases

| Phase | Deliverable | Duration |
|---|---|---|
| REPL infrastructure | Session class, basic loop, signal handlers | 2 days |
| Agent + session integration | Checkpointer, thread_id, multi-turn context | 3 days |
| Meta commands | `/help`, `/history`, `/clear`, `/trust`, `/quit` | 1 day |
| Streaming output | Token streaming, live tool progress | 2 days |
| UI polish | Welcome banner, visual separators, typing indicators | 2 days |
| Backward compatibility | Detect mode, preserve all existing flags | 1 day |
| Session persistence (optional) | SQLite checkpointer, `/sessions`, `/resume` | 1 day |

## RAG Knowledge Base (V2/V3)

Inject business knowledge and guardrails into the agent via retrieval-augmented generation, replacing hardcoded prompt rules with a queryable, updatable knowledge store.

### Why RAG

The parser's system prompt is already ~150 lines of hardcoded rules ("don't use array indexing", "distinguish queries from actions", "handle temporal logic"). Every new business rule makes it longer, slower, and more expensive. RAG moves that knowledge out of the prompt — the agent retrieves only what's relevant to the current instruction.

### Two-Phase Rollout

**V2 — Option A: Pre-retrieval enrichment** (simpler, do this first)

```
User instruction
    ↓
[RAG retrieval] → 3-5 relevant documents from KB
    ↓
[parse_intent] ← enriched context (tool schemas + retrieved SOPs/guardrails)
    ↓
[execute_plan] → [generate_response]
```

Retrieved context gets prepended to the parser's system prompt. The LLM sees "here's what the user asked, and here's the relevant policy" before generating tasks. No new graph nodes — just a retrieval call before the existing parse node.

**V3 — Option B: Dedicated validation node** (hard guardrails)

```
[parse_intent] → [rag_validate] → [execute_plan] → [generate_response]
```

A new LangGraph node between parse and execute that checks the parsed intent against KB constraints. Can reject, modify, or flag plans. Example: "User wants to send marketing template to 10,000 contacts — KB says batch limit is 1,000 and requires manager approval" → node blocks execution and returns a clarification.

### Knowledge Base Content

Three categories, each with different retrieval patterns:

**SOPs (Standard Operating Procedures)** — retrieved by semantic similarity

- "VIP contacts must receive templates in their preferred language"
- "Escalation to Support team requires a ticket first"
- "Marketing templates can only be sent during business hours (9am-6pm local time)"

**Guardrails (hard constraints)** — retrieved + validated post-parse

- "Never send more than 500 messages in a single batch"
- "Never delete contacts — only remove tags"
- "Template messages require 24h opt-in window"

**Domain knowledge** — retrieved for context enrichment

- Template catalog with descriptions and use cases
- Contact segment definitions ("VIP = tier premium + active in last 30 days")
- Team/operator routing rules

### Guardrail Strategy (layered defense)

| Layer | Mechanism | Example | Updateable? |
|---|---|---|---|
| Soft guardrails | Retrieved into prompt, LLM follows voluntarily | "Marketing sends should be reviewed" → LLM adds confirmation | Yes (edit KB) |
| Hard guardrails | Validated in rag_validate node, blocks execution | "Batch > 500 blocked" → plan rejected | Yes (edit KB) |
| Fallback guardrails | Hardcoded in system prompt | "Never delete contacts" | No (code change) |

Critical constraints should exist in both KB and system prompt (defense in depth). Non-critical policies live only in KB for easy updates.

### Implementation Plan

**V2 (Option A) — 3-4 days**

```
conductor/
├── rag/                      # NEW
│   ├── store.py              # Vector store setup (Chroma or FAISS)
│   ├── indexer.py            # Index markdown/text documents into store
│   └── retriever.py          # Retrieve relevant docs for an instruction
├── knowledge/                # NEW — KB content as plain files
│   ├── sops/                 # Standard operating procedures
│   ├── guardrails/           # Hard constraints
│   └── domain/               # Templates, segments, routing rules
```

| Task | Deliverable | Duration |
|---|---|---|
| Vector store setup | Chroma/FAISS with embedding model, index/query interface | 1 day |
| KB content authoring | Initial SOPs, guardrails, domain docs (20-50 documents) | 1 day |
| Parser integration | Retrieve 3-5 docs per instruction, inject into system prompt | 1 day |
| Testing + tuning | Verify retrieval quality, tune chunk size and top-k | 0.5-1 day |

**V3 (Option B) — 3 days additional**

| Task | Deliverable | Duration |
|---|---|---|
| rag_validate node | New LangGraph node, constraint checking logic | 1.5 days |
| Graph rewiring | Insert node between parse and execute, conditional edges | 0.5 day |
| Hard guardrail rules | Structured constraint format, violation handling | 1 day |

### Design Decisions

- **Local vector store** (Chroma or FAISS): KB is small (20-50 docs), no need for hosted solutions
- **Chunk by policy, not by paragraph**: Each SOP or guardrail is one retrievable unit — don't split a "template sending policy" across chunks
- **Retrieve 3-5 docs max**: More than that reintroduces prompt bloat
- **Business-owned content**: KB files are plain markdown — business team can edit without touching code
- **No self-updating KB from conversations**: Introduces drift risk. V4 consideration at earliest
- **Confidence interaction**: Retrieved guardrails naturally lower task confidence when constraints apply, working with existing ≥ 0.7 filtering

## Architecture Decisions Log

Key trade-offs from v1 that inform v2 planning:

### LangGraph over ReAct

LangGraph state machine gives explicit control flow — critical for WATI orchestration where you need deterministic multi-step plans, not exploratory tool use. Human-in-the-loop interrupts are built-in.

### LLM-first over rule-based planning

V1 started with a rule-based planner (6 nodes). V2 simplified to LLM-first (3 nodes) because:
- Adding new tools required planner rule changes
- LLM handles edge cases (temporal logic, query vs action) better than rules
- 40% less code to maintain

### Mock-first development

Real WATI API has strict data structures, template approval workflows, and rate limits. Mock client enabled fast iteration and safe testing of destructive operations. The Protocol-based abstraction means swapping to real is a config change.

### DeepSeek as default LLM

Cost-optimized at $0.014/1M tokens vs Claude at $3/1M. Quality is sufficient for intent parsing. Claude available as fallback for complex instructions.

### 2-turn conversation history limit

Full history caused the agent to repeat old tasks. 2 turns is enough for follow-up questions ("send it to them too") without context pollution. V2 should implement proper summarization.

### RAG before LLM over prompt-stuffing

Business rules, SOPs, and guardrails currently live in the parser's system prompt (~150 lines). This doesn't scale — every new rule increases cost and latency for every call. RAG retrieves only relevant context per instruction (3-5 docs from a local vector store). Two-phase approach: Option A (v2) injects retrieved context into the existing prompt; Option B (v3) adds a dedicated validation node for hard constraints. KB content is plain markdown files owned by the business team — no code changes needed to update policies.

## Spec Change History

- **2026-04-09**: Removed all assignment/candidate framing, repositioned as standalone product
- **2026-04-09**: Reorganized docs — separated v1 specs from v2 vision
- **2026-04-09**: Added multi-model LLM strategy to requirements (DeepSeek primary, Claude fallback)
- **2026-04-10**: V1 implementation complete (9/11 tasks, all P0 done)
- **2026-04-12**: V2 multi-task architecture implemented (3-node graph replaces 6-node)
- **2026-04-14**: Parser and CLI refinements (structured output, interactive mode)
- **2026-04-16**: Documentation reorganized (cbd-style structure, mermaid architecture diagrams)
- **2026-04-16**: RAG knowledge base added to roadmap — Option A (v2 pre-retrieval) + Option B (v3 validation node)
