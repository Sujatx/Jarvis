#!/usr/bin/env python3
"""Jarvis voice line.

The bridge between speech and the brain, and the ONLY writer of the signal bus that the
visualizer reads.

Pipeline per turn:
    wake ("Hey Jarvis" or press Enter)  ->  listen (mic + VAD)  ->  transcribe (Whisper)
    ->  ask the brain (claude -p in the repo folder)  ->  speak (TTS)  ->  idle

Signal bus (Windows-translated from ~/voice-line/), written here, read-only elsewhere:
    .voice_state     text: idle | listening | thinking | speaking
    .voice_waveform  json: {"ts": <unix float>, "samples": [64 floats]}
    .voice_alert     exists only while an alert is active

Usage:
    python voice_line.py            wake-word mode ("Hey Jarvis"), falls back to press-Enter
    python voice_line.py --ptt      press-Enter-to-talk mode (no wake word)
    python voice_line.py --check     verify dependencies / mic / brain and exit
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave

try:
    sys.stdout.reconfigure(encoding="utf-8")   # avoid cp1252 mojibake in the console
except Exception:  # noqa: BLE001
    pass


def clean_text(s):
    """Normalize smart punctuation so the console and TTS don't choke (â€” etc.)."""
    for a, b in (("—", " - "), ("–", "-"), ("’", "'"), ("‘", "'"),
                 ("“", '"'), ("”", '"'), ("…", "..."), ("•", "-")):
        s = s.replace(a, b)
    return s


def strip_markdown(s):
    """Turn any markdown the brain emits into plain speech (TTS reads symbols aloud otherwise)."""
    s = re.sub(r"```.*?```", " ", s, flags=re.S)          # code fences
    s = s.replace("`", "")                                 # inline code
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)         # [text](url) -> text
    s = re.sub(r"\*+", "", s)                              # **bold** *italic*
    out = []
    for ln in s.splitlines():
        ln = ln.strip()
        ln = re.sub(r"^#+\s*", "", ln)                     # headers
        ln = re.sub(r"^>\s*", "", ln)                      # quotes
        ln = re.sub(r"^[-•]\s+", "", ln)                   # bullets
        ln = re.sub(r"^\d+\.\s+", "", ln)                  # numbered list
        if ln:
            out.append(ln)
    s = ". ".join(out)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\.\s*\.", ".", s)                         # collapse ". ."
    return s.replace(":.", ":")


def for_speech(s):
    return strip_markdown(clean_text(s))

# --- Config -----------------------------------------------------------------
BUS_DIR = os.path.join(os.path.expanduser("~"), "voice-line")
STATE_FILE = os.path.join(BUS_DIR, ".voice_state")
WAVEFORM_FILE = os.path.join(BUS_DIR, ".voice_waveform")
ALERT_FILE = os.path.join(BUS_DIR, ".voice_alert")
STATUS_FILE = os.path.join(BUS_DIR, ".voice_status")   # human-readable line shown in the visualizer

# repo root (this file lives in voice-line/) — cwd for `claude` so CLAUDE.md loads
BRAIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Obsidian vault, granted to the brain so it can read/write memory
VAULT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "Second brain")
CLAUDE_TIMEOUT = 180                                 # seconds per brain turn

WAKE_MODEL = "hey_jarvis"                       # openWakeWord bundled model ("Hey Jarvis")
WAKE_THRESHOLD = 0.5
WHISPER_SIZE = "base.en"                        # tiny.en / base.en / small.en

SAMPLE_RATE = 16000
VAD_ON = 0.007          # RMS above this = speech (lower = more sensitive; your mic runs quiet)
SILENCE_MS = 900        # trailing silence that ends an utterance
MIN_SPEECH_S = 0.22     # need at least this much voiced audio, else treat as nothing
START_TIMEOUT_S = 6     # if no speech starts within this, give up the turn
MAX_UTTER_S = 15        # hard cap on one utterance
MIC_GAIN = 5.0          # waveform liveliness while listening
TTS_GAIN = 3.5          # waveform liveliness while speaking
TTS_RATE = 185          # pyttsx3 words-per-minute

# --- Core deps (fail loudly with guidance) ----------------------------------
try:
    import numpy as np
    import sounddevice as sd
except Exception as e:  # noqa: BLE001
    print("[voice] missing core dependency:", e)
    print("        pip install -r requirements.txt")
    if "--check" not in sys.argv:
        sys.exit(1)


# --- Bus writer (atomic-ish, this process is the sole writer) ----------------
def ensure_bus():
    os.makedirs(BUS_DIR, exist_ok=True)


def write_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(state)
    except OSError:
        pass


def write_status(msg):
    """A short human line the visualizer shows (boot progress, subtitles)."""
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            f.write(msg)
    except OSError:
        pass


def _to64(samples, gain):
    """Decimate/scale a mono float array to 64 values in [-1, 1] for the waveform bus."""
    arr = np.asarray(samples, dtype=np.float32).ravel()
    if arr.size == 0:
        return [0.0] * 64
    if arr.size >= 64:
        idx = np.linspace(0, arr.size - 1, 64).astype(np.int32)
        arr = arr[idx]
    else:
        arr = np.pad(arr, (0, 64 - arr.size))
    arr = np.clip(arr * gain, -1.0, 1.0)
    return [round(float(v), 4) for v in arr]


