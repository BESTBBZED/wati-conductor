# WATI Conductor

> AI agent that translates natural language into WATI WhatsApp API workflows using LangGraph ReAct pattern

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)

## Overview

WATI Conductor is an AI agent that translates natural language instructions into executable WATI WhatsApp API workflows. Built with LangGraph's ReAct (Reasoning + Acting) pattern, it enables non-technical users to automate WhatsApp business operations through conversational commands.

## 🎯 Key Feature: Multi-Task Intent System

The agent uses **LLM-powered task decomposition** to break complex instructions into executable tasks with automatic dependency resolution:

### Architecture

```python
# Simplified implementation (Plan-then-Execute pattern, NOT LangChain's AgentExecutor)
class WATIConductor:
    def process_input(self, user_input):
        # 1. LLM generates multi-task plan (single LLM call)
        intent = llm.parse_intent(user_input)  # Returns: Intent(tasks=[...])

        # 2. Show preview to user
        self.show_tasks(intent.tasks)

        # 3. Execute tasks sequentially (no LLM calls, just tool invocations)
        results = []
        for task in intent.tasks:
            if task.confidence < 0.7:
                continue  # Skip low-confidence tasks

            # Inject previous results as parameters
            params = self.resolve_params(task.params, results)

            # Execute tool
            result = tool_registry.get(task.tool).invoke(params)
            results.append({"task": task, "result": result})

        # 4. Generate natural language response (single LLM call)
        return llm.generate_response(user_input, results)
```

### Example: Multi-Task Execution

**Single complex instruction → Multiple tasks:**

```bash
You: Find all VIP contacts and send them the welcome_wati template

🤔 Agent Thinking:
Tasks: 2 (confidence: 0.92)
  1. Find VIP contacts (confidence: 0.95)
  2. Send welcome_wati template to VIP contacts (confidence: 0.90)

🔧 Tool Execution:
Plan has 2 task(s). Will execute one at a time.

Tool: search_contacts
Description: Find VIP contacts
Parameters: {'tag': 'VIP'}
Execute this tool? [Y/n/q]: Y

Tool: send_template_message_batch
Description: Send welcome_wati to VIP contacts
Parameters: {'contacts': '$task_0.contacts', 'template_name': 'welcome_wati'}
Execute this tool? [Y/n/q]: Y

✓ Completed

💬 Response:
Perfect! I found 10 VIP contacts and successfully sent the "welcome_wati"
template to all of them.
```

**Multiple independent tasks:**

```bash
You: Search VIP contacts, create a ticket to Sam about payment, and list templates

🤔 Agent Thinking:
Tasks: 3 (confidence: 0.93)
  1. Find VIP contacts (confidence: 0.95)
  2. Create ticket for Sam about payment (confidence: 0.90)
  3. List all templates (confidence: 0.95)

🔧 Tool Execution:
Tool: search_contacts
Tool: create_ticket
Tool: list_templates
✓ Auto-approved (trust mode)
✓ Completed

💬 Response:
All done! I found 10 VIP contacts, created ticket TKT-55618 for Sam about
payment, and listed 6 available templates.
```

### Task Dependency Resolution

Tasks can reference previous task results using `$task_N.field` syntax:

```json
{
  "tasks": [
    {
      "tool": "search_contacts",
      "params": {"tag": "VIP"},
      "confidence": 0.95
    },
    {
      "tool": "send_template_message_batch",
      "params": {
        "contacts": "$task_0.contacts",  // References task 0 result
        "template_name": "welcome_wati"
      },
      "confidence": 0.90
    }
  ]
}
```

### Trust Mode & Rejection Handling

**Trust Mode** (skip confirmations):
```bash
You: trust
Trust mode enabled ✓

You: Find all VIP contacts and send them the welcome_wati template
Tool: search_contacts
Tool: send_template_message_batch
✓ Auto-approved (trust mode)
✓ Completed
```

**Rejection Handling** (intelligent fallback):
```bash
Tool: send_template_message_batch
Execute this tool? [Y/n/q]: n
⚠ Tool execution rejected by user

💬 Response:
I understand you've chosen not to send the template. Without this tool, I cannot
send messages to your VIP contacts. You can manually send messages through the
WATI dashboard if needed.
```

