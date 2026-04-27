# Design: ReAct Pattern Refactor

> Technical design for refactoring WATI Conductor from Plan-then-Execute to true ReAct.

## Architecture Overview

### Current Flow (Plan-then-Execute)

```
User Input → parse_node (LLM: extract ALL tasks) → execute_node (run all sequentially) → response_node (LLM: summarize)
```

- 2 LLM calls per instruction
- No feedback loop — tool results never go back to LLM
- All tasks planned upfront, no adaptation

### Target Flow (ReAct)

```
User Input → agent_node (LLM: think + pick ONE tool) → tool_node (execute it) → agent_node (observe result, think again) → ... → agent_node (no tool call = done, respond)
```

- N LLM calls per instruction (one per think-act-observe cycle)
- Each tool result feeds back to LLM for reasoning
- LLM decides when to stop

## Graph Design

Two-node LangGraph loop using the standard ReAct pattern:

```
                    ┌──────────────┐
         ┌────────►│  agent_node  │────────┐
         │         │  (LLM call)  │        │
         │         └──────────────┘        │
         │               │                 │
         │          has tool call?          │ no tool call
         │               │                 │
         │              yes                ▼
         │               │           ┌──────────┐
         │               ▼           │   END    │
         │         ┌──────────────┐  └──────────┘
         │         │  tool_node   │
         └─────────│  (execute)   │
                   └──────────────┘
```

### agent_node

- Invokes the LLM with the full message history (system prompt + user message + prior tool calls/results)
- LLM either returns a tool call (continue loop) or a text response (terminate)
- Uses `model.bind_tools(tools)` for native tool-calling

### tool_node

- Receives the tool call from the LLM response
- Executes exactly ONE tool
- In normal mode: prompts user for confirmation before execution
- In trust mode: auto-executes
- Returns tool result as a `ToolMessage` back to the message history

### Routing Logic

```python
def should_continue(state) -> Literal["tool_node", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tool_node"
    return END
```

## State Design

Replace the current `AgentState` with a message-based state:

```python
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    iteration_count: int
    trust_mode: bool
    user_rejected: bool
    rejected_tool: str
```

Key change: instead of separate fields for intent/results/errors, everything lives in the `messages` list as LangChain message objects. This is the standard LangGraph ReAct pattern.

## LLM Configuration

### Model: `deepseek-v4-pro`

The ReAct loop requires strong reasoning for multi-step tool selection. `deepseek-v4-pro` is the stronger model with:
- 1M context window (plenty for multi-turn tool calling)
- Native tool calling support
- Better reasoning than `deepseek-v4-flash`

### Thinking Mode: Disabled

DeepSeek v4 models default to thinking mode enabled. We explicitly disable it:
- Thinking mode ignores `temperature`/`top_p` — we need temperature control
- Thinking mode adds latency per call — unacceptable in a multi-call loop
- Tool calling works fine without thinking mode

```python
ChatOpenAI(
    model="deepseek-v4-pro",
    temperature=0.0,
    api_key=settings.deepseek_api_key,
    base_url="https://api.deepseek.com",
    extra_body={"thinking": {"type": "disabled"}},
)
```

### Config Addition

New setting in `config.py`:

```python
llm_react_model: str = "deepseek-v4-pro"
```

The existing `llm_parse_model` / `llm_plan_model` / `llm_clarify_model` become unused (legacy). The single `llm_react_model` replaces all three.

## System Prompt

The ReAct system prompt is much simpler than the current parser prompt — no need for JSON output format or task-list examples. The LLM just needs to know:

1. What it is (WATI WhatsApp automation agent)
2. What tools are available (injected via `bind_tools`)
3. How to behave (one tool at a time, observe results, adapt)
4. When to stop (respond with text when done)

