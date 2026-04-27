# Roadmap

Feature priorities for WATI Conductor. Consolidated from build notes, vision docs, and the ReAct refactor.

## Version Summary

**V1** (completed): Single-shot and basic REPL CLI agent with mock WATI client. 6-node LangGraph graph with rule-based planner. Production-ready for demos.

**V2** (completed): Simplified to 3-node LLM-first plan-then-execute architecture. 16 tools, structured output parsing, confidence filtering. ~40% code reduction from v1.

**V3** (completed — current): **ReAct refactor** — true Reasoning + Acting loop. 2-node LangGraph graph (`agent_node` ↔ `tool_node`). LLM reasons step-by-step, calls one tool at a time, observes results, adapts dynamically. Native tool calling via `bind_tools`. ~200 lines of agent code.

**V4** (target): Streaming responses, RAG knowledge base for SOPs and guardrails, session persistence, web UI.

**V5** (future): Hard guardrail validation node, self-updating KB from conversation feedback, admin dashboard.

## Feature Priorities

### High Priority

| Feature | Description | Effort |
|---|---|---|
| ReAct integration tests | Write tests for the ReAct loop (multi-step, error recovery, max iterations) | 1-2 days |
| Real WATI API testing | Test real client against WATI sandbox, handle rate limits and error codes | 1-2 days |
| Streaming responses | Token-by-token display for LLM thinking and responses | 2 days |
| RAG knowledge base (Option A) | Pre-retrieval enrichment — inject SOPs, guardrails, domain knowledge into system prompt | 3-4 days |

### Medium Priority

| Feature | Description | Effort |
|---|---|---|
| RAG guardrail node (Option B) | Dedicated graph node that validates tool calls against KB hard constraints | 3 days |
| Web UI | Chat interface with React/Next.js + shadcn/ui | 1 week |
| LangSmith tracing | Full trace visibility for debugging agent behavior | 1 day |
| Session persistence | Save/resume sessions across restarts (LangGraph checkpointer) | 1 day |
| REPL meta commands | `/help`, `/history`, `/clear`, `/sessions`, `/trust` | 1 day |
| Token cost tracking | Track LLM calls per instruction (important for ReAct — more calls than plan-execute) | 1 day |

### Low Priority

| Feature | Description | Effort |
|---|---|---|
| Webhook handling | Process WATI webhook events (message status, delivery receipts) | 3 days |
| Multi-language output | i18n for CLI responses | 2 days |
| Admin dashboard | Visualize workflows, monitor executions | 1 week |
| RBAC / access control | User permissions, API key rotation | 3 days |
| Production deployment | k8s manifests, CI/CD pipeline, health checks | 1 week |
| Legacy code cleanup | Remove unused v1/v2 files (parser.py, planner.py, nodes/) | 0.5 day |

## RAG Knowledge Base (V4/V5)

Inject business knowledge and guardrails into the agent via retrieval-augmented generation, replacing hardcoded prompt rules with a queryable, updatable knowledge store.

### Why RAG

The system prompt is currently ~15 lines of guidelines. As business rules grow, RAG moves that knowledge out of the prompt — the agent retrieves only what's relevant to the current instruction.

### Two-Phase Rollout

**V4 — Option A: Pre-retrieval enrichment** (simpler, do this first)

```
User instruction
    ↓
[RAG retrieval] → 3-5 relevant documents from KB
    ↓
[agent_node] ← enriched system prompt (guidelines + retrieved SOPs/guardrails)
    ↓
agent_node ↔ tool_node (ReAct loop)
```

Retrieved context gets prepended to the system prompt. The LLM sees "here's what the user asked, and here's the relevant policy" before reasoning. No new graph nodes — just a retrieval call before the existing agent node.

**V5 — Option B: Dedicated validation node** (hard guardrails)

```
agent_node → [rag_validate] → tool_node → agent_node (loop)
```

A new LangGraph node between agent and tool that checks each tool call against KB constraints. Can reject, modify, or flag calls. Example: "Agent wants to send marketing template to 10,000 contacts — KB says batch limit is 1,000" → node blocks execution.

