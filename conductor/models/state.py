"""LangGraph agent state definition."""

from typing import TypedDict, Literal
from conductor.models.intent import Intent
from conductor.models.plan import ExecutionPlan


class AgentState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes.

    All fields are optional (``total=False``) so each node only needs
    to return the keys it modifies.
    """

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
