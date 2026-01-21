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
- **UI:** A modern, translucent PySide6 dashboard with Windows 11 Mica/Acrylic effects, per-app URL management, and real-time event logging.
- **Configuration:** Atomic persistence layer implemented via `config_manager.py`.

## Unified Development Roadmap

### Phase 1: JARVIS DASHBOARD — FINAL MODERN UI PLAN (STATUS: COMPLETE)
1. **Window-Level Modernization** (Done)
   - Applied Windows 11 Mica/Acrylic via DWM API.
   - Fallback: semi-transparent dark background.
   - Rounded corners enabled for entire window.
   - Font: Segoe UI Variable globally.

2. **Global Theme** (Done)
   - Sidebar: #1b1b1b
   - Main background: #202020 (opaque/semi-transparent hybrid)
   - Accent: #00e5ff
   - Smooth hover transitions.

3. **App Manager** (Done)
   - Split into "Enabled Apps" and "Available Apps" sections.
   - Toggling moves apps between sections.
   - Modern card layout.

4. **Browser URL Management** (Done)
   - Per-app collapsible URL sections for Chrome, Edge, and Firefox.
   - Integrated directly into the app cards.
   - Fully persistent via `config_manager`.

5. **Settings Page Enhancements** (Done)
   - Card-style sections for Wake Word, Mode, and Restart.
   - Modern input styling.

6. **Status Page Enhancements** (Done)
   - Real-time "Event Log" panel with timestamps.
   - Displays last ~20 system events.

7. **Scroll Behavior** (Done)
   - Kinetic/momentum scrolling enabled (`QScroller`).

8. **Persistence** (Done)
   - All settings saved via `config_manager.py` with atomic writes.

9. **Implementation Sequence** (Done)
   - All steps completed, tested, and packaged.

### Phase 2: Voice Interaction Upgrade (STATUS: PLANNED)
*   **2.1 Text-to-Speech (TTS):** Allow Jarvis to speak back.
*   **2.2 Voice Commands:** Replace/augment claps with spoken commands.

### Phase 3: Automation & AI (STATUS: PLANNED)
*   **3.1 Advanced Automation:** Execute complex tasks beyond app launching.
*   **3.2 AI Brain:** Integrate LLMs for natural language understanding and context memory.

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
