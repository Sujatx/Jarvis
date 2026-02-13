"""
Post Filters - Cleans transcripts and removes common hallucinations.
"""

import re
from typing import Optional

HALLUCINATION_BLACKLIST = [
    "thanks for watching",
    "thank you for watching",
    "please subscribe",
    "subtitles by",
    "captioned by",
    "copyright",
    "all rights reserved",
    "amara.org",
    "open subtitles"
]

def post_transcript_filter(text: str) -> Optional[str]:
    """
    Clean transcript and return None if it's a known hallucination or empty.
    """
    if not text:
        return None
        
    normalized = text.lower().strip()
    
    # 1. Length Check
    if len(normalized) < 2:
        return None
        
    # 2. Blacklist Check
    for phrase in HALLUCINATION_BLACKLIST:
        if phrase in normalized:
            # If the entire transcript is just the hallucination (fuzzy match)
            if len(normalized) < len(phrase) + 5:
                return None
    
    # 3. Repeating char check (e.g. "To be continued..." or ".....")
    if re.match(r'^[\W_]+$', normalized): # Only punctuation/symbols
        return None
        
    return text.strip()
