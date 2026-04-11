"""Tests for plan generation."""

import pytest
from conductor.agent.planner import generate_plan
from conductor.models.intent import Intent


def test_plan_search_contacts():
    """Test planning for contact search."""
    intent = Intent(
        action="search_contacts",
        target={"type": "contacts", "filter": {"tag": "VIP"}},
        parameters={},
        conditions=[],
        confidence=0.9
    )
    
    plan = generate_plan(intent)
    
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "search_contacts"
    assert plan.steps[0].params["tag"] == "VIP"
    assert plan.requires_confirmation is False


def test_plan_send_template_to_segment():
    """Test planning for template send to segment."""
    intent = Intent(
        action="send_template_to_segment",
        target={"type": "contacts", "filter": {"tag": "VIP"}},
        parameters={"template_name": "renewal_reminder"},
        conditions=[],
        confidence=0.9
    )
    
    plan = generate_plan(intent)
    
    assert len(plan.steps) == 3
    assert plan.steps[0].tool == "search_contacts"
    assert plan.steps[1].tool == "get_template_details"
    assert plan.steps[2].tool == "send_template_message_batch"
    assert plan.steps[2].is_destructive is True
    assert plan.requires_confirmation is True
    assert plan.steps[2].depends_on == [0, 1]


def test_plan_escalate_conversation():
    """Test planning for escalation."""
    intent = Intent(
        action="escalate_conversation",
        target={"type": "contact", "phone": "6281234567890"},
        parameters={"team": "Support", "add_tag": "escalated"},
        conditions=[],
        confidence=0.9
    )
    
    plan = generate_plan(intent)
    
    assert len(plan.steps) == 2
    assert plan.steps[0].tool == "add_contact_tag"
    assert plan.steps[0].params["tag"] == "escalated"
    assert plan.steps[1].tool == "assign_to_team"
    assert plan.steps[1].params["team_name"] == "Support"
    assert plan.steps[1].depends_on == [0]


def test_plan_update_attributes():
    """Test planning for attribute update."""
    intent = Intent(
        action="update_contact_attributes",
        target={"type": "contact", "phone": "6281234567890"},
        parameters={"attributes": {"tier": "premium"}},
        conditions=[],
        confidence=0.9
    )
    
    plan = generate_plan(intent)
    
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "update_contact_attributes"
    assert plan.steps[0].params["custom_params"]["tier"] == "premium"
    assert plan.steps[0].is_destructive is True