def write_waveform(samples, gain):
    payload = {"ts": time.time(), "samples": _to64(samples, gain)}
    tmp = WAVEFORM_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, WAVEFORM_FILE)
    except OSError:
        pass


def set_alert():
    try:
        open(ALERT_FILE, "w").close()
    except OSError:
        pass


def clear_alert():
    try:
        os.remove(ALERT_FILE)
    except OSError:
        pass


# --- Wake ------------------------------------------------------------------
_oww = None
_oww_failed = False


def load_wake_model():
    """Load the wake-word model once and cache it. Returns the model, or None if unavailable."""
    global _oww, _oww_failed
    if _oww is not None or _oww_failed:
        return _oww
    try:
        from openwakeword.model import Model
        try:
            import openwakeword
            openwakeword.utils.download_models()  # no-op if already present
        except Exception:  # noqa: BLE001
            pass
        _oww = Model(wakeword_models=[WAKE_MODEL])
    except Exception as e:  # noqa: BLE001
        print("[voice] wake word unavailable (%s) — using press-Enter mode." % e)
        _oww_failed = True
    return _oww


def wait_for_wake_word():
    """Block until "Hey Jarvis" is heard. Returns True, or False if wake word is unavailable."""
    oww = load_wake_model()
    if oww is None:
        return False

    frame = 1280  # 80ms @ 16k
    write_state("idle")
    write_status('Say "Hey Jarvis"')
    print('[voice] listening for "Hey Jarvis" ...')
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=frame) as stream:
        while True:
            block, _ = stream.read(frame)
            preds = oww.predict(block[:, 0])
            if preds and max(preds.values()) >= WAKE_THRESHOLD:
                return True


def wait_for_wake_ptt():
    write_state("idle")
    write_status("Press Enter to talk")
    try:
        input("\n[voice] Press Enter to talk to Jarvis (Ctrl+C to quit) ... ")
    except EOFError:
        time.sleep(1)


# --- Listen (mic capture + VAD, writes the listening waveform) --------------
def listen():
    write_state("listening")
    write_status("Listening…")
    print("[voice] listening — go ahead, Boss.")
    frame = int(SAMPLE_RATE * 0.03)  # 30ms
    silence_frames_needed = int(SILENCE_MS / 30)
    buf, silence, started, voiced_frames, peak = [], 0, False, 0, 0.0
    t0 = time.time()
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=frame) as stream:
        while True:
            block, _ = stream.read(frame)
            mono = block[:, 0].copy()
            buf.append(mono)
            write_waveform(mono, MIC_GAIN)
            rms = float(np.sqrt(np.mean(mono ** 2)) + 1e-9)
            peak = max(peak, rms)
            if rms > VAD_ON:
                started, silence, voiced_frames = True, 0, voiced_frames + 1
            elif started:
                silence += 1
            if started and silence >= silence_frames_needed:
                break
            if not started and time.time() - t0 > START_TIMEOUT_S:
                break  # heard no speech at all
            if time.time() - t0 > MAX_UTTER_S:
                break
    audio = np.concatenate(buf) if buf else np.zeros(1, dtype=np.float32)
    voiced_s = voiced_frames * 0.03
    print("[voice] captured %.1fs, %.2fs voiced, peak level %.3f (threshold %.3f)"
          % (len(audio) / SAMPLE_RATE, voiced_s, peak, VAD_ON))
    if voiced_s < MIN_SPEECH_S:
        return None  # not enough speech -> skip the brain
    return audio


# --- Transcribe -------------------------------------------------------------
_whisper = None


def load_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")
    return _whisper


# Whisper's stock hallucinations on near-silence — drop them.
_HALLUCINATIONS = {"you", "thank you", "thanks for watching", "bye", "thanks", "okay", "."}


def transcribe(audio):
    segments, _info = load_whisper().transcribe(
        audio, language="en", beam_size=1,
        vad_filter=True, condition_on_previous_text=False, no_speech_threshold=0.5)
    text = "".join(seg.text for seg in segments).strip()
    norm = text.lower().strip(" .,!?")
    return "" if norm in _HALLUCINATIONS or norm == "" else text


# --- Brain bridge (claude -p in the repo folder) ----------------------------
_claude = shutil.which("claude")


def ask_brain(text, first_turn):
    if not _claude:
        return "The brain is unreachable. The claude command is not on the path, Boss."
    # --add-dir grants the vault (outside cwd); acceptEdits lets it write memory without a prompt.
    base = [_claude, "-p", text, "--output-format", "text",
            "--add-dir", VAULT_DIR, "--permission-mode", "acceptEdits"]
    # first turn: one clean retry for transient failures.
    # later turns: continue the conversation, falling back to a fresh call if there's no prior one.
    attempts = [base, base] if first_turn else [base + ["--continue"], base]
    last = None
    for cmd in attempts:
        try:
            last = subprocess.run(cmd, cwd=BRAIN_DIR, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",  # claude emits UTF-8, not cp1252
                                  timeout=CLAUDE_TIMEOUT, stdin=subprocess.DEVNULL)
        except (subprocess.TimeoutExpired, OSError) as e:  # noqa: BLE001
            set_alert()
            return "The brain call failed. %s" % e
        if last.returncode == 0 and last.stdout.strip():
            return last.stdout.strip()
    set_alert()
    detail = (last.stderr or last.stdout or "").strip().splitlines() if last else []
    return "The brain returned an error. " + (detail[-1] if detail else "no output")


