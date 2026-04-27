"""LangGraph agent state definition."""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """Shared state passed between ReAct graph nodes.

    Uses a message list as the primary data channel — each LLM response
    and tool result is appended as a LangChain message object.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    """Conversation messages (system, human, AI, tool)."""

    iteration_count: int
    """Number of think-act-observe cycles completed so far."""

    trust_mode: bool
    """When True, skip per-tool confirmation prompts."""

    mode: Literal["execute", "dry-run"]
    """Execution mode."""

    user_rejected: bool
    """Set to True when the user declines a tool execution."""

    rejected_tool: str
    """Name of the tool the user rejected."""
