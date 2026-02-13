"""
Base Provider Interface
Abstract base class for LLM providers.
No implementation allowed.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class RateLimitError(Exception):
    """Raised when an LLM provider hits a rate limit."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_plan(self, prompt: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a plan from the LLM for command execution.
        
        Args:
            prompt: User input
            tools: List of available tool schemas
            
        Returns:
            dict with plan structure
        """
        pass
    
    @abstractmethod
    async def chat(self, prompt: str) -> str:
        """
        Generate a chat response from the LLM.
        
        Args:
            prompt: User input
            
        Returns:
            str with chat response
        """
        pass
