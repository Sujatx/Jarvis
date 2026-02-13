
import asyncio
import os
import sys
import time
import numpy as np
import sounddevice as sd

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.perception.speech_listener import SpeechListener
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def test_stt_simple():
    print("\n--- Robust Whisper STT Test ---")
    listener = SpeechListener()
    
    if not listener.model:
        print("Error: Whisper model not loaded.")
        return

    print(f"Sample Rate: {listener.sample_rate}")
    print(f"Device: {sd.query_devices(kind='input')['name']}")
    
    duration = 5  # seconds
    print(f"\nRecording for {duration} seconds... SPEAK NOW!")
    
    # Simple blocking recording - no callbacks, less prone to errors
    try:
        recording = sd.rec(int(duration * listener.sample_rate), 
                         samplerate=listener.sample_rate, channels=1, dtype='int16')
        sd.wait()  # Wait for recording to finish
        print("Recording complete.")
        
        # Check max amplitude to verify audio capture
        max_amp = np.max(np.abs(recording))
        print(f"Max Amplitude: {max_amp}")
        
        if max_amp < 100:
            print("WARNING: Audio signal is very weak (silence?). Check microphone.")
        
        print("Transcribing...")
        # Convert to float32 for Whisper
        audio_float = recording.flatten().astype(np.float32) / 32768.0
        
        start_time = time.time()
        result = listener.model.transcribe(audio_float, language="en", fp16=False)
        end_time = time.time()
        
        print(f"\nTranscription: '{result['text'].strip()}'")
        print(f"Time taken: {end_time - start_time:.2f}s")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_stt_simple()
