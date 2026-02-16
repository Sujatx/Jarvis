import os
import threading
import numpy as np
import sounddevice as sd
from piper import PiperVoice
from src.core.logging_config import get_logger

logger = get_logger(__name__)

# Resolve model path
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VOICE_PATH = os.path.join(APP_ROOT, "resources", "voices", "en_GB-northern_english_male-medium.onnx")

class Mouth:
    def __init__(self):
        self.voice = None
        self._is_speaking = False
        self._load_voice()

    def _load_voice(self):
        try:
            if os.path.exists(VOICE_PATH):
                self.voice = PiperVoice.load(VOICE_PATH)
                logger.info("Mouth: Piper voice ready.")
            else:
                logger.error(f"Mouth: Voice model not found at {VOICE_PATH}")
        except Exception as e:
            logger.error(f"Mouth Load Error: {e}")

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def speak(self, text: str):
        """Non-blocking speech synthesis and playback."""
        if not self.voice:
            logger.error("Mouth: No voice model loaded.")
            return

        # Start speech in a separate thread
        threading.Thread(target=self._play_text, args=(text,), daemon=True).start()

    def _play_text(self, text: str):
        try:
            self._is_speaking = True
            audio_buffer = []
            for chunk in self.voice.synthesize(text):
                if hasattr(chunk, 'audio_int16_array'):
                    audio_buffer.append(chunk.audio_int16_array)
                else:
                    audio_buffer.append(np.frombuffer(chunk, dtype=np.int16))
            
            if audio_buffer:
                data = np.concatenate(audio_buffer).astype(np.float32) / 32768.0
                sd.play(data, self.voice.config.sample_rate)
                sd.wait() # Wait for playback to finish
            
            self._is_speaking = False
        except Exception as e:
            logger.error(f"Mouth Playback Error: {e}")
            self._is_speaking = False

MOUTH = Mouth()
