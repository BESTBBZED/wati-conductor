"""Template listing and inspection tools."""

from langchain.tools import tool
from conductor.clients.factory import get_wati_client


@tool
async def list_templates(page_size: int = 20) -> dict:
    """List all available WhatsApp message templates.

    Templates are pre-approved message formats that can be used for
    proactive communication with customers.

    Args:
        page_size: Maximum number of templates to return.

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - messageTemplates: List of template objects
            - pageInfo: Pagination information

    Examples:
        >>> await list_templates()
        {
            "result": True,
            "messageTemplates": [
                {"name": "renewal_reminder", "category": "MARKETING", ...},
                {"name": "flash_sale", "category": "MARKETING", ...}
            ],
            "pageInfo": {...}
        }
    """
    client = get_wati_client()
    return await client.get_message_templates(page_size=page_size)


@tool
async def get_template_details(template_name: str) -> dict:
    """Get detailed information about a specific template.

    Use this to check template parameters, body text, and other details
    before sending a template message.

    Args:
        template_name: Name of the template (e.g., "renewal_reminder").

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - template: Template object with full details
            - error: Error message if template not found

    Examples:
        >>> await get_template_details("renewal_reminder")
        {
            "result": True,
            "template": {
                "name": "renewal_reminder",
                "parameters": ["name", "discount"],
                "body": "Hello {{1}}, renew now and get {{2}}% off!",
                "category": "MARKETING"
            }
        }
    """
    client = get_wati_client()
    templates_result = await client.get_message_templates(page_size=100)

    if not templates_result.get("result"):
        return {"result": False, "error": "Failed to fetch templates"}

    templates = templates_result.get("messageTemplates", [])
    template = next((t for t in templates if t["name"] == template_name), None)

    if not template:
        available = [t["name"] for t in templates]
        return {
            "result": False,
            "error": f"Template '{template_name}' not found",
            "available_templates": available,
        }

    return {"result": True, "template": template}
