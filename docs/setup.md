# Setup

Quick start guide for running WATI Conductor locally.

## Prerequisites

- Python 3.12+
- Docker and Docker Compose (recommended)
- An LLM API key (DeepSeek, Anthropic, or OpenAI)

## Quick Start (Docker)

```bash
# Clone and enter project
cd wati-conductor

# Configure environment
cp .env.example .env
# Edit .env with your API key (see Configuration below)

# Start
docker compose up -d

# Run interactive mode
docker compose exec wati-conductor python3 main.py

# Or run a single command
docker compose exec wati-conductor python -m conductor.cli "Find all VIP contacts"
```

## Quick Start (Local)

```bash
cd wati-conductor

# Install dependencies
poetry install
# or
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API key

# Run interactive mode
python -m conductor.cli

# Or single command
python -m conductor.cli "Find all VIP contacts"
```

## Configuration

All settings are in `.env`. Key variables:

### LLM (required — pick one)

```bash
# DeepSeek v4 Pro (default — strong reasoning for ReAct loop)
LLM_REACT_MODEL=deepseek-v4-pro
DEEPSEEK_API_KEY=sk-your-key

# DeepSeek v4 Flash (cheaper, faster, less reliable for complex multi-step)
LLM_REACT_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=sk-your-key

# Claude (Anthropic)
LLM_REACT_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key

# OpenAI
LLM_REACT_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key
```

### ReAct Agent Settings

```bash
# Maximum think-act-observe cycles per instruction (default: 10)
MAX_REACT_ITERATIONS=10

# LLM temperature (default: 0.0 — deterministic for tool calling)
LLM_TEMPERATURE=0.0

# Max tokens per LLM response
LLM_MAX_TOKENS=4096
```

### WATI API (optional — mock mode works without it)

```bash
# Mock mode (default) — no real API needed
USE_MOCK=true

# Real mode — requires WATI credentials
USE_MOCK=false
WATI_API_ENDPOINT=https://live-server-123.wati.io
WATI_TOKEN=your_actual_api_token_here
```

### Other Settings

```bash
# Rate limiting (for real API)
MAX_REQUESTS_PER_SECOND=10
MAX_CONCURRENT_REQUESTS=5
```

## CLI Usage

### Interactive Mode (no args)

```bash
python -m conductor.cli
```

Commands inside the REPL:

- Type any instruction in natural language
- `trust` — Toggle auto-approval mode (skip confirmations)
- `quit` / `exit` / `q` — Exit
- Ctrl+C once — Cancel current, Ctrl+C twice — Exit

### Single-Shot Mode

```bash
python -m conductor.cli "Find all VIP contacts"
python -m conductor.cli "Send renewal_reminder to VIP contacts" --dry-run
python -m conductor.cli "Escalate 6281234567890 to Support" --verbose
python -m conductor.cli "Send template to VIPs" --trust
```

Flags:

- `--dry-run` — Show the first planned tool call without executing
- `--verbose` / `-v` — Show detailed output (debug logging)
- `--trust` — Auto-approve all tool executions

### Python API

```python
from langchain_core.messages import HumanMessage
from conductor.agent import create_agent_graph

agent = create_agent_graph()

result = await agent.ainvoke({
    "messages": [HumanMessage(content="Find all VIP contacts")],
    "iteration_count": 0,
    "trust_mode": True,
    "mode": "execute",
})

# The last message is the agent's final text response
final_response = result["messages"][-1].content
print(final_response)
```

## Switching to Real WATI API

1. Get credentials from your WATI console (API endpoint + token)
2. Update `.env`:
   ```bash
   USE_MOCK=false
   WATI_API_ENDPOINT=https://live-server-123.wati.io
   WATI_TOKEN=your_token
   ```
3. Restart: `docker compose down && docker compose up -d`
4. Test: `docker compose exec wati-conductor python -m conductor.cli "List my templates" --trust`

### Supported WATI API Endpoints

| Function | Endpoint | Method |
|---|---|---|
| Send template message | `/api/v1/sendTemplateMessage` | POST |
| Send session message | `/api/v1/sendSessionMessage/{phone}` | POST |
| Get contacts | `/api/v1/getContacts` | GET |
| Get contact details | `/api/v1/getContact/{phone}` | GET |
| Add tag | `/api/v1/addTag` | POST |
| Remove tag | `/api/v1/removeTag` | DELETE |
| Update contact attributes | `/api/v1/updateContactAttributes/{phone}` | PUT |
| Get message templates | `/api/v1/getMessageTemplates` | GET |
| Assign operator | `/api/v1/assignOperator` | POST |

### Local-Only Features

These work in both mock and real mode but don't use the WATI API:

- **Ticket management**: Stored in `./mock_data/tickets.json`
- **Conversation history**: Stored in `./history/current_session.json`

## Running Tests

```bash
# Legacy unit tests (v1/v2 — may need updates for ReAct)
pytest tests/test_planner.py -v
pytest tests/test_parser.py -v

# Manual tests (require LLM API key)
python tests/manual_test_parser.py
python tests/manual_test_flow.py
python tests/manual_test_graph.py
```

## Troubleshooting

**"API key not set"**: Make sure your `.env` has the correct key for your chosen model. DeepSeek needs `DEEPSEEK_API_KEY`, Claude needs `ANTHROPIC_API_KEY`.

**"Tool not found"**: The LLM generated a tool name that doesn't exist in the registry. This usually means the instruction was ambiguous. Try rephrasing.

**Agent loops too many times**: The ReAct loop has a safety limit (`MAX_REACT_ITERATIONS`, default 10). If the agent hits this limit, it returns a summary of what was accomplished. You can increase the limit in `.env` if needed.

**Agent repeats old tasks**: Conversation history pollution. Restart the session or clear history at `./history/current_session.json`.

**Unicode/emoji errors**: Known issue with some LLM APIs. The history module strips non-ASCII characters automatically, but if you see encoding errors, check that your terminal supports UTF-8.
