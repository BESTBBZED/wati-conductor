"""Plan generation - translate intent into executable API call sequence."""

from conductor.models.intent import Intent
from conductor.models.plan import APICall, ExecutionPlan


def generate_plan(intent: Intent) -> ExecutionPlan:
    """
    Generate API call sequence from intent.
    
    Args:
        intent: Parsed intent with action, target, and parameters
        
    Returns:
        ExecutionPlan with ordered steps and metadata
        
    Raises:
        ValueError: If action type is unknown or intent is invalid
    """
    # Check for low confidence (general questions, greetings)
    if intent.confidence < 0.3:
        raise ValueError(
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
        )
    
    if intent.action == "search_contacts":
        return _plan_search_contacts(intent)
    elif intent.action == "send_template_to_segment":
        return _plan_send_template_to_segment(intent)
    elif intent.action == "send_message_to_contact":
        return _plan_send_message_to_contact(intent)
    elif intent.action == "update_contact_attributes":
        return _plan_update_contact_attributes(intent)
    elif intent.action == "assign_operator":
        return _plan_assign_operator(intent)
    elif intent.action == "escalate_conversation":
        return _plan_escalate_conversation(intent)
    elif intent.action == "list_templates":
        return _plan_list_templates(intent)
    elif intent.action == "create_ticket":
        return _plan_create_ticket(intent)
    elif intent.action == "resolve_ticket":
        return _plan_resolve_ticket(intent)
    else:
        raise ValueError(f"Unknown action: {intent.action}")


def _plan_create_ticket(intent: Intent) -> ExecutionPlan:
    """Plan for creating a support ticket."""
    subject = intent.parameters.get("subject", "Support request")
    priority = intent.parameters.get("priority", "medium")
    reporter = intent.parameters.get("reporter")  # None = use env var
    assignee = intent.parameters.get("assignee")  # None = random staff
    
    params = {"subject": subject, "priority": priority}
    if reporter:
        params["reporter"] = reporter
    if assignee:
        params["assignee"] = assignee
    
    steps = [
        APICall(
            tool="create_ticket",
            params=params,
            description=f"Create {priority} priority ticket: {subject}" + (f" (assign to {assignee})" if assignee else "")
        )
    ]
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Create support ticket" + (f" and assign to {assignee}" if assignee else ""),
        estimated_api_calls=1,
        requires_confirmation=False
    )


def _plan_resolve_ticket(intent: Intent) -> ExecutionPlan:
    """Plan for resolving a support ticket."""
    ticket_id = intent.target.get("ticket_id")
    resolution = intent.parameters.get("resolution", "Issue resolved")
    
    steps = [
        APICall(
            tool="resolve_ticket",
            params={"ticket_id": ticket_id, "resolution": resolution},
            description=f"Resolve ticket {ticket_id}"
        )
    ]
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Resolve ticket {ticket_id}",
        estimated_api_calls=1,
        requires_confirmation=False
    )


def _plan_list_templates(intent: Intent) -> ExecutionPlan:
    """Plan for listing available templates."""
    steps = [
        APICall(
            tool="list_templates",
            params={},
            description="List all available message templates"
        )
    ]
    
    return ExecutionPlan(
        steps=steps,
        explanation="List all available message templates",
        estimated_api_calls=1,
        requires_confirmation=False
    )

def _plan_search_contacts(intent: Intent) -> ExecutionPlan:
    """Plan for searching contacts."""
    # Check if searching for a specific contact by phone
    if intent.target.get("type") == "contact" and "phone" in intent.target:
        phone = intent.target["phone"]
        steps = [
            APICall(
                tool="get_contact_info",
                params={"whatsapp_number": phone},
                description=f"Get details for contact {phone}"
            )
        ]
        return ExecutionPlan(
            steps=steps,
            explanation=f"Get contact information for {phone}",
            estimated_api_calls=1,
            requires_confirmation=False
        )
    
    # Otherwise, search by filter
    filter_params = intent.target.get("filter", {})
    
    steps = [
        APICall(
            tool="search_contacts",
            params=filter_params,
            description=f"Search contacts with filter: {filter_params}"
        )
    ]
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Search for contacts matching: {filter_params}",
        estimated_api_calls=1,
        requires_confirmation=False
    )


