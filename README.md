# Jarvis — Automation Assistant (Windows)

While growing up I was amazed when I saw **Iron Man** and I’m damn sure you had too, and you know **Tony** was kind of a vibe-coder as well — he was the force behind everything. He had some great visions and **Jarvis** helped him achieve it.

**TONY STARK BUILT THIS IN A CAVE, WITH A BOX OF SCRAPS!**

Well, here I am building my own **Jarvis** from scratch, leveraging everything I can — because why not?

---

## System Overview

Jarvis is a persistent background assistant for Windows that automates your workspace initialization through a unique two-stage trigger system. It minimizes distraction by living entirely in the system tray and provides a modern dashboard for complete control.

### Key Features:
*   **Modern Control Dashboard:** A PySide6-based UI featuring Windows 11 Mica effects, dark mode, and smooth transitions.
*   **Two-Stage Activation:** Combines offline wake-word detection ("Jarvis") with precision double-clap recognition. Supports Keyword-only mode for instant activation.
*   **Dynamic App Manager:** Scans your Start Menu for installed applications. Apps are split into "Enabled" and "Available" lists for easy management.
*   **Browser Integration:** Configure custom URL lists for Chrome, Edge, or Firefox directly within the app cards.
*   **Real-Time Status:** Includes an Event Log on the Status page to monitor system activity and errors.
*   **Packaged Executable:** Runs as a standalone `.exe` with zero console flashes.
*   **Privacy-First:** Uses local wake-word detection via Porcupine; no audio is uploaded to the cloud.

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
python jarvis.py
```

**To build the executable:**
```bash
python -m PyInstaller --clean --noconfirm jarvis.spec
```

---

## Usage

1.  **Launch:** Run `Jarvis.exe`. It will appear in your system tray.
2.  **Configure:** Right-click the tray icon and select **Settings** to open the Dashboard.
    *   **App Manager:** Toggle apps you want to launch. Use the arrow on browser cards to manage URLs.
    *   **Settings:** Change your wake-word or switch between **Clap** and **Keyword** modes.
3.  **Trigger:**
    *   Say **"Jarvis"** (or your custom wake-word).
    *   If in **Clap Mode**: Double-clap within 5 seconds.
    *   If in **Keyword Mode**: Jarvis triggers immediately after the wake-word.
4.  **Result:** Jarvis plays a sound and launches your configured workspace.

---

## Project Structure

```text
Jarvis/
├── jarvis.py             # Main background service & tray logic
├── dashboard.py          # PySide6 Control Dashboard UI
├── config_manager.py     # Atomic configuration persistence
├── jarvis.spec           # PyInstaller build configuration
├── apps.json             # Configured applications to launch
├── urls.json             # Configured URLs to open
├── config.json           # System settings (wake-word, mode)
├── requirements.txt      # Python dependencies
├── service.log           # Runtime activity & error logs
├── .env                  # Secrets (Access Keys)
├── icons/                # System tray icon (listening.ico)
└── sounds/               # Audio feedback files (WAV)
```

---

## License

Released under the MIT License.

---

Jarvis runs silently—until you speak. Then it listens only to you.
