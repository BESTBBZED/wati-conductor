"""Clarify node - formats clarification questions when the agent needs more info."""

from conductor.models.state import AgentState


async def clarify_node(state: AgentState) -> dict:
    """Return a formatted list of clarification questions to the user."""
    questions = state.get("clarification_questions", [])
    
    final_response = "⚠️  Need clarification:\n" + "\n".join(f"  • {q}" for q in questions)
    
    return {
        "final_response": final_response,
        "success": False
    }