## Features

- 🎯 **Multi-Task Intent**: LLM decomposes complex instructions into executable tasks
- 🔗 **Dependency Resolution**: Tasks can reference previous task results (`$task_N.field`)
- 🎚️ **Confidence Filtering**: Only executes tasks with confidence >= 0.7
- 🛡️ **Interactive Confirmation**: Step-by-step approval before each tool execution
- 🚀 **Trust Mode**: Skip confirmations for rapid execution
- 🧠 **ReAct Agent Pattern**: Reasoning (LLM planning) + Acting (tool execution) with LangGraph
- 💬 **Conversational Context**: Multi-turn conversations with automatic history tracking
- 🔄 **Interactive Mode**: Persistent chat session, no need to restart for each command
- 🔁 **Error Recovery**: Auto-retry on failures, stays alive for rephrasing
- 📊 **Rich CLI**: Professional output with clear separation of thinking vs. response
- 🔌 **Mock/Real Toggle**: Develop with mock API, deploy with real WATI client
- 🎫 **Ticket Management**: Create and resolve support tickets with staff assignment

## Quick Start

### 1. Build Docker Image

```bash
# Build with optimized caching (uses Tsinghua mirrors for China)
docker build -t wati-conductor:v1 .
```

### 2. Start Container

```bash
# Start with docker-compose
docker compose up -d

# Check status
docker compose ps
```

### 3. Run Interactive Mode

**Recommended for demos:**
```bash
docker compose exec wati-conductor python3 main.py

# Interactive session:
╭──────────────────────────────────────────────────────────────────╮
│ WATI Conductor - Interactive Mode                                │
│ Type your instructions naturally. Type 'quit' or 'exit' to stop. │
│ Type 'trust' to toggle auto-approval mode.                       │
╰──────────────────────────────────────────────────────────────────╯

You: trust
Trust mode enabled ✓

You: What templates do I have?
Tool: list_templates
✓ Auto-approved (trust mode)
✓ Completed

💬 Response:
You have 6 message templates available:
1. welcome_wati – A friendly welcome message (Marketing)
2. shopify_default_cod_confirm_order_v5 – Order confirmation (Marketing)
3. ecom_presales_oct – Pre-sale announcement (Marketing)
...

You: Find all VIP contacts and send them the welcome_wati template
Tool: search_contacts
Tool: get_template_details
Tool: send_template_message_batch
✓ Auto-approved (trust mode)
✓ Completed

💬 Response:
Done! I sent the welcome_wati template to all 10 VIP contacts successfully.

You: quit
Goodbye! 👋
```

### 4. Demo Commands

**One-line demo (automated):**
```bash
./demo.sh
```

**Quick demo sequence (copy-paste ready):**
```bash
# Start interactive mode
docker compose exec wati-conductor python3 main.py

# Then paste these commands one by one:
trust
What templates do I have?
Find all VIP contacts
Find all VIP contacts and send them the welcome_wati template
Create a ticket to Sam about login issue
quit
```
Invalid input. Please enter 'y' or 'n'. (2 attempts left)
Proceed? [Y/n]: y       ← Valid input
✓ Executing...

Proceed? [Y/n]: n       ← Cancel
❌ Cancelled by user
```

### 4. Understand the ReAct Flow

The agent follows a **Reasoning → Acting** loop with user confirmation:

```
User Input: "Send welcome template to new signups"
    ↓
[REASONING] Parse Intent
    → Intent: send_template_to_segment
    → Confidence: 0.95
    → Parameters: {tag: "new_signup", template: "welcome"}
    ↓
[REASONING] Generate Plan
    → Step 1: search_contacts(tag="new_signup")
    → Step 2: get_template_details(name="welcome")
    → Step 3: send_template_message_batch(contacts, template) 🔥
    ↓
[USER CONFIRMATION] ← Interactive prompt
    Proceed? [Y/n]: y
    ↓
