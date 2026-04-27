# Dev Notes

Build notes, problem framing, and design trade-offs from the development of WATI Conductor.

## ReAct Refactor (v3) — 2026-04-27

### Why ReAct

The v2 architecture claimed to be "LLM-first" but was actually Plan-then-Execute: one LLM call generated ALL tasks upfront, then they were executed sequentially with no feedback loop. This meant:

- If `search_contacts` returned 0 results, the agent still tried to send templates to an empty list
- Tool errors crashed the pipeline — the LLM never saw the error
- No dynamic replanning — the plan was fixed at parse time

ReAct fixes all of this. The LLM reasons step-by-step: call one tool, observe the result, decide what to do next. If a search returns nothing, the LLM says "no results found" instead of blindly proceeding.

### What Changed

| Before (v2) | After (v3) |
|---|---|
| `parser.py` — structured output extraction | Native tool calling via `bind_tools` |
| `graph.py` — 3-node graph (parse → execute → response) | `react_graph.py` — 2-node loop (agent ↔ tool) |
| `nodes/execute.py` — sequential executor with `$task_N` resolution | `react_nodes.py` — tool_node with confirmation gate |
| `nodes/response.py` — separate LLM call for response | agent_node generates final response naturally |
| `AgentState` with intent/results/errors fields | `AgentState` with `messages` list (standard LangGraph pattern) |
| 2 LLM calls per instruction | N LLM calls (one per think-act-observe cycle) |

### Key Decisions

**DeepSeek v4 Pro as default**: ReAct needs stronger reasoning than plan-execute. The v4 Pro model handles multi-step tool selection reliably. Flash is available as a cheaper fallback.

**Thinking mode disabled**: DeepSeek v4 models default to thinking mode enabled, which ignores temperature/top_p and adds latency. Since we're making multiple LLM calls per instruction, the latency compounds. Disabled via `extra_body={"thinking": {"type": "disabled"}}`.

**Custom tool_node instead of LangGraph's ToolNode**: We need the human-in-the-loop confirmation gate (print tool details, ask `[Y/n/q]`). LangGraph's built-in `ToolNode` doesn't support this. When the user rejects, we return `ToolMessage("User rejected this tool execution.")` — the LLM observes this naturally and responds accordingly.

**Message-based state**: Instead of separate fields for intent, execution results, and errors, everything flows through the `messages` list. This is the standard LangGraph ReAct pattern and dramatically simplifies the state schema.

### Files Changed

- **New**: `react_graph.py`, `react_nodes.py`
- **Modified**: `llm_factory.py` (added `get_react_llm`), `config.py` (added `llm_react_model`, `max_react_iterations`), `cli.py` (simplified `run_instruction`), `state.py` (message-based), `__init__.py` (re-export from react_graph)
- **Legacy** (kept for reference): `graph.py`, `parser.py`, `planner.py`, `nodes/`, `models/intent.py`, `models/plan.py`

### Cost Implications

ReAct uses more LLM calls than plan-execute. A simple "find VIP contacts" is 2 iterations (search + respond). A complex "find VIPs, send template, tag them" is 4-5 iterations. At DeepSeek v4 Pro pricing this is still very cheap, but token tracking should be added for production use.

---

*Original v1 build notes below.*

---

## Problem Framing

Build a chatbot that lets non-technical business users automate WhatsApp operations through natural language. They should be able to say things like "Send a welcome message to all VIP customers" without knowing anything about APIs.

### What I Focused On

**Multi-task workflows**: The interesting part isn't single commands like "find VIP contacts" — it's complex requests like "find VIP contacts AND send them a template AND create a ticket if it fails". The agent needs to break this down, execute steps in order, and pass data between steps.

**Reliability over cleverness**: I went with a plan-then-execute pattern instead of letting the LLM decide what to do at every step. One LLM call to make a plan, then deterministic execution. This is cheaper, more predictable, and easier to debug.

**Demo-friendly**: Added interactive confirmations so you can see what's about to happen. Built a mock WATI client with realistic data (50 contacts, 6 templates) so demos work without real API credentials.

### What I Skipped

