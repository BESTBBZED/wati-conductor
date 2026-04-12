"""Message sending tools for session and template messages."""

import json
from datetime import datetime
from pathlib import Path
from langchain.tools import tool
from conductor.clients.factory import get_wati_client


@tool
async def send_session_message(whatsapp_number: str, message_text: str) -> dict:
    """Send a session message to a contact (within 24-hour window)."""
    client = get_wati_client()
    return await client.send_session_message(whatsapp_number, message_text)


@tool
async def send_template_message_batch(
    contacts: list[dict], template_name: str, broadcast_name: str = None, parameter_mapping: dict | None = None
) -> dict:
    """Send template message to multiple contacts in batch.

    Args:
        contacts: List of contact dictionaries (must have 'whatsapp_number' field).
        template_name: Name of the approved template.
        broadcast_name: Broadcast name (auto-generated if not provided).
        parameter_mapping: Optional mapping of parameter names to contact field names.
                          If not provided, will auto-map common parameters like 'name'.

    Returns:
        Dictionary with sent/failed counts and details.
    """
    client = get_wati_client()
    
    if not broadcast_name:
        broadcast_name = f"broadcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Get template details to know what parameters are needed
    template_result = await client.get_all_template_message(page_size=100)
    template = next((t for t in template_result.get("templates", []) if t["name"] == template_name), None)
    
    # Auto-generate parameter_mapping if not provided
    if not parameter_mapping and template:
        parameter_mapping = {}
        for param in template.get("custom_params", []):
            param_name = param.get("name")
            # Auto-map common parameters
            if param_name == "name":
                parameter_mapping["name"] = "name"
            elif param_name in ["city", "tier", "language"]:
                parameter_mapping[param_name] = f"custom_params.{param_name}"
    
    # Build recipients list
    recipients = []
    for contact in contacts:
        whatsapp_number = contact.get("whatsapp_number") or contact.get("whatsappNumber")
        if not whatsapp_number:
            continue
        
        # Build customParams from parameter_mapping
        custom_params = []
        if parameter_mapping:
            for param_name, field_path in parameter_mapping.items():
                # Support nested field access like "custom_params.city"
                if "." in field_path:
                    parts = field_path.split(".")
                    value = contact
                    for part in parts:
                        value = value.get(part, {}) if isinstance(value, dict) else ""
                        if not value:
                            break
                else:
                    value = contact.get(field_path, "")
                
                custom_params.append({"name": param_name, "value": str(value)})
        
        recipients.append({
            "whatsappNumber": whatsapp_number,
            "customParams": custom_params
        })
    
    if not recipients:
        return {"result": False, "error": "No valid recipients"}
    
    # Send immediately (scheduled_at = now)
    result = await client.send_template_message(
        template_name, 
        broadcast_name, 
        datetime.now(),
        recipients
    )
    
    # Save demo result with message preview
    _save_demo_result(template_name, result, template, recipients)
    
    return result


def _save_demo_result(template_name: str, result: dict, template: dict | None, recipients: list[dict]):
    """Persist a JSON record of the send operation for demo/debugging purposes."""
    outputs_dir = Path("/app/outputs")
    if not outputs_dir.exists() and not outputs_dir.parent.exists():
        outputs_dir = Path.cwd() / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"send_template_{template_name}_{timestamp}.json"
    
    # Build message preview for each recipient
    message_previews = []
    if template:
        for recipient in recipients:
            # Fill template body with parameters
            message_body = template.get("body_original", template.get("body", ""))
            for param in recipient.get("customParams", []):
                param_name = param.get("name")
                param_value = param.get("value")
                message_body = message_body.replace(f"{{{{{param_name}}}}}", param_value)
            
            message_previews.append({
                "whatsappNumber": recipient.get("whatsappNumber"),
                "parameters": recipient.get("customParams", []),
                "message_preview": message_body[:200] + "..." if len(message_body) > 200 else message_body
            })
    
    demo_result = {
        "timestamp": datetime.now().isoformat(),
        "template_name": template_name,
        "template_category": template.get("category") if template else None,
        "result": result,
        "message_previews": message_previews
    }
    
    output_path = outputs_dir / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(demo_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Demo result saved to: /app/outputs/{filename}")
