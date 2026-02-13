"""
Planner - LLM Plan Generation
Calls provider.generate_plan() and enforces strict JSON output.
Never executes tools.
"""

import json
from typing import Dict, Any, List
from src.cognitive.providers.base_provider import BaseProvider, RateLimitError
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class PlanFormatError(Exception):
    """Raised when plan format is invalid."""
    pass


class Planner:
    """Generates execution plans from LLM."""
    
    def __init__(self, provider: BaseProvider):
        """
        Initialize planner with a provider.
        
        Args:
            provider: BaseProvider instance
        """
        if not isinstance(provider, BaseProvider):
            raise TypeError("Provider must be a BaseProvider instance")
        self.provider = provider
    
    async def generate_plan(self, prompt: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a plan from the LLM.
        
        Args:
            prompt: User input
            tools: List of available tool schemas
            
        Returns:
            dict with validated plan structure
            
        Raises:
            PlanFormatError: If plan format is invalid
        """
        logger.info(f"Planner generating plan for: {prompt[:50]}...")
        
        try:
            plan = await self.provider.generate_plan(prompt, tools)
        except RateLimitError:
            raise # Pass through
        except Exception as e:
            logger.error(f"Provider failed to generate plan: {e}")
            raise PlanFormatError(f"Provider error: {e}")
        
        # Validate plan format
        self._validate_plan_format(plan)
        
        logger.info(f"Plan generated with {len(plan.get('steps', []))} steps")
        return plan
    
    @staticmethod
    def _validate_plan_format(plan: Any) -> None:
        """
        Validate plan structure.
        
        Args:
            plan: Plan dict to validate
            
        Raises:
            PlanFormatError: If plan is invalid
        """
        if not isinstance(plan, dict):
            raise PlanFormatError("Plan must be a dict")
        
        if plan.get("type") != "plan":
            raise PlanFormatError('Plan must have type="plan"')
        
        steps = plan.get("steps")
        if not isinstance(steps, list):
            raise PlanFormatError("Plan steps must be a list")
        
        if len(steps) > 5:
            raise PlanFormatError("Plan exceeds maximum 5 steps")
        
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                raise PlanFormatError(f"Step {i} must be a dict")
            
            if "tool" not in step or "args" not in step:
                raise PlanFormatError(f"Step {i} missing 'tool' or 'args'")
            
            if not isinstance(step["args"], dict):
                raise PlanFormatError(f"Step {i} args must be a dict")
            
            # Check for nested plans
            if any(isinstance(v, dict) and v.get("type") == "plan" for v in step["args"].values()):
                raise PlanFormatError(f"Step {i} contains nested plan (not allowed)")
        
        logger.debug(f"Plan format validation passed. Steps: {len(steps)}")
