# WATI Conductor

> AI agent that translates natural language into WATI WhatsApp API workflows using LangGraph ReAct pattern

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)

## Overview

WATI Conductor is an AI agent that translates natural language instructions into executable WATI WhatsApp API workflows. Built with LangGraph's **ReAct (Reasoning + Acting)** pattern, the LLM reasons step-by-step — calling one tool at a time, observing the result, and deciding what to do next.

## Why This Matters

Traditional API automation requires technical knowledge of endpoints, parameters, and error handling. WATI Conductor removes these barriers — business users describe what they want in plain English, and the agent handles the rest.

```bash
# Instead of writing API integration code:
You: Find all VIP contacts and send them the welcome_wati template
# Agent reasons through it step-by-step, adapting to results
```

## Quick Start

```bash
# Configure
cp .env.example .env
# Edit .env with your LLM API key (see Configuration)

# Start with Docker
docker compose up -d
docker compose exec wati-conductor python3 main.py

# Or run locally
poetry install
python -m conductor.cli
```

## How It Works — ReAct Loop

The agent uses a **think → act → observe** loop. Unlike plan-then-execute approaches, the LLM sees each tool result before deciding the next action:

```
User: "Find all VIP contacts and send them the welcome_wati template"

  Iteration 1 — Think: I need to find VIP contacts first
                Act:   search_contacts(tag="VIP")
                Observe: {contacts: [...], total: 10}

  Iteration 2 — Think: Found 10 contacts, now send the template
                Act:   send_template_message_batch(contacts=[...], template="welcome_wati")
                Observe: {sent: 10, failed: 0}

  Iteration 3 — Think: Both steps done, summarize
                Respond: "Found 10 VIP contacts and sent welcome_wati to all of them."
```

**Dynamic adaptation** — if a search returns 0 results, the agent tells you instead of blindly proceeding:

```
User: "Send welcome_wati to all premium contacts"

  Iteration 1 — Act: search_contacts(tag="premium")
                Observe: {contacts: [], total: 0}

  Iteration 2 — Think: No premium contacts found, inform user
                Respond: "No premium contacts found. Would you like to search by a different tag?"
```

## Usage

### Interactive Mode (Recommended)

```bash
docker compose exec wati-conductor python3 main.py

╭──────────────────────────────────────────────────────────────────╮
│ WATI Conductor - Interactive Mode                                │
│ Type your instructions naturally. Type 'quit' or 'exit' to stop. │
│ Type 'trust' to toggle auto-approval mode.                       │
╰──────────────────────────────────────────────────────────────────╯

You: trust
Trust mode enabled ✓

You: What templates do I have?
💬 Response:
You have 6 message templates available...
(1 iteration)

You: Find all VIP contacts and send them the welcome_wati template
💬 Response:
Found 10 VIP contacts and sent welcome_wati to all of them.
(3 iterations)

You: quit
Goodbye! 👋
```

### Single-Shot Mode

```bash
python -m conductor.cli "Find all VIP contacts"
python -m conductor.cli "Send welcome_wati to VIPs" --dry-run
python -m conductor.cli "Send welcome_wati to VIPs" --trust
python -m conductor.cli "Escalate 628123450000 to Support" --verbose
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Show first planned tool call without executing |
| `--trust` | Auto-approve all tool executions |
| `--verbose` | Enable debug logging |

### Human-in-the-Loop

By default, the agent asks for confirmation before each tool:

```
🔧 Tool: send_template_message_batch
   Args: {'contacts': [...], 'template_name': 'welcome_wati'}
   Execute? [Y/n/q]: Y
```

If you reject, the LLM observes the rejection and responds accordingly. Toggle trust mode with `trust` in the REPL or `--trust` flag.

## Configuration

All settings in `.env`:

```bash
# LLM — pick one (DeepSeek v4 Pro recommended for ReAct reasoning)
LLM_REACT_MODEL=deepseek-v4-pro
DEEPSEEK_API_KEY=sk-your-key

# Or use Claude / OpenAI
# LLM_REACT_MODEL=claude-3-5-sonnet-20241022
# ANTHROPIC_API_KEY=sk-ant-your-key
# LLM_REACT_MODEL=gpt-4o
# OPENAI_API_KEY=sk-your-key

