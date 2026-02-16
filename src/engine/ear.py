"""
Perception Engine - Elite Persistent Stream Ear.
Maintains a single audio stream to prevent first-word loss.
"""

import os
import time
import numpy as np
import sounddevice as sd
import pvporcupine
from faster_whisper import WhisperModel
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class Ear:
    def __init__(self):
        self.sample_rate = 16000
        self.frame_length = 512
        
        # Models
        access_key = os.getenv("PORCUPINE_ACCESS_KEY")
        self.porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"], sensitivities=[0.5])
        self.whisper = WhisperModel("distil-small.en", device="cpu", compute_type="int8")
        
        self.stream = None
        logger.info("Ear: Elite Persistent Engine Ready.")

    def wait_for_wake_word(self) -> bool:
        """Scoped stream for dormancy to save power."""
        with sd.InputStream(samplerate=self.sample_rate, blocksize=self.frame_length, dtype='int16', channels=1) as stream:
            while True:
                data, _ = stream.read(self.frame_length)
                pcm = data[:, 0].astype(np.int16)
                if self.porcupine.process(pcm) >= 0:
                    return True

    def listen_continuous(self, session_ref) -> str:
        """
        Uses a SINGLE stream for the entire call.
        Drops audio if session_ref.is_speaking is True.
        """
        audio_buffer = []
        silence_start = None
        has_speech_started = False
        
        logger.info("Ear: Monitoring stream...")
        
        # Start persistent stream if not already open
        if self.stream is None:
            self.stream = sd.InputStream(samplerate=self.sample_rate, blocksize=self.frame_length, dtype='int16', channels=1)
            self.stream.start()

        while True:
            # 1. Physical Muzzle: Drop audio while Jarvis is talking
            if session_ref.is_speaking:
                self.stream.read(self.frame_length) # Clear OS buffer
                audio_buffer = []
                has_speech_started = False
                continue

            # 2. Read frame
            data, _ = self.stream.read(self.frame_length)
            pcm = data[:, 0].astype(np.int16)
            energy = np.abs(pcm).mean()

            # 3. VAD Logic
            if energy > 400: # Threshold for intentional human voice
                if not has_speech_started:
                    logger.info("Ear: Speech detected.")
                    has_speech_started = True
                audio_buffer.append(pcm.astype(np.float32) / 32768.0)
                silence_start = None
            elif has_speech_started:
                audio_buffer.append(pcm.astype(np.float32) / 32768.0)
                if silence_start is None: silence_start = time.time()
                if time.time() - silence_start > 1.2: # 1.2s silence window
                    break
            
            # Max 8 seconds per phrase to prevent runaway hallucinations
            if len(audio_buffer) * self.frame_length > self.sample_rate * 8:
                break

        if len(audio_buffer) < 20: # Discard noise spikes
            return ""

        # 4. Transcribe
        full_audio = np.concatenate(audio_buffer)
        segments, _ = self.whisper.transcribe(full_audio, beam_size=1, language="en")
        text = " ".join([s.text for s in segments]).strip()
        
        # Hallucination Filter
        if text.lower() in ["thank you.", "thanks.", "okay.", "so.", "sure.", "you"]:
            return ""
            
        if text:
            logger.info(f"Ear: Heard -> {text}")
            return text
        return ""

    def stop_stream(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def close(self):
        self.stop_stream()
        if self.porcupine: self.porcupine.delete()

EAR = Ear()
