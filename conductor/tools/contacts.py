"""Contact management tools — search, tag, and update WhatsApp contacts."""

from langchain.tools import tool
from conductor.clients.factory import get_wati_client


@tool
async def search_contacts(
    tag: str | None = None,
    attribute_name: str | None = None,
    attribute_value: str | None = None,
    page_size: int = 1000,
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

    # If filtering by attribute, fetch all contacts first
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
async def remove_contact_tag(whatsapp_number: str, tag: str) -> dict:
    """Remove a tag from a contact.

    Args:
        whatsapp_number: Contact's WhatsApp number (e.g., "6281234567890").
        tag: Tag to remove (e.g., "regular", "old_customer").

    Returns:
        Dictionary containing:
            - result: Boolean indicating success
            - message: Success message
            - error: Error message if failed

    Examples:
        >>> await remove_contact_tag("6281234567890", "regular")
        {"result": True, "message": "Tag 'regular' removed successfully"}
    """
    client = get_wati_client()
    return await client.remove_tag(whatsapp_number, tag)


@tool
async def add_contact_tag_batch(
    contacts: list[dict],
    tag: str,
    filter_condition: str | None = None
) -> dict:
    """Add a tag to multiple contacts.

    Args:
        contacts: List of contact dictionaries from search_contacts.
        tag: Tag to add (e.g., "VIP", "escalated").
        filter_condition: Optional filter (e.g., "tier == premium").

    Returns:
        Dictionary containing:
            - tagged_count: Number of contacts successfully tagged
            - failed_count: Number of contacts that failed
            - details: List of results for each contact

    Examples:
        >>> contacts = [{"whatsapp_number": "628123", "name": "John"}]
        >>> await add_contact_tag_batch(contacts, "VIP")
        {"tagged_count": 1, "failed_count": 0, "details": [...]}
    """
    client = get_wati_client()
    
    # Apply filter if specified
    filtered_contacts = contacts
    if filter_condition:
        if "!=" in filter_condition:
            parts = filter_condition.split("!=")
            attr_name = parts[0].strip()
            attr_value = parts[1].strip().strip("'\"")
            filtered_contacts = [
                c for c in contacts
                if c.get("custom_params", {}).get(attr_name) != attr_value
            ]
        elif "==" in filter_condition:
            parts = filter_condition.split("==")
            attr_name = parts[0].strip()
            attr_value = parts[1].strip().strip("'\"")
            filtered_contacts = [
                c for c in contacts
                if c.get("custom_params", {}).get(attr_name) == attr_value
            ]
    
    results = []
    tagged_count = 0
    failed_count = 0
    
    for contact in filtered_contacts:
        whatsapp_number = contact.get("whatsappNumber") or contact.get("whatsapp_number")
        if not whatsapp_number:
            failed_count += 1
            results.append({"contact": contact.get("name", "Unknown"), "error": "Missing whatsappNumber"})
            continue
        
        try:
            result = await client.add_tag(whatsapp_number, tag)
            if result.get("result"):
                tagged_count += 1
                results.append({"contact": contact.get("name", whatsapp_number), "status": "tagged"})
            else:
                failed_count += 1
                results.append({"contact": contact.get("name", whatsapp_number), "error": result.get("message")})
        except Exception as e:
            failed_count += 1
            results.append({"contact": contact.get("name", whatsapp_number), "error": str(e)})
    
    return {
        "tagged_count": tagged_count,
        "failed_count": failed_count,
        "total_filtered": len(filtered_contacts),
        "total_input": len(contacts),
        "details": results
    }


@tool
async def remove_contact_tag_batch(
    contacts: list[dict],
    tag: str,
    filter_condition: str | None = None
) -> dict:
    """Remove a tag from multiple contacts.

    Args:
        contacts: List of contact dictionaries from search_contacts.
        tag: Tag to remove (e.g., "regular", "old_customer").
        filter_condition: Optional filter (e.g., "tier == premium").

    Returns:
        Dictionary containing:
            - removed_count: Number of contacts successfully untagged
            - failed_count: Number of contacts that failed
            - details: List of results for each contact

    Examples:
        >>> contacts = [{"whatsapp_number": "628123", "name": "John", "tags": ["regular", "VIP"]}]
        >>> await remove_contact_tag_batch(contacts, "regular", "tier == premium")
        {"removed_count": 1, "failed_count": 0, "details": [...]}
    """
    client = get_wati_client()
    
    # Apply filter if specified
    filtered_contacts = contacts
    if filter_condition:
        if "!=" in filter_condition:
            parts = filter_condition.split("!=")
            attr_name = parts[0].strip()
            attr_value = parts[1].strip().strip("'\"")
            filtered_contacts = [
                c for c in contacts
                if c.get("custom_params", {}).get(attr_name) != attr_value
            ]
        elif "==" in filter_condition:
            parts = filter_condition.split("==")
            attr_name = parts[0].strip()
            attr_value = parts[1].strip().strip("'\"")
            filtered_contacts = [
                c for c in contacts
                if c.get("custom_params", {}).get(attr_name) == attr_value
            ]
    
    results = []
    removed_count = 0
    failed_count = 0
    
    for contact in filtered_contacts:
        whatsapp_number = contact.get("whatsappNumber") or contact.get("whatsapp_number")
        if not whatsapp_number:
            failed_count += 1
            results.append({"contact": contact.get("name", "Unknown"), "error": "Missing whatsappNumber"})
            continue
        
        # Check if contact has the tag
        tags = contact.get("tags", [])
        if tag not in tags:
            results.append({"contact": contact.get("name", whatsapp_number), "status": "skipped", "reason": "tag not present"})
            continue
        
        try:
            result = await client.remove_tag(whatsapp_number, tag)
            if result.get("result"):
                removed_count += 1
                results.append({"contact": contact.get("name", whatsapp_number), "status": "removed"})
            else:
                failed_count += 1
                results.append({"contact": contact.get("name", whatsapp_number), "error": result.get("message")})
        except Exception as e:
            failed_count += 1
            results.append({"contact": contact.get("name", whatsapp_number), "error": str(e)})
    
    return {
        "removed_count": removed_count,
        "failed_count": failed_count,
        "total_filtered": len(filtered_contacts),
        "total_input": len(contacts),
        "details": results
    }


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


@tool
async def update_contact_attributes_batch(
    contacts: list[dict],
    attributes: dict[str, str],
    filter_condition: str | None = None
) -> dict:
    """Update custom attributes for multiple contacts.

    Args:
        contacts: List of contact dictionaries from search_contacts.
        attributes: Dictionary of attribute name-value pairs to update.
        filter_condition: Optional filter description (e.g., "tier != premium").
                         If provided, only contacts matching this condition will be updated.

    Returns:
        Dictionary containing:
            - updated_count: Number of contacts successfully updated
            - failed_count: Number of contacts that failed to update
            - details: List of results for each contact

    Examples:
        >>> contacts = [{"whatsappNumber": "628123", "attributes": {"tier": "basic"}}]
        >>> await update_contact_attributes_batch(contacts, {"tier": "premium"}, "tier != premium")
        {"updated_count": 1, "failed_count": 0, "details": [...]}
    """
    client = get_wati_client()
    custom_params = [{"name": k, "value": v} for k, v in attributes.items()]

    # Apply filter if specified
    filtered_contacts = contacts
    if filter_condition:
        # Parse filter condition: "attribute_name != value" or "attribute_name == value"
        if "!=" in filter_condition:
            parts = filter_condition.split("!=")
            attr_name = parts[0].strip()
            attr_value = parts[1].strip().strip("'\"")
            filtered_contacts = [
                c for c in contacts
                if c.get("custom_params", {}).get(attr_name) != attr_value
            ]
        elif "==" in filter_condition:
            parts = filter_condition.split("==")
            attr_name = parts[0].strip()
            attr_value = parts[1].strip().strip("'\"")
            filtered_contacts = [
                c for c in contacts
                if c.get("custom_params", {}).get(attr_name) == attr_value
            ]

    results = []
    updated_count = 0
    failed_count = 0

    for contact in filtered_contacts:
        # Support both camelCase and snake_case
        whatsapp_number = contact.get("whatsappNumber") or contact.get("whatsapp_number")
        if not whatsapp_number:
            failed_count += 1
            results.append({"contact": contact.get("name", "Unknown"), "error": "Missing whatsappNumber"})
            continue

        try:
            result = await client.update_contact_attributes(whatsapp_number, custom_params)
            if result.get("result"):
                updated_count += 1
                results.append({"contact": contact.get("name", whatsapp_number), "status": "updated"})
            else:
                failed_count += 1
                results.append({"contact": contact.get("name", whatsapp_number), "error": result.get("message")})
        except Exception as e:
            failed_count += 1
            results.append({"contact": contact.get("name", whatsapp_number), "error": str(e)})

    return {
        "updated_count": updated_count,
        "failed_count": failed_count,
        "total_filtered": len(filtered_contacts),
        "total_input": len(contacts),
        "details": results
    }