# ReAct safety limit (default: 10 iterations per instruction)
MAX_REACT_ITERATIONS=10

# WATI API (mock mode works without credentials)
USE_MOCK=true
# USE_MOCK=false
# WATI_API_ENDPOINT=https://live-server-123.wati.io
# WATI_TOKEN=your_token
```

## Available Tools (16)

| Category | Tools |
|----------|-------|
| **Contacts** (8) | `search_contacts`, `get_contact_info`, `add_contact_tag`, `add_contact_tag_batch`, `remove_contact_tag`, `remove_contact_tag_batch`, `update_contact_attributes`, `update_contact_attributes_batch` |
| **Messages** (2) | `send_session_message`, `send_template_message_batch` |
| **Templates** (2) | `list_templates`, `get_template_details` |
| **Operators** (2) | `assign_operator`, `assign_team` |
| **Tickets** (2) | `create_ticket`, `resolve_ticket` |

## Architecture

```
agent_node ──(tool call)──► tool_node ──► agent_node  (loop)
    │
    └──(text response)──► END
```

Two-node LangGraph ReAct loop:

- **agent_node** — LLM reasons about current state, selects one tool or responds with text
- **tool_node** — Executes the tool (with optional user confirmation), returns result

The LLM uses native tool calling via `bind_tools` — no JSON parsing or structured output extraction.

### State

```python
class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]  # All conversation messages
    iteration_count: int       # Think-act-observe cycles
    trust_mode: bool           # Skip confirmations
    mode: Literal["execute", "dry-run"]
```

## Project Structure

```
wati-conductor/
├── conductor/
│   ├── agent/
│   │   ├── react_graph.py     # ReAct LangGraph loop
│   │   ├── react_nodes.py     # agent_node + tool_node
│   │   ├── llm_factory.py     # LLM provider routing + bind_tools
│   │   ├── parser.py          # (legacy) structured output parser
│   │   └── planner.py         # (legacy) rule-based planner
│   ├── models/
│   │   ├── state.py           # AgentState (message-based)
│   │   └── wati.py            # Contact, Template, Message models
│   ├── tools/                 # 16 LangChain @tool functions
│   ├── clients/               # Mock + Real WATI API clients
│   ├── cli.py                 # Click CLI (REPL + single-shot)
│   ├── config.py              # Pydantic settings from .env
│   └── history.py             # Conversation persistence (JSON)
├── docs/                      # Full documentation (mkdocs)
├── tests/
├── mock_data/                 # 50 contacts, 6 templates
├── Dockerfile
├── docker-compose.yaml
└── pyproject.toml
```

## Documentation

Full docs available via mkdocs:

```bash
cd mkdocs && docker compose -f docker-compose.docs.yml up -d
# Open http://localhost:9104
```

| Doc | Content |
|-----|---------|
| [Architecture](docs/architecture.md) | ReAct loop diagrams, state schema, data flow |
| [Components](docs/components.md) | Module breakdown — agent, tools, clients, models |
| [Status](docs/status.md) | What's implemented, what's planned |
| [Roadmap](docs/roadmap.md) | V4 vision, RAG knowledge base plan |
| [Setup](docs/setup.md) | Detailed configuration and troubleshooting |
| [Dev Notes](docs/dev-notes.md) | Build notes and design trade-offs |

## Development

```bash
poetry install

# Run tests
pytest tests/ -v

# Code quality
black conductor/ tests/
isort conductor/ tests/
mypy conductor/
ruff check conductor/
```

## Roadmap

- [x] ReAct agent with LangGraph (v3)
- [x] 16 LangChain tools
- [x] Mock WATI client (50 contacts, 6 templates)
- [x] Rich CLI with dry-run, trust mode
- [x] Docker deployment
- [x] Multi-turn conversations with history
- [x] Dynamic replanning and error reasoning
- [ ] Streaming responses
- [ ] RAG knowledge base (SOPs + guardrails)
- [ ] Real WATI API integration testing
- [ ] Web UI (chat interface)
- [ ] LangSmith tracing
- [ ] Session persistence (LangGraph checkpointer)

## License

MIT License
