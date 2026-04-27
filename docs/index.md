# WATI Conductor Documentation

> **For AI Assistants**: This file is the primary entry point for understanding the WATI Conductor codebase. Read this file first — it contains enough metadata to determine which detailed files to consult for specific questions.

## System Summary

WATI Conductor is a Python AI agent that translates natural language instructions into WhatsApp business automation workflows via the WATI API. It uses a **ReAct (Reasoning + Acting) loop** powered by LangGraph, where the LLM reasons about each step, calls one tool at a time, observes the result, and decides what to do next — adapting dynamically to tool outputs.

## Documentation Files

| File | Purpose | Consult When... |
|---|---|---|
| [architecture.md](architecture.md) | System architecture diagrams, ReAct loop flow, state schema | You need to understand how the agent processes instructions end-to-end |
| [components.md](components.md) | Detailed breakdown of each module — agent, tools, clients, models, CLI | You need to understand what a specific module does or which files to modify |
| [status.md](status.md) | Implemented vs planned features, tool inventory, what works and what doesn't | You need to know what's done, what's missing, or what to build next |
| [roadmap.md](roadmap.md) | V2 vision, feature priorities, RAG knowledge base plan | You're planning future work or want to understand v1→v2 evolution |
| [setup.md](setup.md) | Quick start, environment config, Docker setup, switching to real WATI API | You need to run the project or configure it for a new environment |
| [dev-notes.md](dev-notes.md) | Build notes, problem framing, design trade-offs, demo script | You want context on why decisions were made or need to run a demo |
| [specs/v1/](specs/v1/) | Original v1 specification (requirements, design, tasks) | You need the original spec as a reference artifact |
| [specs/react-refactor/](specs/react-refactor/) | ReAct refactor specification (requirements, design) | You need the ReAct refactor spec as a reference artifact |

## Quick Reference

### Agent Flow (ReAct Loop)

```
User Instruction (natural language)
    ↓
[agent_node] → LLM reasons about the task, selects ONE tool to call
    ↓
[tool_node] → Execute the tool, return result
    ↓
[agent_node] → LLM observes result, decides next step
    ↓
  ... (loop until LLM responds with text instead of a tool call) ...
    ↓
Final text response returned to user
```

### Key Design Patterns

- **True ReAct**: LLM reasons step-by-step, calling one tool at a time and observing results before deciding the next action
- **Native tool calling**: LLM selects tools via `bind_tools` — no JSON parsing or structured output extraction
- **Dynamic replanning**: If a search returns 0 results, the LLM adapts instead of blindly proceeding
- **Max iteration safety**: Configurable limit (default 10) prevents infinite loops
- **Mock-first development**: `MockWATIClient` with 50 contacts and 6 templates for offline dev
- **Interactive confirmation**: Each tool prompts for approval unless trust mode is on

### Module → File Quick Map

| To understand... | Start with... |
|---|---|
| How the ReAct loop works | `conductor/agent/react_graph.py` |
| Agent node (LLM reasoning) and tool node (execution) | `conductor/agent/react_nodes.py` |
| How tools are bound to the LLM | `conductor/agent/llm_factory.py` → `get_react_llm()` |
| What tools are available | `conductor/tools/registry.py` |
| How the WATI API is abstracted | `conductor/clients/base.py` → `mock.py` / `real.py` |
| How the CLI works (REPL + single-shot) | `conductor/cli.py` |
| Agent state (message-based) | `conductor/models/state.py` |
| LLM provider routing (DeepSeek/Claude/OpenAI) | `conductor/agent/llm_factory.py` |
| Environment config | `conductor/config.py` |

### Legacy Files (from Plan-then-Execute architecture)

These files are retained for reference but are **not wired into the current graph**:

| File | Was | Replaced By |
|---|---|---|
| `conductor/agent/graph.py` | 3-node plan-execute graph | `react_graph.py` |
| `conductor/agent/parser.py` | LLM intent extraction | Native tool calling in `react_nodes.py` |
| `conductor/agent/planner.py` | Rule-based plan generator | LLM reasoning in ReAct loop |
| `conductor/agent/nodes/` | parse, plan, validate, execute, clarify, response nodes | `react_nodes.py` (agent_node + tool_node) |
| `conductor/models/intent.py` | Task/Intent Pydantic models | Message-based state |
| `conductor/models/plan.py` | ExecutionPlan model | Message-based state |

### Tech Stack

- **Language**: Python 3.12
- **Agent Framework**: LangGraph (ReAct state machine)
- **LLM**: DeepSeek v4 Pro (default), Claude, OpenAI (swappable)
- **CLI**: Click + Rich
- **HTTP Client**: httpx (async)
- **Validation**: Pydantic v2
- **Dependencies**: LangChain, LangChain-Anthropic, LangChain-OpenAI
