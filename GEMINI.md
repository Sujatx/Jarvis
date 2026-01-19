# Gemini Project Context: Jarvis Assistant

## Project Overview

This project is a Windows desktop automation assistant named "Jarvis," inspired by Iron Man's AI. It runs as a persistent background application, managed via a system tray icon.

The core functionality involves:
1.  **Wake-Word Detection:** It uses the `pvporcupine` engine to listen for the "jarvis" wake word.
2.  **Clap Trigger:** After the wake word is detected, it listens for a distinct double-clap pattern.
3.  **Action Execution:** Upon detecting a double-clap, it launches a predefined set of applications: Visual Studio Code, ChatGPT in a new Chrome window, and a specific Notion page.

The application is built in Python and uses `sounddevice` and `numpy` for audio processing and `pystray` for the system tray interface. It is designed to be a single-instance application and includes audio feedback for different states (wake, clap, error).

**Current Status (Jan 2026):**
The application has been successfully packaged into a standalone Windows executable (`dist/clap_launcher.exe`).
- **Packaging:** Completed. The executable works with the custom icon and no console flashes.
- **Environment:** Correctly loads configuration from a `.env` file in the application root.
- **Stability:** Dynamic libraries for `pvporcupine` are explicitly bundled.

## Unified Development Roadmap

### Phase 1: Core System & Packaging (STATUS: COMPLETE)
*   **1.1 Core Logic:** Persistent background service, Wake-word (Porcupine), Clap detection, Auto-launch apps. (Done)
*   **1.2 Code Preparation:** Resource path handling (`_MEIPASS`), separation of UI/Tray from core logic, removal of console prints. (Done)
*   **1.3 Packaging:** Build standalone `.exe` with PyInstaller, including `python-dotenv` for config, custom icons, and proper metadata. (Done)
    *   *Build Command:* `python -m PyInstaller --noconsole --onefile ...` (See `clap_launcher.spec`)

### Phase 2: System Integration (STATUS: PENDING)
*   **2.1 Autostart:** Configure Jarvis to launch automatically on Windows startup (via Startup folder shortcut).
*   **2.2 Optimization:** Minimize CPU load (e.g., reduce audio buffer reads when idle).
*   **2.3 Error Monitoring:** Implement robust crash recovery and error logging to `errors.log`.

### Phase 3: User Interface Layer (STATUS: PLANNED)
*   **3.1 Modern Control Dashboard:** Create a GUI (using **PySide6**) to:
    *   View live status (Listening/Awake/Error).
    *   Adjust sensitivity and settings.
    *   View logs and manage auto-launch apps.
*   **3.2 Mini Overlay HUD:** Implement a transparent, frameless floating HUD (Iron Man style) for visual feedback ("Wake word detected", "Launching...").

### Phase 4: Voice Interaction Upgrade (STATUS: PLANNED)
*   **4.1 Text-to-Speech (TTS):** Allow Jarvis to speak back (e.g., "Ready, sir").
    *   *Options:* Edge TTS, Microsoft SAPI, or ElevenLabs.
*   **4.2 Voice Commands:** Replace/augment claps with spoken commands (e.g., "Open Notion", "Shutdown system").
    *   *Tech:* Picovoice Rhino (offline commands) or Vosk (offline STT).

### Phase 5: Automation & AI (STATUS: PLANNED)
*   **5.1 Advanced Automation:** Execute complex tasks beyond app launching (e.g., "Send WhatsApp", "Search YouTube", "Coding Mode").
    *   *Tech:* `pywinauto`, Notion API, Chrome automation.
*   **5.2 AI Brain:** Integrate LLMs for natural language understanding and context memory.
    *   *Tech:* Local LLM (Ollama) or OpenAI API.
    *   *Features:* Context awareness, daily summaries, proactive suggestions.

## Building and Running

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Configuration:**
    Create a `.env` file in the root directory:
    ```
    PORCUPINE_ACCESS_KEY=your_key_here
    CHROME_PROFILE=Profile 1
    ```

3.  **Run the Application:**
    - **Script:** `python clap_launcher.py`
    - **Executable:** Run `dist/clap_launcher.exe`

## Development Conventions

*   **Entry Point:** `clap_launcher.py` (contains `UnifiedLauncher` and `TrayManager`).
*   **Resources:** Use `resource_path()` for all assets (icons, sounds).
*   **Logging:** Logs to `service.log` in the application root.
*   **Configuration:** Secrets managed via `.env`.