### Knowledge Base Content

Three categories:

**SOPs** — retrieved by semantic similarity:

- "VIP contacts must receive templates in their preferred language"
- "Marketing templates can only be sent during business hours"

**Guardrails** — retrieved + validated:

- "Never send more than 500 messages in a single batch"
- "Never delete contacts — only remove tags"

**Domain knowledge** — context enrichment:

- Template catalog with descriptions and use cases
- Contact segment definitions
- Team/operator routing rules

### Implementation Plan

**V4 (Option A) — 3-4 days**

| Task | Deliverable | Duration |
|---|---|---|
| Vector store setup | Chroma/FAISS with embedding model | 1 day |
| KB content authoring | Initial SOPs, guardrails, domain docs | 1 day |
| System prompt integration | Retrieve 3-5 docs per instruction, inject into prompt | 1 day |
| Testing + tuning | Verify retrieval quality, tune chunk size and top-k | 0.5-1 day |

**V5 (Option B) — 3 days additional**

| Task | Deliverable | Duration |
|---|---|---|
| rag_validate node | New LangGraph node, constraint checking logic | 1.5 days |
| Graph rewiring | Insert node between agent and tool, conditional edges | 0.5 day |
| Hard guardrail rules | Structured constraint format, violation handling | 1 day |

## Architecture Decisions Log

Key trade-offs that inform future planning:

### ReAct over Plan-then-Execute (v3)

Plan-then-Execute (v2) generated all tasks upfront in one LLM call, then executed them sequentially. This was cheaper (2 LLM calls) but couldn't adapt — if a search returned 0 results, the agent still tried to send messages to an empty list. ReAct costs more LLM calls per instruction but produces dramatically better behavior for multi-step workflows.

### DeepSeek v4 Pro as default

ReAct requires stronger reasoning than plan-then-execute. `deepseek-v4-pro` handles multi-step tool selection reliably. `deepseek-v4-flash` is available as a cheaper fallback via `LLM_REACT_MODEL` config.

### Thinking mode disabled

DeepSeek v4 models default to thinking mode enabled. We disable it (`{"thinking": {"type": "disabled"}}`) because: (1) it ignores temperature/top_p settings, (2) it adds latency per call — unacceptable in a multi-call loop, (3) tool calling works fine without it.

### Mock-first development

Real WATI API has strict data structures, template approval workflows, and rate limits. Mock client enabled fast iteration and safe testing of destructive operations. The Protocol-based abstraction means swapping to real is a config change.

### 2-turn conversation history limit

Full history caused the agent to repeat old tasks. 2 turns is enough for follow-up questions without context pollution. Future: implement proper summarization.

### Message-based state over structured fields

The ReAct pattern uses a `messages` list as the primary data channel instead of separate fields for intent/results/errors. This is the standard LangGraph pattern and simplifies the state schema significantly.

## Spec Change History

- **2026-04-09**: Removed all assignment/candidate framing, repositioned as standalone product
- **2026-04-09**: Reorganized docs — separated v1 specs from v2 vision
- **2026-04-09**: Added multi-model LLM strategy to requirements (DeepSeek primary, Claude fallback)
- **2026-04-10**: V1 implementation complete (9/11 tasks, all P0 done)
- **2026-04-12**: V2 multi-task architecture implemented (3-node graph replaces 6-node)
- **2026-04-14**: Parser and CLI refinements (structured output, interactive mode)
- **2026-04-16**: Documentation reorganized (cbd-style structure, mermaid architecture diagrams)
- **2026-04-16**: RAG knowledge base added to roadmap — Option A (v2 pre-retrieval) + Option B (v3 validation node)
- **2026-04-27**: **ReAct refactor completed** — 2-node ReAct loop replaces 3-node plan-execute. New files: `react_graph.py`, `react_nodes.py`. Updated: `llm_factory.py`, `config.py`, `cli.py`, `state.py`, `__init__.py`. Default model changed to `deepseek-v4-pro`
