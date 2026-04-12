"""Intent and entity models for natural language understanding."""

from typing import Literal
from pydantic import BaseModel, Field


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
