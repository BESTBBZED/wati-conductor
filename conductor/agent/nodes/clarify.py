"""Clarify node - handle clarification requests."""

from conductor.models.state import AgentState


async def clarify_node(state: AgentState) -> dict:
    """Handle clarification - just format the questions."""
    questions = state.get("clarification_questions", [])
    
    final_response = "⚠️  Need clarification:\n" + "\n".join(f"  • {q}" for q in questions)
    
    return {
        "final_response": final_response,
        "success": False
    }
