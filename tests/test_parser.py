"""Tests for intent parser."""

import pytest
from conductor.agent.parser import parse_intent


@pytest.mark.asyncio
async def test_parse_simple_search():
    """Test parsing simple contact search."""
    intent = await parse_intent("Find all VIP contacts")
    
    assert intent.action == "search_contacts"
    assert intent.target["type"] == "contacts"
    assert intent.target["filter"]["tag"] == "VIP"
    assert intent.confidence > 0.8


@pytest.mark.asyncio
async def test_parse_template_to_segment():
    """Test parsing template send to segment."""
    intent = await parse_intent("Send renewal_reminder template to all VIP contacts")
    
    assert intent.action == "send_template_to_segment"
    assert intent.target["filter"]["tag"] == "VIP"
    assert intent.parameters["template_name"] == "renewal_reminder"
    assert intent.confidence > 0.8


@pytest.mark.asyncio
async def test_parse_escalation():
    """Test parsing escalation instruction."""
    intent = await parse_intent("Escalate 6281234567890 to Support")
    
    assert intent.action == "escalate_conversation"
    assert intent.target["phone"] == "6281234567890"
    assert intent.parameters["team"] == "Support"
    assert intent.confidence > 0.8


@pytest.mark.asyncio
async def test_parse_attribute_filter():
    """Test parsing with custom attribute filter."""
    intent = await parse_intent("Send flash_sale to all Jakarta contacts")
    
    assert intent.action == "send_template_to_segment"
    assert intent.target["filter"]["attribute_name"] == "city"
    assert intent.target["filter"]["attribute_value"] == "Jakarta"
    assert intent.parameters["template_name"] == "flash_sale"


@pytest.mark.asyncio
async def test_parse_update_attributes():
    """Test parsing attribute update."""
    intent = await parse_intent("Update contact 6281234567890 tier to premium")
    
    assert intent.action == "update_contact_attributes"
    assert intent.target["phone"] == "6281234567890"
    assert intent.parameters["attributes"]["tier"] == "premium"