[ACTING] Execute Tools
    → Tool Call: search_contacts → 15 contacts found
    → Tool Call: get_template_details → template params retrieved
    → Tool Call: send_template_message_batch → 14 sent, 1 failed
    ↓
[RESULT] Final Response
    → "I found 15 contacts and sent the welcome template. 14 succeeded, 1 failed (invalid phone)"
```

**Key Components:**
- **Parser Node**: LLM-powered intent extraction
## Example Commands

### Multi-Task Workflows (Demo Highlights)

**Single instruction → Multiple tasks:**
```bash
You: Find all VIP contacts and send them the welcome_wati template

# Agent decomposes into 2 tasks:
# Task 1: search_contacts(tag="VIP")
# Task 2: send_template_message_batch(contacts=$task_0.contacts, template_name="welcome_wati")
```

**Multiple independent tasks:**
```bash
You: Search VIP contacts, create a ticket to Sam about payment, and list templates

# Agent decomposes into 3 independent tasks:
# Task 1: search_contacts(tag="VIP")
# Task 2: create_ticket(subject="payment issue", assignee="Sam")
# Task 3: list_templates()
```

**Complex workflow with dependencies:**
```bash
You: Update 628123450000 to premium and send them welcome template

# Agent decomposes into 3 tasks with dependencies:
# Task 1: update_contact_attributes(phone="628123450000", attributes={tier: "premium"})
# Task 2: get_template_details(template_name="welcome_wati")
# Task 3: send_template_message_batch(contacts=[...], template=$task_1.result)
```

### Contact Management

**Search contacts:**
```bash
You: Find all VIP contacts
You: Show me contacts from Jakarta
You: List all premium members
```

**Get contact details:**
```bash
You: What is 628123450000, is he a premium?
You: Show me details for 6281234567890
```

**Update contact attributes:**
```bash
You: Update contact 6281234567890 tier to premium
You: Degrade 6281234567890 to normal level
You: Set 628123450000 city to Jakarta
```

### Template Operations

**List templates:**
```bash
You: What templates do I have?
You: Show me all available templates
```

**Send templates:**
```bash
You: Send renewal_reminder template to all VIP contacts
You: Send flash_sale to all Jakarta contacts
You: Send appointment_reminder to 628123450000
```

### Ticket Management

**Create tickets:**
```bash
You: Create a ticket for 628123450000 about payment issue
You: Create a ticket to Sam about login issue
You: Create a ticket for 628123450005 about network error, reporter is customer_service
```

**Resolve tickets:**
```bash
You: Resolve ticket TKT-12345
You: Close ticket TKT-67890 with resolution "Fixed database connection"
```

### Conversation Management

**Escalate conversations:**
```bash
You: Escalate 6281234567890 to Support
You: Escalate 628123450000 to premium support team
```

**Assign operators:**
```bash
You: Assign 628123450000 to operator John
You: Assign conversation 6281234567890 to team Support
```

## Configuration

Create `.env` file (or use environment variables in docker-compose.yaml):

```bash
# LLM Configuration (for intent parsing & planning)
LLM_PARSE_MODEL=deepseek-chat          # or claude-3-5-sonnet-20241022
DEEPSEEK_API_KEY=your-key              # or ANTHROPIC_API_KEY
OPENAI_API_KEY=your-key                # optional

# WATI API
USE_MOCK=true                          # Set to false for real WATI API
WATI_API_ENDPOINT=https://live-server-123.wati.io  # Your WATI server
WATI_TOKEN=your_api_token              # Your WATI API token

# Ticket Management
TICKET_REPORTER=Zachary                # Default reporter name for tickets

# Logging
LOG_LEVEL=INFO
```

### Using Real WATI API

To connect to your actual WATI account:

1. Set `USE_MOCK=false` in `.env`
2. Configure `WATI_API_ENDPOINT` and `WATI_TOKEN`
3. Restart the container: `docker compose down && docker compose up -d`

See [docs/WATI_API_SETUP.md](docs/WATI_API_SETUP.md) for detailed setup instructions.

**Note**: Ticket management is always stored locally (not via WATI API).

## Interactive Mode

The interactive mode provides a persistent chat session where you can have multi-turn conversations without restarting the CLI.

### Starting Interactive Mode

```bash
# Inside container
docker compose exec -it wati-conductor python chat.py

