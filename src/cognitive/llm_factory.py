import os
import json
from typing import List, Optional
from src.cognitive.providers.base_llm import BaseLLM
from src.cognitive.providers.gemini_provider import GeminiProvider
from src.cognitive.providers.local_provider import LocalProvider
from src.cognitive.providers.mock_provider import MockProvider
from src.core.config_manager import load_json

class LLMFactory:
    @staticmethod
    def create_provider(provider_type: str, **kwargs) -> BaseLLM:
        """Create an LLM provider instance based on type"""
        if provider_type == "gemini":
            return GeminiProvider(**kwargs)
        elif provider_type == "local":
            return LocalProvider(**kwargs)
        elif provider_type == "mock":
            return MockProvider()
        else:
            raise ValueError(f"Unknown LLM provider type: {provider_type}")

    @staticmethod
    def get_providers_from_config(config_path: str = "config.json") -> List[BaseLLM]:
        """
        Load provider chain from config.
        Default to [gemini] if not specified.
        """
        config = load_json(config_path)
        llm_config = config.get("llm", {})
        provider_names = llm_config.get("providers", ["gemini"])
        
        provider_instances = []
        for name in provider_names:
            try:
                # Use kwargs from config if available (e.g. model name)
                kwargs = llm_config.get(f"{name}_config", {})
                provider_instances.append(LLMFactory.create_provider(name, **kwargs))
            except Exception as e:
                print(f"[LLMFactory] Failed to load provider {name}: {e}")
                
        # Always ensure at least one provider (mock as absolute fallback if all fail)
        if not provider_instances:
            provider_instances.append(MockProvider())
            
        return provider_instances
