import os
import json
import re
import google.generativeai as genai
from typing import Optional, Dict, Any, List
from src.cognitive.providers.base_llm import BaseLLM
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class GeminiProvider(BaseLLM):
    def __init__(self, model_name: str = 'gemini-2.5-flash'):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        self.chat = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(model_name)
                self.chat = self.model.start_chat(history=[])
                logger.info(f"Gemini Provider ({model_name}) initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        else:
            logger.warning("GEMINI_API_KEY not found in environment.")

    async def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.chat:
            raise RuntimeError("Gemini Provider not initialized or API key missing.")
            
        tools_schema = json.dumps(tools, indent=2) if tools else "[]"
        
        system_instructions = (
            "You are Jarvis, a system controller for a Windows machine. "
            "Analyze the user's request and determine if a system action is needed.\n\n"
            "AVAILABLE TOOLS:\n"
            f"{tools_schema}\n\n"
            "OUTPUT FORMAT:\n"
            "If user requests a system action, return ONLY JSON:\n"
            "{{\n"
            '  "tool": "<tool_name>",\n'
            "  \"args\": { ... }\n"
            "}}\n\n"
            "If user is chatting normally or asking a question, return ONLY JSON:\n"
            "{{\n"
            '  "tool": null,\n'
            '  "reply": "<text_response>"\n'
            "}}\n\n"
            "RULES:\n"
            "- Return VALID JSON only.\n"
            "- Address the user as 'sir'.\n"
            "- Keep replies professional and concise."
        )
        
        try:
            full_prompt = f"System Instructions: {system_instructions}\n\nUser Input: {prompt}"
            response = self.chat.send_message(full_prompt)
            text = response.text.strip()
            
            # Clean JSON if wrapped in markdown
            if "```json" in text:
                text = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL).group(1)
            elif "```" in text:
                text = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL).group(1)
                
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"Gemini Generate Error: {e}")
            raise e
