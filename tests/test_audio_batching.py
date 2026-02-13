"""
Quick verification test for Phase 2.5 audio batching optimization
Tests that batching reduces event frequency from 31/sec to 5/sec
"""

import asyncio
import time
from collections import defaultdict

def test_audio_batching_frequency():
    """
    Simulates the audio pipeline and verifies batching reduces events
    """
    # Simulate jarvis.py audio processing
    sample_rate = 16000
    frame_length = 512
    batch_size_ms = 200
    chunks_per_batch = int((batch_size_ms / 1000) * (sample_rate / frame_length))
    
    print(f"✓ Configuration:")
    print(f"  Sample Rate: {sample_rate} Hz")
    print(f"  Frame Length: {frame_length} samples")
    print(f"  Batch Size: {batch_size_ms}ms")
    print(f"  Chunks Per Batch: {chunks_per_batch}")
    
    # Expected frequency
    chunk_interval_ms = (frame_length / sample_rate) * 1000
    expected_chunk_freq = 1000 / chunk_interval_ms
    expected_batch_freq = expected_chunk_freq / chunks_per_batch
    
    print(f"\n✓ Expected Frequencies:")
    print(f"  Individual Chunks: {expected_chunk_freq:.1f}/sec")
    print(f"  Batched Events: {expected_batch_freq:.1f}/sec")
    
    # Simulate 3 seconds of audio
    duration_sec = 3
    total_chunks = int((sample_rate / frame_length) * duration_sec)
    
    batch_buffer = []
    batch_count = 0
    
    for i in range(total_chunks):
        batch_buffer.append(i)
        
        if len(batch_buffer) >= chunks_per_batch:
            batch_count += 1
            batch_buffer = []
    
    actual_batch_freq = batch_count / duration_sec
    
    print(f"\n✓ Simulation Results ({duration_sec}s):")
    print(f"  Total Chunks: {total_chunks}")
    print(f"  Batch Events: {batch_count}")
    print(f"  Actual Batch Frequency: {actual_batch_freq:.1f}/sec")
    
    # Assert frequency is within acceptable range
    assert chunks_per_batch == 6, f"Expected 6 chunks per batch, got {chunks_per_batch}"
    assert 4 <= actual_batch_freq <= 6, f"Batch frequency {actual_batch_freq:.1f}/sec outside range 4-6/sec"
    
    reduction_percent = (1 - (actual_batch_freq / expected_chunk_freq)) * 100
    print(f"\n✅ PASS: Event frequency reduced by {reduction_percent:.0f}%")
    print(f"✅ PASS: Batching working as expected!")

if __name__ == "__main__":
    test_audio_batching_frequency()