# Or add to your shell alias
alias wati="docker compose -f /path/to/wati-conductor/docker-compose.yaml exec -it wati-conductor python chat.py"
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `trust` | Toggle auto-approval mode (no confirmation prompts) |
| `quit` / `exit` / `q` | Exit the interactive session |
| Ctrl+C | Interrupt current request (session stays alive) |

### Example Session

```bash
╭──────────────────────────────────────────────────────╮
│ WATI Conductor - Interactive Mode                    │
│ Type your instructions naturally.                    │
│ Type 'quit' to stop. Type 'trust' to auto-approve.  │
╰──────────────────────────────────────────────────────╯

You: trust
Trust mode enabled ✓

You: What templates do I have?
💬 Response:
You have 5 message templates available:
- renewal_reminder (MARKETING)
- flash_sale (MARKETING)
- vip_exclusive (MARKETING)
- order_confirmation (UTILITY)
- appointment_reminder (UTILITY)

You: Create a ticket to Sam about database connection error
💬 Response:
I've created ticket TKT-45131 for Sam about the database connection error.
The ticket is currently open with medium priority.

You: List all VIP contacts
💬 Response:
Found 10 VIP contacts from Jakarta, Surabaya, and Bandung...

You: quit
Goodbye! 👋
```

### Error Handling

If a request fails, the agent will automatically retry (up to 2 times) and stay alive:

```bash
You: Some unclear request
⚠ Error occurred: Failed to parse intent
Retrying... (attempt 1/2)

❌ Failed after 2 retries
Something went wrong. Please try rephrasing your request.

You: [You can continue with a new request]
```

## Usage Examples

### Interactive Mode (Recommended)

The interactive mode provides the best experience with persistent sessions and context:

```bash
$ docker compose exec -it wati-conductor python chat.py

You: trust
Trust mode enabled ✓

You: What is 628123450000?
💬 Response:
The number 628123450000 belongs to Customer 0. They're a VIP contact from Jakarta,
and their account is set as premium.

You: I want to degrade him to normal
💬 Response:
Done! I've successfully downgraded him from premium to normal tier.

You: What's his tier now?
💬 Response:
His tier is now set to normal.

You: Create a ticket to Sam about login issue
💬 Response:
I've created ticket TKT-45131 and assigned it to Sam...

You: quit
Goodbye! 👋
```

**Conversation history is stored in:** `./history/current_session.json`

### Single Command Mode

For one-off commands or scripting:

```bash
# With confirmation prompt
docker compose exec wati-conductor python -m conductor.cli \
  "Find all VIP contacts"

# Auto-approve (for scripts)
docker compose exec wati-conductor python -m conductor.cli \
  "Find all VIP contacts" --trust

# Preview only (dry-run)
docker compose exec wati-conductor python -m conductor.cli \
  "Send flash_sale template to Jakarta contacts" --dry-run

# Verbose output
docker compose exec wati-conductor python -m conductor.cli \
  "Add escalated tag to contact 6281234567890" --verbose

```

**Get Contact Info:**
```bash
docker compose exec wati-conductor python -m conductor.cli \
  "Show me details for 6281234567890"

# Interactive confirmation before fetching
```

### Real-World Scenarios

**1. VIP Customer Outreach**
```bash
# Preview the plan
docker compose exec wati-conductor python -m conductor.cli \
  "Find all VIP contacts and send them renewal_reminder template" --dry-run

# Execute with confirmation
docker compose exec wati-conductor python -m conductor.cli \
  "Find all VIP contacts and send them renewal_reminder template"

# Or auto-approve
docker compose exec wati-conductor python -m conductor.cli \
  "Find all VIP contacts and send them renewal_reminder template" --trust
```

**2. Segmented Campaign**
```bash
docker compose exec wati-conductor python -m conductor.cli \
  "Send flash_sale template to all contacts in Jakarta"
```

