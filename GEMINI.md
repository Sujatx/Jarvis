# Gemini Project Context: Jarvis Assistant

## Project Overview

This project is a Windows desktop automation assistant named "Jarvis," inspired by Iron Man's AI. It runs as a persistent background application, managed via a system tray icon.

The core functionality involves:
1.  **Wake-Word Detection:** It uses the `pvporcupine` engine to listen for the "jarvis" wake word.
2.  **Clap Trigger:** After the wake word is detected, it listens for a distinct double-clap pattern (or immediate keyword trigger).
3.  **Action Execution:** Upon detection, it launches a dynamic set of applications and URLs configured via the dashboard.

The application is built in Python and uses `sounddevice` and `numpy` for audio processing, `pystray` for the system tray interface, and `PySide6` for the control dashboard.

**Current Status (Jan 2026):**
The application has been successfully packaged into a standalone Windows executable (`dist/Jarvis.exe`).
- **Packaging:** Completed using PyInstaller with a custom spec file for PIL and Porcupine resources.
- **UI:** A modern PySide6 dashboard allows for real-time app management and system configuration.
- **Configuration:** Dynamic loading from `apps.json`, `urls.json`, and `config.json`.

## Unified Development Roadmap

### Phase 1: Core System & Packaging (STATUS: COMPLETE)
*   **1.1 Core Logic:** Persistent background service, Wake-word (Porcupine), Clap detection, Auto-launch apps. (Done)
*   **1.2 Code Preparation:** Resource path handling (`_MEIPASS`), separation of UI/Tray from core logic. (Done)
*   **1.3 Packaging:** Build standalone `.exe` with PyInstaller. (Done)

### Phase 2: User Interface Layer (STATUS: COMPLETE)
*   **2.1 Modern Control Dashboard (PySide6):** 
    *   **Status Panel:** Real-time monitoring of Jarvis state and events. (Done)
    *   **App Launch Manager:** Start-Menu based app scanner with path-based launching. (Done)
    *   **Browser Management:** Dynamic URL list for Chrome/Edge/Firefox. (Done)
    *   **Configuration:** On-the-fly updates for wake-word and execution mode (Clap vs Keyword). (Done)
    *   **Process Management:** Tray-based restart and full shutdown. (Done)

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

*   **Entry Point:** `jarvis.py` (orchestrates `UnifiedLauncher`, `TrayManager`, and `DashboardWindow`).
*   **Resources:** Use `resource_path()` for all assets (icons, sounds).
*   **Logging:** Logs to `service.log` with real-time error reporting to the dashboard.
*   **Configuration:** 
    - Secrets: `.env`
    - App preferences: `apps.json`, `urls.json`
    - System settings: `config.json`
