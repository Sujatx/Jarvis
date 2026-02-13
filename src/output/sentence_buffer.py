"""
Sentence Buffer - Accumulates streaming tokens into complete sentences.
Used for streaming TTS to prevent robotic pausing mid-sentence.
"""

import re
from typing import List

class SentenceBuffer:
    def __init__(self):
        self.buffer = ""
        # Match punctuation (. ? !) followed by whitespace or end of string
        self.split_pattern = re.compile(r'(?<=[.?!])\s+(?=[A-Z])|(?<=[.?!])$')

    def add(self, text: str) -> List[str]:
        """
        Add text chunk and return list of complete sentences found so far.
        """
        self.buffer += text
        sentences = []
        
        # Split buffer by delimiters
        # We use a lookbehind to keep the punctuation with the sentence
        parts = self.split_pattern.split(self.buffer)
        
        # If we have more than one part, it means we found delimiters
        if len(parts) > 1:
            # All parts except the last are complete sentences
            for part in parts[:-1]:
                if part.strip():
                    sentences.append(part.strip())
            
            # The last part is the incomplete fragment
            self.buffer = parts[-1]
            
        return sentences

    def flush(self) -> List[str]:
        """
        Return any remaining text in the buffer as a final sentence.
        """
        remaining = []
        if self.buffer.strip():
            remaining.append(self.buffer.strip())
        self.buffer = ""
        return remaining
