# Components

## Agent (`conductor/agent/`)

The orchestration core. Contains the ReAct LangGraph loop, agent/tool nodes, and LLM provider factory.

### ReAct Graph (`agent/react_graph.py`)

Defines the 2-node ReAct LangGraph loop: `agent_node` ↔ `tool_node`.

- `_should_continue(state)` — Routing function: if the LLM returned a tool call → `tool_node`; if it returned text or dry-run mode → `END`
- `create_agent_graph()` — Builds and compiles the `StateGraph(AgentState)` with the ReAct loop

### ReAct Nodes (`agent/react_nodes.py`)

The two nodes that form the ReAct loop:

**`agent_node`** — LLM reasoning node:

- Invokes the LLM with the full message history (system prompt + user message + prior tool calls/results)
- LLM either returns a tool call (continue loop) or a text response (terminate)
- Enforces max iteration safety — if `iteration_count >= max_react_iterations`, forces a text summary
- Injects system prompt with recent conversation context via `get_recent_context()`

**`tool_node`** — Tool execution node:

- Receives the tool call from the last `AIMessage`
- In normal mode: prints tool details and prompts user for confirmation (`[Y/n/q]`)
- In trust mode: auto-executes without prompting
- If user rejects: returns `ToolMessage("User rejected this tool execution.")` — the LLM observes this and responds accordingly
- On error: catches exceptions and returns error as `ToolMessage` — the LLM can reason about the error

**System prompt** — concise guidelines for the ReAct agent:

