"""Ticket management tools."""

import asyncio
import os
from langchain_core.tools import tool
from conductor.clients.factory import get_wati_client
from conductor.data.staff import get_random_staff


@tool
def create_ticket(subject: str, priority: str = "medium", 
                 reporter: str = None, assignee: str = None) -> dict:
    """Create a support ticket.
    
    Args:
        subject: Ticket subject/description
        priority: Ticket priority (low/medium/high)
        reporter: Who reported the issue (default: from TICKET_REPORTER env var)
        assignee: Who to assign the ticket to (default: random staff member)
    """
    if reporter is None:
        reporter = os.getenv("TICKET_REPORTER", "Zachary")
    
    if assignee is None:
        assignee = get_random_staff()
    
    client = get_wati_client()
    result = asyncio.run(client.create_ticket(subject, priority, reporter, assignee))
    return result


@tool
def resolve_ticket(ticket_id: str, resolution: str = "") -> dict:
    """Resolve/close a support ticket.
    
    Args:
        ticket_id: Ticket ID to resolve
        resolution: Resolution notes
    """
    client = get_wati_client()
    result = asyncio.run(client.resolve_ticket(ticket_id, resolution))
    return result
