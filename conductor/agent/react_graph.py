"""ReAct agent graph — two-node loop: agent ↔ tool."""

from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from conductor.models.state import AgentState
from conductor.agent.react_nodes import agent_node, tool_node


def _should_continue(state: AgentState) -> Literal["tool_node", "__end__"]:
    """Route after the agent node.

    * If the LLM returned a tool call → go to tool_node.
    * If the LLM returned plain text (or dry-run mode) → END.
    """
    if state.get("mode") == "dry-run":
        return END

    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tool_node"
    return END


def create_agent_graph() -> CompiledStateGraph:
    """Build and compile the ReAct agent graph.

    Flow::

        agent_node ──(tool call)──► tool_node ──► agent_node  (loop)
            │
            └──(text response)──► END

    Returns:
        Compiled LangGraph state machine.
    """
    graph = StateGraph(AgentState)

    graph.add_node("agent_node", agent_node)
    graph.add_node("tool_node", tool_node)

    graph.set_entry_point("agent_node")

    graph.add_conditional_edges(
        "agent_node",
        _should_continue,
        {"tool_node": "tool_node", END: END},
    )
    graph.add_edge("tool_node", "agent_node")

    return graph.compile()
