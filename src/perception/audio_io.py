"""
Audio IO - Robust wrapper for SoundDevice input stream.
Handles device selection, buffering, and error recovery.
"""

import sounddevice as sd
import numpy as np
import threading
import time
from queue import Queue, Full
from src.core.logging_config import get_logger

logger = get_logger(__name__)

class AudioIO:
    def __init__(self, sample_rate=16000, frame_length=512, dtype='int16'):
        self.sample_rate = sample_rate
        self.frame_length = frame_length
        self.dtype = dtype
        self.stream = None
        self.queue = Queue(maxsize=100) # Buffer ~3 seconds
        self.running = False
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self.running: return
            self.running = True
            
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.frame_length,
                dtype=self.dtype,
                channels=1,
                callback=self._callback
            )
            self.stream.start()
            logger.info("AudioIO stream started.")
        except Exception as e:
            logger.error(f"AudioIO Start Error: {e}")
            self.running = False
            raise e

    def stop(self):
        with self._lock:
            self.running = False
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception as e:
                    logger.error(f"AudioIO Stop Error: {e}")
                finally:
                    self.stream = None
            
            # Clear queue
            with self.queue.mutex:
                self.queue.queue.clear()

    def _callback(self, indata, frames, time_info, status):
        """Audio callback - critical section, must be fast."""
        if status:
            logger.warning(f"AudioIO Status: {status}")
        
        if self.running:
            try:
                # Copy data to prevent buffer overwrites
                self.queue.put_nowait(indata.copy())
            except Full:
                pass # Drop frame if buffer full (lag)

    def read(self):
        """Blocking read for next frame."""
        if not self.running: return None
        return self.queue.get()
