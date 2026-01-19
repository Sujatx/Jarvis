# clap_launcher.py — Phase 1 hardened (single-instance + cooldowns + tray + sounds)
import os
import sys
import time
import signal
import subprocess
from collections import deque
import shutil
import threading
import webbrowser
import socket

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
                access_key=os.getenv("PORCUPINE_ACCESS_KEY"),
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

        # Chrome path and profile (Profile 1 by default)
        self.chrome_path = find_chrome_path()
        if not self.chrome_path:
            log("WARNING: Chrome not found on common paths or PATH.")
        self.chrome_profile = os.getenv("CHROME_PROFILE") or "Profile 1"

        # VS Code path resolution:
        default_code_exe = r"C:\Users\muska\AppData\Local\Programs\Microsoft VS Code\Code.exe"
        if os.path.exists(default_code_exe):
            self.vscode_exec = default_code_exe
        else:
            which_code = shutil.which("code")
            if which_code:
                self.vscode_exec = which_code
            else:
                alt1 = r"C:\Program Files\Microsoft VS Code\Code.exe"
                alt2 = r"C:\Program Files (x86)\Microsoft VS Code\Code.exe"
                if os.path.exists(alt1):
                    self.vscode_exec = alt1
                elif os.path.exists(alt2):
                    self.vscode_exec = alt2
                else:
                    self.vscode_exec = None
                    log("WARNING: VS Code executable not found; 'code' launch may fail.")

        # ensure neutral startup state
        self.is_active = False
        self.clap_times = []

        # external tray icon reference (set by TrayManager)
        self.tray_icon = None

    def handle_exit(self, *args):
        log("Received exit signal.")
        self.running = False

    # audio open with retries so the process stays alive and can recover
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

                # only double clap logic
                if len(self.clap_times) >= 2:
                    span = self.clap_times[-1] - self.clap_times[-2]
                    if span < self.clap_interval:
                        self.clap_times.clear()
                        return 2

            self.previous_amplitude = amplitude
            # cleanup old claps
            if len(self.clap_times) > 0 and current_time - self.clap_times[-1] > self.clap_interval * 2:
                self.clap_times.clear()
            return 0

        except Exception as e:
            log(f"Clap detection error: {e}")
            return 0

    def activate(self):
        now = time.time()
        # guard wake-cooldown
        if now - self.last_wake_time < WAKE_COOLDOWN:
            if self.debug:
                log("Ignored wake due to wake cooldown.")
            return
        self.last_wake_time = now

        self.is_active = True
        self.activation_time = time.time()
        self.clap_times.clear()
        log("Wake word detected. Clap mode active.")
        # update tray icon to active if present
        if self.tray_icon:
            self.tray_icon.set_active_icon()

        # play wake sound
        play_sound(SOUND_WAKE)

    def deactivate(self):
        self.is_active = False
        self.clap_times.clear()
        log("Clap window ended. Returning to idle (listening for wake word).")
        if self.tray_icon:
            self.tray_icon.set_listening_icon()

    # ------------------- Actions -------------------
    def launch_all_apps(self):
        now = time.time()
        # enforce cooldown so we don't spam launches
        if now - self.last_launch_time < LAUNCH_COOLDOWN:
            log(f"Launch suppressed — cooldown in effect ({now - self.last_launch_time:.2f}s elapsed).")
            return
        self.last_launch_time = now

        log("Double clap detected. Launching apps.")
        play_sound(SOUND_CLAP)

        # -------------------------
        # VS CODE (no cmd popup)
        # -------------------------
        try:
            before = count_processes("Code.exe")
            if self.vscode_exec:
                subprocess.Popen([self.vscode_exec], creationflags=CREATE_NO_WINDOW)
            else:
                subprocess.Popen(["code"], creationflags=CREATE_NO_WINDOW)
            time.sleep(0.6)
            after = count_processes("Code.exe")
            if after > before:
                log("VS Code launch: detected new Code.exe processes (success).")
            else:
                log("VS Code launch: attempted (existing instance or re-used window).")
        except Exception as e:
            log(f"ERROR launching VS Code: {e}")

        # -------------------------
        # CHROME (no cmd popup)
        # -------------------------
        if not self.chrome_path:
            log("Chrome launch skipped: chrome path not found.")
            return

        profile = self.chrome_profile

        try:
            before_chrome = count_processes("chrome.exe")

            subprocess.Popen([
                self.chrome_path,
                f'--profile-directory={profile}',
                '--disable-background-mode',
                '--new-window',
                "https://chat.openai.com"
            ], creationflags=CREATE_NO_WINDOW)

            time.sleep(0.7)
            mid = count_processes("chrome.exe")
            if mid > before_chrome:
                log("Chrome → ChatGPT: success.")
            else:
                log("Chrome → ChatGPT: attempted (no new chrome process detected).")

            subprocess.Popen([
                self.chrome_path,
                f'--profile-directory={profile}',
                '--disable-background-mode',
                "https://www.notion.so/SECOND-BRAIN-28486dda46e280729db4c98997785ffa"
            ], creationflags=CREATE_NO_WINDOW)

            time.sleep(0.7)
            end = count_processes("chrome.exe")
            if end > mid:
                log("Chrome → Notion: success.")
            else:
                log("Chrome → Notion: attempted (no new chrome process detected).")

        except Exception as e:
            log(f"ERROR launching Chrome/Notion: {e}")

        # small settle time to avoid immediate re-triggers
        time.sleep(0.5)
        # clear clap buffer after doing the action
        self.clap_times.clear()

    # ------------------- Main Loop -------------------
    def run(self):
        # small startup delay so audio devices can appear after logon
        time.sleep(2)

        # ensure audio stream open (keeps trying without exiting the whole script)
        if not self.start_audio_stream(retries=6, retry_delay=2.0):
            log("Unable to open audio on startup; will keep retrying in run loop.")

        # main persistent loop
        while self.running:
            # if audio stream is not open, attempt to open it periodically
            if not self.audio_stream:
                opened = self.start_audio_stream(retries=2, retry_delay=2.0)
                if not opened:
                    time.sleep(3)
                    continue  # try again later

            # if paused from tray, sleep and continue
            if self.paused:
                time.sleep(0.5)
                continue

            try:
                data, overflow = self.audio_stream.read(self.frame_length)
                if overflow:
                    log("Audio overflow detected.")

                pcm = data[:, 0].astype(np.int16).tolist()

                # If not active, watch for wake word continuously
                if not self.is_active:
                    if self.detect_wake_word(pcm):
                        self.activate()
                        # now will enter clap-listening state
                        continue
                    else:
                        # idle; continue listening for wake word
                        continue

                # If active, watch for claps until active_duration elapses
                if self.is_active:
                    clap = self.detect_clap(pcm)
                    if clap == 2:
                        # double clap — launch apps and immediately return to idle
                        self.launch_all_apps()
                        self.deactivate()
                        continue

                    # if the clap window timed out, deactivate and continue listening
                    if time.time() - self.activation_time > self.active_duration:
                        self.deactivate()
                        continue

            except Exception as e:
                log(f"Main loop error: {e}")
                time.sleep(0.5)
                # if audio read repeatedly fails, restart audio stream later
                try:
                    self.stop_audio_stream()
                except Exception:
                    pass
                time.sleep(1)

        # cleanup on exit
        self.cleanup()

    def cleanup(self):
        log("Shutting down.")
        try:
            if self.audio_stream:
                self.audio_stream.stop()
                self.audio_stream.close()
        except Exception:
            pass
        try:
            if self.porcupine:
                self.porcupine.delete()
        except Exception:
            pass
        log("Cleanup complete.")


