"""
Response Generator - Template-based response system for Phase 2

Provides simple, varied responses for different scenarios.
Will be replaced by Gemini-powered personality in Phase 4.
"""

import random
from typing import Dict, List


class ResponseGenerator:
    """
    Generates template-based responses for Jarvis.
    
    Features:
    - Multiple response variations to avoid repetition
    - Variable substitution for dynamic content
    - Response categories (acknowledge, success, failure, timeout)
    """
    
    def __init__(self):
        """Initialize response templates"""
        self.templates = {
            "acknowledge": [
                "Right away, sir",
                "Certainly, sir",
                "At your service, sir",
                "Of course, sir",
                "Yes, sir"
            ],
            "success": [
                "{action} complete, sir",
                "{target} is ready, sir",
                "Done, sir",
                "Task completed, sir",
                "{action} successful, sir"
            ],
            "failure": [
                "I'm afraid that didn't work, sir",
                "My apologies, sir. {error}",
                "Unable to {action}, sir",
                "That command failed, sir. {error}",
                "I encountered an error, sir: {error}"
            ],
            "timeout": [
                "I'll be here if you need me, sir",
                "Standing by, sir",
                "Awaiting your command, sir"
            ],
            "greeting": [
                "Yes, sir?",
                "At your service, sir",
                "How may I assist you, sir?",
                "Ready when you are, sir",
                "Here, sir",
                "Awaiting your command, sir",
                "Good to hear from you, sir",
                "I'm listening, sir",
                "What can I do for you, sir?",
                "Standing by, sir"
            ],
            "unknown": [
                "I didn't quite understand that, sir",
                "Could you rephrase that, sir?",
                "I'm not sure what you mean, sir",
                "Pardon me, sir, I didn't catch that"
            ]
        }
    
    def generate(self, category: str, **kwargs) -> str:
        """
        Generate a response from the specified category
        
        Args:
            category: Response category (acknowledge, success, failure, etc.)
            **kwargs: Variables for template substitution
            
        Returns:
            Generated response string
        """
        templates = self.templates.get(category, self.templates["unknown"])
        template = random.choice(templates)
        
        # Variable substitution
        try:
            response = template.format(**kwargs)
        except KeyError:
            # If variable missing, return template as-is
            response = template
        
        return response
    
    def acknowledge(self) -> str:
        """Generate an acknowledgment response"""
        return self.generate("acknowledge")
    
    def success(self, action: str = "Task", target: str = "") -> str:
        """
        Generate a success response
        
        Args:
            action: Action that was performed
            target: Target of the action
        """
        return self.generate("success", action=action, target=target)
    
    def failure(self, action: str = "execute command", error: str = "") -> str:
        """
        Generate a failure response
        
        Args:
            action: Action that failed
            error: Error description
        """
        return self.generate("failure", action=action, error=error)
    
    def timeout(self) -> str:
        """Generate a timeout response"""
        return self.generate("timeout")
    
    def greeting(self) -> str:
        """Generate a greeting response"""
        return self.generate("greeting")
    
    def unknown(self) -> str:
        """Generate an unknown command response"""
        return self.generate("unknown")


# Singleton instance
_response_generator: ResponseGenerator = None


def get_response_generator() -> ResponseGenerator:
    """
    Get or create the global ResponseGenerator instance
    
    Returns:
        Global ResponseGenerator instance
    """
    global _response_generator
    
    if _response_generator is None:
        _response_generator = ResponseGenerator()
    
    return _response_generator
