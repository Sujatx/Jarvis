import time
import uuid
from typing import List, Dict, Optional

class Message:
    def __init__(self, role: str, content: str, metadata: Optional[Dict] = None):
        self.role = role # user, assistant, action, event, system
        self.content = content
        self.timestamp = time.time()
        self.metadata = metadata or {}

    def to_dict(self):
        return {"role": self.role, "content": self.content}

class Session:
    def __init__(self, inactivity_timeout: int = 30):
        self.session_id = str(uuid.uuid4())
        self.created_at = time.time()
        self.last_activity = time.time()
        self.inactivity_timeout = inactivity_timeout
        self.message_history: List[Message] = []
        self.is_active = True
        self.is_speaking = False

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        msg = Message(role, content, metadata)
        self.message_history.append(msg)
        self.last_activity = time.time()

    def refresh_activity(self):
        self.last_activity = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > self.inactivity_timeout

    def get_history_for_llm(self) -> List[Dict]:
        return [m.to_dict() for m in self.message_history]
