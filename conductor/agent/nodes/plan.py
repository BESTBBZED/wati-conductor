"""Plan node - generate execution plan from intent."""

from conductor.agent.planner import generate_plan
from conductor.models.state import AgentState


async def plan_node(state: AgentState) -> dict:
    """Generate execution plan from intent."""
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
