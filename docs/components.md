# Components

## Agent (`conductor/agent/`)

The orchestration core. Contains the LangGraph state machine, LLM-powered parser, graph nodes, and LLM provider factory.

### Graph (`agent/graph.py`)

Defines the 3-node LangGraph state machine: `parse_intent` → `execute_plan` → `generate_response`.

- `route_after_parse()` — Conditional edge: skips execution when confidence < 0.7 or mode is dry-run
- `create_agent_graph()` — Builds and compiles the `StateGraph(AgentState)`

### Parser (`agent/parser.py`)

LLM-powered intent extraction. Sends the user instruction plus tool schemas to the LLM and gets back a structured `Intent` with tasks.

- `parse_intent(instruction)` — Main entry point. Uses `with_structured_output(Intent)` for guaranteed Pydantic validation
- `_build_system_prompt()` — Injects current tool signatures from the registry into the system prompt
- `extract_json(text)` — Fallback JSON extraction from LLM output (strips markdown fences)
- Includes 2 turns of conversation history via `get_recent_context()` for follow-up support
- System prompt contains few-shot examples for: search, multi-task, temporal logic, query vs action distinction

### LLM Factory (`agent/llm_factory.py`)

Provider-agnostic LLM instantiation. Routes to DeepSeek, Anthropic, or OpenAI based on model name in config.

- `get_llm(temperature)` — Returns a configured `ChatOpenAI` or `ChatAnthropic` instance
- DeepSeek uses `ChatOpenAI` with custom `base_url`
- Validates API key presence before instantiation

### Nodes (`agent/nodes/`)

| Node | File | LLM? | Description |
|---|---|---|---|
| `parse_node` | `parse.py` | — | Thin wrapper calling `parse_intent()` from parser |
| `plan_node` | `plan.py` | — | Legacy v1 node (not wired into current graph) |
| `validate_node` | `validate.py` | — | Legacy v1 node (not wired into current graph) |
| `execute_node` | `execute.py` | No | Runs tools sequentially with `$task_N` resolution and user confirmation |
| `clarify_node` | `clarify.py` | — | Legacy v1 node (not wired into current graph) |
| `response_node` | `response.py` | Yes | LLM generates conversational summary from execution results |

**`execute_node` details:**
- Iterates through `intent.tasks` in order
- Calls `_resolve_params()` to replace `$task_N.field` references with actual values from prior results
- Prompts user for confirmation per tool (unless `trust_mode=True`)
- Stops on first error; records errors in `execution_errors`

**`response_node` details:**
- Three code paths: user rejected → empathetic explanation; errors → error message; success → LLM summary
- Uses temperature 0.7 for natural-sounding responses
- System prompt instructs concise, jargon-free replies

### Planner (`agent/planner.py`) — Legacy

Rule-based plan generator from v1. Maps intent action types to `ExecutionPlan` with `APICall` steps. Supports 6 action types with dependency tracking. Not used in current v2 graph but retained as reference.

## Models (`conductor/models/`)

Pydantic models shared across the agent.

### Intent (`models/intent.py`)

- `Task` — One tool invocation: `tool`, `params`, `description`, `confidence`. Includes a validator that normalizes `$task_N` reference formats
- `Entity` — Named entity extracted from text (type, value, confidence)
- `Intent` — List of `Task` objects + `overall_confidence`

### Plan (`models/plan.py`)

Legacy v1 models:
- `APICall` — Single API call with tool name, params, description, `depends_on` list, `is_destructive` flag
- `ExecutionPlan` — List of `APICall` steps + explanation + `requires_confirmation` flag

### State (`models/state.py`)

- `AgentState` — LangGraph `TypedDict` with all fields optional (`total=False`). Contains instruction, mode, trust_mode, intent, execution results/errors, and final response

### WATI (`models/wati.py`)

Domain models for WATI API objects:
- `Contact` — WhatsApp contact with name, number, tags, custom params, timestamps
- `Template` — Message template with name, category, status, components, language
- `Message` — Chat message with direction, type, text, timestamp, status

## Tools (`conductor/tools/`)

LangChain `@tool` decorated async functions. Each tool calls the WATI client (mock or real) via `get_wati_client()`.

### Registry (`tools/registry.py`)

Central tool management:
- `get_all_tools()` — Returns all 16 tool objects
- `get_tool(name)` — Lookup by name (used by executor)
- `get_tool_schemas()` — JSON schemas for all tools (for LLM context)
- `get_tools_prompt()` — Auto-generated tool descriptions with signatures for the parser system prompt

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

Batch tools accept a `filter_condition` string (e.g. `"tier != premium"`) to filter the contact list before applying the operation.

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

Abstraction layer for the WATI API. Uses a Protocol class so mock and real clients are interchangeable.

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

Dual-mode command-line interface built with Click and Rich.

**Interactive mode** (no args): REPL loop with `Prompt.ask()`, trust mode toggle, dual Ctrl+C handling (first interrupts current, second exits), conversation history persistence.

**Single-shot mode** (with instruction arg): `python -m conductor.cli "instruction"` with `--dry-run`, `--verbose`, `--trust` flags.

Both modes use `run_instruction()` which:
1. Invokes the agent graph in dry-run mode first (to show thinking)
2. Re-invokes in execute mode if tasks exist
3. Retries up to 2 times on failure
4. Saves each turn to conversation history

## Supporting Modules

### Config (`conductor/config.py`)

Pydantic `BaseSettings` loaded from `.env`. Key settings: `use_mock`, `llm_parse_model`, API keys for DeepSeek/Anthropic/OpenAI, `wati_api_endpoint`, `wati_token`.

### History (`conductor/history.py`)

JSON-based conversation persistence:
- `save_conversation_turn()` — Appends `{timestamp, human, ai}` to session file
- `get_recent_context(max_turns=2)` — Returns last N turns as text for parser context
- Strips emoji/non-ASCII to avoid serialization issues with some LLM APIs
- Session file: `/app/history/current_session.json`

### Staff Data (`conductor/data/staff.py`)

Static staff directory used by operator assignment tools.
