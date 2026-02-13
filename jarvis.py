# jarvis.py — Jarvis 2.0: Conversational Agent
import os
os.environ["PYINSTALLER_SAFE_MODE"] = "1"

import sys
import time
import signal
import subprocess
from collections import deque
import shutil
import threading
import webbrowser
import socket
import asyncio
import win32com.client
from src.core import config_manager

# Phase 1 & 2 Modules
try:
    from src.core.event_bus import get_event_bus, Event
    from src.cognitive.conversation_manager import get_conversation_manager
    from src.cognitive.response_generator import get_response_generator
    from src.perception.speech_listener import get_speech_listener
    from src.output.speaker import get_jarvis_speaker
    from src.cognitive.llm_handler import LLMHandler
    from src.cognitive.agent_router import AgentRouter
    from src.actions.action_router import ActionRouter
    from src.core.security_manager import get_security_manager
    from src.core.logging_config import setup_logging, get_logger
    from src.tools.loader import load_plugins
    PHASE1_ENABLED = True
    PHASE2_ENABLED = True
except ImportError as e:
    PHASE1_ENABLED = False
    PHASE2_ENABLED = False
    print(f"[Warning] Phase 1/2 modules not found or error: {e}")

# UI
from src.ui.dashboard import DashboardWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QMetaObject, Qt

import numpy as np
from dotenv import load_dotenv
from PIL import Image
import pystray

# Global reference
_launcher_ref = None

try:
    import winsound
except Exception:
    winsound = None

def resource_path(relative_path):
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, relative_path)

# Config
if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(APP_ROOT, ".env"))
LOG_PATH = os.path.join(APP_ROOT, "service.log")
ICONS_DIR = resource_path("resources/icons")
SOUNDS_DIR = resource_path("resources/sounds")

SOUND_WAKE = os.path.join(SOUNDS_DIR, "wake.wav")
SINGLETON_PORT = 49624

# Initialize core logging
main_logger = setup_logging(LOG_PATH, format_type='text')

def log(msg):
    try:
        main_logger.info(msg)
        if _launcher_ref and "error" in msg.lower() and _launcher_ref.dashboard:
            QMetaObject.invokeMethod(_launcher_ref.dashboard, "add_error", Qt.QueuedConnection, Qt.Argument("QString", msg))
    except: pass

def play_sound(path):
    if not os.path.exists(path): return
    if winsound:
        try: winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except: pass

