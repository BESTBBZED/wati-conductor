"""Parse node - extract intent from instruction."""

from conductor.agent.parser import parse_intent
from conductor.models.state import AgentState


async def parse_node(state: AgentState) -> dict:
    """Parse user instruction into structured intent."""
    try:
        intent = await parse_intent(state["instruction"])
        return {"intent": intent}
    except Exception as e:
        return {
            "needs_clarification": True,
            "clarification_questions": [
                "I couldn't understand your instruction. Could you rephrase it?",
                f"Error: {str(e)}"
            ]
        }
