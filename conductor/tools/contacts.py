"""Contact management tools."""

from langchain.tools import tool
from conductor.clients.factory import get_wati_client


@tool
async def search_contacts(
    tag: str | None = None,
    attribute_name: str | None = None,
    attribute_value: str | None = None,
    page_size: int = 20,
) -> dict:
    """Search for WhatsApp contacts by tag or custom attributes.

    Args:
        tag: Filter contacts by tag (e.g., "VIP", "new_signup").
        attribute_name: Custom attribute to filter by (e.g., "city").
        attribute_value: Value for the attribute (e.g., "Jakarta").
        page_size: Maximum number of results to return.

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - contacts: List of contact objects
            - pageInfo: Pagination information

    Examples:
        >>> await search_contacts(tag="VIP")
        {"result": True, "contacts": [...], "pageInfo": {...}}

        >>> await search_contacts(attribute_name="city", attribute_value="Jakarta")
        {"result": True, "contacts": [...], "pageInfo": {...}}
    """
    client = get_wati_client()
    result = await client.get_contacts(tag=tag, page_size=page_size)

    # Filter by attribute if specified
    if attribute_name and attribute_value and result.get("result"):
        contacts = result["contacts"]
        filtered = [
            c
            for c in contacts
            if c.get("custom_params", {}).get(attribute_name) == attribute_value
        ]
        result["contacts"] = filtered
        result["pageInfo"]["totalRecords"] = len(filtered)

    return result


@tool
async def get_contact_info(whatsapp_number: str) -> dict:
    """Get detailed information about a specific contact.

    Args:
        whatsapp_number: Contact's WhatsApp number (e.g., "6281234567890").

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - contact: Contact object with full details
            - error: Error message if contact not found

    Examples:
        >>> await get_contact_info("6281234567890")
        {"result": True, "contact": {"id": "...", "name": "...", ...}}
    """
    client = get_wati_client()
    return await client.get_contact_info(whatsapp_number)


@tool
async def add_contact_tag(whatsapp_number: str, tag: str) -> dict:
    """Add a tag to a contact.

    Args:
        whatsapp_number: Contact's WhatsApp number (e.g., "6281234567890").
        tag: Tag to add (e.g., "VIP", "escalated").

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - message: Success message
            - error: Error message if failed

    Examples:
        >>> await add_contact_tag("6281234567890", "VIP")
        {"result": True, "message": "Tag 'VIP' added successfully"}
    """
    client = get_wati_client()
    return await client.add_tag(whatsapp_number, tag)


@tool
async def update_contact_attributes(whatsapp_number: str, attributes: dict[str, str]) -> dict:
    """Update custom attributes for a contact.

    Args:
        whatsapp_number: Contact's WhatsApp number (e.g., "6281234567890").
        attributes: Dictionary of attribute name-value pairs.

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - message: Success message
            - error: Error message if failed

    Examples:
        >>> await update_contact_attributes("6281234567890", {"city": "Jakarta", "tier": "gold"})
        {"result": True, "message": "Attributes updated successfully"}
    """
    client = get_wati_client()
    custom_params = [{"name": k, "value": v} for k, v in attributes.items()]
    return await client.update_contact_attributes(whatsapp_number, custom_params)
