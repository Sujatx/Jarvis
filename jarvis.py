# jarvis.py — Jarvis Elite-Session Conductor
import os
import traceback
from dotenv import load_dotenv

# DPI Fix
os.environ["QT_FONT_DPI"] = "96"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(APP_ROOT, ".env"))

import sys
import asyncio
import threading
import queue
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QMetaObject, Qt, Q_ARG

# --- Core & Engines ---
from src.core.database import MEMORY
from src.core.session import Session, Message
from src.engine.ear import EAR
from src.engine.mouth import MOUTH
from src.engine.brain import BRAIN
from src.core.logging_config import setup_logging, get_logger
from src.core.event_bus import get_event_bus
from src.ui.dashboard import DashboardWindow

# --- Skills ---
import src.skills.system as system_skill
from src.skills.web_controller import WEB

LOG_PATH = os.path.join(APP_ROOT, "service.log")
setup_logging(LOG_PATH, format_type='text')
logger = get_logger(__name__)

class JarvisConductor:
    def __init__(self):
        self.running = True
        self.state = "DORMANT" 
        self.session = None
        self.dashboard = None
        self.input_queue = queue.Queue()
        self.event_bus = get_event_bus()
        self._state_lock = threading.Lock()
        self.is_busy = False 
        
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

    def run(self):
        """Main loop that keeps the app alive forever."""
        logger.info("Jarvis Elite Conductor Started.")
        
        threading.Thread(target=self._voice_worker, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self.event_bus.start(), self.loop)
        asyncio.run_coroutine_threadsafe(self._inactivity_monitor(), self.loop)
        self.event_bus.subscribe("command.text", self._on_text_command)
        
        while self.running:
            try:
                source, text = self.input_queue.get(timeout=0.1)
                
                with self._state_lock:
                    if self.state == "DORMANT":
                        # Any input wakes him up
                        self._start_session(silent=(source == "text"))
                        if text == "WAKE": continue
                    
                    if not self.session: continue

                self.is_busy = True
                # Standard Turn
                future = asyncio.run_coroutine_threadsafe(self._execute_turn(text, source), self.loop)
                future.result() 
                self.is_busy = False

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Conductor Loop Error: {e}")
                self.is_busy = False

    def _voice_worker(self):
        while self.running:
            with self._state_lock:
                current_state = self.state
                can_listen = not self.is_busy and not MOUTH.is_speaking

            if current_state == "DORMANT":
                if EAR.wait_for_wake_word():
                    self.input_queue.put(("voice", "WAKE"))
                    time.sleep(1.0)
            
            elif current_state == "ACTIVE_SESSION":
                if not can_listen:
                    time.sleep(0.2)
                    continue
                
                with self._state_lock:
                    s_ref = self.session
                
                if s_ref:
                    text = EAR.listen_continuous(s_ref)
                    if text:
                        self.input_queue.put(("voice", text))
                else:
                    time.sleep(0.5)

    def _on_text_command(self, event):
        text = event.payload.get("text", "").strip()
        if text:
            self.input_queue.put(("text", text))

    def _start_session(self, silent=False):
        logger.info(f"Conductor: Session Started (Silent={silent})")
        self.state = "ACTIVE_SESSION"
        self.session = Session(inactivity_timeout=30)
        self.session.long_term_summary = MEMORY.get_recent_summaries()
        
        if not silent:
            self._update_ui("Systems Active.", "assistant")
            MOUTH.speak("Systems Active.")

    async def _inactivity_monitor(self):
        """Resets session only, keeps app running."""
        while self.running:
            with self._state_lock:
                if self.state == "ACTIVE_SESSION" and self.session and not self.is_busy:
                    if self.session.is_expired():
                        self._end_session("Timeout")
            await asyncio.sleep(1.0)

    def _end_session(self, reason):
        logger.info(f"Conductor: Ending Conversation ({reason})")
        if self.session:
            history = self.session.get_history_for_llm()
            asyncio.run_coroutine_threadsafe(self._persist_session(history), self.loop)
            self._update_ui("[Conversation Offline]", "system")
            MOUTH.speak("Standing by.")
            # ELITE: Removed WEB.close() to keep browser persistent across conversations.
        
        EAR.stop_stream()
        self.state = "DORMANT"
        self.session = None

    async def _persist_session(self, history):
        summary = await BRAIN.summarize(history)
        MEMORY.save_session_summary(summary)

    async def _execute_turn(self, text, source):
        try:
            if source == "voice":
                self._update_ui(text, "user")
            
            with self._state_lock:
                if not self.session: return
                self.session.add_message("user", text)
                self.session.refresh_activity()
                history = self.session.get_history_for_llm()
                lt_context = self.session.long_term_summary

            # 1. Think
            result = await BRAIN.think(history, lt_context)
            resp_text = result.get("text", "")
            actions = result.get("actions", [])

            # 2. UI Update
            if resp_text:
                with self._state_lock:
                    if self.session: self.session.add_message("assistant", resp_text)
                self._update_ui(resp_text, "assistant")

            # 3. Speak (Blocking)
            if resp_text:
                self.session.is_speaking = True
                MOUTH.speak(resp_text)
                start_wait = time.time()
                while MOUTH.is_speaking and (time.time() - start_wait < 15):
                    await asyncio.sleep(0.1)
                await asyncio.sleep(0.5) 
                self.session.is_speaking = False

            # 4. Act
            if actions:
                for action in actions:
                    func_name = action.get("func")
                    params = action.get("params", {})
                    try:
                        if func_name.startswith("web_"):
                            url = params.get("url", "")
                            # ELITE: Hybrid Navigation - Reuse existing Brave window if possible
                            if func_name == "web_navigate":
                                if system_skill.focus_window("Brave"):
                                    logger.info("Conductor: Reusing existing Brave window.")
                                    # Open new tab and type URL
                                    system_skill.execute_hotkey(["ctrl", "t"])
                                    time.sleep(0.3)
                                    system_skill.execute_hotkey(["ctrl", "l"])
                                    time.sleep(0.2)
                                    system_skill.input_text(url)
                                    res = f"Navigated to {url} in existing Brave window."
                                else:
                                    # Fallback to managed Playwright
                                    await WEB.navigate(url)
                                    res = f"Navigated to {url} in new Elite instance."
                            elif func_name == "web_click":
                                html = await WEB.get_interactive_html()
                                selector = await BRAIN.get_selector(params.get("description"), html)
                                res = await WEB.click(selector)
                            elif func_name == "web_type":
                                html = await WEB.get_interactive_html()
                                selector = await BRAIN.get_selector(params.get("description"), html)
                                res = await WEB.type_text(selector, params.get("text"))
                            else: res = f"Unknown web action: {func_name}"
                        else:
                            func = getattr(system_skill, func_name)
                            res = func(**params)
                        
                        with self._state_lock:
                            if self.session: self.session.add_message("event", f"Result: {res}")
                    except Exception as e:
                        logger.error(f"Action Error ({func_name}): {e}")

        except Exception as e:
            logger.error(f"Turn Error: {e}")

    def _update_ui(self, text, role):
        if self.dashboard:
            QMetaObject.invokeMethod(self.dashboard, "display_signal", Qt.AutoConnection, Q_ARG(str, text), Q_ARG(str, role))

def main():
    app = QApplication(sys.argv)
    conductor = JarvisConductor()
    conductor.dashboard = DashboardWindow(launcher_callback=conductor)
    threading.Thread(target=conductor.run, daemon=True).start()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
