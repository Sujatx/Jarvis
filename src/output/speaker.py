"""
Jarvis Speaker - Robust Piper TTS Implementation
Handles speech queue and audio playback with definitive AudioChunk byte extraction.
"""

import asyncio
import threading
import time
import os
import sys
import numpy as np
import sounddevice as sd
from queue import Queue, PriorityQueue, Empty
from dataclasses import dataclass, field

try:
    from piper import PiperVoice
except ImportError:
    PiperVoice = None

try:
    from src.core.event_bus import get_event_bus
    from src.core.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = None

def log(msg):
    if logger: logger.info(msg)
    else: print(msg)

# Resolve APP_ROOT
if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    # speaker.py is in src/output/, so root is 2 levels up
    APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass(order=True)
class SpeechRequest:
    priority: int
    text: str = field(compare=False)

class JarvisSpeaker:
    def __init__(self, config_path: str = "config/tts.json", event_loop=None):
        self._event_loop = event_loop
        # Use absolute path for the voice model
        self.voice_model = os.path.join(APP_ROOT, "resources", "voices", "en_GB-northern_english_male-medium.onnx")
        self.volume = 0.8
        self.voice = None
        self.speech_queue = PriorityQueue()
        self._running = False
        self.is_speaking = False
        self.event_bus = get_event_bus()
        self._load_voice()

    def _load_voice(self):
        if not PiperVoice:
            log("Piper library missing.")
            return
        try:
            if os.path.exists(self.voice_model):
                self.voice = PiperVoice.load(self.voice_model)
                log(f"Piper voice loaded from: {self.voice_model}")
            else:
                log(f"CRITICAL: Voice model not found at {self.voice_model}")
        except Exception as e:
            log(f"Error loading Piper: {e}")

    async def start(self):
        self._running = True
        if self.event_bus:
            self.event_bus.subscribe("speech.request", self._on_request)
            self.event_bus.subscribe("speech.stop", self._on_stop)
        
        threading.Thread(target=self._worker_loop, daemon=True).start()
        log("Speaker worker thread started.")

    async def stop(self):
        """Stop the speaker thread and clear queue"""
        self._running = False
        self.stop_current()
        log("Speaker stopped.")

    async def _on_request(self, event):
        payload = event.payload if hasattr(event, 'payload') else event
        text = payload.get("text", "")
        if text: self.speak(text)

    async def _on_stop(self, event):
        self.stop_current()

    def speak(self, text: str, priority: int = 5):
        self.speech_queue.put(SpeechRequest(priority, text))

    def stop_current(self):
        while not self.speech_queue.empty():
            try: self.speech_queue.get_nowait()
            except Empty: break
        sd.stop()

    def _worker_loop(self):
        while self._running:
            try:
                request = self.speech_queue.get(timeout=0.1)
                self._play_text(request.text)
            except Empty: continue
            except Exception as e: log(f"Speaker Loop Error: {e}")

    def _play_text(self, text: str):
        if not self.voice: return
        try:
            self.is_speaking = True
            # Redundant speech.started removed to prevent double-rendering

            # Extract audio from chunks
            audio_buffer = []
            for chunk in self.voice.synthesize(text):
                # Piper synthesize() yields AudioChunk objects
                # Based on diagnostic, use audio_int16_bytes or audio_int16_array
                if hasattr(chunk, 'audio_int16_bytes'):
                    audio_buffer.append(np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16))
                elif hasattr(chunk, 'audio_int16_array'):
                    audio_buffer.append(chunk.audio_int16_array)
                elif hasattr(chunk, 'audio'):
                    audio_buffer.append(np.frombuffer(chunk.audio, dtype=np.int16))
                elif isinstance(chunk, (bytes, bytearray)):
                    audio_buffer.append(np.frombuffer(chunk, dtype=np.int16))
            
            if audio_buffer:
                audio_data = np.concatenate(audio_buffer)
                audio_float = audio_data.astype(np.float32) / 32768.0 * self.volume
                
                # Play using sounddevice
                sd.play(audio_float, samplerate=self.voice.config.sample_rate)
                sd.wait()

            if self.event_bus and self._event_loop:
                asyncio.run_coroutine_threadsafe(self.event_bus.publish("speech.completed", {"text": text}), self._event_loop)
        except Exception as e:
            log(f"Playback error: {e}")
        finally:
            self.is_speaking = False

_speaker = None
def get_jarvis_speaker(config_path="config/tts.json", event_loop=None):
    global _speaker
    if _speaker is None: _speaker = JarvisSpeaker(config_path, event_loop)
    return _speaker
