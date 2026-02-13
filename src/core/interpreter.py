"""
Interpreter - User Input Normalization
Normalizes user input before LLM sees it.
Never calls LLM.
"""

import re
from typing import Dict, Any
from src.core.logging_config import get_logger

logger = get_logger(__name__)

# Command keywords to detect command intents
COMMAND_KEYWORDS = {
    "open", "launch", "start", "close", "exit", "quit",
    "search", "play", "stop", "pause", "resume",
    "run", "execute", "kill", "end", "terminate"
}

class Interpreter:
    """Normalizes and classifies user input."""
    
    @staticmethod
    def interpret(text: str) -> Dict[str, Any]:
        """
        Normalize user input and classify intent.
        
        Args:
            text: Raw user input
            
        Returns:
            dict with keys:
            - intent_type: "chat" | "command"
            - text: normalized text
            - metadata: {}
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        # Strip wake word (case insensitive)
        normalized = Interpreter._strip_wake_word(text)
        
        # Lowercase
        normalized = normalized.lower()
        
        # Trim spaces
        normalized = normalized.strip()
        
        # Empty input
        if not normalized:
            return {
                "intent_type": "chat",
                "text": normalized,
                "metadata": {}
            }
        
        # Detect command keywords in first word
        first_word = normalized.split()[0] if normalized else ""
        intent_type = "command" if first_word in COMMAND_KEYWORDS else "chat"
        
        return {
            "intent_type": intent_type,
            "text": normalized,
            "metadata": {}
        }
    
    @staticmethod
    def _strip_wake_word(text: str) -> str:
        """
        Remove wake word 'jarvis' from start of text.
        Case insensitive.
        """
        # Pattern: optional whitespace, then "jarvis", then optional whitespace/comma/period
        pattern = r"^\s*jarvis[\s,.\-]?"
        stripped = re.sub(pattern, "", text, flags=re.IGNORECASE)
        return stripped if stripped else text
