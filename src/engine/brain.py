import os
import json
import asyncio
from typing import List, Dict
from groq import Groq
from src.core.database import MEMORY
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class Brain:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=api_key)
        self.model_id = "llama-3.3-70b-versatile"
        logger.info(f"Brain: Engine Active ({self.model_id})")

    async def think(self, history: List[Dict], lt_summary: str = "") -> dict:
        """Stateful reasoning with hypothetical guard."""
        
        system_prompt = f"""
        You are Jarvis, an Elite Windows Assistant.
        Identity: Boss (Sujat). 
        
        LONG-TERM CONTEXT:
        {lt_summary}
        
        TOOLS:
        - open_visual(target): Non-browser apps ONLY.
        - web_navigate(url): Sites ONLY. (Handles browser focus/opening).
        - execute_hotkey(keys): Key combinations.
        - input_text(text): Direct typing.
        - navigation(action): OS navigation.
        
        RULES:
        1. VALID JSON ONLY.
        2. Format: {{"thought": "reasoning", "text": "verbal reply", "actions": [{{"func": "name", "params": {{}}}} ]}}
        3. HYPOTHETICAL GUARD: If Boss asks a question about the future (e.g., "where would you open..."), DO NOT return any actions. Only return verbal text.
        4. DIRECT INTENT ONLY: Only return 'actions' if the user gives a direct command to do something NOW.
        5. BE LOYAL: Follow preferences (like using Brave) without being asked every time.
        """
        
        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = "user" if msg["role"] in ["user", "system"] else "assistant"
            api_messages.append({"role": role, "content": msg["content"]})

        try:
            chat_completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                messages=api_messages,
                model=self.model_id,
                response_format={"type": "json_object"},
                temperature=0.1
            )
            data = json.loads(chat_completion.choices[0].message.content)
            
            if "text" not in data: data["text"] = ""
            if "actions" not in data: data["actions"] = []
            
            logger.info(f"Brain Thought: {data.get('thought')}")
            return data

        except Exception as e:
            logger.error(f"Brain Error: {e}")
            return {"text": "My logic core is flickering.", "actions": []}

    async def summarize(self, history: List[Dict]) -> str:
        prompt = f"Summarize concisely: {json.dumps(history)}"
        try:
            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                messages=[{"role": "user", "content": prompt}],
                model=self.model_id
            )
            return completion.choices[0].message.content.strip()
        except:
            return "Session summary failed."

BRAIN = Brain()
