"""
Executor - Sequential Plan Execution
Executes validated plans step-by-step.
Never calls LLM. Only calls tools via registry.
"""

import asyncio
from typing import Dict, Any, List
from src.tools.registry import get_tool
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class ExecutionError(Exception):
    """Raised when execution fails."""
    pass


class Executor:
    """Executes validated execution plans."""
    
    # Timeout per step in seconds
    DEFAULT_STEP_TIMEOUT = 30
    
    # Maximum retries per step
    MAX_RETRIES = 1
    
    def __init__(self, step_timeout: int = DEFAULT_STEP_TIMEOUT):
        """
        Initialize executor.
        
        Args:
            step_timeout: Timeout per step in seconds
        """
        self.step_timeout = step_timeout
        self.results = []
    
    async def execute(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a validated plan sequentially.
        
        Args:
            plan: Validated plan dict with steps
            
        Returns:
            list of execution results
            
        Raises:
            ExecutionError: If execution fails
        """
        self.results = []
        steps = plan.get("steps", [])
        
        logger.info(f"Plan execution starting. Steps: {len(steps)}")
        
        for i, step in enumerate(steps):
            try:
                result = await self._execute_step(step, i)
                self.results.append(result)
            except Exception as e:
                logger.error(f"Step {i} execution failed: {e}")
                raise ExecutionError(f"Step {i} failed: {e}")
        
        logger.info(f"Plan execution complete. Results: {len(self.results)}")
        return self.results
    
    async def _execute_step(self, step: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Execute a single step with retry logic.
        
        Args:
            step: Step dict with tool and args
            index: Step index
            
        Returns:
            dict with execution result
            
        Raises:
            ExecutionError: If step execution fails
        """
        tool_name = step.get("tool")
        args = step.get("args", {})
        
        logger.info(f"Step {index}: executing tool '{tool_name}'")
        
        # Retry loop
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                tool = get_tool(tool_name)
                if tool is None:
                    raise ExecutionError(f"Tool '{tool_name}' not found")
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    tool.execute(**args),
                    timeout=self.step_timeout
                )
                
                logger.debug(f"Step {index}: tool returned {result}")
                
                return {
                    "step": index,
                    "tool": tool_name,
                    "status": "success",
                    "result": result
                }
                
            except asyncio.TimeoutError:
                logger.error(f"Step {index}: execution timeout ({self.step_timeout}s)")
                if attempt < self.MAX_RETRIES:
                    logger.info(f"Step {index}: retrying (attempt {attempt + 2}/{self.MAX_RETRIES + 1})")
                    continue
                raise ExecutionError(f"Step {index} timeout after {self.MAX_RETRIES + 1} attempts")
            
            except Exception as e:
                logger.error(f"Step {index}: execution error: {e}")
                if attempt < self.MAX_RETRIES:
                    logger.info(f"Step {index}: retrying (attempt {attempt + 2}/{self.MAX_RETRIES + 1})")
                    await asyncio.sleep(0.5)  # Brief pause before retry
                    continue
                raise ExecutionError(f"Step {index} failed after {self.MAX_RETRIES + 1} attempts: {e}")
    
    def get_results(self) -> List[Dict[str, Any]]:
        """Get execution results."""
        return self.results
