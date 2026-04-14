"""Intent and entity models for natural language understanding."""

import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Entity(BaseModel):
    """A named entity extracted from user text (e.g. a contact name, tag, or phone number)."""

    type: str = Field(description="Entity type (contact, tag, template, etc.)")
    value: str = Field(description="Entity value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Task(BaseModel):
    """One tool invocation with its parameters, as planned by the LLM."""
    
    tool: str = Field(description="Tool name to execute")
    params: dict = Field(default_factory=dict, description="Tool parameters")
    description: str = Field(description="Human-readable task description")
    confidence: float = Field(ge=0.0, le=1.0, description="Task confidence")
    
    @field_validator('params')
    @classmethod
    def validate_task_references(cls, v: dict) -> dict:
        """Ensure task references use the correct $task_N format.
        
        Normalizes common variations like @task_0, {task_0}, task_0 to $task_0.
        """
        normalized = {}
        for key, value in v.items():
            if isinstance(value, str) and 'task' in value.lower():
                # Normalize: @task_0, {task_0}, task_0 → $task_0
                value = re.sub(r'[@{]?\s*task[_\s]*(\d+)\s*[}]?', r'$task_\1', value, flags=re.IGNORECASE)
            normalized[key] = value
        return normalized


class Intent(BaseModel):
    """Structured representation of a user instruction as a list of tasks."""

    tasks: list[Task] = Field(description="List of tasks to execute")
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Overall parse confidence")

    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "tool": "search_contacts",
                        "params": {"tag": "VIP"},
                        "description": "Find VIP contacts",
                        "confidence": 0.95
                    },
                    {
                        "tool": "send_template_message_batch",
                        "params": {"template_name": "welcome_wati", "contacts": "$task_0.result"},
                        "description": "Send welcome template to VIP contacts",
                        "confidence": 0.90
                    }
                ],
                "overall_confidence": 0.92
            }
        }
