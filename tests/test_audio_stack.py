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
    from src.output.speaker import JarvisSpeaker
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def list_devices():
    print("\n--- Audio Devices ---")
    print(sd.query_devices())
    print(f"Default Input Device: {sd.default.device[0]}")
    print(f"Default Output Device: {sd.default.device[1]}")

async def test_tts():
    print("\n--- Testing Piper TTS ---")
    speaker = JarvisSpeaker()
    if not speaker.voice:
        print("Error: Piper voice model not loaded.")
        return
    
    test_text = "Hello sir, I am testing my voice systems. Can you hear me clearly?"
    print(f"Speaking: '{test_text}'")
    # We call the internal speak_text to wait for completion in this script
    speaker._speak_text(test_text)
    print("TTS Test Complete.")

async def test_stt():
    print("\n--- Testing Whisper STT ---")
    listener = SpeechListener()
    if not listener.model:
        print("Error: Whisper model not loaded.")
        return

    print("Model loaded. Monitoring microphone...")
    print("If you don't see the volume meter moving, your mic isn't being picked up.")
    print("Press ENTER to stop monitoring and start the 5-second transcription test.")

    # Real-time volume meter using a non-blocking approach isn't easily possible 
    # while waiting for input() in a single thread without complex cursor manipulation.
    # Instead, we'll monitor for a few seconds then ask to continue.
    
    try:
        # Show levels for 5 seconds then auto-proceed or ask
        print("Monitoring levels for 2 seconds...")
        for _ in range(20):
            recording = sd.rec(int(0.1 * listener.sample_rate), 
                             samplerate=listener.sample_rate, channels=1, dtype='int16')
            sd.wait()
            volume_norm = np.linalg.norm(recording) * 10
            bar = '#' * int(volume_norm)
            sys.stdout.write(f"\rVolume: {volume_norm:4.1f} {bar:<50}")
            sys.stdout.flush()
        
        print("\n")
        # input("Press Enter to start recording...")

    except KeyboardInterrupt:
        pass
    
    print("\n\n--- Starting 5-second recording test ---")
    
    print("Recording now... Speak clearly!")
    duration = 5  # seconds
    recording = sd.rec(int(duration * listener.sample_rate), 
                       samplerate=listener.sample_rate, channels=1, dtype='int16')
    
    for i in range(duration, 0, -1):
        print(f"{i}...")
        await asyncio.sleep(1)
    
    print("Processing with Whisper...")
    audio_float = recording.flatten().astype(np.float32) / 32768.0
    result = listener.model.transcribe(audio_float, language="en", fp16=False)
    
    print(f"\nResult: '{result['text'].strip()}'")

async def main():
    list_devices()
    
    print("\n--- Running Automated Tests ---")
    
    # 1. Test TTS
    await test_tts()
    
    # 2. Test STT
    await test_stt()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
