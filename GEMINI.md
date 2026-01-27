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
- **Installation:** Automated via `bootstrap.ps1`, `setup.py`, and `build.py` for one-command setup.
- **Access Key Management:** In-app management for Porcupine Access Key with live validation and startup hardening.

## Unified Development Roadmap

### FINAL RELEASE PLAN — JARVIS v1.0 (STATUS: COMPLETE)

#### Phase A — Access Key Integration (STATUS: COMPLETE)
**A1. In-App Porcupine Key Management** (Done)
**A2. Startup Hardening** (Done)

#### Phase B — Release Readiness (STATUS: COMPLETE)
**B1. First-Run Experience** (Done)
**B2. Repo + Release Structure** (Done)
**B3. Documentation Split** (Done)

#### Phase C — Packaging & QA (STATUS: COMPLETE)
**C1. Build** (Done)
**C2. Test Matrix** (Done)

#### Phase D — Release (STATUS: COMPLETE)
- **Version:** Jarvis v1.0 (Released Jan 2026)

#### Phase E — Next (POST-RELEASE)
*Only after v1.0 ships:*
- Text-to-Speech (TTS)
- Spoken commands
- AI automation

## Developer: Installation & Setup

### 1. Quick Start
```powershell
.\bootstrap.ps1
```

### 2. Manual Setup
```bash
# Create venv
python -m venv venv
.\venv\Scripts\activate

# Install dependencies and create configs
python setup.py
```

### 3. Run or Build
**To run from source:**
```bash
python jarvis.py
```

**To build the executable:**
```bash
python build.py
```

## Project Structure

```text
Jarvis/
├── bootstrap.ps1         # One-click setup script
├── setup.py              # Dependency & config installer
├── build.py              # PyInstaller build wrapper
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

## Development Conventions

*   **Entry Point:** `jarvis.py` (orchestrates `UnifiedLauncher`, `TrayManager`, and `DashboardWindow`).
*   **Resources:** Use `resource_path()` for all assets (icons, sounds).
*   **Logging:** Logs to `service.log` with real-time error reporting to the dashboard.
*   **Configuration:** 
    - Secrets: `.env`
    - App preferences: `apps.json`, `urls.json`
    - System settings: `config.json`
