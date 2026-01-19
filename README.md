# Jarvis — Automation Assistant (Windows)

While growing up I was amazed when I saw **Iron Man** and I’m damn sure you had too, and you know **Tony** was kind of a vibe-coder as well — he was the force behind everything. He had some great visions and **Jarvis** helped him achieve it.

**TONY STARK BUILT THIS IN A CAVE, WITH A BOX OF SCRAPS!**

Well, here I am building my own **Jarvis** from scratch, leveraging everything I can — because why not?

---

## System Overview

Jarvis is a persistent background assistant for Windows that automates your workspace initialization through a unique two-stage trigger system. It minimizes distraction by living entirely in the system tray and provides clear audio/visual feedback for every state.

### Key Features:
*   **Two-Stage Activation:** Combines offline wake-word detection ("Jarvis") with precision double-clap recognition to prevent accidental triggers.
*   **Packaged Executable:** Runs as a standalone `.exe` with zero console flashes, no Python installation required for the end-user.
*   **System Tray Management:** Full control via a tray icon (Pause, Resume, Restart Audio, View Logs).
*   **Workspace Automation:** Automatically launches VS Code and Chrome (ChatGPT & Notion) with a single command.
*   **Resilient Audio Engine:** Auto-recovers from audio device disconnections or overflows.
*   **Privacy-First:** Uses local wake-word detection; no audio is uploaded to the cloud for triggering.

---

## Requirements

*   **OS:** Windows 10 or 11
*   **Hardware:** Functional Microphone
*   **Software (for Developers):** Python 3.10+ (Tested on 3.13)
*   **Configuration:** [Porcupine Access Key](https://picovoice.ai/console/) (Free tier available)

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Sujatx/Jarvis.git
cd Jarvis
```

### 2. Configure Environment
Create a `.env` file in the project root:
```env
PORCUPINE_ACCESS_KEY=your_access_key_here
CHROME_PROFILE=Profile 1
```

### 3. Run or Build
**To run from source:**
```bash
pip install -r requirements.txt
python clap_launcher.py
```

**To build the executable:**
```bash
python -m PyInstaller clap_launcher.spec
```

---

## Usage

1.  **Wake Up:** Say **"Jarvis"**. You will hear a confirmation sound, and the tray icon will turn blue.
2.  **Command:** Perform a **double-clap** within 5 seconds.
3.  **Result:** Jarvis will play a success sound and launch your predefined workspace:
    *   **VS Code**
    *   **Chrome** -> ChatGPT
    *   **Chrome** -> Notion (Second Brain)

### Customizing Apps
To change which applications are launched, modify the `launch_all_apps` function in `clap_launcher.py`.

```python
def launch_all_apps(self):
    # ... code ...
    
    # Example: Launch Spotify
    subprocess.Popen(["C:\\Users\\YourUser\\AppData\\Roaming\\Spotify\\Spotify.exe"], creationflags=CREATE_NO_WINDOW)
    
    # Example: Open a website
    webbrowser.open("https://youtube.com")
```
After modifying the script, rebuild the executable if you are using the packaged version.

---

## Project Structure

```text
Jarvis/
├── clap_launcher.py      # Main application logic
├── clap_launcher.spec    # PyInstaller build configuration
├── requirements.txt      # Python dependencies
├── service.log           # Runtime activity logs
├── .env                  # Configuration (Access Keys)
├── icons/                # System tray & app icons
└── sounds/               # Audio feedback files (WAV)
```

---

## License

Released under the MIT License.

---

Jarvis runs silently—until you speak. Then it listens only to you.