- **Streaming responses**: Would be nice but not critical for MVP
- **Web UI**: CLI is faster to iterate and good enough for demos
- **Advanced error recovery**: If a tool fails, the agent stops. Could add retry/fallback but felt like over-engineering
- **Real WATI integration**: Mock data throughout. Real API has strict data structures that would take days to get right

### Key Trade-offs

**WATI Sandbox API**: Registered for the sandbox and tested it on their website, but didn't integrate it. The API has strict field formats, template approval workflows, and webhook handling that would've taken days. Instead, built a mock client that reads/writes local files. Same interface, so swapping later is straightforward.

**Conversation history**: Keeping full history made the agent repeat old tasks. Limiting to last 2 turns fixed it but means the agent can't reference things from 3+ turns ago.

**Batch operations**: Added tools like `update_contact_attributes_batch` instead of making the LLM loop through contacts one by one. More tools to maintain but way more reliable.

**Prompt complexity**: Spent ~30% of time on prompt engineering (don't use array indexing, distinguish queries from actions, handle temporal logic). Feels brittle but works.

## Build Notes

### Development Timeline

- **Hour 1**: Built the core LangGraph state machine. Used KIRO with Claude to draft the initial spec. Hit encoding bugs immediately (emoji in responses broke JSON serialization).
- **Hour 2**: Added conversation history. Realized long histories made the agent repeat old tasks. Fixed by limiting context window and adding "for context only" markers in prompts.
- **Hour 3**: Built the CLI with Rich library. Added trust mode, dual Ctrl+C handling, and auto-retry. Created batch operations for common workflows.

### Problems Solved

**Temporal Logic**: "Upgrade to premium and tag those who were regular" — the second task needs to filter on the *original* tier value, not the modified one. Fixed by having both tasks reference `$task_0.contacts` (the original search result).

**Query vs Action**: "How many customers are from Tokyo?" shouldn't trigger updates. Added prompt rules: "let me know" = info only, "upgrade" = execute action.

**Parameter Mapping**: Templates need parameters like `{{name}}`. Built auto-mapping that extracts required params from templates and fills them from contact data.

**Unicode Issues**: Emoji broke things in 3 different places (JSON serialization, file I/O, API requests). Added `remove_emoji()` helper that strips non-ASCII characters.

### What Worked Well

- Confidence filtering (≥ 0.7) reduced false positives dramatically
- Interactive confirmations made demos much better
- Batch tools eliminated complex array indexing in prompts
- Mock-first development enabled fast iteration

### What Was Annoying

- Unicode handling across 3 different failure points
- Prompt engineering took 30% of total time
- LLM sometimes generates dict when you ask for string — had to add explicit type examples

## Demo Script

### Setup

```bash
docker compose up -d
docker compose exec wati-conductor python3 main.py
```

### Demo Scenarios (in order)

1. **Enable trust mode**: `trust` — skips confirmations for smoother demo

2. **List templates**: `What templates do I have?` — shows tool calling basics

3. **Find contacts**: `Find all VIP contacts` — simple search

4. **Multi-task workflow**: `Find all VIP contacts and send them the welcome_wati template` — shows task decomposition and `$task_0.contacts` dependency

5. **Contextual follow-up**: `How many of them are from Beijing?` — uses conversation history

6. **Chained action**: `Upgrade them all to premium tier` — context-aware batch update

7. **Temporal logic** (advanced): `Find all contacts from Beijing who are not premium, upgrade them to premium, and tag those who were regular as VIP` — shows original-value filtering

8. **Query vs action**: `How many customers are from Tokyo?` — information-only, no modifications

9. **Ticket creation**: `Create a ticket to Sam about database connection error` — local ticket system

### Backup Scenarios

- **Batch tag**: `Find all contacts from Jakarta and add them to the "jakarta_campaign" tag`
- **Template with params**: `Send the ecom_presales_oct template to contact 628123450000`
- **Error handling**: `Send a template that doesn't exist to VIP contacts`
- **Dry run**: `python -m conductor.cli "Find all VIP contacts and send them the welcome_wati template" --dry-run`

### Demo Tips

- Don't rush — let people read the "Agent Thinking" section
- Point at the screen when showing task dependencies
- Emphasize trade-off reasoning for the mock API decision
- Pause 2-3 seconds between commands
- Have screenshots or video as backup if Docker fails
- The temporal logic example is the most impressive — practice explaining it clearly
