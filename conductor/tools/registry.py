"""Tool registry — central list of all LangChain tools available to the agent."""

import logging

from conductor.config import settings
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

logger = logging.getLogger(__name__)

# Map of tool name -> tool object for all known tools
_ALL_TOOLS_MAP: dict | None = None


def _build_tools_map() -> dict:
    """Build name->tool mapping for all known tools (including KB tools)."""
    global _ALL_TOOLS_MAP
    if _ALL_TOOLS_MAP is not None:
        return _ALL_TOOLS_MAP

    tools = [
        search_contacts,
        get_contact_info,
        add_contact_tag,
        add_contact_tag_batch,
        remove_contact_tag,
        remove_contact_tag_batch,
        update_contact_attributes,
        update_contact_attributes_batch,
        send_session_message,
        send_template_message_batch,
        list_templates,
        get_template_details,
        assign_operator,
        assign_team,
        create_ticket,
        resolve_ticket,
    ]

    # Add KB tools if enabled
    if settings.kb_enabled:
        from conductor.tools.kb_tools import search_knowledge, get_guardrails
        tools.extend([search_knowledge, get_guardrails])

    _ALL_TOOLS_MAP = {t.name: t for t in tools}
    return _ALL_TOOLS_MAP


def get_all_tools() -> list:
    """Get all available tools for the agent.

    Returns:
        List of LangChain tool objects.
    """
    return list(_build_tools_map().values())


async def get_active_tools() -> list:
    """Get tools filtered by enabled skills.

    Queries the skill registry for active tool names, then resolves
    to actual tool objects. Falls back to all tools if DB unavailable.

    Returns:
        List of active LangChain tool objects.
    """
    if not settings.skills_enabled:
        return get_all_tools()

    try:
        from conductor.db.session import async_session
        from conductor.skills.registry import get_active_tool_names

        async with async_session() as session:
            active_names = await get_active_tool_names(session)

        # Always include KB tools when KB is enabled
        if settings.kb_enabled:
            active_names.extend(["search_knowledge", "get_guardrails"])

        tools_map = _build_tools_map()
        return [tools_map[name] for name in active_names if name in tools_map]

    except Exception as exc:
        logger.warning("Skill resolution failed, using all tools: %s", exc)
        return get_all_tools()


def get_tool(name: str):
    """Get a specific tool by name.

    Args:
        name: Tool name.

    Returns:
        Tool object.

    Raises:
        ValueError: If tool not found.
    """
    tools_map = _build_tools_map()
    if name in tools_map:
        return tools_map[name]
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
