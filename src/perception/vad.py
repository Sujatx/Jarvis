"""
VAD - Voice Activity Detection
Hybrid approach: WebRTC VAD (if available) + Energy fallback.
"""

import numpy as np
from src.core.logging_config import get_logger

logger = get_logger(__name__)

try:
    import webrtcvad
    HAS_WEBRTC = True
except ImportError:
    HAS_WEBRTC = False

class VADAgent:
    def __init__(self, mode=2, sample_rate=16000, threshold=200):
        self.sample_rate = sample_rate
        self.threshold = threshold # Energy threshold
        self.vad = None
        
        if HAS_WEBRTC:
            try:
                self.vad = webrtcvad.Vad(mode)
                logger.info(f"WebRTC VAD initialized (Mode {mode})")
            except Exception as e:
                logger.error(f"WebRTC VAD Init Error: {e}")
                
    def is_speech(self, pcm_int16):
        """
        Detect speech in a chunk of audio.
        pcm_int16: numpy array of int16
        """
        # 1. WebRTC VAD (Preferred)
        # WebRTC requires 10, 20, or 30ms frames. 
        # At 16000Hz, 30ms = 480 samples.
        if self.vad and len(pcm_int16) in [160, 320, 480]:
            try:
                return self.vad.is_speech(pcm_int16.tobytes(), self.sample_rate)
            except:
                pass # Fallback to energy if frame size wrong or error

        # 2. Energy Fallback
        energy = np.abs(pcm_int16).mean()
        return energy > self.threshold