**3. Contact Attribute Update**
```bash
docker compose exec wati-conductor python -m conductor.cli \
  "Update contact 628123450000 tier to premium"
```

**4. Support Escalation**
```bash
docker compose exec wati-conductor python -m conductor.cli \
  "Escalate contact 628123450000 to Support team and add escalated tag"
```

**5. Bulk Contact Discovery**
```bash
docker compose exec wati-conductor python -m conductor.cli \
  "Find all contacts tagged new_signup and tell me who they are" --verbose
```

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| (none) | Interactive mode - prompts for confirmation | `python -m conductor.cli "..."` |
| `--trust` | Auto-approve all tool executions | `python -m conductor.cli "..." --trust` |
| `--dry-run` | Preview plan without executing | `python -m conductor.cli "..." --dry-run` |
| `--verbose` | Show detailed execution plan table | `python -m conductor.cli "..." --verbose` |

### Interactive Confirmation Behavior

**Default Mode (Safe):**
- Shows execution plan
- Prompts: `Proceed? [Y/n]:`
- Press **Enter** or type `y`/`yes` → Execute
- Type `n`/`no` → Cancel
- Invalid input → 3 attempts, then auto-cancel

**Trust Mode (Convenience):**
- Use `--trust` flag
- Skips confirmation prompt
- Executes immediately after planning
- Still shows tool execution progress

**Dry-Run Mode (Preview):**
- Use `--dry-run` flag
- Shows plan only
- Never executes tools
- No confirmation needed

## Architecture

### Multi-Task Intent System

The agent uses a **simplified LLM-first architecture** where the LLM directly generates executable tasks:

```
┌─────────────────────────────────────────────────────────────┐
│                     LangGraph State Machine                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Parse Node]                                               │
│    ↓ (LLM: decompose instruction into tasks)               │
│    Intent: {                                                │
│      tasks: [                                               │
│        {tool: "search_contacts", params: {...}, conf: 0.95},│
│        {tool: "send_template", params: {...}, conf: 0.90}   │
│      ],                                                     │
│      overall_confidence: 0.92                               │
│    }                                                        │
│                                                             │
│  [Execute Node]                                             │
│    ↓ (for each task with confidence >= 0.7)                │
│    ├─ Resolve params ($task_N.field references)            │
│    ├─ User confirmation (unless trust mode)                │
│    └─ Execute tool → append result                         │
│                                                             │
│  [Response Node]                                            │
│    ↓ (LLM: generate natural language response)             │
│    Final Response                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Implementation Details

**1. Task Decomposition (Parser)**
```python
# conductor/agent/parser.py
async def parse_intent(instruction: str) -> Intent:
    llm = get_llm(temperature=0.0)
    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),  # Examples of task decomposition
        HumanMessage(content=f"User: {instruction}")
    ])
    intent = Intent(**extract_json(response.content))
    # Filter by confidence
    intent.tasks = [t for t in intent.tasks if t.confidence >= 0.7]
    return intent
```

**2. Dependency Resolution (Executor)**
```python
# conductor/agent/nodes/execute.py
def _resolve_params(params: dict, prior_results: list) -> dict:
    for key, value in params.items():
        if isinstance(value, str) and value.startswith("$task_"):
            # "$task_0.contacts" → prior_results[0]["result"]["contacts"]
            parts = value.split(".")
            task_idx = int(parts[0].replace("$task_", ""))
            result = prior_results[task_idx]["result"]
            for field in parts[1:]:
                result = result[field]
            params[key] = result
    return params
```

**3. Interactive Confirmation**
```python
# conductor/agent/nodes/execute.py
for task in intent.tasks:
    params = _resolve_params(task.params, results)

    if not trust_mode:
        print(f"Tool: {task.tool}")
        print(f"Description: {task.description}")
        print(f"Parameters: {params}")
        response = input("Execute this tool? [Y/n/q]: ")
        if response == 'n':
            return {"user_rejected": True, "rejected_tool": task.tool}

    result = await tool.ainvoke(params)
    results.append({"task": task, "result": result})
