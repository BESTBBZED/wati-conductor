#!/usr/bin/env python3
"""Clean conversation history."""

import json
from pathlib import Path

HISTORY_FILE = Path("/app/history/current_session.json")

if HISTORY_FILE.exists():
    HISTORY_FILE.write_text("[]")
    print(f"✅ Cleaned {HISTORY_FILE}")
else:
    print(f"⚠️  {HISTORY_FILE} does not exist")
