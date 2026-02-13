"""
Mock Provider - Testing Backend
Stub for mock LLM used in testing.
Subclasses BaseProvider.
"""

from typing import Dict, Any, List
from src.cognitive.providers.base_provider import BaseProvider
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class MockProvider(BaseProvider):
    """Provider for mock/test LLM responses."""
    
    def __init__(self):
        """Initialize mock provider."""
        logger.info("Mock Provider initialized.")
    
    async def generate_plan(self, prompt: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a mock plan for testing.
        
        Args:
            prompt: User input
            tools: List of available tool schemas
            
        Returns:
            dict with mock plan structure
        """
        raise NotImplementedError("Mock provider plan generation not yet implemented.")
    
    async def chat(self, prompt: str) -> str:
        """
        Generate a mock chat response.
        
        Args:
            prompt: User input
            
        Returns:
            str with mock response
        """
        raise NotImplementedError("Mock provider chat not yet implemented.")