def _plan_send_template_to_segment(intent: Intent) -> ExecutionPlan:
    """Plan for sending template to contact segment."""
    filter_params = intent.target.get("filter", {})
    template_name = intent.parameters.get("template_name")
    
    if not template_name:
        raise ValueError("template_name is required for send_template_to_segment")
    
    steps = [
        APICall(
            tool="search_contacts",
            params=filter_params,
            description=f"Find contacts matching: {filter_params}"
        ),
        APICall(
            tool="get_template_details",
            params={"template_name": template_name},
            description=f"Get template details for '{template_name}'"
        ),
        APICall(
            tool="send_template_message_batch",
            params={
                "contacts": "$step_0.contacts",
                "template_name": template_name,
                "parameters": intent.parameters.get("template_params", {})
            },
            description=f"Send '{template_name}' template to all matching contacts",
            depends_on=[0, 1],
            is_destructive=True
        )
    ]
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Find contacts with {filter_params} and send them the '{template_name}' template",
        estimated_api_calls=3,
        requires_confirmation=True
    )


def _plan_send_message_to_contact(intent: Intent) -> ExecutionPlan:
    """Plan for sending message to specific contact."""
    phone = intent.target.get("phone")
    message = intent.parameters.get("message")
    
    if not phone:
        raise ValueError("phone is required for send_message_to_contact")
    if not message:
        raise ValueError("message is required for send_message_to_contact")
    
    steps = [
        APICall(
            tool="send_session_message",
            params={
                "whatsapp_number": phone,
                "message_text": message  # Fixed: use message_text instead of message
            },
            description=f"Send message to {phone}",
            is_destructive=True
        )
    ]
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Send message to contact {phone}",
        estimated_api_calls=1,
        requires_confirmation=False
    )


def _plan_update_contact_attributes(intent: Intent) -> ExecutionPlan:
    """Plan for updating contact attributes."""
    phone = intent.target.get("phone")
    attributes = intent.parameters.get("attributes", {})
    
    if not phone:
        raise ValueError("phone is required for update_contact_attributes")
    if not attributes:
        raise ValueError("attributes are required for update_contact_attributes")
    
    steps = [
        APICall(
            tool="update_contact_attributes",
            params={
                "whatsapp_number": phone,
                "attributes": attributes
            },
            description=f"Update contact {phone} attributes: {attributes}",
            is_destructive=True
        )
    ]
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Update contact {phone} with attributes: {attributes}",
        estimated_api_calls=1,
        requires_confirmation=False
    )


def _plan_assign_operator(intent: Intent) -> ExecutionPlan:
    """Plan for assigning operator to conversation."""
    phone = intent.target.get("phone")
    operator = intent.parameters.get("operator")
    team = intent.parameters.get("team")
    
    if not phone:
        raise ValueError("phone is required for assign_operator")
    if not operator and not team:
        raise ValueError("Either operator or team is required for assign_operator")
    
    steps = []
    
    if team:
        steps.append(APICall(
            tool="assign_team",
            params={
                "whatsapp_number": phone,
                "team_name": team
            },
            description=f"Assign conversation {phone} to team '{team}'",
            is_destructive=True
        ))
    else:
        steps.append(APICall(
            tool="assign_operator",
            params={
                "whatsapp_number": phone,
                "operator_email": operator
            },
            description=f"Assign conversation {phone} to operator '{operator}'",
            is_destructive=True
        ))
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Assign conversation {phone} to {team or operator}",
        estimated_api_calls=1,
        requires_confirmation=False
    )


def _plan_escalate_conversation(intent: Intent) -> ExecutionPlan:
    """Plan for escalating conversation (tag + assign)."""
    phone = intent.target.get("phone")
    team = intent.parameters.get("team", "Support")
    add_tag = intent.parameters.get("add_tag", "escalated")
    
    if not phone:
        raise ValueError("phone is required for escalate_conversation")
    
    steps = [
        APICall(
            tool="add_contact_tag",
            params={
                "whatsapp_number": phone,
                "tag": add_tag
            },
            description=f"Tag contact {phone} as '{add_tag}'",
            is_destructive=True
        ),
        APICall(
            tool="assign_team",
            params={
                "whatsapp_number": phone,
                "team_name": team
            },
            description=f"Assign conversation to '{team}' team",
            depends_on=[0],
            is_destructive=True
        )
    ]
    
    return ExecutionPlan(
        steps=steps,
        explanation=f"Escalate conversation {phone}: tag as '{add_tag}' and assign to '{team}' team",
        estimated_api_calls=2,
        requires_confirmation=False
    )
