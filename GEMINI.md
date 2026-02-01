# Gemini Project Context: Jarvis Assistant

## Project Overview

This project is a Windows desktop automation assistant named "Jarvis," inspired by Iron Man's AI. It runs as a persistent background application, managed via a system tray icon.

The core functionality involves:
1.  **Wake-Word Detection:** It uses the `pvporcupine` engine to listen for the "jarvis" wake word.
2.  **Clap Trigger:** After the wake word is detected, it listens for a distinct double-clap pattern (or immediate keyword trigger).
3.  **Action Execution:** Upon detection, it launches a dynamic set of applications and URLs configured via the dashboard.

The application is built in Python and uses `sounddevice` and `numpy` for audio processing, `pystray` for the system tray interface, and `PySide6` for the control dashboard.

**Current Status (Feb 2026):**
The application has been successfully packaged into a standalone Windows executable (`dist/Jarvis.exe`) and is evolving into a cognitive companion.
- **Packaging:** Completed using PyInstaller with a custom spec file for PIL and Porcupine resources.
- **UI:** A modern, translucent PySide6 dashboard with Windows 11 Mica/Acrylic effects, per-app URL management, and real-time event logging.
- **Configuration:** Atomic persistence layer implemented via `config_manager.py`.
- **Installation:** Automated via `bootstrap.ps1`, `setup.py`, and `build.py` for one-command setup.
- **Access Key Management:** In-app management for Porcupine Access Key with live validation and startup hardening.
- **Architecture:** Event-driven architecture with Event Bus and Session Memory (Phase 1 complete).

## Unified Development Roadmap

### JARVIS v1.0 (STATUS: COMPLETE)

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

### JARVIS EVOLUTION (IN PROGRESS)

#### Phase 1 — Foundation (STATUS: ✅ COMPLETE - Feb 1, 2026)
**Event-Driven Architecture**
- ✅ Event Bus with AsyncIO pub/sub pattern  
- ✅ Session Memory with SQLite persistence
- ✅ Structured logging (JSON format)
- ✅ Event replay and debugging capabilities
- ✅ Context tracking and preference learning

#### Phase 2 — Conversation Foundation (NEXT)
*Planned Features:*
- Multi-turn dialogue tracking
- Text-to-Speech (TTS) integration
- Pronoun resolution
- Verbal acknowledgments

#### Phase 3-6 — Intelligence, Personality, Proactive Features (PLANNED)
*See `Jarvis_Evolution_Migration_Plan.md` for full roadmap*

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

### 4. Run Tests (Phase 1)
```bash
# Integration test
python tests/test_phase1_integration.py

# Unit tests
pytest tests/test_event_bus.py -v
```

## Project Structure

```text
Jarvis/
├── jarvis.py             # Main entry point (orchestrates all components)
│
├── src/                  # Source modules
│   ├── core/             # Core infrastructure (Phase 1)
│   │   ├── event_bus.py          # Event Bus (pub/sub messaging)
│   │   ├── session_memory.py     # Session Memory (context tracking)
│   │   ├── logging_config.py     # Structured logging
│   │   └── config_manager.py     # Atomic configuration persistence
│   │
│   └── ui/               # User interface
│       └── dashboard.py          # PySide6 Control Dashboard UI
│
├── resources/            # Static resources
│   ├── icons/            # System tray icon (listening.ico)
│   └── sounds/           # Audio feedback files (WAV)
│
├── scripts/              # Build & setup automation
│   ├── bootstrap.ps1     # One-click setup script
│   ├── setup.py          # Dependency & config installer
│   └── build.py          # PyInstaller build wrapper
│
├── tests/                # Unit and integration tests
│   ├── test_event_bus.py
│   └── test_phase1_integration.py
│
├── jarvis.spec           # PyInstaller build configuration
├── apps.json             # Configured applications to launch
├── urls.json             # Configured URLs to open
├── config.json           # System settings (wake-word, mode, Phase 1 config)
├── requirements.txt      # Python dependencies
├── service.log           # Runtime activity & error logs
├── .env                  # Secrets (Access Keys)
├── jarvis_events.db      # Phase 1: Event persistence database
└── jarvis_sessions.db    # Phase 1: Session memory database
```

## Development Conventions

*   **Entry Point:** `jarvis.py` (orchestrates `UnifiedLauncher`, `TrayManager`, `DashboardWindow`, and Phase 1 components).
*   **Resources:** Use `resource_path()` for all assets (icons, sounds).
*   **Logging:** Logs to `service.log` with real-time error reporting to the dashboard. Phase 1 adds structured JSON logging.
*   **Configuration:** 
    - Secrets: `.env`
    - App preferences: `apps.json`, `urls.json`
    - System settings: `config.json` (includes Phase 1 event_bus, session_memory, logging config)
*   **Events:** All major actions publish events to the Event Bus for tracking and debugging.
*   **Testing:** Run integration tests before committing changes.

## Phase 1 Architecture

**Event Flow:**
```
Wake Word → Event Bus → Session Memory
    ↓            ↓            ↓
  Clap     Event Log    Context Update
    ↓            ↓            ↓
Launch Apps  Persistence  Tasks/Prefs
```

**Event Types:**
- `system.initialized` - Jarvis startup
- `wake.detected` - Wake word heard
- `clap.detected` - Double clap detected
- `apps.launching` - Before launching apps
- `app.launched` - Successful app launch
- `app.failed` - App launch failure
- `activation.timeout` - Returning to idle
- `system.shutdown` - Jarvis shutdown
