#!/usr/bin/env python3
"""Jarvis visualizer server.

Two jobs, nothing more:
  1. Serve the self-contained scene (index.html + assets).
  2. Serve /state as JSON by READING the voice line's signal bus.

It is strictly READ-ONLY on the bus — it never writes .voice_state / .voice_waveform / .voice_alert.

Run modes:
  python server.py            -> real bus, port 8777
  python server.py --mock     -> scripted state loop, port 8778 (never touches the real bus)

Stdlib only. No packages, no build step.
"""

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# --- Config (Windows-translated from ~/voice-line/) -------------------------
BUS_DIR = os.path.join(os.path.expanduser("~"), "voice-line")
STATE_FILE = os.path.join(BUS_DIR, ".voice_state")
WAVEFORM_FILE = os.path.join(BUS_DIR, ".voice_waveform")
ALERT_FILE = os.path.join(BUS_DIR, ".voice_alert")
STATUS_FILE = os.path.join(BUS_DIR, ".voice_status")

HERE = os.path.dirname(os.path.abspath(__file__))

REAL_PORT = 8777
MOCK_PORT = 8778

WAVEFORM_FRESH_SECS = 2.0   # a waveform newer than this counts as "live voice"
VALID_STATES = ("idle", "listening", "thinking", "speaking", "booting")

MOCK = "--mock" in sys.argv


# --- Bus reading ------------------------------------------------------------
def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def _read_waveform():
    """Return (level, samples, fresh) from the waveform file, or (0.0, [], False)."""
    raw = _read_text(WAVEFORM_FILE)
    if not raw:
        return 0.0, [], False
    try:
        data = json.loads(raw)
        ts = float(data.get("ts", 0))
        samples = [float(s) for s in data.get("samples", [])]
    except (ValueError, TypeError):
        return 0.0, [], False
    fresh = (time.time() - ts) <= WAVEFORM_FRESH_SECS
    if not samples:
        return 0.0, [], fresh
    # level = scaled mean-abs of samples, clamped 0..1
    level = sum(abs(s) for s in samples) / len(samples)
    level = max(0.0, min(1.0, level))
    return level, samples, fresh


def real_state():
    state = _read_text(STATE_FILE)
    if state not in VALID_STATES:
        state = "idle"
    level, samples, fresh = _read_waveform()
    # CRITICAL stomp-tolerance: a fresh waveform means the voice is speaking no matter
    # what the state file says. Protects the show from a stray process stomping the state.
    if fresh and level > 0.0:
        state = "speaking"
    if not fresh:
        level = 0.0
        samples = []
    alert = os.path.exists(ALERT_FILE)
    status = _read_text(STATUS_FILE) or ""
    return {"state": state, "level": round(level, 4), "alert": alert,
            "status": status, "samples": samples}


# --- Mock loop (never touches the real bus) ---------------------------------
# Scripted: idle -> listening -> thinking -> speaking (breathing) -> alert -> idle
_MOCK_SCRIPT = [
    ("idle", 3.0),
    ("listening", 2.5),
    ("thinking", 2.5),
    ("speaking", 5.0),
    ("alert", 2.0),
]
_MOCK_TOTAL = sum(d for _, d in _MOCK_SCRIPT)


def mock_state():
    t = time.time() % _MOCK_TOTAL
    acc = 0.0
    cur, elapsed = "idle", 0.0
    for name, dur in _MOCK_SCRIPT:
        if t < acc + dur:
            cur, elapsed = name, t - acc
            break
        acc += dur
    alert = cur == "alert"
    state = "speaking" if cur == "alert" else cur  # alert overlays speaking-ish activity
    if cur == "speaking":
        # synthetic breathing level
        level = 0.5 + 0.45 * abs(__import__("math").sin(elapsed * 3.2))
    elif cur == "listening":
        level = 0.25 + 0.1 * abs(__import__("math").sin(elapsed * 4.0))
    elif cur == "alert":
        level = 0.6
    else:
        level = 0.0
    status = {"listening": "Listening…", "thinking": "Thinking…",
              "speaking": "All systems nominal, Boss."}.get(cur, "")
    return {"state": state, "level": round(level, 4), "alert": alert,
            "status": status, "samples": []}


# --- HTTP handler -----------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # quiet

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/state":
            payload = mock_state() if MOCK else real_state()
            self._send(200, json.dumps(payload).encode("utf-8"), "application/json")
            return
        # static files
        if path in ("/", "/index.html"):
            fname = "index.html"
        else:
            fname = path.lstrip("/")
        safe = os.path.normpath(os.path.join(HERE, fname))
        if not safe.startswith(HERE) or not os.path.isfile(safe):
            self._send(404, b"not found", "text/plain")
            return
        ctype = {
            ".html": "text/html", ".js": "text/javascript", ".css": "text/css",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml", ".ico": "image/x-icon",
        }.get(os.path.splitext(safe)[1].lower(), "application/octet-stream")
        with open(safe, "rb") as f:
            self._send(200, f.read(), ctype)


def main():
    port = MOCK_PORT if MOCK else REAL_PORT
    if not MOCK:
        os.makedirs(BUS_DIR, exist_ok=True)  # ensure dir exists to read from; we never write bus files
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    mode = "MOCK" if MOCK else "LIVE"
    print(f"[jarvis-visualizer] {mode} server on http://127.0.0.1:{port}  (bus: {BUS_DIR})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
