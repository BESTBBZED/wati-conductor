"""Operator and team conversation-routing tools."""

from langchain.tools import tool
from conductor.clients.factory import get_wati_client


@tool
async def assign_operator(whatsapp_number: str, operator_email: str) -> dict:
    """Assign a conversation to a specific operator.

    Use this to route customer conversations to specific support agents.

    Args:
        whatsapp_number: Contact's WhatsApp number (e.g., "6281234567890").
        operator_email: Email address of the operator to assign.

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - message: Success message
            - error: Error message if failed

    Examples:
        >>> await assign_operator("6281234567890", "agent@company.com")
        {"result": True, "message": "Conversation assigned to agent@company.com"}
    """
    client = get_wati_client()
    return await client.assign_operator(whatsapp_number, operator_email)


@tool
async def assign_team(whatsapp_number: str, team_name: str) -> dict:
    """Assign a conversation to a team.

    Use this to route customer conversations to specific teams (e.g., Support, Sales).

    Args:
        whatsapp_number: Contact's WhatsApp number (e.g., "6281234567890").
        team_name: Name of the team to assign (e.g., "Support", "Sales").

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - message: Success message
            - error: Error message if failed

    Examples:
        >>> await assign_team("6281234567890", "Support")
        {"result": True, "message": "Conversation assigned to team 'Support'"}
    """
    client = get_wati_client()
    return await client.assign_team(whatsapp_number, team_name)
