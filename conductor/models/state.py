"""LangGraph agent state."""

from typing import TypedDict, Literal
from conductor.models.intent import Intent
from conductor.models.plan import ExecutionPlan


class AgentState(TypedDict, total=False):
    """State for the LangGraph agent."""

    # Input
    instruction: str
    mode: Literal["execute", "dry-run"]
    trust_mode: bool

    # Parsing
    intent: Intent | None

    # Execution
    execution_results: list[dict]
    execution_errors: list[dict]
    user_rejected: bool
    rejected_tool: str

    # Output
    final_response: str
    success: bool
