"""
LLM Handler - Provider-Agnostic Architecture
Orchestrates LLM calls across multiple providers with failover support.
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from src.core.logging_config import get_logger
from src.tools.registry import list_schemas
from src.cognitive.llm_factory import LLMFactory
from src.cognitive.providers.base_llm import BaseLLM

logger = get_logger(__name__)

class LLMHandler:
    def __init__(self, config_path: str = "config.json"):
        # Load providers based on config
        self.providers: List[BaseLLM] = LLMFactory.get_providers_from_config(config_path)
        logger.info(f"LLM Handler initialized with {len(self.providers)} providers.")

    async def analyze_and_respond(self, user_input: str) -> Dict[str, Any]:
        """
        Attempt to generate a response using the provider chain.
        Primary provider -> secondary -> fallback text responder.
        """
        tools = list_schemas()
        
        # Try each provider in the chain
        for provider in self.providers:
            try:
                response = await provider.generate(user_input, tools=tools)
                if response:
                    return response
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} failed: {e}")
                continue # Try next provider
        
        # Absolute fallback if all providers fail
        return {
            "tool": None, 
            "reply": "I'm having trouble connecting to my cognitive services right now, sir. I apologize."
        }
