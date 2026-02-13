"""
Local Provider - On-Device LLM Backend
Stub for local LLM implementation.
Subclasses BaseProvider.
"""

from typing import Dict, Any, List
from src.cognitive.providers.base_provider import BaseProvider
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class LocalProvider(BaseProvider):
    """Provider for local/on-device LLM execution."""
    
    def __init__(self):
        """Initialize local provider."""
        logger.info("Local Provider initialized (stub).")
    
    async def generate_plan(self, prompt: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a plan for command execution.
        
        Args:
            prompt: User input
            tools: List of available tool schemas
            
        Returns:
            dict with plan structure
        """
        raise NotImplementedError("Local provider plan generation not yet implemented.")
    
    async def chat(self, prompt: str) -> str:
        """
        Generate a chat response.
        
        Args:
            prompt: User input
            
        Returns:
            str with chat response
        """
        raise NotImplementedError("Local provider chat not yet implemented.")
