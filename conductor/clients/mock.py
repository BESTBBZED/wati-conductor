"""Mock WATI client — persists data to local JSON files for development and testing."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from conductor.models.wati import Contact, Template, Ticket


# Persistent storage paths - use project root's mock_data if /app doesn't exist
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_MOCK_DATA_DIR = Path(os.getenv("MOCK_DATA_DIR", "/app/mock_data"))
if not _MOCK_DATA_DIR.exists() and not _MOCK_DATA_DIR.parent.exists():
    _MOCK_DATA_DIR = _PROJECT_ROOT / "mock_data"

_CONTACTS_FILE = _MOCK_DATA_DIR / "contacts.json"
_TEMPLATES_FILE = _MOCK_DATA_DIR / "templates.json"
_TICKETS_FILE = _MOCK_DATA_DIR / "tickets.json"


def _load_tickets() -> list[Ticket]:
    """Load tickets from JSON file."""
    if _TICKETS_FILE.exists():
        with open(_TICKETS_FILE, "r") as f:
            data = json.load(f)
            return [Ticket(**t) for t in data]
    return []


def _save_tickets(tickets: list[Ticket]):
    """Save tickets to JSON file."""
    _MOCK_DATA_DIR.mkdir(exist_ok=True)
    with open(_TICKETS_FILE, "w") as f:
        json.dump([t.model_dump() for t in tickets], f, indent=2)


def _load_contacts() -> list[Contact]:
    """Load contacts from JSON file or generate if not exists."""
    if _CONTACTS_FILE.exists():
        with open(_CONTACTS_FILE, "r") as f:
            data = json.load(f)
            return [Contact(**c) for c in data]

    # Generate initial data
    contacts = _generate_contacts()
    _save_contacts(contacts)
    return contacts


def _save_contacts(contacts: list[Contact]):
    """Save contacts to JSON file."""
    _MOCK_DATA_DIR.mkdir(exist_ok=True)
    with open(_CONTACTS_FILE, "w") as f:
        json.dump([c.model_dump() for c in contacts], f, indent=2)


def _load_templates() -> list[Template]:
    """Load templates from JSON file or generate if not exists."""
    if _TEMPLATES_FILE.exists():
        with open(_TEMPLATES_FILE, "r") as f:
            data = json.load(f)
            return [Template(**t) for t in data]

    # Generate initial data
    templates = _generate_templates()
    _save_templates(templates)
    return templates


def _save_templates(templates: list[Template]):
    """Save templates to JSON file."""
    _MOCK_DATA_DIR.mkdir(exist_ok=True)
    with open(_TEMPLATES_FILE, "w") as f:
        json.dump([t.model_dump() for t in templates], f, indent=2)


def _generate_contacts() -> list[Contact]:
    """Generate 50 randomized mock contacts."""
    import random
    contacts = []
    cities = ["New York", "Beijing", "London", "Tokyo", "Singapore", "Dubai", "Sydney", "Paris"]
    tiers = ["premium", "standard", "basic"]
    first_names = ["James", "Wei", "Sarah", "Yuki", "Omar", "Emma", "Raj", "Sofia", "Chen", "Liam"]
    last_names = ["Smith", "Zhang", "Johnson", "Tanaka", "Ali", "Garcia", "Patel", "Kim", "Wang", "Brown"]

    for i in range(50):
        is_vip = random.random() < 0.2  # ~20% VIP
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        contact = Contact(
            id=f"contact_{i}",
            whatsapp_number=f"62812345{i:04d}",
            name=name,
            tags=["VIP"] if is_vip else ["regular"],
            custom_params={
                "city": random.choice(cities),
                "tier": "premium" if is_vip else random.choice(tiers),
                "language": random.choice(["en", "zh", "ja", "ar"]),
            },
        )
        contacts.append(contact)

    return contacts


def _generate_templates() -> list[Template]:
    """Generate mock templates matching WATI API format with real examples."""
    return [
        # Welcome message
        Template(
            id="real_template_001",
            name="welcome_wati",
            category="MARKETING",
            status="approved",
            language_option={"key": "English (US)", "value": "en_US", "text": "English (US)"},
            custom_params=[{"name": "name", "value": "John"}],
            body="Hi {{1}} 👋,\n\nThank you for your message.\n\nHow can I help you today?",
            body_original="Hi {{name}} 👋,\n\nThank you for your message.\n\nHow can I help you today?"
        ),
        # Order confirmation
        Template(
            id="real_template_002",
            name="shopify_default_cod_confirm_order_v5",
            category="MARKETING",
            status="approved",
            language_option={"key": "English (US)", "value": "en_US", "text": "English (US)"},
            custom_params=[
                {"name": "name", "value": "John"},
                {"name": "total_price", "value": "$99.99"},
                {"name": "shop_name", "value": "My Shop"},
                {"name": "cod_confirm_url", "value": "https://example.com/confirm"},
                {"name": "cod_cancel_url", "value": "https://example.com/cancel"}
            ],
            body="Dear {{1}}.\n\nThank you for placing an order of {{2}} from {{3}}. Please confirm your order so that we can process it.\n\nClick the link or confirm order button below to confirm your order.\n{{4}}\n\nIf you wish to cancel your order, please click the link below.\n{{5}}\n\nThank you,\n{{3}}",
            body_original="Dear {{name}}.\n\nThank you for placing an order of {{total_price}} from {{shop_name}}. Please confirm your order so that we can process it.\n\nClick the link or confirm order button below to confirm your order.\n{{cod_confirm_url}}\n\nIf you wish to cancel your order, please click the link below.\n{{cod_cancel_url}}\n\nThank you,\n{{shop_name}}"
        ),
        # Sale broadcast
        Template(
            id="real_template_003",
            name="ecom_presales_oct",
            category="MARKETING",
            status="approved",
            language_option={"key": "English (US)", "value": "en_US", "text": "English (US)"},
            custom_params=[{"name": "name", "value": "Sarah"}],
            body="🎉 Exclusive Pre-Sale Alert! 🎉\nHello {{1}},  \nGet ready for our special pre-sale event! 🌟 \n🗓️ Date & Time: [Date]: [Start Time] - [End Time]  \n🔥 Benefits:  \n✅ Early access to hot products.  \n✅ Exclusive discounts. \n ✅ Limited-time deals. \n✅ Free shipping.  \n\n🛒 How to Shop: 1. Visit [Website URL]. 2. Use code [PRESALE15] at checkout for [15% off!]  \n📦 Don't miss out – mark your calendar! \nQuestions? Reply here or visit our website.  Happy shopping! 🛒✨",
            body_original="🎉 Exclusive Pre-Sale Alert! 🎉\nHello {{name}},  \nGet ready for our special pre-sale event! 🌟 \n🗓️ Date & Time: [Date]: [Start Time] - [End Time]  \n🔥 Benefits:  \n✅ Early access to hot products.  \n✅ Exclusive discounts. \n ✅ Limited-time deals. \n✅ Free shipping.  \n\n🛒 How to Shop: 1. Visit [Website URL]. 2. Use code [PRESALE15] at checkout for [15% off!]  \n📦 Don't miss out – mark your calendar! \nQuestions? Reply here or visit our website.  Happy shopping! 🛒✨"
        ),
        # Appointment reminder
        Template(
            id="real_template_004",
            name="appointment_reminder_with_buttons",
            category="UTILITY",
            status="approved",
            language_option={"key": "English (US)", "value": "en_US", "text": "English (US)"},
            custom_params=[
                {"name": "name", "value": "John"},
                {"name": "place", "value": "Clinic"},
                {"name": "date", "value": "2026-04-15 10:00 AM"}
            ],
            body="Hi *{{1}}*, This is a reminder that you have an upcoming appointment at *{{2}}* on *{{3}}*\n\nPlease confirm your availability",
            body_original="Hi *{{name}}*, This is a reminder that you have an upcoming appointment at *{{place}}* on *{{date}}*\n\nPlease confirm your availability"
        ),
        # Festival sale
        Template(
            id="real_template_005",
            name="navratri_and_dussehra_eng",
            category="MARKETING",
            status="approved",
            language_option={"key": "English (US)", "value": "en_US", "text": "English (US)"},
            custom_params=[],
            body="🌼 Navratri & Dussehra Mega Sale 🌼 \n\nThis Navratri and Dussehra, celebrate the festive season with our exclusive offers and discounts! 🎉 \n\n🛍️ Enjoy [X% Off] on a wide range of products/services.  \n🎁 Special festive bundles and gifts with every purchase.  \n🚚 Free delivery on orders over [Amount].  \n💳 Easy EMI options available.  \n\nHurry, these deals won't last long! Make your celebrations even more special with our offerings. Visit our website to explore the festive collection. Don't miss out! Offer valid until [Expiration Date].  \n\n🌟 Wishing you a joyous Navratri and a victorious Dussehra! 🌟",
            body_original="🌼 Navratri & Dussehra Mega Sale 🌼 \n\nThis Navratri and Dussehra, celebrate the festive season with our exclusive offers and discounts! 🎉 \n\n🛍️ Enjoy [X% Off] on a wide range of products/services.  \n🎁 Special festive bundles and gifts with every purchase.  \n🚚 Free delivery on orders over [Amount].  \n💳 Easy EMI options available.  \n\nHurry, these deals won't last long! Make your celebrations even more special with our offerings. Visit our website to explore the festive collection. Don't miss out! Offer valid until [Expiration Date].  \n\n🌟 Wishing you a joyous Navratri and a victorious Dussehra! 🌟"
        ),
        # Pricing info
        Template(
            id="real_template_006",
            name="pricing_wati_v1",
            category="MARKETING",
            status="approved",
            language_option={"key": "English (US)", "value": "en_US", "text": "English (US)"},
            custom_params=[],
            body="Thank you for your enquiry about your pricing.\n\n*Our setup fee is zero*\n\nMonthly Fee is $49/month\n\n*Includes*\n- 1000 free conversations\n- 5 Agents\n\nAnnual Plan fee is $40/month.",
            body_original="Thank you for your enquiry about your pricing.\n\n*Our setup fee is zero*\n\nMonthly Fee is $49/month\n\n*Includes*\n- 1000 free conversations\n- 5 Agents\n\nAnnual Plan fee is $40/month."
        ),
    ]


class MockWATIClient:
    """In-memory WATI client backed by JSON files on disk.

    Simulates network latency and persists contacts, templates, and
    tickets so state survives across runs.
    """

    def __init__(self, delay_ms: int = 100):
        """Initialize mock client.

        Args:
            delay_ms: Simulated network latency in milliseconds.
        """
        self.delay_ms = delay_ms
        self.contacts = _load_contacts()
        self.templates = _load_templates()
        self.tickets = _load_tickets()

    async def _simulate_delay(self):
        """Simulate network latency."""
        await asyncio.sleep(self.delay_ms / 1000)

    async def get_contacts(
        self, tag: str | None = None, page_size: int = 20, page_number: int = 1
    ) -> dict:
        """Get contacts list."""
        await self._simulate_delay()

        contacts = self.contacts
        if tag:
            contacts = [c for c in contacts if tag in c.tags]

        start = (page_number - 1) * page_size
        end = start + page_size
        page_contacts = contacts[start:end]

        return {
            "result": True,
            "contacts": [c.model_dump() for c in page_contacts],
            "pageInfo": {
                "pageSize": page_size,
                "pageNumber": page_number,
                "totalRecords": len(contacts),
            },
        }

    async def get_contact_info(self, whatsapp_number: str) -> dict:
        """Get detailed contact information."""
        await self._simulate_delay()

        contact = next((c for c in self.contacts if c.whatsapp_number == whatsapp_number), None)

        if not contact:
            return {"result": False, "error": "Contact not found"}

        return {"result": True, "contact": contact.model_dump()}

    async def add_tag(self, whatsapp_number: str, tag: str) -> dict:
        """Add tag to contact."""
        await self._simulate_delay()

        contact = next((c for c in self.contacts if c.whatsapp_number == whatsapp_number), None)

        if not contact:
            return {"result": False, "error": "Contact not found"}

        if tag not in contact.tags:
            contact.tags.append(tag)

        _save_contacts(self.contacts)
        return {"result": True, "message": f"Tag '{tag}' added successfully"}

    async def remove_tag(self, whatsapp_number: str, tag: str) -> dict:
        """Remove tag from contact."""
        await self._simulate_delay()

        contact = next((c for c in self.contacts if c.whatsapp_number == whatsapp_number), None)

        if not contact:
            return {"result": False, "error": "Contact not found"}

        if tag in contact.tags:
            contact.tags.remove(tag)

        _save_contacts(self.contacts)
        return {"result": True, "message": f"Tag '{tag}' removed successfully"}

    async def update_contact_attributes(
        self, whatsapp_number: str, custom_params: list[dict]
    ) -> dict:
        """Update contact custom attributes."""
        await self._simulate_delay()

        contact = next((c for c in self.contacts if c.whatsapp_number == whatsapp_number), None)

        if not contact:
            return {"result": False, "error": "Contact not found"}

        for param in custom_params:
            contact.custom_params[param["name"]] = param["value"]

        _save_contacts(self.contacts)
        return {"result": True, "message": "Attributes updated successfully"}

    async def send_session_message(self, whatsapp_number: str, message_text: str) -> dict:
        """Send session message."""
        await self._simulate_delay()

        contact = next((c for c in self.contacts if c.whatsapp_number == whatsapp_number), None)

        if not contact:
            return {"result": False, "error": "Contact not found"}

        return {
            "result": True,
            "messageId": f"msg_{whatsapp_number}_{asyncio.get_event_loop().time()}",
            "message": "Session message sent successfully",
        }

    async def send_template_message(
        self, template_name: str, broadcast_name: str, scheduled_at: datetime, recipients: list[dict], channel: str = None
    ) -> dict:
        """Send template message and create local file record.

        Args:
            template_name: Template name
            broadcast_name: Broadcast name
            scheduled_at: Scheduled time (ignored in mock, sends immediately)
            recipients: List of {whatsappNumber, customParams}
            channel: Channel (ignored in mock)
        """
        await self._simulate_delay()

        template = next((t for t in self.templates if t.name == template_name), None)
        if not template:
            return {"result": False, "error": f"Template '{template_name}' not found"}

        results = []
        for recipient in recipients:
            whatsapp_number = recipient.get("whatsappNumber")
            custom_params = recipient.get("customParams", [])

            contact = next((c for c in self.contacts if c.whatsapp_number == whatsapp_number), None)
            if not contact:
                results.append({"whatsappNumber": whatsapp_number, "status": "failed", "error": "Contact not found"})
                continue

            # Create message record file
            file_path = self._create_message_record(contact, template, custom_params)
            results.append({
                "whatsappNumber": whatsapp_number,
                "status": "sent",
                "messageId": f"msg_{whatsapp_number}_{asyncio.get_event_loop().time()}"
            })

        return {
            "result": True,
            "broadcast_name": broadcast_name,
            "template_name": template_name,
            "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
            "total_recipients": len(recipients),
            "sent": len([r for r in results if r["status"] == "sent"]),
            "failed": len([r for r in results if r["status"] == "failed"]),
            "details": results
        }

    def _create_message_record(self, contact: Contact, template: Template, parameters: list[dict]) -> str:
        """Write a text file simulating a delivered WhatsApp message.

        Returns:
            Path to the created message file.
        """
        # Create messages directory - use project root if /app doesn't exist
        messages_dir = Path("/app/mock_messages")
        if not messages_dir.exists() and not messages_dir.parent.exists():
            messages_dir = _PROJECT_ROOT / "mock_messages"

        messages_dir.mkdir(exist_ok=True)

        # Create contact-specific directory
        contact_name = contact.name.replace(" ", "_") if contact.name else "Unknown"
        contact_dir = messages_dir / f"{contact_name}_{contact.whatsapp_number}"
        contact_dir.mkdir(exist_ok=True)

        # Generate message content
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        message_file = contact_dir / f"{timestamp}_{template.name}.txt"

        # Fill template with parameters
        message_body = template.body
        for i, param in enumerate(parameters, 1):
            placeholder = f"{{{{{i}}}}}"
            message_body = message_body.replace(placeholder, param.get("value", ""))

        # Write message record
        content = f"""=== WhatsApp Template Message ===
