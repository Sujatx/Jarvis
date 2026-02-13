"""
Gemini Provider - Google Generative AI Backend
Subclasses BaseProvider for plan generation and chat.
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from src.cognitive.providers.base_provider import BaseProvider, RateLimitError
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class GeminiProvider(BaseProvider):
    """Provider for Google Generative AI (Gemini)."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize Gemini provider."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.model = None
        self.session = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(model_name)
                self.session = self.model.start_chat(history=[])
                logger.info(f"Gemini Provider ({model_name}) initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        else:
            logger.warning("GEMINI_API_KEY not found in environment.")
    
    async def generate_plan(self, prompt: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a plan for command execution.
        
        Args:
            prompt: User input
            tools: List of available tool schemas
            
        Returns:
            dict with plan structure
            
        Raises:
            RuntimeError: If provider not initialized
        """
        if not self.session:
            raise RuntimeError("Gemini Provider not initialized or API key missing.")
        
        tools_schema = json.dumps(tools, indent=2) if tools else "[]"
        
        system_instructions = (
            "You are Jarvis, a command planning agent for a Windows machine. "
            "Your job is to create a step-by-step plan to execute user commands.\n\n"
            "AVAILABLE TOOLS:\n"
            f"{tools_schema}\n\n"
            "OUTPUT FORMAT:\n"
            "Return ONLY valid JSON with this exact structure:\n"
            "{\n"
            '  "type": "plan",\n'
            '  "steps": [\n'
            '    {"tool": "tool_name", "args": {...}}\n'
            "  ]\n"
            "}\n\n"
            "RULES:\n"
            "- Return VALID JSON only.\n"
            "- Each step must reference a tool from AVAILABLE TOOLS.\n"
            "- Maximum 5 steps per plan.\n"
            "- Include all required arguments for each tool.\n"
            "- No nested plans allowed.\n"
        )
        
        try:
            full_prompt = f"System Instructions: {system_instructions}\n\nUser Input: {prompt}"
            response = self.session.send_message(full_prompt)
            text = response.text.strip()
            
            # Clean JSON if wrapped in markdown
            if "```json" in text:
                text = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL).group(1)
            elif "```" in text:
                text = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL).group(1)
            
            plan = json.loads(text)
            return plan
            
        except google_exceptions.ResourceExhausted as e:
            self._handle_rate_limit(e)
        except json.JSONDecodeError as e:
            logger.error(f"Gemini JSON parsing error: {e}")
            raise ValueError(f"Provider returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Gemini generate_plan error: {e}")
            raise
    
    async def chat(self, prompt: str) -> str:
        """
        Generate a chat response.
        
        Args:
            prompt: User input
            
        Returns:
            str with chat response
            
        Raises:
            RuntimeError: If provider not initialized
        """
        if not self.session:
            raise RuntimeError("Gemini Provider not initialized or API key missing.")
        
        system_instructions = (
            "You are Jarvis, a conversational AI assistant for a Windows machine. "
            "You are helpful, professional, and address the user as 'sir'. "
            "Keep responses concise and friendly."
        )
        
        try:
            full_prompt = f"System Instructions: {system_instructions}\n\nUser Input: {prompt}"
            response = self.session.send_message(full_prompt)
            return response.text.strip()
        except google_exceptions.ResourceExhausted as e:
            self._handle_rate_limit(e)
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            raise

    def _handle_rate_limit(self, e):
        """Extract retry time and raise RateLimitError"""
        error_msg = str(e)
        # Match "Please retry in 15.224970477s" or similar
        match = re.search(r"retry in ([\d.]+)s", error_msg)
        retry_after = float(match.group(1)) if match else None
        
        logger.warning(f"Gemini Rate Limit Hit. Retry after: {retry_after}s")
        raise RateLimitError("Gemini quota exceeded", retry_after=retry_after)
