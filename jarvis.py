# jarvis.py — Phase 1 hardened + Phase 2 UI Integration
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
import json

# Dashboard UI
from dashboard import DashboardWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QMetaObject, Qt

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

# Third-party UI for tray
from PIL import Image
import pystray

try:
    import pvporcupine
except ImportError:
    sys.exit(1)

# Global reference for logging
_launcher_ref = None

# Optional winsound for Windows WAV playback (built-in)
try:
    import winsound
except Exception:
    winsound = None

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, relative_path)


# --------------------- Config ---------------------
# Determine application root (where the .exe or script is located)
if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Load .env from the application root
load_dotenv(os.path.join(APP_ROOT, ".env"))

BASE_DIR = os.path.dirname(__file__)
LOG_PATH = os.path.join(APP_ROOT, "service.log") # Log to app root, not temp dir
ICONS_DIR = resource_path("icons")
SOUNDS_DIR = resource_path("sounds")
CREATE_NO_WINDOW = 0x08000000  # hide intermediate console windows for Popen

# sound files (project-local)
SOUND_WAKE = os.path.join(SOUNDS_DIR, "wake.wav")
SOUND_CLAP = os.path.join(SOUNDS_DIR, "clap.wav")
SOUND_ERROR = os.path.join(SOUNDS_DIR, "error.wav")

# icon files
ICON_LISTEN = os.path.join(ICONS_DIR, "listening.png")
ICON_ACTIVE = os.path.join(ICONS_DIR, "active.png")
ICON_ERROR = os.path.join(ICONS_DIR, "error.png")

# single-instance port (high-numbered)
SINGLETON_PORT = 49624

# cooldowns
LAUNCH_COOLDOWN = 8.0  # seconds between allowed app launches
WAKE_COOLDOWN = 1.0    # seconds between wake detections accepted

# wipe old log on start to avoid stale state
try:
    open(LOG_PATH, "w", encoding="utf-8").close()
except Exception:
    pass


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        
        # UI error reporting
        if _launcher_ref and "error" in msg.lower() and _launcher_ref.dashboard:
            QMetaObject.invokeMethod(
                _launcher_ref.dashboard,
                "add_error",
                Qt.QueuedConnection,
                Qt.Argument("QString", msg)
            )
    except Exception:
        pass


# --------------------- Helpers ---------------------
def play_sound(path):
    """Play WAV asynchronously using winsound (Windows). If not available, ignore."""
    if not os.path.exists(path):
        return
    if winsound:
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass


def count_processes(exe_name):
    try:
        # Use CREATE_NO_WINDOW to prevent CMD flash on Windows
        out = subprocess.check_output(
            ['tasklist', '/FI', f'IMAGENAME eq {exe_name}'], 
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW
        )
        text = out.decode('cp1252', errors='ignore')
        lines = [L for L in text.splitlines() if L.strip()]
        count = sum(1 for L in lines if exe_name.lower() in L.lower())
        return count
    except Exception:
        return 0


def find_chrome_path():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    which = shutil.which("chrome")
    if which:
        return which
    return None


