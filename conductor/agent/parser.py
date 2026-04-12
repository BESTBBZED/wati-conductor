"""Intent parsing — sends user text to an LLM and returns structured tasks."""

import json
import re
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from conductor.models.intent import Intent
from conductor.agent.llm_factory import get_llm
from conductor.tools.registry import get_tools_prompt


SYSTEM_PROMPT = """You are an API orchestration planner for WATI WhatsApp API.
Parse user instructions into a list of tasks with tools and parameters.

IMPORTANT: 
- Break down complex instructions into multiple tasks
- Each task should have confidence >= 0.7 to be executed
- Tasks can reference previous task results using "$task_N.field" (e.g., "$task_0.contacts")
- DO NOT use array indexing like "$task_0.contacts[0]" - use batch tools instead
- DO NOT use JSONPath filters like "$task_0.contacts[?(...)]" - instead, describe the filtering in the task description and let the tool handle it
- For batch operations on filtered results, pass the full list and describe the filter condition in a separate parameter
- search_contacts already returns full contact details — do NOT add get_contact_info after it
- For unclear requests, return empty tasks list with overall_confidence < 0.3
- For update_contact_attributes_batch and add_contact_tag_batch, filter_condition must be a STRING like "tier != premium" or "tier == basic", NOT a dict
- Use batch tools (update_contact_attributes_batch, add_contact_tag_batch) when operating on multiple contacts
- CRITICAL: If user says "let me know", "tell me", "show me", "how many", "who are", they want INFORMATION ONLY - do NOT create update/modify tasks
- Only create update/modify tasks when user explicitly says "upgrade", "change", "update", "add tag", "remove tag", "send message", etc.
- TEMPORAL LOGIC: When a task modifies data (e.g., upgrade tier) and a later task needs to filter on the ORIGINAL value (e.g., "tag those who WERE regular"), both tasks should use the SAME source ($task_0.contacts) with filters based on the original data

Available tools:
{tools}

Output JSON with:
{{
  "tasks": [
    {{
      "tool": "<tool_name>",
      "params": {{...}},
      "description": "Human-readable description",
      "confidence": 0.0-1.0
    }}
  ],
  "overall_confidence": 0.0-1.0
}}

Examples:

User: "Find all VIP contacts and send them the welcome_wati template"
{{"tasks": [{{"tool": "search_contacts", "params": {{"tag": "VIP"}}, "description": "Find VIP contacts", "confidence": 0.95}}, {{"tool": "send_template_message_batch", "params": {{"contacts": "$task_0.contacts", "template_name": "welcome_wati"}}, "description": "Send welcome_wati to VIP contacts", "confidence": 0.90}}], "overall_confidence": 0.92}}

User: "How many customers are from Tokyo and if they are not premium, let me know"
{{"tasks": [{{"tool": "search_contacts", "params": {{"attribute_name": "city", "attribute_value": "Tokyo"}}, "description": "Find Tokyo customers", "confidence": 0.95}}], "overall_confidence": 0.95}}

User: "Find Beijing contacts, upgrade non-premium ones to premium, and tag them all as VIP"
{{"tasks": [{{"tool": "search_contacts", "params": {{"attribute_name": "city", "attribute_value": "Beijing"}}, "description": "Find Beijing contacts", "confidence": 0.95}}, {{"tool": "update_contact_attributes_batch", "params": {{"contacts": "$task_0.contacts", "attributes": {{"tier": "premium"}}, "filter_condition": "tier != premium"}}, "description": "Upgrade non-premium Beijing contacts", "confidence": 0.90}}, {{"tool": "add_contact_tag_batch", "params": {{"contacts": "$task_0.contacts", "tag": "VIP"}}, "description": "Tag all Beijing contacts as VIP", "confidence": 0.90}}], "overall_confidence": 0.92}}

User: "Upgrade Beijing non-premium to premium and tag those who were regular as VIP"
{{"tasks": [{{"tool": "search_contacts", "params": {{"attribute_name": "city", "attribute_value": "Beijing"}}, "description": "Find Beijing contacts", "confidence": 0.95}}, {{"tool": "update_contact_attributes_batch", "params": {{"contacts": "$task_0.contacts", "attributes": {{"tier": "premium"}}, "filter_condition": "tier != premium"}}, "description": "Upgrade non-premium Beijing contacts", "confidence": 0.90}}, {{"tool": "add_contact_tag_batch", "params": {{"contacts": "$task_0.contacts", "tag": "VIP", "filter_condition": "tier == regular"}}, "description": "Tag those who were originally regular tier", "confidence": 0.90}}], "overall_confidence": 0.92}}

User: "Remove 'regular' tag from Beijing VIP customers"
{{"tasks": [{{"tool": "search_contacts", "params": {{"attribute_name": "city", "attribute_value": "Beijing"}}, "description": "Find Beijing contacts", "confidence": 0.95}}, {{"tool": "remove_contact_tag_batch", "params": {{"contacts": "$task_0.contacts", "tag": "regular"}}, "description": "Remove regular tag from Beijing contacts", "confidence": 0.90}}], "overall_confidence": 0.92}}

User: "Remove 'regular' tag from 628123450041"
{{"tasks": [{{"tool": "remove_contact_tag", "params": {{"whatsapp_number": "628123450041", "tag": "regular"}}, "description": "Remove regular tag from contact", "confidence": 0.95}}], "overall_confidence": 0.95}}

User: "What templates do I have?"
{{"tasks": [{{"tool": "list_templates", "params": {{}}, "description": "List all available templates", "confidence": 0.95}}], "overall_confidence": 0.95}}

User: "Hi what are you?"
{{"tasks": [], "overall_confidence": 0.0}}

Respond ONLY with valid JSON. No markdown, no explanation."""


def _build_system_prompt() -> str:
    """Build the system prompt by injecting the current tool signatures."""
    return SYSTEM_PROMPT.format(tools=get_tools_prompt())


def extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM output, stripping markdown fences if present."""
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        raise ValueError(f"Could not extract valid JSON from response: {e}")


async def parse_intent(instruction: str) -> Intent:
    """Parse a natural language instruction into a multi-task Intent.

    Includes recent conversation history for context and filters out
    low-confidence tasks (< 0.7).
    """
    from conductor.history import get_recent_context
    
    llm = get_llm(temperature=0.0)
    
    # Include recent conversation context with clear instruction
    context = get_recent_context(max_turns=2)
    if context:
        user_message = f"""Previous conversation (for context only, tasks already completed):
{context}

Current user request (ONLY parse this into tasks):
User: {instruction}"""
    else:
        user_message = f"User: {instruction}"

    messages = [
        SystemMessage(content=_build_system_prompt()),
        HumanMessage(content=user_message)
    ]

    response = await llm.ainvoke(messages)

    try:
        data = extract_json(response.content)
        intent = Intent(**data)
        intent.tasks = [t for t in intent.tasks if t.confidence >= 0.7]
        return intent
    except Exception as e:
        raise ValueError(f"Failed to parse intent: {e}\nLLM response: {response.content}")
