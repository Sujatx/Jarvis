from typing import Dict, Any
from src.core.logging_config import get_logger
from src.security.action_registry import ACTION_REGISTRY
from src.security.rate_limiter import LIMITER
from src.core.pending_action_store import STORE
from src.tools import executor

logger = get_logger(__name__)

class ActionRouter:
    def __init__(self):
        pass
        
    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> bool:
        """
        Execution Firewall: Validate tool exists and args are safe.
        """
        if tool_name not in ACTION_REGISTRY:
            logger.warning(f"Firewall Block: Unknown tool '{tool_name}'")
            return False
            
        # Arg Sanitization
        for key, val in arguments.items():
            val_str = str(val).lower()
            # Block shell injection/dangerous paths
            if any(char in val_str for char in ["&&", "||", ";", "|", "`"]):
                logger.warning(f"Firewall Block: Dangerous characters in arg '{key}'")
                return False
            if "../" in val_str or "\\.." in val_str:
                logger.warning(f"Firewall Block: Path traversal in arg '{key}'")
                return False
                
        return True

    async def route_tool(self, tool_name: str, arguments: Dict[str, Any]) -> dict:
        """
        Securely route tool call to execution.
        """
        # 1. Firewall Check
        if not self.validate_tool_call(tool_name, arguments):
            return {"status": "blocked", "message": "I'm sorry sir, but I'm not permitted to perform that action."}

        # 2. Rate Limiting
        if not LIMITER.allow():
            return {"status": "blocked", "message": "Too many requests. Please slow down, sir."}

        policy = ACTION_REGISTRY[tool_name]

        # 3. Confirmation Mode
        if policy.get("confirm", False):
            STORE.set({"name": tool_name, "args": arguments})
            return {
                "status": "confirm_required",
                "message": f"I require your confirmation to execute '{tool_name}', sir."
            }

        # 4. Safe Execution
        return await self.execute_tool(tool_name, arguments)

    async def execute_tool(self, name: str, args: Dict[str, Any]) -> dict:
        """
        Final execution logic - Delegates to Tool Executor.
        """
        try:
            logger.info(f"Executing tool: {name} with {args}")
            
            # Delegate to the modular tool executor
            result = await executor.execute(name, args)
            
            if "error" in result:
                return {"status": "error", "message": result["error"]}
            
            return result
            
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            return {"status": "error", "message": "I encountered a problem executing that task, sir."}
