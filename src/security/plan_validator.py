"""
Plan Validator - Security Vetting for Execution Plans
Validates plans before executor runs them.
"""

from typing import Dict, Any, List
from src.tools.registry import get_tool
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class PlanValidationError(Exception):
    """Raised when plan validation fails."""
    pass


class PlanValidator:
    """Validates execution plans for safety and correctness."""
    
    # Dangerous paths to block
    BLOCKED_PATHS = {
        "c:\\windows",
        "c:\\windows\\system32",
        "c:\\program files",
        "system32",
        "systemroot"
    }
    
    # Dangerous strings in arguments
    DANGEROUS_STRINGS = {
        "&&", "||", ";", "|", "`", "$", "cmd", "powershell", "bash", "sh"
    }
    
    @classmethod
    def validate(cls, plan: Dict[str, Any]) -> None:
        """
        Validate a plan before execution.
        
        Args:
            plan: Plan dict to validate
            
        Raises:
            PlanValidationError: If plan fails validation
        """
        logger.info("Plan validation starting...")
        
        # Basic structure
        if not isinstance(plan, dict):
            raise PlanValidationError("Plan must be a dict")
        
        steps = plan.get("steps", [])
        if not isinstance(steps, list) or len(steps) == 0:
            raise PlanValidationError("Plan must have non-empty steps list")
        
        if len(steps) > 5:
            raise PlanValidationError("Plan exceeds maximum 5 steps")
        
        # Validate each step
        for i, step in enumerate(steps):
            cls._validate_step(step, i)
        
        logger.info(f"Plan validation passed. {len(steps)} steps approved.")
    
    @classmethod
    def _validate_step(cls, step: Dict[str, Any], index: int) -> None:
        """
        Validate a single step.
        
        Args:
            step: Step dict to validate
            index: Step index for error messages
            
        Raises:
            PlanValidationError: If step is invalid
        """
        if not isinstance(step, dict):
            raise PlanValidationError(f"Step {index}: must be a dict")
        
        tool_name = step.get("tool")
        if not tool_name or not isinstance(tool_name, str):
            raise PlanValidationError(f"Step {index}: missing or invalid tool name")
        
        args = step.get("args")
        if not isinstance(args, dict):
            raise PlanValidationError(f"Step {index}: args must be a dict")
        
        # Check tool exists
        tool = get_tool(tool_name)
        if tool is None:
            raise PlanValidationError(f"Step {index}: unknown tool '{tool_name}'")
        
        logger.debug(f"Step {index}: tool '{tool_name}' found")
        
        # Validate arguments
        cls._validate_args(args, tool_name, index)
    
    @classmethod
    def _validate_args(cls, args: Dict[str, Any], tool_name: str, step_index: int) -> None:
        """
        Validate step arguments for dangerous content.
        
        Args:
            args: Arguments dict
            tool_name: Name of tool for context
            step_index: Step index for error messages
            
        Raises:
            PlanValidationError: If args contain dangerous content
        """
        for key, value in args.items():
            value_str = str(value).lower()
            
            # Check for dangerous strings
            for dangerous in cls.DANGEROUS_STRINGS:
                if dangerous in value_str:
                    raise PlanValidationError(
                        f"Step {step_index} (tool={tool_name}): "
                        f"dangerous character/string '{dangerous}' in arg '{key}'"
                    )
            
            # Check for blocked paths
            for blocked_path in cls.BLOCKED_PATHS:
                if blocked_path in value_str:
                    raise PlanValidationError(
                        f"Step {step_index} (tool={tool_name}): "
                        f"blocked filesystem path '{blocked_path}' in arg '{key}'"
                    )
            
            # Check for path traversal
            if ".." in value_str or "..\\" in value_str or "../" in value_str:
                raise PlanValidationError(
                    f"Step {step_index} (tool={tool_name}): "
                    f"path traversal attempted in arg '{key}'"
                )
        
        logger.debug(f"Step {step_index} args validation passed")
