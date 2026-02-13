"""
Agent Router - OpenClaw-style Agent Architecture  
Routes user input through: Interpreter -> LocalRouter -> Planner/Chat -> Validator -> Executor
Strict separation between reasoning (LLM) and execution (system).
Local fallback for offline and quota-exceeded scenarios.
"""

from typing import Dict, Any, List
from src.core.interpreter import Interpreter
from src.cognitive.local_router import LocalRouter
from src.cognitive.planner import Planner, PlanFormatError
from src.security.plan_validator import PlanValidator, PlanValidationError
from src.execution.executor import Executor, ExecutionError
from src.cognitive.provider_factory import ProviderFactory
from src.cognitive.providers.base_provider import RateLimitError
from src.tools.registry import get_schemas
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class AgentRouter:
    """Routes user input through the OpenClaw agent pipeline."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize router with providers from config.
        
        Args:
            config_path: Path to config.json with provider settings
        """
        self.config_path = config_path
        self.local_router = LocalRouter()  # Initialize local fallback first
        self.providers = ProviderFactory.get_providers_from_config(config_path)
        self.planner = Planner(self.providers[0])  # Use primary provider
        self.executor = Executor()
        logger.info("AgentRouter initialized with LocalRouter fallback")
    
    async def route(self, text: str) -> Dict[str, Any]:
        """
        Route user input through the agent pipeline.
        
        Args:
            text: User input
            
        Returns:
            dict with response or execution result
        """
        logger.info(f"Routing input: {text[:50]}...")
        
        # Step 1: Interpreter - Input Normalization
        interpreted = Interpreter.interpret(text)
        logger.debug(f"Interpreted intent: {interpreted['intent_type']}")
        
        # Route based on intent type
        if interpreted["intent_type"] == "chat":
            return await self._handle_chat(interpreted["text"])
        else:  # command
            return await self._handle_command(interpreted["text"])
    
    async def _handle_chat(self, text: str) -> Dict[str, Any]:
        """
        Handle chat intent - Try LocalRouter first, then LLM generates response.
        
        Args:
            text: Normalized user input
            
        Returns:
            dict with response
        """
        logger.info("Routing to chat handler")
        
        # Try LocalRouter for common chat patterns (greetings, thank you, help)
        local_result = self.local_router.route(text)
        if local_result and local_result["type"] == "chat":
            logger.info("[Chat] Local handler responded")
            return {
                "type": "response",
                "response": local_result["response"]
            }
        
        # Fall back to LLM for complex chat
        logger.info("[Chat] Using LLM provider")
        try:
            # Use primary provider for chat
            provider = self.providers[0]
            response_text = await provider.chat(text)
            return {
                "type": "response",
                "response": response_text
            }
        except RateLimitError as e:
            time_str = f" {int(e.retry_after)} seconds " if e.retry_after else " a short while "
            return {
                "type": "response",
                "response": f"We hit rate limits on Gemini sir, it will cool down in{time_str}sir."
            }
        except Exception as e:
            logger.error(f"Chat provider failed: {e}")
            return {
                "type": "response",
                "response": "I'm having trouble responding right now, sir. Please try again."
            }
    
    async def _handle_command(self, text: str) -> Dict[str, Any]:
        """
        Handle command intent - Try LocalRouter first, then Plan, Validate, Execute.
        
        Args:
            text: Normalized user input
            
        Returns:
            dict with execution result
        """
        logger.info("Routing to command handler")
        
        # Step 1: Try LocalRouter first (offline/fast path)
        local_result = self.local_router.route(text)
        if local_result:
            logger.info(f"Local router handled: {local_result['type']}")
            
            # If it's a chat response, return directly
            if local_result["type"] == "chat":
                return {
                    "type": "response",
                    "response": local_result["response"]
                }
            
            # If it's a plan, validate and execute
            if local_result["type"] == "plan":
                try:
                    PlanValidator.validate(local_result)
                    logger.info("Local plan validation passed")
                    results = await self.executor.execute(local_result)
                    logger.info(f"Local execution complete: {len(results)} steps")
                    return {
                        "type": "execution",
                        "results": results,
                        "response": local_result.get("response", "Right away, sir.")
                    }
                except PlanValidationError as e:
                    logger.warning(f"Local plan validation failed: {e}")
                    return {
                        "type": "blocked",
                        "reason": str(e),
                        "response": "I'm sorry sir, but I'm not permitted to perform that action."
                    }
                except ExecutionError as e:
                    logger.error(f"Local execution error: {e}")
                    return {
                        "type": "error",
                        "error": str(e),
                        "response": f"Execution failed: {e}"
                    }
        
        # Step 2: LocalRouter didn't handle it, try Planner (LLM)
        logger.info("LocalRouter passed, trying LLM Planner")
        
        try:
            # Try to generate plan with LLM
            tools = get_schemas()
            plan = await self.planner.generate_plan(text, tools)
            logger.info(f"LLM plan generated: {len(plan.get('steps', []))} steps")
            
        except RateLimitError as e:
            time_str = f" {int(e.retry_after)} seconds " if e.retry_after else " a short while "
            return {
                "type": "error",
                "error": "Rate limit exceeded",
                "response": f"We hit rate limits on Gemini sir, it will cool down in{time_str}sir."
            }
        except PlanFormatError as e:
            logger.error(f"LLM plan format error: {e}")
            return {
                "type": "error",
                "error": f"Plan format error: {e}",
                "response": "I couldn't understand that command, sir."
            }
        except Exception as e:
            logger.error(f"LLM plan generation failed: {e}. Falling back to local.")
            return {
                "type": "error",
                "error": f"Cognitive services unavailable: {e}",
                "response": "Cognitive services unavailable. Try asking for something simpler, sir."
            }
        
        try:
            # Step 3: Validate LLM plan
            PlanValidator.validate(plan)
            logger.info("LLM plan validation passed")
            
        except PlanValidationError as e:
            logger.warning(f"LLM plan validation failed: {e}")
            return {
                "type": "blocked",
                "reason": str(e),
                "response": "I'm sorry sir, but I'm not permitted to perform that action."
            }
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "type": "error",
                "error": str(e),
                "response": f"Validation error: {e}"
            }
        
        try:
            # Step 4: Execute LLM plan
            results = await self.executor.execute(plan)
            logger.info(f"LLM execution complete: {len(results)} steps")
            
            return {
                "type": "execution",
                "results": results,
                "response": "Done, sir." # Minimalist, natural response
            }
            
        except ExecutionError as e:
            logger.error(f"Execution error: {e}")
            return {
                "type": "error",
                "error": str(e),
                "response": f"Execution failed: {e}"
            }
        except Exception as e:
            logger.error(f"Unexpected execution error: {e}")
            return {
                "type": "error",
                "error": str(e),
                "response": f"An unexpected error occurred during execution, sir."
            }
