from dataclasses import dataclass

@dataclass
class Intent:
    name: str
    args: dict
    type: str  # "system_action", "information", "conversation", "meta", "unsafe"
    requires_execution: bool
    confidence: float
    source: str
