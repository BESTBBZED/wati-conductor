# Requirements: ReAct Pattern Refactor

> Refactor WATI Conductor's agent state machine from Plan-then-Execute to true ReAct (Reasoning + Acting) pattern.

## Problem Statement

The current agent architecture claims to use ReAct but actually implements Plan-then-Execute:

| Aspect | Current (Plan-then-Execute) | Target (ReAct) |
|---|---|---|
| Planning | Single LLM call generates ALL tasks upfront | LLM decides ONE action at a time |
| Execution | Sequential tool execution, no LLM involvement | Each tool result feeds back to LLM |
| Adaptation | None — if tool returns unexpected results, agent can't adjust | LLM observes results and decides next step dynamically |
| LLM calls | 2 per instruction (parse + response) | N per instruction (one per think-act-observe cycle) |
| Error handling | Stops on first error | LLM can reason about errors and try alternatives |

### What's Broken

1. **No observe step** — tool results never feed back to the LLM for reasoning
2. **No iterative loop** — all tasks planned upfront, executed linearly
3. **No dynamic replanning** — if `search_contacts` returns 0 results, the agent still tries to send templates to them
4. **No thought/action/observation cycle** — the core of ReAct is missing

## Functional Requirements

### FR-1: Think-Act-Observe Loop

The agent MUST implement the ReAct cycle:

1. **Think**: LLM reasons about the current state and decides what to do next
2. **Act**: Agent executes exactly ONE tool call
3. **Observe**: Tool result is added to the conversation and fed back to the LLM
4. **Repeat** until the LLM decides the task is complete (or max iterations reached)

### FR-2: LLM-Driven Tool Selection

The LLM MUST select which tool to call at each step, using LangGraph's native tool-calling mechanism (not structured output parsing of a task list). The LLM receives:

- The user's original instruction
- Conversation history
- All available tool schemas (via `bind_tools`)
- Results from all prior tool calls in this turn

### FR-3: Dynamic Replanning

The agent MUST be able to adapt based on tool results:

- If `search_contacts` returns 0 results → LLM should inform the user instead of proceeding to send messages
- If a tool returns an error → LLM should reason about the error and try an alternative or report the issue
- If intermediate results change the plan → LLM adjusts (e.g., "found 500 contacts, that's a lot — should I proceed?")

### FR-4: Natural Termination

The LLM MUST decide when the task is complete by responding with a text message (no tool call). The graph detects "no tool call in LLM response" as the termination signal.

### FR-5: Human-in-the-Loop Confirmation

The agent MUST preserve the existing confirmation UX:

- In normal mode: prompt user before executing each tool (same as current behavior)
- In trust mode: auto-approve all tool executions
- User can reject a tool call → LLM observes the rejection and responds accordingly

### FR-6: Max Iteration Safety

The agent MUST enforce a maximum number of think-act-observe cycles (configurable, default: 10) to prevent infinite loops. When the limit is hit, the agent MUST generate a summary response with whatever was accomplished.

### FR-7: Conversation History Compatibility

The agent MUST continue to work with the existing 2-turn conversation history system (`conductor/history.py`). The final response (not intermediate thoughts) is saved to history.

### FR-8: Dry-Run Mode

Dry-run mode MUST still work: the LLM generates its first thought/action, but no tools are executed. The planned action is displayed to the user.

## Non-Functional Requirements

### NFR-1: Tool Compatibility

All 16 existing tools MUST work without modification. The tools layer (`conductor/tools/`) is not touched by this refactor.

### NFR-2: LLM Provider Compatibility

The ReAct loop MUST work with all three supported LLM providers:

- DeepSeek (default, via OpenAI-compatible API)
- Anthropic Claude
- OpenAI GPT

All three support tool-calling / function-calling natively.

### NFR-3: Model Selection & Cost Awareness

ReAct uses more LLM calls than Plan-then-Execute. The design MUST:

- Use `deepseek-v4-pro` as the default model for the ReAct loop — the stronger model is needed for reliable multi-step reasoning and tool selection
- Keep `deepseek-v4-flash` available as a fallback option via config (`LLM_REACT_MODEL` env var)
- Keep the system prompt concise — no need for the massive example-heavy prompt since the LLM now reasons step-by-step
- Log iteration count per instruction for cost monitoring
- Explicitly disable thinking mode (`{"thinking": {"type": "disabled"}}`) for the ReAct loop to keep latency low and avoid conflicts with tool calling

### NFR-4: Latency Tolerance

Each think-act-observe cycle adds ~1-3s of LLM latency. This is acceptable for a CLI tool. The design SHOULD show progress indicators (e.g., "Thinking...", "Executing tool...") to keep the user informed.

### NFR-5: Backward Compatibility

- CLI interface (`conductor` command) MUST remain unchanged
- All CLI flags (`--dry-run`, `--verbose`, `--trust`) MUST continue to work
- Single-shot mode and interactive REPL MUST both work
- `pyproject.toml` entry point MUST remain the same

### NFR-6: Code Cleanliness

- Remove or clearly mark legacy code (planner.py, plan.py models, unused nodes)
- The refactored graph should be simpler than the current one, not more complex
- Follow existing project conventions (Black formatting, Google-style docstrings, type hints)

## Out of Scope

These are explicitly NOT part of this refactor:

- Streaming responses (separate V2 feature)
- RAG knowledge base integration (separate V2 feature)
- Web UI (separate V2 feature)
- Session persistence / LangGraph checkpointer (separate V2 feature)
- New tools or WATI API endpoints
- Multi-agent architecture
- Parallel tool execution

## Success Criteria

1. **ReAct loop works**: Agent can handle multi-step instructions by reasoning through them one tool call at a time
2. **Adaptation works**: Agent adjusts behavior based on tool results (e.g., empty search → inform user)
3. **All existing tools work**: No tool modifications needed
4. **CLI unchanged**: All flags and modes work as before
5. **Tests pass**: Existing tests updated and passing, new tests for ReAct loop
6. **Error recovery**: Agent can reason about tool errors instead of crashing

## Constraints

- Must use LangGraph (already a dependency)
- Must use LangGraph's `ToolNode` or equivalent for tool execution
- Must use LLM's native tool-calling (not JSON parsing of a task list)
- Default model: `deepseek-v4-pro` (via OpenAI-compatible API at `https://api.deepseek.com`)
- Thinking mode must be explicitly disabled — v4 models default to thinking enabled, which conflicts with temperature/top_p and adds unnecessary latency
- Python 3.11+, Poetry for dependency management
