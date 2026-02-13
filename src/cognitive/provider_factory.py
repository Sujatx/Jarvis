"""
Provider Factory - Dynamic Provider Loading
Loads providers by name from config. No hardcoded providers.
"""

import json
from typing import Dict, Any, List, Optional
from src.core.logging_config import get_logger
from src.cognitive.providers.base_provider import BaseProvider

logger = get_logger(__name__)


class ProviderFactory:
    """Factory for loading providers dynamically."""
    
    # Map of provider names to classes
    # Providers are imported on demand
    _PROVIDER_MODULES = {
        "gemini": ("src.cognitive.providers.gemini", "GeminiProvider"),
        "local": ("src.cognitive.providers.local", "LocalProvider"),
        "mock": ("src.cognitive.providers.mock", "MockProvider"),
    }
    
    @classmethod
    def get_provider(cls, name: str, **kwargs) -> BaseProvider:
        """
        Get a provider instance by name.
        
        Args:
            name: Provider name (e.g., "gemini", "local", "mock")
            **kwargs: Arguments to pass to provider constructor
            
        Returns:
            BaseProvider instance
            
        Raises:
            ValueError: If provider name is unknown
            ImportError: If provider module cannot be imported
        """
        logger.info(f"Loading provider: {name}")
        
        if name not in cls._PROVIDER_MODULES:
            raise ValueError(f"Unknown provider: {name}")
        
        module_name, class_name = cls._PROVIDER_MODULES[name]
        
        try:
            module = __import__(module_name, fromlist=[class_name])
            provider_class = getattr(module, class_name)
            provider = provider_class(**kwargs)
            logger.info(f"Provider '{name}' loaded successfully")
            return provider
        
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load provider '{name}': {e}")
            raise ImportError(f"Cannot load provider '{name}': {e}")
    
    @classmethod
    def get_providers_from_config(cls, config_path: str = "config.json") -> List[BaseProvider]:
        """
        Load providers from config file.
        
        Args:
            config_path: Path to config.json
            
        Returns:
            list of BaseProvider instances in order
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        logger.info(f"Loading providers from config: {config_path}")
        
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config: {e}")
        
        # Get main provider
        provider_name = config.get("provider")
        if not provider_name:
            raise ValueError("Config must specify 'provider'")
        
        providers = []
        
        # Load primary provider
        try:
            primary = cls.get_provider(provider_name)
            providers.append(primary)
            logger.info(f"Primary provider: {provider_name}")
        except Exception as e:
            logger.error(f"Failed to load primary provider '{provider_name}': {e}")
            raise
        
        # Load fallback provider if specified
        fallback_name = config.get("fallback_provider")
        if fallback_name:
            try:
                fallback = cls.get_provider(fallback_name)
                providers.append(fallback)
                logger.info(f"Fallback provider: {fallback_name}")
            except Exception as e:
                logger.warning(f"Failed to load fallback provider '{fallback_name}': {e}")
        
        if not providers:
            raise ValueError("No providers could be loaded")
        
        logger.info(f"Loaded {len(providers)} provider(s)")
        return providers
