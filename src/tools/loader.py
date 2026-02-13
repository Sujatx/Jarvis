import os
import importlib
import pkgutil
from src.core.logging_config import get_logger

logger = get_logger(__name__)

def load_plugins():
    """Dynamically load all tool plugins from the plugins directory"""
    plugins_path = os.path.join(os.path.dirname(__file__), "plugins")
    if not os.path.exists(plugins_path):
        return

    for _, name, is_pkg in pkgutil.iter_modules([plugins_path]):
        full_module_name = f"src.tools.plugins.{name}"
        try:
            importlib.import_module(full_module_name)
            logger.info(f"Loaded tool plugin: {name}")
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
