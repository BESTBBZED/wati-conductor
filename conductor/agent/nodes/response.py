"""Response node - uses LLM to turn raw execution results into a conversational reply."""

from langchain_core.messages import SystemMessage, HumanMessage
from conductor.models.state import AgentState
from conductor.agent.llm_factory import get_llm


RESPONSE_PROMPT = """You are a helpful assistant summarizing the results of API operations.

Given:
- User's original instruction
- Execution results from API calls

Generate a natural, conversational response that:
1. Directly answers the user's question
2. Includes relevant details from the results
3. Uses friendly, human-like language
4. Avoids technical jargon

Be concise but complete. If the user asked a yes/no question, answer it clearly first, then provide supporting details.

Examples:

User: "What is 628123450000, is he a premium?"
Results: {"name": "Customer 0", "tier": "premium", "tags": ["VIP"]}
Response: "Yes, Customer 0 (628123450000) is a premium member. They're also tagged as VIP."

User: "Find all VIP contacts"
Results: {"contacts": [{"name": "Customer 0"}, {"name": "Customer 5"}], "total": 10}
Response: "I found 10 VIP contacts, including Customer 0, Customer 5, and 8 others."

User: "Send renewal reminder to VIP contacts"
Results: {"sent": 10, "failed": 0}
Response: "Done! I sent the renewal reminder template to all 10 VIP contacts successfully."
"""


async def response_node(
    state: AgentState, reject_response_temp: float = 0.7, response_temp: float = 0.7
) -> dict:
    """Generate a human-friendly response from execution results.

    Handles three cases: user rejected a tool, execution errors occurred,
    or everything succeeded and results need to be summarised.
    """
    instruction = state.get("instruction", "")
    results = state.get("execution_results", [])
    errors = state.get("execution_errors", [])
    user_rejected = state.get("user_rejected", False)
    rejected_tool = state.get("rejected_tool", "")

    # If user rejected tool execution
    if user_rejected:
        llm = get_llm(temperature=reject_response_temp)
        messages = [
            SystemMessage(
                content="""You are a helpful assistant explaining why a task cannot be completed.
The user rejected the use of a tool, so you cannot complete their request.
Generate a polite, understanding response that:
1. Acknowledges their decision
2. Explains what information you cannot access without the tool
3. Suggests alternative ways they could get the information (if applicable)

Be empathetic and helpful."""
            ),
            HumanMessage(
                content=f"""User instruction: {instruction}
Rejected tool: {rejected_tool}

Generate a response explaining why you cannot complete the task:"""
            ),
        ]
        response = await llm.ainvoke(messages)
        return {"final_response": response.content.strip()}

    # If there were errors, return error message
    if errors:
        error_msg = errors[0]
        return {
            "final_response": f"❌ Execution failed at step {error_msg['step']+1} ({error_msg['tool']}): {error_msg['error']}"
        }

    # Format results for LLM
    results_summary = _format_results_for_llm(results)

    # Generate response with LLM
    llm = get_llm(temperature=response_temp)

    messages = [
        SystemMessage(content=RESPONSE_PROMPT),
        HumanMessage(
            content=f"""User instruction: {instruction}

Execution results:
{results_summary}

Generate a natural response:"""
        ),
    ]

    response = await llm.ainvoke(messages)

    return {"final_response": response.content.strip()}


def _format_results_for_llm(results: list) -> str:
    """Flatten execution results into a text block the LLM can read."""
    lines = []
    for r in results:
        tool = r["tool"]
        result = r["result"]
        lines.append(f"Tool: {tool}")
        lines.append(f"Result: {result}")
        lines.append("")
    return "\n".join(lines)