def acquire_singleton_socket(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s
    except: return None

# --------------------- Unified Launcher ---------------------
class UnifiedLauncher:
    def __init__(self, wake_word="jarvis"):
        self.wake_word = wake_word.lower()
        self.running = True
        self.event_bus = None
        self.event_loop = None
        
        self.conversation_manager = None
        self.response_generator = None
        self.speech_listener = None
        self.jarvis_speaker = None
        self.agent_router = None
        self.voice_mode_enabled = False
        self.is_active = False
        self.has_greeted = False
        
        if PHASE1_ENABLED: self._init_phase1()
        if PHASE2_ENABLED: self._init_phase2()

        self.dashboard = None
        self.tray_icon = None

    def _init_phase1(self):
        try:
            self.event_loop = asyncio.new_event_loop()
            threading.Thread(target=lambda: self.event_loop.run_forever(), daemon=True).start()
            self.event_bus = get_event_bus()
            asyncio.run_coroutine_threadsafe(self.event_bus.start(), self.event_loop).result(timeout=5)
            log("[Phase 1] Event Bus initialized")
        except Exception as e:
            log(f"[Phase 1] Init Failed: {e}")

    def _init_phase2(self):
        try:
            self.conversation_manager = get_conversation_manager()
            self.response_generator = get_response_generator()
            self.speech_listener = get_speech_listener()
            self.jarvis_speaker = get_jarvis_speaker(event_loop=self.event_loop)
            self.agent_router = AgentRouter()
            load_plugins()
            
            asyncio.run_coroutine_threadsafe(self.conversation_manager.start_conversation(), self.event_loop).result(timeout=5)
            asyncio.run_coroutine_threadsafe(self.speech_listener.start(), self.event_loop).result(timeout=5)
            asyncio.run_coroutine_threadsafe(self.jarvis_speaker.start(), self.event_loop).result(timeout=5)
            
            self.event_bus.subscribe("speech.transcribed", self._handle_speech_event)
            self.event_bus.subscribe("command.text", self._handle_text_event)
            self.event_bus.subscribe("wake_word.detected", self._on_wake_word)
            self.event_bus.subscribe("voice_mode.changed", self._on_voice_mode_changed)
            
            log("[Phase 2] All components initialized.")
        except Exception as e:
            log(f"[Phase 2] Init Failed: {e}")

    async def _on_voice_mode_changed(self, event):
        self.voice_mode_enabled = event.payload.get("enabled", False)
        if not self.voice_mode_enabled:
            self.is_active = False
            self.update_status("Idle")

    async def _on_wake_word(self, event):
        log("Wake word detected.")
        play_sound(SOUND_WAKE)
        
        # Immediate state update to gate mic
        await self.event_bus.publish("speech.started", {"text": "GREETING"})
        
        self.is_active = True
        self.update_status("Listening...", wake=True)
        
        if not self.has_greeted:
            greeting = self.response_generator.greeting()
            await self.event_bus.publish("speech.started", {"text": greeting})
            await self.event_bus.publish("speech.request", {"text": greeting})
            self.has_greeted = True

    async def _handle_text_event(self, event):
        text = event.payload.get("text", "").strip()
        if text: await self._process_command(text, source="text")

    async def _handle_speech_event(self, event):
        text = event.payload.get("text", "").strip()
        if text: await self._process_command(text, source="voice")

    async def _process_command(self, text: str, source: str = "voice"):
        log(f"Processing command ({source}): {text}")
        security = get_security_manager()
        
        # 1. Sanitization
        blocked_chars = ["&&", "||", ";", "../", "\\..", "|", "$(", "`"]
        if any(char in text for char in blocked_chars):
            await self.event_bus.publish("speech.started", {"text": "Restricted input."})
            return

        # 2. Agent Router
        try:
            result = await self.agent_router.route(text)
        except Exception as e:
            log(f"Router error: {e}")
            await self.event_bus.publish("speech.started", {"text": "Error processing command."})
            return
        
        response_text = result.get("response", "I'm not sure how to assist.")
        response_text = security.redact_pii(response_text)
        
        # 3. Output
        log(f"Jarvis Response: {response_text}")
        await self.event_bus.publish("speech.started", {"text": response_text})
        await self.event_bus.publish("speech.request", {"text": response_text})

        if result.get("type") == "execution":
            self.update_status("Acting")
            await asyncio.sleep(1.0)
        
        self.is_active = False
        self.update_status("Idle")

    def update_status(self, status, wake=False):
        if self.dashboard:
            last_wake = time.strftime('%H:%M:%S') if wake else None
            self.dashboard.update_status(status, last_wake, None)

    def run(self):
        while self.running: time.sleep(1)

    def stop(self):
        """Gracefully stop all launcher components"""
        self.running = False
        log("Stopping launcher components...")
        
        if self.speech_listener:
            asyncio.run_coroutine_threadsafe(self.speech_listener.stop(), self.event_loop)
            
        if self.jarvis_speaker:
            asyncio.run_coroutine_threadsafe(self.jarvis_speaker.stop(), self.event_loop)
            
        if self.event_bus:
            asyncio.run_coroutine_threadsafe(self.event_bus.stop(), self.event_loop)
            
        if self.event_loop:
            self.event_loop.call_soon_threadsafe(self.event_loop.stop())

# ------------------- Tray & Main -------------------
class TrayManager:
    def __init__(self, launcher):
        self.launcher = launcher
        self.icon = None
        img = Image.open(os.path.join(ICONS_DIR, "listening.ico")).resize((16, 16))
        self.icon_image = img

    def show_dashboard(self, icon, item):
        if self.launcher.dashboard: QMetaObject.invokeMethod(self.launcher.dashboard, "show_window", Qt.QueuedConnection)

    def exit_app(self, icon, item):
        log("Exit requested.")
        if self.icon:
            self.icon.stop()
        
        self.launcher.stop()
        
        # Ensure we quit from the main thread
        QMetaObject.invokeMethod(QApplication.instance(), "quit", Qt.QueuedConnection)

    def run(self):
        self.icon = pystray.Icon("Jarvis", self.icon_image, "Jarvis", menu=pystray.Menu(
            pystray.MenuItem("Dashboard", self.show_dashboard, default=True),
            pystray.MenuItem("Exit", self.exit_app)
        ))
        self.icon.run()

def ensure_config_files():
    for f in ["config/intents.json", "config/voice_interaction.json", "config/tools.json", ".env"]:
        target = os.path.join(APP_ROOT, f)
        if not os.path.exists(target):
            src = resource_path(f)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy(src, target)

def main():
    global _launcher_ref
    ensure_config_files()
    app = QApplication(sys.argv)
    launcher = UnifiedLauncher()
    _launcher_ref = launcher
    launcher.dashboard = DashboardWindow(launcher_callback=launcher)
    tray = TrayManager(launcher)
    threading.Thread(target=tray.run, daemon=True).start()
    threading.Thread(target=launcher.run, daemon=True).start()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
