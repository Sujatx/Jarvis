# Gemini Project Context: Jarvis Assistant

## Project Overview

This project is a Windows desktop automation assistant named "Jarvis," inspired by Iron Man's AI. It runs as a persistent background application, managed via a system tray icon.

The core functionality involves:
1.  **Wake-Word Detection:** It uses the `pvporcupine` engine to listen for the "jarvis" wake word.
2.  **Clap Trigger:** After the wake word is detected, it listens for a distinct double-clap pattern.
3.  **Action Execution:** Upon detecting a double-clap, it launches a predefined set of applications: Visual Studio Code, ChatGPT in a new Chrome window, and a specific Notion page.

The application is built in Python and uses `sounddevice` and `numpy` for audio processing and `pystray` for the system tray interface. It is designed to be a single-instance application and includes audio feedback for different states (wake, clap, error).

**Current Status (Jan 2026):**
The application has been successfully packaged into a standalone Windows executable (`dist/Jarvis.exe`).
- **Packaging:** Completed. The executable works with the custom icon and no console flashes.
- **Environment:** Correctly loads configuration from a `.env` file in the application root.
- **Stability:** Dynamic libraries for `pvporcupine` are explicitly bundled.

## Unified Development Roadmap

### Phase 1: Core System & Packaging (STATUS: COMPLETE)
*   **1.1 Core Logic:** Persistent background service, Wake-word (Porcupine), Clap detection, Auto-launch apps. (Done)
*   **1.2 Code Preparation:** Resource path handling (`_MEIPASS`), separation of UI/Tray from core logic, removal of console prints. (Done)
*   **1.3 Packaging:** Build standalone `.exe` with PyInstaller, including `python-dotenv` for config, custom icons, and proper metadata. (Done)

### Phase 2: User Interface Layer (STATUS: PLANNED)
*   **2.1 Modern Control Dashboard (PySide6):**
    *   **Window:** Standard fixed-size (~900×600), opened from Tray -> "Settings". Closing does NOT exit Jarvis.
    *   **Status Panel (Read-only):** Live status (Idle/Listening/Triggered), last wake-event, last action-event.
    *   **App Launch Manager:**
        *   **Installed Apps List:** Icons + Names + Toggle. Sourced from Registry/Start Menu. Toggles update `apps.json` immediately.
        *   **Browser Sub-Section:** For Chrome/Edge/Firefox, when toggled ON, allows management of a URL list ("Open these links"). Updates `urls.json`.
    *   **Wake-Word Settings:** Textbox for wake-word. Saves to `config.json`. Marks "restart required".
    *   **Execution Mode:** Toggle between "Clap" and "Keyword". Saves to `config.json`. Marks "restart required".
    *   **Restart Jarvis Button:** Visible only when "restart required" is true. Closes listener/tray and relaunches `Jarvis.exe`.
*   **2.2 Mini Overlay HUD:** Implement a transparent, frameless floating HUD for visual feedback.

### Phase 3: Voice Interaction Upgrade (STATUS: PLANNED)
*   **3.1 Text-to-Speech (TTS):** Allow Jarvis to speak back.
*   **3.2 Voice Commands:** Replace/augment claps with spoken commands.

### Phase 4: Automation & AI (STATUS: PLANNED)
*   **4.1 Advanced Automation:** Execute complex tasks beyond app launching.
*   **4.2 AI Brain:** Integrate LLMs for natural language understanding and context memory.

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
    - **Script:** `python jarvis.py`
    - **Executable:** Run `dist/Jarvis.exe`

## Development Conventions

*   **Entry Point:** `jarvis.py` (contains `UnifiedLauncher` and `TrayManager`).
*   **Resources:** Use `resource_path()` for all assets (icons, sounds).
*   **Logging:** Logs to `service.log` in the application root.
*   **Configuration:** 
    - Secrets: `.env`
    - App preferences: `apps.json`, `urls.json`
    - System settings: `config.json`