# --- Speak (TTS -> WAV -> play while writing the speaking waveform) ----------
def _synth_wav(text):
    import pyttsx3
    path = os.path.join(tempfile.gettempdir(), "jarvis_tts.wav")
    eng = pyttsx3.init()
    eng.setProperty("rate", TTS_RATE)
    eng.save_to_file(text, path)
    eng.runAndWait()
    return path


def _read_wav(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        raw = w.readframes(n)
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def speak(text):
    try:
        path = _synth_wav(text)
        data, sr = _read_wav(path)
    except Exception as e:  # noqa: BLE001
        print("[voice] TTS failed:", e)
        write_state("idle")
        return
    write_state("speaking")
    sd.play(data, sr)
    win = int(sr * 0.04)
    start = time.time()
    while True:
        pos = int((time.time() - start) * sr)
        if pos >= len(data):
            break
        write_waveform(data[pos:pos + win], TTS_GAIN)
        time.sleep(0.04)
    sd.stop()
    write_state("idle")


# --- Self-check -------------------------------------------------------------
def check():
    ok = True
    print("Jarvis voice line — dependency check\n")
    for mod in ("numpy", "sounddevice", "faster_whisper", "openwakeword", "pyttsx3"):
        try:
            __import__(mod)
            print("  [ok]  %s" % mod)
        except Exception as e:  # noqa: BLE001
            ok = False
            print("  [--]  %s  (%s)" % (mod, e))
    print("  [%s]  claude on PATH  (%s)" % ("ok" if _claude else "--", _claude or "not found"))
    try:
        devs = [d["name"] for d in sd.query_devices() if d["max_input_channels"] > 0]
        print("  [%s]  microphone  (%s)" % ("ok" if devs else "--", devs[0] if devs else "none"))
    except Exception as e:  # noqa: BLE001
        ok = False
        print("  [--]  microphone  (%s)" % e)
    print("\nBus dir:", BUS_DIR)
    print("Brain dir:", BRAIN_DIR)
    print("\n%s" % ("All good." if ok else "Some deps missing — pip install -r requirements.txt"))
    return ok


# --- Main -------------------------------------------------------------------
def main():
    if "--check" in sys.argv:
        check()
        return
    ensure_bus()
    clear_alert()
    write_state("idle")
    ptt = "--ptt" in sys.argv
    greet = "--no-greeting" not in sys.argv
    print("=" * 48)
    print(" Jarvis voice line starting.  Ctrl+C to quit.")
    print(" Mode:", "press-Enter" if ptt else '"Hey Jarvis" wake word')
    print("=" * 48)

    # Warm up the models once, up front, so the first real turn isn't slow.
    write_state("booting")
    t0 = time.time()
    if not ptt:
        print("[voice] loading wake word ...")
        write_status("Loading wake word…")
        load_wake_model()
    print("[voice] loading Whisper (%s) ..." % WHISPER_SIZE)
    write_status("Loading speech recognition…")
    load_whisper()
    print("\n" + "#" * 48)
    print("#   JARVIS READY  ({:.1f}s)".format(time.time() - t0))
    print("#   " + ('say "Hey Jarvis"' if not (ptt or _oww_failed) else "press Enter to talk"))
    print("#" * 48 + "\n")
    write_status("Ready")
    write_state("idle")
    if greet:
        write_status("Jarvis online. What do you need, Boss?")
        speak("Jarvis online. What do you need, Boss?")

    wake_ok = None  # unknown until first attempt
    first_turn = True
    try:
        while True:
            clear_alert()
            if ptt or wake_ok is False:
                wait_for_wake_ptt()
            else:
                got = wait_for_wake_word()
                wake_ok = got
                if got is False:
                    wait_for_wake_ptt()

            audio = listen()
            if audio is None:
                print("[voice] (heard nothing — speak a bit louder or closer to the mic)")
                write_state("idle")
                continue
            write_state("thinking")
            write_status("Thinking…")
            try:
                utterance = transcribe(audio)
            except Exception as e:  # noqa: BLE001
                print("[voice] STT failed:", e)
                write_state("idle")
                continue
            if not utterance:
                print("[voice] (heard nothing)")
                write_state("idle")
                continue
            print("\n  You: %s" % utterance)
            write_status('“%s”' % utterance)

            reply = for_speech(ask_brain(utterance, first_turn))
            first_turn = False
            print("  Jarvis: %s\n" % reply)
            write_status(reply)
            speak(reply)
    except KeyboardInterrupt:
        pass
    finally:
        write_state("idle")
        clear_alert()
        print("\n[voice] offline.")


if __name__ == "__main__":
    main()
