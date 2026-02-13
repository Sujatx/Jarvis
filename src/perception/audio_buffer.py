# src/perception/audio_buffer.py
from collections import deque
from typing import Deque, Optional
import numpy as np
import logging

SAMPLE_RATE = 16000
DEFAULT_WINDOW_SECONDS = 15
INT16_MAX = 32767  # use this to normalize int16 -> float32

logger = logging.getLogger(__name__)

def _ensure_1d_mono_chunk(chunk: np.ndarray) -> np.ndarray:
    """
    Ensure chunk is 1-D PCM samples.
    Accepts:
      - shape (n_frames,) dtype=int16 or float32
      - shape (n_frames, channels) -> convert to mono by averaging channels
      - shape (n_frames, 1) -> squeeze
    Returns int16 ndarray (not float) if possible.
    """
    if not isinstance(chunk, np.ndarray):
        raise TypeError("chunk must be a numpy.ndarray")

    # If shape like (n_frames, channels)
    if chunk.ndim == 2:
        # average channels to mono (use float averaging then convert)
        chunk = chunk.mean(axis=1)

    # If shape higher dims, try to flatten last axis but raise if very wrong
    if chunk.ndim > 2:
        chunk = chunk.reshape(-1)

    # If float, assume in [-1,1], convert to int16
    if np.issubdtype(chunk.dtype, np.floating):
        # clip then scale -> int16
        chunk = np.clip(chunk, -1.0, 1.0)
        # convert to int16 view
        chunk = (chunk * INT16_MAX).astype(np.int16, copy=False)
        return chunk

    # If integer but not int16, convert safely
    if np.issubdtype(chunk.dtype, np.integer):
        if chunk.dtype != np.int16:
            chunk = chunk.astype(np.int16)
        return chunk

    raise TypeError(f"Unsupported chunk dtype: {chunk.dtype}")


class AudioRingBuffer:
    """
    Maintain a deque of int16 mono chunks as a sliding window.
    Add chunks with add_chunk(...).
    Retrieve concatenated float32 mono in [-1,1] via get_array().
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, window_seconds: int = DEFAULT_WINDOW_SECONDS):
        self.sample_rate = sample_rate
        self.max_samples = int(sample_rate * window_seconds)
        self._deque: Deque[np.ndarray] = deque()
        self._total_samples = 0

    def add_chunk(self, raw_chunk: np.ndarray) -> None:
        """
        Add a raw chunk (from sounddevice callback or thread).
        raw_chunk may be float32 in [-1,1] or int16; may be 2D.
        Stored internally as int16 1-D mono arrays.
        """
        chunk = _ensure_1d_mono_chunk(raw_chunk)
        n = chunk.shape[0]
        if n == 0:
            return
        self._deque.append(chunk)
        self._total_samples += n
        # Drop oldest chunks until under window
        while self._total_samples > self.max_samples:
            old = self._deque.popleft()
            self._total_samples -= old.shape[0]

    def clear(self) -> None:
        """Empty the buffer."""
        self._deque.clear()
        self._total_samples = 0

    def get_array(self, normalize: bool = True) -> np.ndarray:
        """
        Return contiguous 1D audio of the current buffer.
        normalize=True -> float32 in [-1,1]
        This uses a single preallocated output array and fills it to avoid extra concatenation temporaries.
        """
        total = self._total_samples
        if total == 0:
            return np.zeros((0,), dtype=np.float32) if normalize else np.zeros((0,), dtype=np.int16)

        # Preallocate float32 buffer if normalizing, else int16
        if normalize:
            out = np.empty((total,), dtype=np.float32)
            pos = 0
            for arr in self._deque:
                out[pos: pos + arr.shape[0]] = arr.astype(np.float32, copy=False) / INT16_MAX
                pos += arr.shape[0]
            return out
        else:
            out = np.empty((total,), dtype=np.int16)
            pos = 0
            for arr in self._deque:
                out[pos: pos + arr.shape[0]] = arr
                pos += arr.shape[0]
            return out

    def get_and_trim(self, max_seconds: Optional[float] = None, normalize: bool = True) -> np.ndarray:
        """
        Convenience: get array and then optionally trim to a shorter duration if requested.
        """
        arr = self.get_array(normalize=normalize)
        if max_seconds is None:
            return arr
        max_samps = int(self.sample_rate * max_seconds)
        if arr.shape[0] <= max_samps:
            return arr
        return arr[-max_samps:]

    @property
    def total_samples(self) -> int:
        return self._total_samples
