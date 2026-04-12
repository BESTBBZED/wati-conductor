"""Parse node - first step in the agent graph, extracts intent from user text."""

from conductor.agent.parser import parse_intent
from conductor.models.state import AgentState


async def parse_node(state: AgentState) -> dict:
    """Call the LLM parser to extract a structured intent from the user instruction."""
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
