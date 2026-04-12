"""Validate node - sanity-checks the execution plan before running it."""

from conductor.models.state import AgentState


async def validate_node(state: AgentState) -> dict:
    """Check that the plan is safe to execute.

    Verifies the plan exists, has steps, and that destructive steps
    include parameters. Returns validation errors or an empty list.
    """
    errors = []
    plan = state.get("plan")
    
    # Check if plan exists
    if plan is None:
        # Get the error message from planner (if it's a help message)
        intent = state.get("intent")
        if intent and intent.confidence < 0.3:
            return {
                "validation_errors": ["Low confidence - general question"],
                "needs_clarification": True,
                "clarification_questions": [
                    "I'm a WATI automation agent. I can help you with:\n"
                    "• Search and manage contacts\n"
                    "• Send template messages\n"
                    "• Create and resolve tickets\n"
                    "• Assign conversations to operators\n"
                    "• Update contact attributes\n\n"
                    "Try asking something like:\n"
                    "- 'Find all VIP contacts'\n"
                    "- 'Create a ticket to Sam about login issue'\n"
                    "- 'What templates do I have?'"
                ]
            }
        return {
            "validation_errors": ["Failed to generate plan"],
            "needs_clarification": True,
            "clarification_questions": ["I couldn't understand your request. Could you rephrase it?"]
        }
    
    # Basic validation
    if not plan.steps:
        errors.append("Plan has no steps")
    
    # Check for missing parameters in destructive operations
    for i, step in enumerate(plan.steps):
        if step.is_destructive and not step.params:
            errors.append(f"Step {i+1} ({step.tool}) is destructive but has no parameters")
    
    if errors:
        return {
            "validation_errors": errors,
            "needs_clarification": True,
            "clarification_questions": [f"Validation issue: {e}" for e in errors]
        }
    
    return {"validation_errors": []}
