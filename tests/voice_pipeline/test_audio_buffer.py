# tests/voice_pipeline/test_audio_buffer.py
import pytest
import numpy as np
from src.perception.audio_buffer import AudioRingBuffer, SAMPLE_RATE

def test_buffer_structure_and_normalization():
    """Test adding chunks and retrieving normalized array."""
    # 1 second buffer
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=1)
    
    # 1. Add int16 chunk (512 samples, flat)
    chunk1 = np.random.randint(-1000, 1000, size=(512,), dtype=np.int16)
    buf.add_chunk(chunk1)
    assert buf.total_samples == 512
    
    # 2. Add float32 chunk (512 samples, range [-1, 1], shape (512,1))
    chunk2 = np.random.uniform(-1.0, 1.0, size=(512, 1)).astype(np.float32)
    buf.add_chunk(chunk2)
    assert buf.total_samples == 1024
    
    # 3. Get array (normalized)
    arr = buf.get_array(normalize=True)
    assert arr.ndim == 1
    assert arr.shape == (1024,)
    assert arr.dtype == np.float32
    assert np.all(arr >= -1.0) and np.all(arr <= 1.0)
    
    # Verify content roughly matches (float conversion precision)
    # First 512 should match chunk1 normalized
    expected_chunk1 = chunk1.astype(np.float32) / 32767.0
    # Tolerance for int16 quantization round-trip
    assert np.allclose(arr[:512], expected_chunk1, atol=1e-4)

def test_get_and_trim():
    """Test getting last N seconds."""
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=10)
    # Add 2 seconds of audio
    chunk = np.zeros((16000 * 2,), dtype=np.int16)
    buf.add_chunk(chunk)
    assert buf.total_samples == 32000
    
    # Trim to last 0.5 seconds
    trimmed = buf.get_and_trim(max_seconds=0.5, normalize=True)
    expected_len = int(16000 * 0.5)
    assert trimmed.shape == (expected_len,)

def test_clear():
    """Test clearing the buffer."""
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=5)
    chunk = np.zeros((1024,), dtype=np.int16)
    buf.add_chunk(chunk)
    assert buf.total_samples == 1024
    buf.clear()
    assert buf.total_samples == 0
    empty = buf.get_array()
    assert empty.size == 0
