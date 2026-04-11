"""Real WATI API client implementation."""

import httpx
from datetime import datetime
from conductor.models.wati import Ticket


class RealWATIClient:
    """Real WATI API client."""

    def __init__(self, api_endpoint: str, token: str):
        """Initialize WATI client.

        Args:
            api_endpoint: WATI API endpoint (e.g., https://live-mt-server.wati.io/api/ext/v3)
            token: WATI API token
        """
        self.api_endpoint = api_endpoint.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_all_template_message(
        self, page_number: int = 1, page_size: int = 100
    ) -> dict:
        """Get message templates with pagination.
        
        Args:
            page_number: Page number (default: 1)
            page_size: Page size (default: 100)
            
        Returns:
            {
                "templates": [...],
                "page_number": 1,
                "page_size": 100,
                "total": 29
            }
        """
        url = f"{self.api_endpoint}/messageTemplates"
        params = {
            "page_number": page_number,
            "page_size": page_size
        }

        response = await self.client.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()


    async def send_template_message(
        self, template_name: str, broadcast_name: str, scheduled_at: datetime, recipients: list[dict], channel: str = None
    ) -> dict:
        """Send template message via WATI API.

        Args:
            template_name: Template name
            broadcast_name: Broadcast name
            recipients: List of recipient objects with whatsappNumber and customParams
            channel: Channel name/number (null for default)
        """
        url = f"{self.api_endpoint}/messageTemplates/schedule"
        payload = {
            "template_name": template_name,
            "broadcast_name": broadcast_name,
            "scheduled_at": scheduled_at,
            "recipients": recipients
        }
        if channel:
            payload["channel"] = channel

        response = await self.client.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    async def send_session_message(self, whatsapp_number: str, message_text: str) -> dict:
        """Send session message (within 24h window)."""
        raise NotImplementedError

    async def get_contacts(
        self, tag: str | None = None, page_size: int = 20, page_number: int = 1
    ) -> dict:
        """Get contacts list."""
        raise NotImplementedError

    async def get_contact_info(self, whatsapp_number: str) -> dict:
        """Get detailed contact information."""
        raise NotImplementedError

    async def add_tag(self, whatsapp_number: str, tag: str) -> dict:
        """Add tag to contact."""
        raise NotImplementedError

    async def update_contact_attributes(
        self, whatsapp_number: str, custom_params: list[dict]
    ) -> dict:
        """Update contact custom attributes."""
        raise NotImplementedError

    async def get_message_templates(self, page_size: int = 20, page_number: int = 1) -> dict:
        """Get available message templates."""
        raise NotImplementedError

    async def assign_operator(self, whatsapp_number: str, email: str) -> dict:
        """Assign conversation to operator."""
        raise NotImplementedError
    # Ticket methods remain local (not WATI API)
    async def create_ticket(self, subject: str, priority: str = "medium",
                           reporter: str = None, assignee: str = None) -> dict:
        """Create support ticket (local storage, not WATI API)."""
        # Tickets are stored locally, not via WATI API
        raise NotImplementedError("Ticket management should use local storage")

    async def resolve_ticket(self, ticket_id: str, resolution: str = "") -> dict:
        """Resolve support ticket (local storage, not WATI API)."""
        raise NotImplementedError("Ticket management should use local storage")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
