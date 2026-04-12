"""Abstract WATI client protocol — defines the interface all clients must implement."""

from typing import Protocol


class WATIClient(Protocol):
    """Protocol that both ``RealWATIClient`` and ``MockWATIClient`` satisfy."""

    async def get_contacts(
        self, tag: str | None = None, page_size: int = 20, page_number: int = 1
    ) -> dict:
        """Get contacts list."""
        ...

    async def get_contact_info(self, whatsapp_number: str) -> dict:
        """Get detailed contact information."""
        ...

    async def add_tag(self, whatsapp_number: str, tag: str) -> dict:
        """Add tag to contact."""
        ...

    async def remove_tag(self, whatsapp_number: str, tag: str) -> dict:
        """Remove tag from contact."""
        ...

    async def update_contact_attributes(
        self, whatsapp_number: str, custom_params: list[dict]
    ) -> dict:
        """Update contact custom attributes."""
        ...

    async def send_session_message(self, whatsapp_number: str, message_text: str) -> dict:
        """Send session message (within 24h window)."""
        ...

    async def get_all_template_message(
        self, page_number: int = 1, page_size: int = 100
    ) -> dict:
        """Get message templates with pagination.
        
        Returns:
            {
                "templates": [...],
                "page_number": 1,
                "page_size": 100,
                "total": 29
            }
        """
        ...

    async def send_template_message(
        self, template_name: str, broadcast_name: str, scheduled_at, recipients: list[dict], channel: str | None = None
    ) -> dict:
        """Send template message.
        
        Args:
            template_name: Template name
            broadcast_name: Broadcast name
            scheduled_at: Scheduled datetime
            recipients: List of recipient objects with whatsappNumber and customParams
            channel: Channel name/number (null for default)
        """
        ...

    async def get_message_templates(self, page_size: int = 20, page_number: int = 1) -> dict:
        """Get available message templates."""
        ...

    async def assign_operator(self, whatsapp_number: str, email: str) -> dict:
        """Assign conversation to operator."""
        ...

    async def assign_team(self, whatsapp_number: str, team_name: str) -> dict:
        """Assign conversation to team."""
        ...

    async def send_broadcast_to_segment(
        self, template_name: str, broadcast_name: str, segment_name: str
    ) -> dict:
        """Send broadcast to segment."""
        ...
