"""
Security Manager - Protects Jarvis and the System
Handles:
- PII Redaction (Email, Keys, IPs)
- Command Blacklisting (Dangerous system calls)
- Response Sanitization
"""

import re
from typing import Dict, Any, List
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class SecurityManager:
    def __init__(self):
        # Blacklisted commands/keywords for system execution
        self.dangerous_keywords = [
            r"\brm\b", r"\bdel\b", r"\berase\b", r"\bformat\b", 
            r"\bshutdown\b", r"\breboot\b", r"\bkill\b", r"\btaskkill\b",
            r"\bwipe\b", r"\bdrop\b", r"\btruncate\b"
        ]
        
        # PII Regex patterns
        self.pii_patterns = {
            "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "aws_key": r"AKIA[0-9A-Z]{16}",
            "generic_secret": r"(?:key|password|secret|token|auth)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]+)"
        }

    def is_safe_command(self, command: str) -> bool:
        """Check if a system command contains dangerous keywords"""
        command = command.lower()
        for pattern in self.dangerous_keywords:
            if re.search(pattern, command):
                logger.warning(f"Security Block: Dangerous keyword detected in command: {command}")
                return False
        return True

    def redact_pii(self, text: str) -> str:
        """Redact sensitive information from strings"""
        if not text:
            return text
            
        redacted = text
        try:
            for label, pattern in self.pii_patterns.items():
                redacted = re.sub(pattern, f"[{label.upper()}_REDACTED]", redacted, flags=re.IGNORECASE)
        except Exception as e:
            logger.error(f"Redaction error: {e}")
            
        return redacted

    def sanitize_action(self, action: str, params: Dict[str, Any]) -> bool:
        """Verify if an action and its params are safe to execute"""
        # Block dangerous close/kill actions
        if action == "app.close":
            target = str(params.get("target", "")).lower()
            protected_apps = ["explorer", "system", "svchost", "wininit", "jarvis"]
            if any(app in target for app in protected_apps):
                logger.warning(f"Security Block: Attempted to close protected app: {target}")
                return False
        
        return True

# Singleton
_security_manager = SecurityManager()

def get_security_manager():
    return _security_manager
