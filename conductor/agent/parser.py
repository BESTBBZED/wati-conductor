"""Intent parsing using LLM with structured output."""

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
- For unclear requests, return empty tasks list with overall_confidence < 0.3
- search_contacts already returns full contact details — do NOT add get_contact_info after it

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

User: "Search VIP contacts, create a ticket to Sam about payment, and list templates"
{{"tasks": [{{"tool": "search_contacts", "params": {{"tag": "VIP"}}, "description": "Find VIP contacts", "confidence": 0.95}}, {{"tool": "create_ticket", "params": {{"subject": "payment issue", "assignee": "Sam", "priority": "high"}}, "description": "Create ticket for Sam about payment", "confidence": 0.90}}, {{"tool": "list_templates", "params": {{}}, "description": "List all templates", "confidence": 0.95}}], "overall_confidence": 0.93}}

User: "What templates do I have?"
{{"tasks": [{{"tool": "list_templates", "params": {{}}, "description": "List all available templates", "confidence": 0.95}}], "overall_confidence": 0.95}}

User: "Hi what are you?"
{{"tasks": [], "overall_confidence": 0.0}}

Respond ONLY with valid JSON. No markdown, no explanation."""


def _build_system_prompt() -> str:
    """Build system prompt with auto-generated tools description."""
    return SYSTEM_PROMPT.format(tools=get_tools_prompt())


def extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response, handling markdown code blocks."""
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
    """Parse natural language instruction into multi-task intent."""
    llm = get_llm(temperature=0.0)

    messages = [
        SystemMessage(content=_build_system_prompt()),
        HumanMessage(content=f"User: {instruction}")
    ]

    response = await llm.ainvoke(messages)

    try:
        data = extract_json(response.content)
        intent = Intent(**data)
        intent.tasks = [t for t in intent.tasks if t.confidence >= 0.7]
        return intent
    except Exception as e:
        raise ValueError(f"Failed to parse intent: {e}\nLLM response: {response.content}")
