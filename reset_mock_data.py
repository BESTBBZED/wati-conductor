#!/usr/bin/env python3
"""Reset mock data - regenerate contacts and templates."""

import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from conductor.clients.mock import (
    _generate_contacts, 
    _generate_templates, 
    _MOCK_DATA_DIR, 
    _CONTACTS_FILE, 
    _TEMPLATES_FILE,
    _TICKETS_FILE
)


def reset_mock_data():
    """Regenerate and save mock contacts and templates."""
    print("🔄 Resetting mock data...")
    
    # Create directory
    _MOCK_DATA_DIR.mkdir(exist_ok=True)
    
    # Generate contacts
    contacts = _generate_contacts()
    with open(_CONTACTS_FILE, "w") as f:
        json.dump([c.model_dump() for c in contacts], f, indent=2)
    print(f"✅ Generated {len(contacts)} contacts → {_CONTACTS_FILE}")
    
    # Generate templates
    templates = _generate_templates()
    with open(_TEMPLATES_FILE, "w") as f:
        json.dump([t.model_dump() for t in templates], f, indent=2)
    print(f"✅ Generated {len(templates)} templates → {_TEMPLATES_FILE}")
    
    # Reset tickets to empty
    with open(_TICKETS_FILE, "w") as f:
        json.dump([], f, indent=2)
    print(f"✅ Reset tickets → {_TICKETS_FILE}")
    
    print("\n🎉 Mock data reset complete!")


if __name__ == "__main__":
    reset_mock_data()
