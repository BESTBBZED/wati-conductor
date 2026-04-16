# WATI Conductor Documentation

> **For AI Assistants**: This file is the primary entry point for understanding the WATI Conductor codebase. Read this file first — it contains enough metadata to determine which detailed files to consult for specific questions.

## System Summary

WATI Conductor is a Python AI agent that translates natural language instructions into WhatsApp business automation workflows via the WATI API. It uses LangGraph for orchestration, LLM-powered intent parsing for multi-task decomposition, and a confidence-based execution pipeline with interactive user confirmation.

## Documentation Files

| File | Purpose | Consult When... |
|---|---|---|
| [architecture.md](architecture.md) | System architecture diagrams, LangGraph flow, data flow between nodes | You need to understand how the agent processes instructions end-to-end |
| [components.md](components.md) | Detailed breakdown of each module — agent, tools, clients, models, CLI | You need to understand what a specific module does or which files to modify |
| [status.md](status.md) | Implemented vs planned features, tool inventory, what works and what doesn't | You need to know what's done, what's missing, or what to build next |
| [roadmap.md](roadmap.md) | V2 vision, interactive REPL refactor plan, feature priorities | You're planning future work or want to understand v1→v2 evolution |
| [setup.md](setup.md) | Quick start, environment config, Docker setup, switching to real WATI API | You need to run the project or configure it for a new environment |
| [dev-notes.md](dev-notes.md) | Build notes, problem framing, design trade-offs, demo script | You want context on why decisions were made or need to run a demo |
| [specs/v1/](specs/v1/) | Original v1 specification (requirements, design, tasks) | You need the original spec as a reference artifact |

## Quick Reference

### Agent Flow (3 nodes)

```
User Instruction (natural language)
    ↓
[parse_intent] → LLM extracts tasks with tools + params (Intent model)
    ↓
[execute_plan] → Run tools sequentially, resolve $task_N dependencies
    ↓
[generate_response] → LLM summarises results as conversational reply
```

### Key Design Patterns

- **LLM-first parsing**: One LLM call decomposes instructions into executable tasks — no rule-based planner
- **Confidence filtering**: Tasks below 0.7 confidence are dropped before execution
- **Inter-task references**: `$task_0.contacts` passes output from task 0 to task 1
- **Mock-first development**: `MockWATIClient` with 50 contacts and 6 templates for offline dev
- **Interactive confirmation**: Each tool prompts for approval unless trust mode is on

### Module → File Quick Map

| To understand... | Start with... |
|---|---|
| How instructions become tasks | `conductor/agent/parser.py` |
| How the LangGraph state machine works | `conductor/agent/graph.py` |
| How tools are executed with dependency resolution | `conductor/agent/nodes/execute.py` |
| How results become conversational responses | `conductor/agent/nodes/response.py` |
| What tools are available | `conductor/tools/registry.py` |
| How the WATI API is abstracted | `conductor/clients/base.py` → `mock.py` / `real.py` |
| How the CLI works (REPL + single-shot) | `conductor/cli.py` |
| All data models (Intent, Task, AgentState) | `conductor/models/` |
| LLM provider routing (DeepSeek/Claude/OpenAI) | `conductor/agent/llm_factory.py` |
| Environment config | `conductor/config.py` |

### Tech Stack

- **Language**: Python 3.12
- **Agent Framework**: LangGraph (state machine)
- **LLM**: DeepSeek (default), Claude, OpenAI (swappable)
- **CLI**: Click + Rich
- **HTTP Client**: httpx (async)
- **Validation**: Pydantic v2
- **Dependencies**: LangChain, LangChain-Anthropic, LangChain-OpenAI
