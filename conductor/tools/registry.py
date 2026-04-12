"""Tool registry — central list of all LangChain tools available to the agent."""

from conductor.tools.contacts import (
    search_contacts,
    get_contact_info,
    add_contact_tag,
    add_contact_tag_batch,
    remove_contact_tag,
    remove_contact_tag_batch,
    update_contact_attributes,
    update_contact_attributes_batch,
)
from conductor.tools.messages import (
    send_session_message,
    send_template_message_batch,
)
from conductor.tools.templates import list_templates, get_template_details
from conductor.tools.operators import assign_operator, assign_team
from conductor.tools.tickets import create_ticket, resolve_ticket


def get_all_tools() -> list:
    """Get all available tools for the agent.

    Returns:
        List of LangChain tool objects that can be used by the agent.

    Examples:
        >>> tools = get_all_tools()
        >>> len(tools)
        13
    """
    return [
        # Contact tools
        search_contacts,
        get_contact_info,
        add_contact_tag,
        add_contact_tag_batch,
        remove_contact_tag,
        remove_contact_tag_batch,
        update_contact_attributes,
        update_contact_attributes_batch,
        # Message tools
        send_session_message,
        send_template_message_batch,
        # Template tools
        list_templates,
        get_template_details,
        # Operator tools
        assign_operator,
        assign_team,
        # Ticket tools
        create_ticket,
        resolve_ticket,
    ]


def get_tool(name: str):
    """Get a specific tool by name.
    
    Args:
        name: Tool name
        
    Returns:
        Tool object
        
    Raises:
        ValueError: If tool not found
    """
    tools = get_all_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    raise ValueError(f"Tool not found: {name}")


def get_tool_schemas() -> list[dict]:
    """Get JSON schemas for all tools.

    Useful for passing to LLM for tool selection.

    Returns:
        List of tool schema dictionaries.

    Examples:
        >>> schemas = get_tool_schemas()
        >>> schemas[0]["name"]
        'search_contacts'
    """
    tools = get_all_tools()
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.args_schema.schema() if tool.args_schema else {},
        }
        for tool in tools
    ]


def get_tools_prompt() -> str:
    """Generate tools description for LLM prompt from tool definitions.

    Auto-extracts name, description, and parameter signatures from
    LangChain @tool decorated functions. Uses only the first line of
    the docstring as description.

    Returns:
        Formatted string describing all available tools.
    """
    lines = []
    for tool in get_all_tools():
        # Extract params from schema
        schema = tool.args_schema.schema() if tool.args_schema else {}
        props = schema.get("properties", {})
        required = schema.get("required", [])

        params = []
        for name, info in props.items():
            ptype = info.get("type", "any")
            suffix = "" if name in required else "?"
            params.append(f"{name}{suffix}: {ptype}")

        sig = ", ".join(params)
        # Only first line of description
        desc = tool.description.split("\n")[0].strip()
        lines.append(f"- {tool.name}({sig}) — {desc}")

    return "\n".join(lines)
