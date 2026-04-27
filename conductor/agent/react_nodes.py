"""ReAct graph nodes — agent (LLM) and tool (execution) nodes."""

import logging

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from conductor.config import settings
from conductor.history import get_recent_context
from conductor.models.state import AgentState
from conductor.tools.registry import get_all_tools, get_tool
from conductor.agent.llm_factory import get_react_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a WATI WhatsApp automation agent. You help users manage contacts, \
send messages, and handle support tickets via the WATI API.

Guidelines:
- Execute ONE tool at a time, observe the result, then decide the next step.
- If a search returns 0 results, inform the user — do not proceed with dependent actions.
- If a tool returns an error, explain the issue and suggest alternatives.
- When the task is complete, respond with a natural summary of what was done.
- For informational requests ("how many", "show me", "who are"), only use read-only tools.
- For destructive actions, describe what you're about to do before calling the tool.
- Be concise but complete in your final response."""


def _build_system_message() -> SystemMessage:
    """Build the system message, optionally including recent conversation context."""
    parts = [SYSTEM_PROMPT]
    context = get_recent_context(max_turns=2)
    if context:
        parts.append(f"\n{context}")
    return SystemMessage(content="\n".join(parts))


def _get_bound_llm():
    """Return the LLM with all tools bound."""
    tools = get_all_tools()
    return get_react_llm(tools)


async def agent_node(state: AgentState) -> dict:
    """Invoke the LLM to think and optionally select a tool.

    If ``max_react_iterations`` is reached, forces a text-only response
    summarising what was accomplished so far.
    """
    iteration = state.get("iteration_count", 0)

    # Safety: max iterations reached
    if iteration >= settings.max_react_iterations:
        logger.warning("Max ReAct iterations (%d) reached", settings.max_react_iterations)
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I've reached the maximum number of steps. "
                        "Here's what I accomplished so far based on the conversation above."
                    )
                )
            ],
        }

    # Ensure system message is first
    messages = list(state.get("messages", []))
    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, _build_system_message())

    llm = _get_bound_llm()
    response = await llm.ainvoke(messages)

    return {
        "messages": [response],
        "iteration_count": iteration + 1,
    }


async def tool_node(state: AgentState) -> dict:
    """Execute the tool requested by the last AI message.

    In normal mode, prompts the user for confirmation before execution.
    In trust mode, auto-executes. If the user rejects, returns a
    ``ToolMessage`` telling the LLM the execution was declined.
    """
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    call_id = tool_call["id"]

    trust_mode = state.get("trust_mode", False)

    # --- confirmation gate ---
    if not trust_mode:
        print(f"\n🔧 Tool: {tool_name}")
        print(f"   Args: {tool_args}")
        response = input("   Execute? [Y/n/q]: ").strip().lower()
        if response in ("n", "q"):
            return {
                "messages": [
                    ToolMessage(
                        content="User rejected this tool execution.",
                        tool_call_id=call_id,
                    )
                ],
                "user_rejected": True,
                "rejected_tool": tool_name,
            }

    # --- execute ---
    try:
        tool = get_tool(tool_name)
        result = await tool.ainvoke(tool_args)
        content = str(result)
    except Exception as exc:
        logger.error("Tool %s failed: %s", tool_name, exc)
        content = f"Error executing {tool_name}: {exc}"

    return {
        "messages": [ToolMessage(content=content, tool_call_id=call_id)],
    }
