"""
Local Router - Offline Intent Handling
Handles common intents locally without LLM.
Fast, reliable, non-async pattern matching.
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class LocalRouter:
    """Handles locally-supported intents without calling LLM."""
    
    # Regex patterns for intent detection
    PATTERNS = {
        "greeting": r"^(hi|hello|hey|yo|good morning|good afternoon|good evening|howdy)\b",
        "farewell": r"^(bye|goodbye|exit|quit)\b",
        # Specific browser pattern - MUST match before open_app
        "open_website_browser": r"^(?:open|search|browse)\s+(?P<site>[\w\.]+)\s+(?:in|using|on|with)\s+(?P<browser>chrome|firefox|brave|edge|opera|safari)\b",
        "website_only": r"^(open|search|visit|browse)\s+(?P<site>[\w\.]+\.(com|org|net|io|edu|gov|co|ai))\b",
        "open_app": r"^(?:open|launch|start)\s+(?P<app>[a-zA-Z0-9\s]+)$",
        "time_query": r"(time|what.{0,5}time|tell me the time)",
        "date_query": r"(date|today|what.{0,5}today)",
        "help": r"^(help|what can you do|capabilities|what are your capabilities|what can you help with)$",
        "thank_you": r"(thank you|thanks|appreciate it|thanks for that)",
    }

    # Common web services that should be handled by LLM/Planner instead of local open_app
    WEB_SERVICE_KEYWORDS = {
        "chatgpt", "google", "youtube", "gmail", "facebook", "instagram", 
        "twitter", "x", "linkedin", "github", "reddit", "netflix", "spotify",
        "amazon", "outlook", "discord", "whatsapp", "gemini", "claude"
    }
    
    def __init__(self):
        """Initialize LocalRouter."""
        logger.info("LocalRouter initialized")
    
    def route(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Route text to locally-handled intent.
        
        Args:
            text: Normalized user input (already processed by Interpreter)
            
        Returns:
            dict with {"type": "chat"|"plan", ...} if handled
            None if should go to Planner (LLM)
        """
        if not isinstance(text, str) or not text.strip():
            return None
        
        text_lower = text.lower().strip()
        
        # Try each pattern (order matters - more specific patterns first)
        result = self._match_greeting(text_lower)
        if result:
            return result
        
        result = self._match_farewell(text_lower)
        if result:
            return result
        
        # Website patterns before app patterns (more specific)
        result = self._match_open_website(text_lower)
        if result:
            return result
        
        result = self._match_open_app(text_lower)
        if result:
            return result
        
        result = self._match_time(text_lower)
        if result:
            return result
        
        result = self._match_date(text_lower)
        if result:
            return result
        
        result = self._match_help(text_lower)
        if result:
            return result
        
        result = self._match_thank_you(text_lower)
        if result:
            return result
        
        # No local match
        logger.debug("[LocalRouter] no match")
        return None
    
    @staticmethod
    def _match_greeting(text: str) -> Optional[Dict[str, Any]]:
        """Match greeting intents."""
        if re.match(LocalRouter.PATTERNS["greeting"], text):
            logger.info("[LocalRouter] handled greeting")
            return {
                "type": "chat",
                "response": "Hello, sir. How can I assist you today?"
            }
        return None
    
    @staticmethod
    def _match_farewell(text: str) -> Optional[Dict[str, Any]]:
        """Match farewell intents."""
        if re.match(LocalRouter.PATTERNS["farewell"], text):
            logger.info("[LocalRouter] handled farewell")
            return {
                "type": "chat",
                "response": "Goodbye, sir. Have a great day."
            }
        return None
    
    @staticmethod
    def _match_open_app(text: str) -> Optional[Dict[str, Any]]:
        """Match open app intents."""
        match = re.match(LocalRouter.PATTERNS["open_app"], text)
        if match:
            app = match.group("app").strip()
            
            # EXCLUSION: If the app name is a known web service, fall back to LLM
            if app.lower() in LocalRouter.WEB_SERVICE_KEYWORDS:
                logger.info(f"[LocalRouter] excluding web service '{app}' from local open_app")
                return None

            logger.info(f"[LocalRouter] handled open_app: {app}")
            return {
                "type": "plan",
                "response": f"Certainly sir, opening {app} for you.",
                "steps": [
                    {"tool": "open_app", "args": {"app": app}}
                ]
            }
        return None
    
    @staticmethod
    def _match_open_website(text: str) -> Optional[Dict[str, Any]]:
        """Match open website with browser intents."""
        match = re.match(LocalRouter.PATTERNS["open_website_browser"], text)
        if match:
            site = match.group("site")
            browser = match.group("browser")
            logger.info(f"[LocalRouter] handled open_website: {site} in {browser}")
            
            # Normalize site if needed
            if not site.startswith("http"):
                site = f"https://{site}" if "." in site else f"https://www.google.com/search?q={site}"
            
            return {
                "type": "plan",
                "response": f"Right away sir, opening {site} in {browser}.",
                "steps": [
                    {"tool": "open_website", "args": {"url": site, "browser": browser}}
                ]
            }
        
        # Try simple website opening (without browser specified)
        match = re.match(LocalRouter.PATTERNS["website_only"], text)
        if match:
            site = match.group("site")
            logger.info(f"[LocalRouter] handled open_website: {site}")
            
            # Normalize site
            if not site.startswith("http"):
                site = f"https://{site}"
            
            return {
                "type": "plan",
                "response": f"Of course sir, navigating to {site}.",
                "steps": [
                    {"tool": "open_website", "args": {"url": site}}
                ]
            }
        
        return None
    
    @staticmethod
    def _match_time(text: str) -> Optional[Dict[str, Any]]:
        """Match time query intents."""
        if re.search(LocalRouter.PATTERNS["time_query"], text):
            current_time = datetime.now().strftime("%I:%M %p")
            logger.info("[LocalRouter] handled time query")
            return {
                "type": "chat",
                "response": f"The current time is {current_time}, sir."
            }
        return None
    
    @staticmethod
    def _match_date(text: str) -> Optional[Dict[str, Any]]:
        """Match date query intents."""
        if re.search(LocalRouter.PATTERNS["date_query"], text):
            current_date = datetime.now().strftime("%A, %B %d, %Y")
            logger.info("[LocalRouter] handled date query")
            return {
                "type": "chat",
                "response": f"Today is {current_date}, sir."
            }
        return None
    
    @staticmethod
    def _match_help(text: str) -> Optional[Dict[str, Any]]:
        """Match help/capabilities intents."""
        if re.match(LocalRouter.PATTERNS["help"], text):
            logger.info("[LocalRouter] handled help")
            return {
                "type": "chat",
                "response": (
                    "I can help you with: "
                    "opening applications, browsing websites, telling time and date, "
                    "and executing system commands. What would you like me to do, sir?"
                )
            }
        return None
    
    @staticmethod
    def _match_thank_you(text: str) -> Optional[Dict[str, Any]]:
        """Match thank you intents."""
        if re.search(LocalRouter.PATTERNS["thank_you"], text):
            logger.info("[LocalRouter] handled thank you")
            return {
                "type": "chat",
                "response": "You're welcome, sir. Happy to help."
            }
        return None
