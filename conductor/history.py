"""Conversation history — persists user/AI turns to a JSON session file."""

import json
from datetime import datetime
from pathlib import Path


_HISTORY_DIR = Path(__file__).resolve().parent.parent / "history"
_CURRENT_SESSION_FILE = _HISTORY_DIR / "current_session.json"


def load_conversation_history() -> list[dict]:
    """Load all turns from the current session file."""
    if _CURRENT_SESSION_FILE.exists():
        with open(_CURRENT_SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_conversation_turn(instruction: str, response: str):
    """Append a user instruction + AI response pair to the session file."""
    _HISTORY_DIR.mkdir(exist_ok=True)
    
    history = load_conversation_history()
    
    turn = {
        "timestamp": datetime.now().isoformat(),
        "human": instruction,
        "ai": response
    }
    
    history.append(turn)
    
    with open(_CURRENT_SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def clear_conversation_history():
    """Clear current session history."""
    if _CURRENT_SESSION_FILE.exists():
        _CURRENT_SESSION_FILE.unlink()


def get_recent_context(max_turns: int = 3) -> str:
    """Return the last few conversation turns as a plain-text string.

    Strips non-ASCII characters to avoid serialization issues with some LLM APIs.
    """
    import re
    
    history = load_conversation_history()
    
    if not history:
        return ""
    
    recent = history[-max_turns:]
    
    # Remove emoji to avoid JSON serialization issues with Anthropic API
    def remove_emoji(text: str) -> str:
        """Strip non-ASCII characters (emoji, etc.) from text."""
        return re.sub(r'[^\x00-\x7F]+', '', text)
    
    lines = ["Recent conversation:"]
    for turn in recent:
        human_text = remove_emoji(turn['human'])
        ai_text = remove_emoji(turn['ai'])
        lines.append(f"Human: {human_text}")
        lines.append(f"AI: {ai_text}")
    
    return "\n".join(lines)