- Execute ONE tool at a time, observe results, then decide next step
- Adapt to empty results (don't proceed with dependent actions)
- Reason about errors and suggest alternatives
- Distinguish read-only queries from destructive actions

### LLM Factory (`agent/llm_factory.py`)

Provider-agnostic LLM instantiation with tool binding.

- `get_react_llm(tools)` — Returns a configured LLM with all tools bound via `bind_tools()`. Uses `llm_react_model` setting (default: `deepseek-v4-pro`)
- `get_llm(temperature)` — Standalone LLM instance for legacy/utility usage
- `_build_llm(model_name, temperature)` — Internal factory that routes to DeepSeek, Anthropic, or OpenAI based on model name
- DeepSeek v4 models use `extra_body={"thinking": {"type": "disabled"}}` to avoid conflicts with temperature and reduce latency

### Legacy Files (not wired into current graph)

These files remain in the codebase for reference but are **not used** by the ReAct architecture:

| File | Original Purpose | Replaced By |
|---|---|---|
| `agent/graph.py` | 3-node plan-execute graph | `react_graph.py` |
| `agent/parser.py` | LLM intent extraction via structured output | Native tool calling in `react_nodes.py` |
| `agent/planner.py` | Rule-based plan generator (v1) | LLM reasoning in ReAct loop |
| `agent/nodes/parse.py` | Thin wrapper for parser | `agent_node` in `react_nodes.py` |
| `agent/nodes/plan.py` | Plan generation node (v1) | `agent_node` |
| `agent/nodes/validate.py` | Parameter validation node (v1) | Not needed — LLM validates via reasoning |
| `agent/nodes/execute.py` | Sequential tool executor with `$task_N` resolution | `tool_node` in `react_nodes.py` |
| `agent/nodes/clarify.py` | Clarification node (v1) | LLM handles clarification naturally |
| `agent/nodes/response.py` | LLM response generation | `agent_node` final text response |

## Models (`conductor/models/`)

Pydantic models shared across the agent.

### State (`models/state.py`)

The primary state model for the ReAct graph:

```python
class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]  # All conversation messages
    iteration_count: int          # Think-act-observe cycles completed
    trust_mode: bool              # Skip per-tool confirmation prompts
    mode: Literal["execute", "dry-run"]  # Execution mode
    user_rejected: bool           # User declined a tool execution
    rejected_tool: str            # Which tool was declined
```

Key design: the `messages` field uses LangGraph's `add_messages` reducer, which automatically appends new messages to the list. All data flows through messages — `SystemMessage`, `HumanMessage`, `AIMessage` (with optional `tool_calls`), and `ToolMessage` (tool results).

### WATI (`models/wati.py`)

Domain models for WATI API objects:

- `Contact` — WhatsApp contact with name, number, tags, custom params, timestamps
- `Template` — Message template with name, category, status, components, language
- `Message` — Chat message with direction, type, text, timestamp, status

### Legacy Models (retained for reference)

| File | Original Purpose | Status |
|---|---|---|
| `models/intent.py` | `Task`, `Entity`, `Intent` models for structured output parsing | Unused — ReAct uses native tool calling |
| `models/plan.py` | `APICall`, `ExecutionPlan` models for rule-based planner | Unused — ReAct uses LLM reasoning |

## Tools (`conductor/tools/`)

LangChain `@tool` decorated async functions. Each tool calls the WATI client (mock or real) via `get_wati_client()`. **No changes from the previous architecture** — all 16 tools work unchanged with the ReAct pattern.

### Registry (`tools/registry.py`)

Central tool management:

- `get_all_tools()` — Returns all 16 tool objects (used by `get_react_llm()` to bind tools to the LLM)
- `get_tool(name)` — Lookup by name (used by `tool_node` to execute the selected tool)
- `get_tool_schemas()` — JSON schemas for all tools
- `get_tools_prompt()` — Auto-generated tool descriptions (legacy, not used by ReAct)

### Contact Tools (`tools/contacts.py`) — 8 tools

| Tool | Description |
|---|---|
| `search_contacts` | Find contacts by tag, attribute name/value, or phone number |
| `get_contact_info` | Get detailed info for a single contact by phone number |
| `add_contact_tag` | Add a tag to one contact |
| `add_contact_tag_batch` | Add a tag to multiple contacts (with optional `filter_condition`) |
| `remove_contact_tag` | Remove a tag from one contact |
| `remove_contact_tag_batch` | Remove a tag from multiple contacts |
| `update_contact_attributes` | Update attributes for one contact |
| `update_contact_attributes_batch` | Update attributes for multiple contacts (with optional `filter_condition`) |

### Message Tools (`tools/messages.py`) — 2 tools

| Tool | Description |
|---|---|
| `send_session_message` | Send a text message to one contact (within 24h window) |
| `send_template_message_batch` | Send a template message to multiple contacts |

### Template Tools (`tools/templates.py`) — 2 tools

| Tool | Description |
|---|---|
| `list_templates` | List all available message templates |
| `get_template_details` | Get details for a specific template by name |

### Operator Tools (`tools/operators.py`) — 2 tools

| Tool | Description |
|---|---|
| `assign_operator` | Assign a conversation to an operator by email |
| `assign_team` | Assign a conversation to a team |

### Ticket Tools (`tools/tickets.py`) — 2 tools

| Tool | Description |
|---|---|
| `create_ticket` | Create a support ticket (stored locally, not via WATI API) |
| `resolve_ticket` | Resolve an existing ticket |

## Clients (`conductor/clients/`)

Abstraction layer for the WATI API. Uses a Protocol class so mock and real clients are interchangeable. **No changes from the previous architecture.**

### Base (`clients/base.py`)

`WATIClient` Protocol defining the interface: `get_contacts`, `get_contact_info`, `add_tag`, `remove_tag`, `update_contact_attributes`, `send_session_message`, `get_message_templates`, `send_template_message`, `assign_operator`, `assign_team`.

### Mock (`clients/mock.py`)

Full mock implementation with:

- 50 generated contacts across 5 cities (Tokyo, Beijing, Jakarta, Singapore, Bangkok)
- 6 message templates (welcome, order confirmation, marketing, etc.)
- Local file persistence for tickets (`mock_data/tickets.json`)
- Realistic response structures matching the real WATI API

### Real (`clients/real.py`)

httpx-based async client for the actual WATI REST API. Implements all Protocol methods with proper authentication headers (`Authorization: Bearer {token}`).

### Factory (`clients/factory.py`)

`get_wati_client()` — Returns `MockWATIClient` or `RealWATIClient` based on `settings.use_mock`.

## CLI (`conductor/cli.py`)

Dual-mode command-line interface built with Click and Rich. Simplified in the ReAct refactor — the graph now handles the full loop, so the CLI just invokes it once.

**Interactive mode** (no args): REPL loop with `Prompt.ask()`, trust mode toggle, dual Ctrl+C handling (first interrupts current, second exits).

**Single-shot mode** (with instruction arg): `python -m conductor.cli "instruction"` with `--dry-run`, `--verbose`, `--trust` flags.

Both modes use `run_instruction()` which:

1. Builds initial state with `HumanMessage`, trust/mode settings
2. Invokes the ReAct graph (which loops internally until done)
3. Extracts the final text response from the last `AIMessage`
4. Saves the turn to conversation history
5. Displays iteration count for cost awareness

## Supporting Modules

### Config (`conductor/config.py`)

Pydantic `BaseSettings` loaded from `.env`. Key settings:

| Setting | Default | Purpose |
|---|---|---|
| `llm_react_model` | `deepseek-v4-pro` | Model for the ReAct agent loop |
| `max_react_iterations` | `10` | Safety limit on think-act-observe cycles |
| `use_mock` | `true` | Use mock WATI client |
| `llm_temperature` | `0.0` | LLM sampling temperature |
| `deepseek_api_key` | — | DeepSeek API key |
| `anthropic_api_key` | — | Anthropic API key |
| `openai_api_key` | — | OpenAI API key |
| `wati_api_endpoint` | — | Real WATI API URL |
| `wati_token` | — | Real WATI API token |

Legacy settings (`llm_parse_model`, `llm_plan_model`, `llm_clarify_model`) are retained for backward compatibility but unused by the ReAct graph.

### History (`conductor/history.py`)

JSON-based conversation persistence:

- `save_conversation_turn()` — Appends `{timestamp, human, ai}` to session file
- `get_recent_context(max_turns=2)` — Returns last N turns as text for system prompt context
- Strips emoji/non-ASCII to avoid serialization issues with some LLM APIs
- Only the final text response is saved — intermediate tool calls are ephemeral within the ReAct loop

### Staff Data (`conductor/data/staff.py`)

Static staff directory used by operator assignment tools.