# ------------------- Tray Manager -------------------
class TrayManager:
    def __init__(self, launcher: UnifiedLauncher):
        self.launcher = launcher
        self.icon = None

        def load_icon(path):
            try:
                img = Image.open(path)
                img = img.resize((16, 16), Image.LANCZOS)
                return img
            except Exception as e:
                log(f"Tray icon load error: {e}")
                return Image.new("RGBA", (16, 16), (255, 0, 0, 255))

        # load images (auto resized)
        self.img_listening = load_icon(ICON_LISTEN)
        self.img_active = load_icon(ICON_ACTIVE)
        self.img_error = load_icon(ICON_ERROR)

        # so launcher can call icon changes
        self.launcher.tray_icon = self

    def set_listening_icon(self):
        if self.icon:
            self.icon.icon = self.img_listening

    def set_active_icon(self):
        if self.icon:
            self.icon.icon = self.img_active

    def set_error_icon(self):
        if self.icon:
            self.icon.icon = self.img_error

    def toggle_pause(self, icon, item):
        self.launcher.paused = not self.launcher.paused
        state = "paused" if self.launcher.paused else "resumed"
        log(f"User toggled listening: {state}")

        if self.launcher.paused:
            self.set_error_icon()
            play_sound(SOUND_ERROR)
        else:
            self.set_listening_icon()
            play_sound(SOUND_WAKE)

    def restart_audio(self, icon, item):
        log("User requested audio restart from tray.")
        threading.Thread(target=self.launcher.restart_audio, daemon=True).start()

    def open_logs(self, icon, item):
        try:
            if os.path.exists(LOG_PATH):
                os.startfile(LOG_PATH)
            else:
                os.startfile(BASE_DIR)
        except Exception as e:
            log(f"Failed to open logs: {e}")

    def exit_app(self, icon, item):
        log("User requested exit from tray.")
        self.launcher.running = False
        try:
            self.icon.stop()
        except:
            pass

    def make_menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                lambda icon: "Pause Listening" if not self.launcher.paused else "Resume Listening",
                self.toggle_pause
            ),
            pystray.MenuItem("Restart Audio", self.restart_audio),
            pystray.MenuItem("Open Logs", self.open_logs),
            pystray.MenuItem("Exit", self.exit_app)
        )

    def run(self):
        self.icon = pystray.Icon("Jarvis", self.img_listening, "Jarvis Assistant", menu=self.make_menu())
        try:
            self.icon.run()
        except Exception as e:
            log(f"Tray icon run error: {e}")


# ------------------- Main -------------------
def main():
    # single-instance check
    sock = acquire_singleton_socket(SINGLETON_PORT)
    if sock is None:
        # another instance is running — log and exit
        log("Another instance detected — exiting.")
        return

    launcher = UnifiedLauncher()
    tray = TrayManager(launcher)

    # run tray in background thread (so launcher.run can be main thread)
    t = threading.Thread(target=tray.run, daemon=True)
    t.start()

    # small delay so tray initializes visually
    time.sleep(0.5)
    # set initial icon state
    tray.set_listening_icon()

    # run the audio engine on this thread (keeps process alive)
    try:
        launcher.run()
    except Exception as e:
        log(f"Launcher top-level error: {e}")
    finally:
        # ensure icon removed on exit
        try:
            if tray.icon:
                tray.icon.stop()
        except Exception:
            pass
        # close the singleton socket on exit
        try:
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
