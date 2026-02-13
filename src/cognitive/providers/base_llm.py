from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseLLM(ABC):
    """Abstract Base Class for LLM Providers"""
    
    @abstractmethod
    async def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        Should return a dictionary with either 'tool' and 'args' or 'reply'.
        """
        pass
