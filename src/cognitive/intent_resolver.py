import json
import re
from typing import Optional, Dict, Any
from src.core.intent_model import Intent
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class IntentResolver:
    def __init__(self, intents_config_path: str = "config/intents.json"):
        self.config_path = intents_config_path
        self.exact_commands = {}
        self.patterns = []
        self._load_config()
        
    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.exact_commands = data.get("exact_commands", {})
                self.patterns = data.get("patterns", [])
                
                for p in self.patterns:
                    p["compiled"] = re.compile(p["regex"], re.IGNORECASE)
                    
        except Exception as e:
            logger.error(f"Failed to load intents config: {e}")
            
    def resolve(self, text: str) -> Intent:
        """
        Resolve text to structured Intent with classification.
        """
        raw_text = text.lower().strip()
        text = raw_text
        
        if text.startswith("jarvis"):
            text = text.replace("jarvis", "", 1).strip(", ").strip()

        # 1. Unsafe/Dangerous Check
        unsafe_patterns = [r"delete system32", r"format c:", r"erase drive"]
        if any(re.search(p, text) for p in unsafe_patterns):
            return Intent("unsafe_action", {}, "unsafe", False, 1.0, "security_failsafe")

        # 2. Information Check (Time/Date)
        if any(x in text for x in ["what time", "what is the time", "what's the time", "today's date", "what is the date"]):
             # Map to names used in ActionRouter logic if still needed, but type is information
             name = "system_time" if "time" in text else "system_date"
             return Intent(name, {}, "information", False, 1.0, "exact")

        # 3. Conversation Check
        greetings = ["hello", "hi", "hey", "greetings", "how are you", "good morning", "good evening"]
        if any(text == g or text.startswith(g + " ") for g in greetings):
            return Intent("greeting", {}, "conversation", False, 1.0, "heuristic")

        # 4. Pattern Match (System Actions)
        for p in self.patterns:
            match = p["compiled"].match(text)
            if match:
                data = p["intent"]
                params = data.get("params", {}).copy()
                if match.groups():
                    params["target"] = match.group(1)
                
                # Registry-backed intents are system_actions
                return Intent(
                    name=data["action"],
                    args=params,
                    type="system_action",
                    requires_execution=True,
                    confidence=0.9,
                    source="pattern"
                )
                
        # 5. Exact Match (Legacy/Manual)
        if text in self.exact_commands:
            data = self.exact_commands[text]
            # Check if it looks like an action
            is_action = any(x in data["action"] for x in ["open", "close", "launch", "restart"])
            return Intent(
                name=data["action"],
                args=data.get("params", {}),
                type="system_action" if is_action else "information",
                requires_execution=is_action,
                confidence=1.0,
                source="exact"
            )

        # 6. Fallback to Conversation
        return Intent("unknown", {}, "conversation", False, 0.0, "fallback")
