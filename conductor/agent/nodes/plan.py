"""Plan node - converts parsed intent into an execution plan."""

from conductor.agent.planner import generate_plan
from conductor.models.state import AgentState


async def plan_node(state: AgentState) -> dict:
    """Generate an execution plan from the parsed intent.

    Returns the plan on success, or clarification questions on failure.
    """
    try:
        plan = generate_plan(state["intent"])
        return {"plan": plan}
    except Exception as e:
        return {
            "plan": None,
            "needs_clarification": True,
            "clarification_questions": [
                f"I couldn't create a plan: {str(e)}"
            ]
        }