```

### Available Tools

All tools are LangChain `@tool` decorated functions:

**Contacts:**
- `search_contacts(tag, attribute_name, attribute_value)` - Search contacts
- `get_contact_info(whatsapp_number)` - Get contact details
- `update_contact_attributes(whatsapp_number, attributes)` - Update custom attributes

**Messages:**
- `send_session_message(whatsapp_number, message_text)` - Send text message
- `send_template_message_batch(contacts, template_name, params)` - Bulk send template (🔥 destructive)

**Templates:**
- `get_template_details(template_name)` - Get template parameters
- `list_templates()` - List all available templates

**Tickets:**
- `create_ticket(subject, assignee, priority)` - Create support ticket
- `resolve_ticket(ticket_id, resolution)` - Resolve ticket

**Operators:**
- `assign_operator(whatsapp_number, team_name)` - Assign conversation to team

## Project Structure

```
wati-conductor/
├── conductor/
│   ├── agent.py              # LangGraph agent graph definition
│   ├── cli.py                # Click CLI interface
│   ├── config.py             # Pydantic settings
│   ├── models/               # Pydantic models (Intent, Plan, State)
│   ├── clients/              # WATI API clients (mock/real)
│   │   ├── factory.py
│   │   ├── mock.py
│   │   └── real.py
│   └── tools/                # LangChain tools
│       ├── contacts.py
│       ├── messages.py
│       ├── templates.py
│       └── operators.py
├── tests/                    # Pytest tests
├── Dockerfile                # Optimized multi-layer build
├── docker-compose.yaml       # Container orchestration
├── pyproject.toml            # Poetry dependencies
└── README.md
```

## Development

### Local Setup (without Docker)

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run CLI
poetry run python -m conductor.cli "your instruction"
```

### Code Quality

```bash
# Format
poetry run black conductor/ tests/
poetry run isort conductor/ tests/

# Type check
poetry run mypy conductor/

# Lint
poetry run ruff check conductor/
```

## Troubleshooting

**Q: CLI shows `TyperArgument.make_metavar()` error**
A: This is a typer 0.12.5 + click 8.3.2 compatibility issue. Fixed by using click directly. Rebuild image: `docker build -t wati-conductor:v1 .`

**Q: No logs in `docker compose logs`**
A: Container runs in interactive mode (`command: /bin/bash`). Logs appear when you execute commands via `docker compose exec`.

**Q: How to use real WATI API?**
A: Set `USE_MOCK=false` in `.env` and provide `WATI_TENANT_ID` and `WATI_TOKEN`.

**Q: How to see tool execution details?**
A: Use `--verbose` flag to see detailed execution plan table with tool dependencies.

**Q: How to skip confirmation prompts?**
A: Use `--trust` flag to auto-approve all tool executions.

**Q: What inputs are accepted for confirmation?**
A:
- **Yes**: `y`, `yes`, `Y`, `YES`, `YeS`, or just press Enter (default)
- **No**: `n`, `no`, `N`, `NO`
- **Invalid**: You get 3 attempts before auto-cancel

**Q: Can I preview actions without executing?**
A: Yes, use `--dry-run` flag to see the execution plan without running tools.

**Q: How do I know which tools will be called?**
A: The CLI always shows the execution plan before asking for confirmation. Look for the "🤔 Agent Thinking" section.

**Q: What does the 🔥 symbol mean?**
A: It indicates a destructive action (e.g., sending messages, deleting data) that requires extra caution.

## Roadmap

- [x] ReAct agent with LangGraph
- [x] LangChain tool integration
- [x] Mock WATI client
- [x] Rich CLI with dry-run
- [x] Docker deployment
- [x] Multi-turn conversations with history tracking
- [x] Natural language response generation
- [ ] Real WATI API client
- [ ] Streaming responses
- [ ] Web UI (chat interface)
- [ ] LangSmith tracing

## License

MIT License

## Acknowledgments

- **LangChain/LangGraph**: ReAct agent framework
- **WATI**: WhatsApp Business API platform
- **Anthropic & DeepSeek**: LLM providers
- **Rich**: Beautiful CLI output