def acquire_singleton_socket(port):
    """Bind to localhost:port to ensure only one instance runs. Returns socket or None if failed."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s
    except Exception:
        try:
            s.close()
        except:
            pass
        return None


# --------------------- Unified Launcher ---------------------
class UnifiedLauncher:
    def __init__(self, wake_word="jarvis", clap_threshold=1800, debug=False):
        self.access_key = os.getenv("PORCUPINE_ACCESS_KEY")
        self.wake_word = wake_word.lower()
        self.clap_threshold = clap_threshold
        self.debug = debug

        # runtime state
        self.is_active = False
        self.activation_time = 0
        self.active_duration = 5  # seconds to listen for claps after wake word
        self.running = True
        self.paused = False  # pause/resume from tray

        self.clap_times = []
        self.last_clap_time = 0
        self.clap_interval = 0.7
        self.previous_amplitude = 0
        self.amplitude_history = deque(maxlen=10)

        # cooldown timestamps
        self.last_launch_time = 0.0
        self.last_wake_time = 0.0

        # Porcupine init
        builtin_keywords = pvporcupine.KEYWORDS
        if self.wake_word not in builtin_keywords:
            self.wake_word = "jarvis"

        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=[self.wake_word]
            )
            log(f"Wake word '{self.wake_word}' loaded.")
        except Exception as e:
            log(f"ERROR initializing Porcupine: {e}")
            sys.exit(1)

        self.sample_rate = self.porcupine.sample_rate
        self.frame_length = self.porcupine.frame_length

        self.audio_stream = None
        signal.signal(signal.SIGTERM, self.handle_exit)
        signal.signal(signal.SIGINT, self.handle_exit)

        # Chrome path and profile
        self.chrome_path = find_chrome_path()
        self.chrome_profile = os.getenv("CHROME_PROFILE") or "Profile 1"

        # external tray icon reference (set by TrayManager)
        self.tray_icon = None
        self.dashboard = None
        self.load_dynamic_config()

    def load_dynamic_config(self):
        # System settings
        config_path = os.path.join(APP_ROOT, "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                try:
                    cfg = json.load(f)
                    self.wake_word = cfg.get("wake_word", "jarvis").lower()
                    self.mode = cfg.get("mode", "clap")
                except:
                    self.mode = "clap"
        else:
            self.mode = "clap"

        # Apps to launch
        apps_path = os.path.join(APP_ROOT, "apps.json")
        if os.path.exists(apps_path):
            with open(apps_path, 'r', encoding='utf-8') as f:
                try:
                    self.apps_to_launch = json.load(f)
                except:
                    self.apps_to_launch = {}
        else:
            self.apps_to_launch = {}

        # URLs to open
        urls_path = os.path.join(APP_ROOT, "urls.json")
        if os.path.exists(urls_path):
            with open(urls_path, 'r', encoding='utf-8') as f:
                try:
                    self.urls_to_open = json.load(f).get("browser_urls", [])
                except:
                    self.urls_to_open = []
        else:
            self.urls_to_open = []

    def update_status(self, status, wake=False, action=False):
        if self.dashboard:
            last_wake = time.strftime('%H:%M:%S') if wake else None
            last_action = time.strftime('%H:%M:%S') if action else None
            self.dashboard.update_status(status, last_wake, last_action)

    def handle_exit(self, *args):
        log("Received exit signal.")
        self.running = False

    def start_audio_stream(self, retries=5, retry_delay=2.0):
        attempt = 0
        while attempt < retries and self.running:
            try:
                time.sleep(0.5 if attempt == 0 else retry_delay)
                self.audio_stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16",
                    blocksize=self.frame_length,
                )
                self.audio_stream.start()
                log("Audio stream started. Listening...")
                return True
            except Exception as e:
                attempt += 1
                log(f"Attempt {attempt}/{retries} - ERROR opening audio stream: {e}")
                time.sleep(retry_delay)
        log("Failed to open audio stream after retries.")
        self.audio_stream = None
        return False

    def stop_audio_stream(self):
        try:
            if self.audio_stream:
                try:
                    self.audio_stream.stop()
                except Exception:
                    pass
                try:
                    self.audio_stream.close()
                except Exception:
                    pass
            self.audio_stream = None
            log("Audio stream stopped.")
        except Exception as e:
            log(f"Error stopping audio: {e}")

    def restart_audio(self):
        log("Restarting audio stream (requested).")
        self.stop_audio_stream()
        ok = self.start_audio_stream(retries=4, retry_delay=1.0)
        if ok:
            play_sound(SOUND_WAKE)
            log("Audio restart successful.")
        else:
            play_sound(SOUND_ERROR)
            log("Audio restart failed.")

    def detect_wake_word(self, pcm):
        try:
            return self.porcupine.process(pcm) >= 0
        except Exception:
            return False

    def detect_clap(self, pcm):
        try:
            audio_data = np.array(pcm, dtype=np.int16)
            amplitude = np.abs(audio_data).max()

            self.amplitude_history.append(amplitude)
            current_time = time.time()

            amplitude_jump = amplitude - self.previous_amplitude
            sharp_attack = amplitude_jump > (self.clap_threshold * 0.4)
            loud_enough = amplitude > self.clap_threshold

            if len(self.amplitude_history) >= 3:
                avg_recent = sum(self.amplitude_history) / len(self.amplitude_history)
                not_sustained = avg_recent < (self.clap_threshold * 0.5)
            else:
                not_sustained = True

            is_clap = loud_enough and (sharp_attack or not_sustained)

            if is_clap and current_time - self.last_clap_time > 0.1:
                self.clap_times.append(current_time)
                self.last_clap_time = current_time

                if len(self.clap_times) >= 2:
                    span = self.clap_times[-1] - self.clap_times[-2]
                    if span < self.clap_interval:
                        self.clap_times.clear()
                        return 2

            self.previous_amplitude = amplitude
            if len(self.clap_times) > 0 and current_time - self.clap_times[-1] > self.clap_interval * 2:
                self.clap_times.clear()
            return 0

        except Exception as e:
            log(f"Clap detection error: {e}")
            return 0

    def activate(self):
        now = time.time()
        if now - self.last_wake_time < WAKE_COOLDOWN:
            return
        self.last_wake_time = now

        self.is_active = True
        self.activation_time = time.time()
        self.clap_times.clear()
        log("Wake word detected. Active mode.")
        
        self.update_status("Listening for claps...", wake=True)
        play_sound(SOUND_WAKE)

    def deactivate(self):
        self.is_active = False
        self.clap_times.clear()
        log("Returning to idle.")
        self.update_status("Idle")

    # ------------------- Actions -------------------
    def launch_all_apps(self):
        self.load_dynamic_config()
        now = time.time()
        if now - self.last_launch_time < LAUNCH_COOLDOWN:
            return
        self.last_launch_time = now

        log("Trigger detected. Launching apps.")
        self.update_status("Launching...", action=True)
        play_sound(SOUND_CLAP)

        for name, exe_path in self.apps_to_launch.items():
            log(f"Launching: {name} ({exe_path})")
            if any(b in name.lower() for b in ["chrome", "firefox", "edge"]):
                self.launch_browser(name, exe_path)
            else:
                try:
                    subprocess.Popen(f'start "" "{exe_path}"', shell=True, creationflags=CREATE_NO_WINDOW)
                except Exception as e:
                    log(f"Launch failed {name}: {e}")

    def launch_browser(self, name, exe_path):
        if "chrome" in name.lower():
            for i, url in enumerate(self.urls_to_open):
                args = [exe_path, f'--profile-directory={self.chrome_profile}']
                if i == 0:
                    args.append('--new-window')
                args.append(url)
                subprocess.Popen(args, creationflags=CREATE_NO_WINDOW)
        else:
            # Fallback for Edge/Firefox
            for url in self.urls_to_open:
                subprocess.Popen([exe_path, url], creationflags=CREATE_NO_WINDOW)

    def run(self):
        time.sleep(2)
        if not self.start_audio_stream(retries=6, retry_delay=2.0):
            log("No audio on startup.")

        self.update_status("Idle")

        while self.running:
            if not self.audio_stream:
                self.update_status("Error: No Audio")
                if self.start_audio_stream(retries=1):
                    self.update_status("Idle")
                else:
                    time.sleep(3)
                    continue

            if self.paused:
                self.update_status("Paused")
                time.sleep(0.5)
                continue

            try:
                data, overflow = self.audio_stream.read(self.frame_length)
                pcm = data[:, 0].astype(np.int16).tolist()

                if not self.is_active:
                    if self.detect_wake_word(pcm):
                        if getattr(self, 'mode', 'clap') == "keyword":
                            self.update_status("Triggered!", wake=True)
                            self.launch_all_apps()
                        else:
                            self.activate()
                    continue

                if self.is_active:
                    clap = self.detect_clap(pcm)
                    if clap == 2:
                        self.launch_all_apps()
                        self.deactivate()
                        continue

                    if time.time() - self.activation_time > self.active_duration:
                        self.deactivate()
            except Exception as e:
                log(f"Loop error: {e}")
                time.sleep(1)

        self.cleanup()

    def cleanup(self):
        log("Shutting down.")
        self.stop_audio_stream()
        if hasattr(self, 'porcupine') and self.porcupine:
            try:
                self.porcupine.delete()
            except:
                pass

# ------------------- Tray Manager -------------------
class TrayManager:
    def __init__(self, launcher: UnifiedLauncher):
        self.launcher = launcher
        self.icon = None

        def load_icon(path):
            try:
                img = Image.open(path).resize((16, 16), Image.LANCZOS)
                return img
            except Exception as e:
                return Image.new("RGBA", (16, 16), (255, 0, 0, 255))

        self.icon_image = load_icon(os.path.join(ICONS_DIR, "listening.ico"))
        self.launcher.tray_icon = self

    def toggle_pause(self, icon, item):
        self.launcher.paused = not self.launcher.paused
        if self.launcher.paused:
            play_sound(SOUND_ERROR)
        else:
            play_sound(SOUND_WAKE)

    def restart_audio(self, icon, item):
        threading.Thread(target=self.launcher.restart_audio, daemon=True).start()

    def open_logs(self, icon, item):
        if os.path.exists(LOG_PATH):
            os.startfile(LOG_PATH)

    def show_dashboard(self, icon, item):
        if self.launcher.dashboard:
            QMetaObject.invokeMethod(
                self.launcher.dashboard,
                "show_window",
                Qt.QueuedConnection
            )

    def restart_app(self, icon, item):
        log("Restarting Jarvis app...")
        if self.icon:
            self.icon.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def exit_app(self, icon, item):
        log("Stopping Jarvis app...")
        self.launcher.running = False           # stop audio loop
        if self.icon:
            self.icon.stop()                    # stop tray loop

        QMetaObject.invokeMethod(
            QApplication.instance(),
            "quit",
            Qt.QueuedConnection
        )                                        # stop Qt loop safely

        sys.exit(0)                              # terminate process

    def make_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Settings", self.show_dashboard, default=True),
            pystray.MenuItem(lambda i: "Resume" if self.launcher.paused else "Pause", self.toggle_pause),
            pystray.MenuItem("Restart Audio", self.restart_audio),
            pystray.MenuItem("Open Logs", self.open_logs),
            pystray.MenuItem("Restart Jarvis", self.restart_app),
            pystray.MenuItem("Stop Jarvis", self.exit_app)
        )

    def run(self):
        self.icon = pystray.Icon("Jarvis", self.icon_image, "Jarvis", menu=self.make_menu())
        self.icon.run()

def main():
    global _launcher_ref
    sock = acquire_singleton_socket(SINGLETON_PORT)
    if not sock: return

    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    launcher = UnifiedLauncher()
    _launcher_ref = launcher
    launcher.dashboard = DashboardWindow(launcher_callback=launcher)
    tray = TrayManager(launcher)

    threading.Thread(target=tray.run, daemon=True).start()
    threading.Thread(target=launcher.run, daemon=True).start()

    sys.exit(qt_app.exec())

if __name__ == "__main__":
    main()