```
You are a WATI WhatsApp automation agent. You help users manage contacts,
send messages, and handle support tickets via the WATI API.

Guidelines:
- Execute ONE tool at a time, observe the result, then decide the next step
- If a search returns 0 results, inform the user — do not proceed with dependent actions
- If a tool returns an error, explain the issue and suggest alternatives
- When the task is complete, respond with a natural summary of what was done
- For informational requests ("how many", "show me", "who are"), only use read-only tools
- For destructive actions, describe what you're about to do before calling the tool
- Be concise but complete in your final response
```

## Human-in-the-Loop

The confirmation UX is implemented in a custom `tool_node` (not LangGraph's built-in `ToolNode`), because we need to intercept before execution:

```python
async def tool_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]

    if not state.get("trust_mode", False):
        # Show tool details, ask for confirmation
        response = input(f"Execute {tool_call['name']}? [Y/n/q]: ")
        if response in ('n', 'q'):
            # Return a ToolMessage saying "user rejected"
            # LLM will observe this and respond accordingly
            return {"messages": [ToolMessage(
                content="User rejected this tool execution.",
                tool_call_id=tool_call["id"]
            )], "user_rejected": True, "rejected_tool": tool_call["name"]}

    # Execute the tool
    tool = get_tool(tool_call["name"])
    result = await tool.ainvoke(tool_call["args"])
    return {"messages": [ToolMessage(
        content=str(result),
        tool_call_id=tool_call["id"]
    )]}
```

When the user rejects, the LLM receives "User rejected this tool execution" as the tool result and can reason about it naturally.

## Max Iteration Safety

```python
async def agent_node(state: AgentState) -> dict:
    if state.get("iteration_count", 0) >= settings.max_react_iterations:
        return {"messages": [AIMessage(
            content="I've reached the maximum number of steps. Here's what I accomplished so far: ..."
        )]}
    # ... normal LLM call ...
    return {"messages": [response], "iteration_count": state.get("iteration_count", 0) + 1}
```

Default: 10 iterations. Configurable via `MAX_REACT_ITERATIONS` env var.

## Dry-Run Mode

In dry-run mode, the agent runs ONE iteration of the ReAct loop (LLM thinks and selects a tool), but does not execute it. The planned tool call is displayed to the user.

```python
def should_continue(state) -> Literal["tool_node", END]:
    if state.get("mode") == "dry-run":
        return END  # Stop after first thought
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tool_node"
    return END
```

## File Changes

### New Files
- `conductor/agent/react_graph.py` — new ReAct graph (replaces `graph.py`)
- `conductor/agent/react_nodes.py` — agent_node + tool_node (replaces all current nodes)

### Modified Files
- `conductor/config.py` — add `llm_react_model`, `max_react_iterations`
- `conductor/agent/llm_factory.py` — add `get_react_llm()` that returns model with tools bound
- `conductor/agent/__init__.py` — re-export `create_agent_graph` from new module
- `conductor/cli.py` — simplify `run_instruction()` (the graph now handles everything)
- `.env.example` — add new config vars

### Legacy Files (mark as deprecated, keep for reference)
- `conductor/agent/parser.py` — replaced by LLM native tool calling
- `conductor/agent/planner.py` — replaced by LLM reasoning
- `conductor/agent/nodes/` — all nodes replaced by react_nodes.py
- `conductor/models/intent.py` — Task/Intent models no longer needed
- `conductor/models/plan.py` — ExecutionPlan no longer needed

## Integration with CLI

The CLI changes are minimal. `run_instruction()` simplifies because the graph handles the full loop:

```python
async def run_instruction(instruction, agent, trust=False, dry_run=False):
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=instruction)],
        "trust_mode": trust,
        "mode": "dry-run" if dry_run else "execute",
        "iteration_count": 0,
    })
    # Final message is the agent's text response
    final_response = result["messages"][-1].content
    save_conversation_turn(instruction, final_response)
    return True, final_response
```

## Integration with History

Only the final text response (the last AIMessage without tool calls) is saved to conversation history. Intermediate tool calls and results are not persisted — they're ephemeral within the ReAct loop.

The `get_recent_context()` function continues to work as-is, providing prior conversation turns as context in the system prompt.