Recipient: {contact.name}
Phone: {contact.whatsapp_number}
Template: {template.name}
Category: {template.category}
Sent At: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

--- Message Content ---
{message_body}

--- Contact Info ---
Tags: {', '.join(contact.tags)}
City: {contact.custom_params.get('city', 'N/A')}
Tier: {contact.custom_params.get('tier', 'N/A')}
Language: {contact.custom_params.get('language', 'N/A')}

--- Parameters ---
"""
        for i, param in enumerate(parameters, 1):
            content += f"{{{{{{i}}}}}}: {param.get('value', 'N/A')}\n"

        message_file.write_text(content, encoding="utf-8")
        return str(message_file)

    async def get_all_template_message(
        self, page_number: int = 1, page_size: int = 100
    ) -> dict:
        """Get message templates with pagination.

        Returns:
            {
                "templates": [...],
                "page_number": 1,
                "page_size": 100,
                "total": 5
            }
        """
        await self._simulate_delay()

        start = (page_number - 1) * page_size
        end = start + page_size
        page_templates = self.templates[start:end]

        return {
            "templates": [t.model_dump() for t in page_templates],
            "page_number": page_number,
            "page_size": page_size,
            "total": len(self.templates)
        }

    async def get_message_templates(self, page_size: int = 20, page_number: int = 1) -> dict:
        """Get available message templates."""
        await self._simulate_delay()

        start = (page_number - 1) * page_size
        end = start + page_size
        page_templates = self.templates[start:end]

        return {
            "result": True,
            "messageTemplates": [t.model_dump() for t in page_templates],
            "pageInfo": {
                "pageSize": page_size,
                "pageNumber": page_number,
                "totalRecords": len(self.templates),
            },
        }

    async def assign_operator(self, whatsapp_number: str, email: str) -> dict:
        """Assign conversation to operator."""
        await self._simulate_delay()

        contact = next((c for c in self.contacts if c.whatsapp_number == whatsapp_number), None)

        if not contact:
            return {"result": False, "error": "Contact not found"}

        return {
            "result": True,
            "message": f"Conversation assigned to {email}",
        }

    async def assign_team(self, whatsapp_number: str, team_name: str) -> dict:
        """Assign conversation to team."""
        await self._simulate_delay()

        contact = next((c for c in self.contacts if c.whatsapp_number == whatsapp_number), None)

        if not contact:
            return {"result": False, "error": "Contact not found"}

        return {
            "result": True,
            "message": f"Conversation assigned to team '{team_name}'",
        }

    async def create_ticket(self, subject: str, priority: str = "medium",
                           reporter: str = None, assignee: str = None) -> dict:
        """Create support ticket."""
        await self._simulate_delay()

        ticket_id = f"TKT-{int(asyncio.get_event_loop().time())}"
        ticket = Ticket(
            ticket_id=ticket_id,
            subject=subject,
            priority=priority,
            status="open",
            reporter=reporter or "unknown",
            assignee=assignee,
            created_at=datetime.now().isoformat(),
            resolved_at=None,
            resolution=None
        )

        self.tickets.append(ticket)
        _save_tickets(self.tickets)

        return ticket.model_dump()

    async def resolve_ticket(self, ticket_id: str, resolution: str = "") -> dict:
        """Resolve support ticket."""
        await self._simulate_delay()

        ticket = next((t for t in self.tickets if t.ticket_id == ticket_id), None)
        if not ticket:
            return {"result": False, "error": "Ticket not found"}

        ticket.status = "resolved"
        ticket.resolution = resolution
        ticket.resolved_at = datetime.now().isoformat()

        _save_tickets(self.tickets)

        return ticket.model_dump()

    async def send_broadcast_to_segment(
        self, template_name: str, broadcast_name: str, segment_name: str
    ) -> dict:
        """Send broadcast to segment."""
        await self._simulate_delay()

        template = next((t for t in self.templates if t.name == template_name), None)

        if not template:
            return {"result": False, "error": f"Template '{template_name}' not found"}

        # Simulate broadcast to segment
        return {
            "result": True,
            "broadcastId": f"broadcast_{asyncio.get_event_loop().time()}",
            "message": f"Broadcast '{broadcast_name}' sent to segment '{segment_name}'",
        }
