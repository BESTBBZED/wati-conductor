"""LangGraph state machine for the WATI Conductor agent.

Defines the three-node graph: parse → execute → respond.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from conductor.models.state import AgentState
from conductor.agent.nodes import (
    parse_node,
    execute_node,
    response_node
)


def route_after_parse(state: AgentState) -> Literal["execute", "generate_response"]:
    """Decide the next node after parsing.

    Skips execution when confidence is too low or mode is dry-run.
    """
    intent = state.get("intent")

    # If no tasks or low confidence, end
    if not intent or not intent.tasks or intent.overall_confidence < 0.7:
        return "generate_response"

    # In dry-run mode, skip execution
    if state.get("mode") == "dry-run":
        return "generate_response"

    return "execute"


def create_agent_graph() -> CompiledStateGraph:
    """Create the ReAct agent state machine.

    Simplified flow:
        1. parse_intent: LLM extracts tasks with tools and parameters
        2. execute_plan: Execute tools (with user confirmation unless trust mode)
        3. generate_response: LLM generates natural language response

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("parse_intent", parse_node)
    graph.add_node("execute_plan", execute_node)
    graph.add_node("generate_response", response_node)

    # Set entry point
    graph.set_entry_point("parse_intent")

    # Add edges
    graph.add_conditional_edges(
        "parse_intent",
        route_after_parse,
        {"execute": "execute_plan", "generate_response": "generate_response"}
    )

    graph.add_edge("execute_plan", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()
