from typing import Dict, Any, List, Optional
from src.cognitive.providers.base_llm import BaseLLM

class MockProvider(BaseLLM):
    """Mock LLM provider for testing"""
    
    async def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        if "open chrome" in prompt_lower:
            return {"tool": "open_app", "args": {"app": "chrome"}}
        return {"tool": None, "reply": f"Mock response to: {prompt}"}
