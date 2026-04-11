"""Message sending tools."""

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

    Returns:
        Dictionary with sent/failed counts and details.
    """
    client = get_wati_client()
    
    if not broadcast_name:
        broadcast_name = f"broadcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Build recipients list
    recipients = []
    for contact in contacts:
        whatsapp_number = contact.get("whatsapp_number")
        if not whatsapp_number:
            continue
        
        # Build customParams from parameter_mapping
        custom_params = []
        if parameter_mapping:
            for param_name, field_name in parameter_mapping.items():
                value = contact.get(field_name, "")
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
    
    # Save demo result
    _save_demo_result(template_name, result)
    
    return result


def _save_demo_result(template_name: str, result: dict):
    """Save send template result to outputs directory for demo purposes."""
    outputs_dir = Path("/app/outputs")
    outputs_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"send_template_{template_name}_{timestamp}.json"
    
    demo_result = {
        "timestamp": datetime.now().isoformat(),
        "template_name": template_name,
        "result": result
    }
    
    output_path = outputs_dir / filename
    with open(output_path, "w") as f:
        json.dump(demo_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Demo result saved to: /app/outputs/{filename}")
