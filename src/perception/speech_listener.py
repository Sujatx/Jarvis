"""
Speech Listener - Robust Ada-Native Implementation
Manages Mic, Wake Word, and STT with improved state recovery.
"""

import os
import asyncio
import threading
import time
import json
import numpy as np
import sounddevice as sd
import pvporcupine
from faster_whisper import WhisperModel
from typing import Optional, Dict, Any

from src.core.event_bus import get_event_bus
from src.core.logging_config import get_logger
from src.perception.audio_buffer import AudioRingBuffer

logger = get_logger(__name__)

# States
STATE_IDLE = "idle"
STATE_WAKE_WORD = "wake_word"
STATE_LISTENING = "listening"
STATE_TRANSCRIBING = "transcribing"

class SpeechListener:
    def __init__(self, config_path: str = "config/speech.json"):
        self.config = self._load_config(config_path)
        self.event_bus = get_event_bus()
        
        # Audio Settings
        self.sample_rate = 16000
        self.frame_length = 512
        self.silence_threshold = self.config.get("audio", {}).get("silence_threshold", 150)
        self.silence_duration = self.config.get("audio", {}).get("silence_duration", 1.5)
        
        # Models
        self.porcupine = None
        self.whisper = None
        self.whisper_size = self.config.get("whisper", {}).get("model", "medium")
        
        # State
        self.state = STATE_IDLE
        self.running = False
        self.is_voice_mode_enabled = False
        self.is_jarvis_speaking = False
        
        # Internal Buffers
        self.audio_buffer = AudioRingBuffer(sample_rate=self.sample_rate, window_seconds=15)
        self.silence_start = None
        self._loop = None
        self._listening_start = None

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, 'r') as f: return json.load(f)
        except: return {}

    async def start(self):
        self.running = True
        self._loop = asyncio.get_running_loop()
        
        self.event_bus.subscribe("speech.started", self._on_speaker_started)
        self.event_bus.subscribe("speech.completed", self._on_speaker_stopped)
        self.event_bus.subscribe("voice_mode.changed", self._on_voice_mode_changed)
        
        threading.Thread(target=self._run_loop, daemon=True).start()
        logger.info("SpeechListener initialized.")

    async def stop(self):
        """Stop the audio thread and cleanup"""
        self.running = False
        logger.info("SpeechListener stopped.")

    def _on_speaker_started(self, event): 
        self.is_jarvis_speaking = True
        self.audio_buffer.clear()
    def _on_speaker_stopped(self, event): self.is_jarvis_speaking = False

    def _on_voice_mode_changed(self, event):
        payload = event.payload if hasattr(event, 'payload') else event
        self.is_voice_mode_enabled = payload.get("enabled", False)
        self.state = STATE_WAKE_WORD if self.is_voice_mode_enabled else STATE_IDLE
        logger.info(f"Voice Mode: {self.is_voice_mode_enabled}, State: {self.state}")

    def _init_models(self):
        try:
            access_key = os.getenv("PORCUPINE_ACCESS_KEY")
            if access_key:
                self.porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"])
                self.frame_length = self.porcupine.frame_length
            
            device = self.config.get("audio", {}).get("device", "cpu")
            compute_type = self.config.get("whisper", {}).get("compute_type", "int8")
            self.whisper = WhisperModel(self.whisper_size, device=device, compute_type=compute_type)
            
            self.event_bus.publish_sync("speech.status", {"text": "Voice Engine Ready"})
            return True
        except Exception as e:
            logger.error(f"STT Init Failed: {e}")
            return False

    def _run_loop(self):
        if not self._init_models(): return

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16', blocksize=self.frame_length) as stream:
                while self.running:
                    data, _ = stream.read(self.frame_length)
                    pcm = data[:, 0].astype(np.int16)
                    
                    if not self.is_voice_mode_enabled: 
                        time.sleep(0.1)
                        continue
                        
                    if self.is_jarvis_speaking and self.state != STATE_LISTENING:
                        continue

                    if self.state == STATE_WAKE_WORD:
                        # Porcupine expects simple list
                        if self.porcupine.process(pcm.tolist()) >= 0:
                            logger.info(">>> WAKE WORD DETECTED")
                            self.state = STATE_LISTENING
                            self.audio_buffer.clear()
                            self.silence_start = None
                            self.event_bus.publish_sync("wake_word.detected", {"source": "native"})

                    elif self.state == STATE_LISTENING:
                        self.audio_buffer.add_chunk(pcm)
                        energy = np.abs(pcm).mean()
                        
                        # Track start time of listening
                        if self._listening_start is None:
                            self._listening_start = time.time()
                            self.event_bus.publish_sync("speech.status", {"text": "Listening for command..."})

                        if energy < self.silence_threshold:
                            if self.silence_start is None: self.silence_start = time.time()
                            
                            # Only stop if:
                            # 1. Silence has lasted 1.5s
                            # 2. AND we have at least 2 seconds of total audio (prevents tiny ghost clips)
                            if time.time() - self.silence_start > self.silence_duration:
                                total_duration = time.time() - self._listening_start
                                if total_duration > 2.0: 
                                    self.state = STATE_TRANSCRIBING
                                    self._listening_start = None
                                    self.event_bus.publish_sync("speech.status", {"text": "Thinking..."})
                                    logger.info(f">>> SILENCE DETECTED (Total recording: {total_duration:.1f}s)")
                                else:
                                    # Too short, keep listening
                                    self.silence_start = None
                        else:
                            self.silence_start = None

                    elif self.state == STATE_TRANSCRIBING:
                        try:
                            # Retrieve flattened 1D float32 array from ring buffer
                            waveform = self.audio_buffer.get_array(normalize=True)
                            
                            # Defensive safety check
                            if waveform.ndim != 1 or waveform.size > self.sample_rate * 60:
                                logger.warning("Audio waveform too large or wrong shape. Trimming to last 15s.")
                                waveform = self.audio_buffer.get_and_trim(max_seconds=15.0, normalize=True)
                            
                            if waveform.size == 0:
                                logger.warning("Empty waveform, skipping transcription.")
                                self.audio_buffer.clear()
                                self.state = STATE_WAKE_WORD
                                continue

                            segments, _ = self.whisper.transcribe(
                                waveform, 
                                beam_size=5,
                                language="en"
                            )
                            text = " ".join([s.text for s in segments]).strip()
                            
                            hallucinations = ["thanks for watching", "thank you for watching", "subscribe", "please subscribe", "thank you."]
                            if text and not any(h in text.lower() for h in hallucinations):
                                logger.info(f"Speech: {text}")
                                self.event_bus.publish_sync("speech.transcribed", {"text": text})
                        except Exception as e:
                            logger.error(f"Transcribe Error: {e}")
                        finally:
                            self.audio_buffer.clear()
                            self.state = STATE_WAKE_WORD

        except Exception as e:
            logger.error(f"Mic Loop Error: {e}")
        finally:
            if self.porcupine: self.porcupine.delete()

_listener = None
def get_speech_listener(config_path="config/speech.json"):
    global _listener
    if _listener is None: _listener = SpeechListener(config_path)
    return _listener
