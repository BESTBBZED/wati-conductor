"""WATI API data models."""

from pydantic import BaseModel, Field


class Contact(BaseModel):
    """WhatsApp contact."""

    id: str = Field(description="Contact ID")
    whatsapp_number: str = Field(description="WhatsApp number (e.g., 628123456789)")
    name: str | None = Field(default=None, description="Contact name")
    tags: list[str] = Field(default_factory=list, description="Contact tags")
    custom_params: dict[str, str] = Field(
        default_factory=dict, description="Custom attributes"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "contact_1",
                "whatsapp_number": "628123456789",
                "name": "John Doe",
                "tags": ["VIP", "premium"],
                "custom_params": {"city": "Jakarta", "tier": "gold"},
            }
        }


class Template(BaseModel):
    """WhatsApp message template (WATI API format)."""

    id: str = Field(description="Template ID")
    name: str = Field(description="Template name")
    category: str = Field(description="Template category (MARKETING, UTILITY, etc.)")
    status: str = Field(default="approved", description="Template status")
    language_option: dict = Field(description="Language option")
    custom_params: list[dict] = Field(default_factory=list, description="Custom parameters")
    body: str = Field(description="Template body text with {{1}} placeholders")
    body_original: str = Field(description="Template body with {{name}} placeholders")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "69d9ecef1f4be5791d1c449c",
                "name": "renewal_reminder",
                "category": "MARKETING",
                "status": "approved",
                "language_option": {"key": "English (US)", "value": "en_US", "text": "English (US)"},
                "custom_params": [{"name": "name", "value": "Peter"}],
                "body": "Hello {{1}}, renew now!",
                "body_original": "Hello {{name}}, renew now!",
            }
        }


class Message(BaseModel):
    """WhatsApp message."""

    id: str | None = Field(default=None, description="Message ID")
    whatsapp_number: str = Field(description="Recipient WhatsApp number")
    message_text: str | None = Field(default=None, description="Message text (session message)")
    template_name: str | None = Field(default=None, description="Template name (template message)")
    parameters: dict[str, str] = Field(
        default_factory=dict, description="Template parameters"
    )
    status: str | None = Field(default=None, description="Message status")


class Ticket(BaseModel):
    """Support ticket."""

    ticket_id: str = Field(description="Unique ticket ID")
    subject: str = Field(description="Ticket subject/description")
    priority: str = Field(default="medium", description="Priority: low/medium/high")
    status: str = Field(default="open", description="Status: open/resolved/closed")
    reporter: str | None = Field(default=None, description="Who reported the issue")
    assignee: str | None = Field(default=None, description="Who is assigned to handle it")
    created_at: str = Field(description="Creation timestamp (ISO format)")
    resolved_at: str | None = Field(default=None, description="Resolution timestamp")
    resolution: str | None = Field(default=None, description="Resolution notes")

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TKT-12345",
                "subject": "Payment issue",
                "priority": "high",
                "status": "open",
                "reporter": "Zachary",
                "assignee": "support_team",
                "created_at": "2026-04-11T13:45:00Z",
                "resolved_at": None,
                "resolution": None,
            }
        }

