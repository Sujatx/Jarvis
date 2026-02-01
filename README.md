# Jarvis — AI Automation Assistant (Windows)

While growing up I was amazed when I saw **Iron Man** and I'm damn sure you had too, and you know **Tony** was kind of a vibe-coder as well — he was the force behind everything. He had some great visions and **Jarvis** helped him achieve it.

**TONY STARK BUILT THIS IN A CAVE, WITH A BOX OF SCRAPS!**

Well, here I am building my own **Jarvis** from scratch, leveraging everything I can — because why not?

---

## 🚀 Evolution Status

**Current Version:** v1.0 + Phase 1 Foundation  
**Phase Completed:** Phase 1 - Event-Driven Architecture ✅  
**Status:** Ready for Phase 2 (Conversation Foundation)

Jarvis is evolving from a simple automation assistant into a true **cognitive companion** with conversational intelligence, contextual awareness, and proactive capabilities.

---

## System Overview

Jarvis is a persistent background assistant for Windows that automates your workspace initialization through a unique two-stage trigger system. It minimizes distraction by living entirely in the system tray and provides a modern dashboard for complete control.

### Key Features:

#### **v1.0 Features**
*   **Modern Control Dashboard:** A PySide6-based UI featuring Windows 11 Mica effects, dark mode, and smooth transitions.
*   **Two-Stage Activation:** Combines offline wake-word detection ("Jarvis") with precision double-clap recognition. Supports Keyword-only mode for instant activation.
*   **Dynamic App Manager:** Scans your Start Menu for installed applications. Apps are split into "Enabled" and "Available" lists for easy management.
*   **Browser Integration:** Configure custom URL lists for Chrome, Edge, or Firefox directly within the app cards.
*   **Real-Time Status:** Includes an Event Log on the Status page to monitor system activity and errors.
*   **Packaged Executable:** Runs as a standalone `.exe` with zero console flashes.
*   **Privacy-First:** Uses local wake-word detection via Porcupine; no audio is uploaded to the cloud.

#### **Phase 1: Foundation (New!) ✅**
*   **Event-Driven Architecture:** All actions now publish events to a central Event Bus for tracking and debugging
*   **Session Memory:** Persistent storage tracks your work sessions, context, tasks, and learned preferences
*   **Structured Logging:** JSON-formatted logs with severity levels and automatic rotation
*   **Event Persistence:** Complete event history stored in SQLite for replay and analysis
*   **Context Tracking:** Remembers what you're working on across restarts
*   **Preference Learning:** Learns your patterns and habits over time

---

## Architecture

### **Event Bus**
- AsyncIO-based publish/subscribe message queue
- Topic-based routing with wildcard support (`app.*`, `*`)
- Event persistence to SQLite with correlation ID tracking
- Event replay capability for debugging multi-step operations

### **Session Memory**
- Tracks active work sessions and project context
- Flexible key-value context storage (JSON blobs)
- Task management (create, complete, list pending)
- Preference learning with confidence scoring

### **Event Flow**
```
Wake Word → Event Bus → Session Memory
    ↓            ↓            ↓
  Clap     Event Log    Context Update
    ↓            ↓            ↓
Launch Apps  Persistence  Tasks/Prefs
```

---

## Requirements

*   **OS:** Windows 10 or 11
*   **Hardware:** Functional Microphone
*   **Configuration:** [Porcupine Access Key](https://picovoice.ai/console/) (Free tier available)
*   **Python:** 3.8+ (for development only, not needed for `.exe`)

---

## Getting Started

### **Option 1: Run from Executable**
1.  **Download:** Download the latest `Jarvis.exe` from the Releases page.
2.  **Launch:** Run `Jarvis.exe`. It will appear in your system tray.
3.  **Configure:** Right-click the tray icon and select **Settings** to open the Dashboard.
    - Go to **Settings** → **Voice Engine**.
    - Paste your **Porcupine Access Key** and click **Verify & Save**.
    - Toggle the apps you want Jarvis to launch in the **App Manager**.
4.  **Trigger:**
    *   Say **"Jarvis"** (or your custom wake-word).
    *   If in **Clap Mode**: Double-clap within 5 seconds.
    *   If in **Keyword Mode**: Jarvis triggers immediately after the wake-word.
5.  **Result:** Jarvis plays a sound and launches your configured workspace.

### **Option 2: Run from Source (Developers)**
```bash
# Quick setup
.\bootstrap.ps1

# Or manual setup
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Run Jarvis
python jarvis.py
```

---

## Project Structure

```
Jarvis/
├── jarvis.py                     # Main entry point
│
├── src/                          # Source modules
│   ├── core/                     # Core infrastructure
│   │   ├── event_bus.py          # Phase 1: Event Bus
│   │   ├── session_memory.py     # Phase 1: Session Memory
│   │   ├── logging_config.py     # Phase 1: Structured logging
│   │   └── config_manager.py     # Config utilities
│   │
│   └── ui/                       # User interface
│       └── dashboard.py          # Control Dashboard
│
├── resources/                    # Static resources
│   ├── icons/                    # System tray icons
│   └── sounds/                   # Audio feedback
│
├── scripts/                      # Build & setup scripts
│   ├── bootstrap.ps1            # One-click setup
│   ├── setup.py                  # Dependency installer
│   └── build.py                  # Build automation
│
├── tests/                        # Unit and integration tests
│   ├── test_event_bus.py
│   └── test_phase1_integration.py
│
├── config.json                   # System settings
├── apps.json                     # App launcher config
├── urls.json                     # Browser URLs
├── .env                          # Secrets (Access Keys)
├── requirements.txt              # Dependencies
├── jarvis.spec                   # Build configuration
└── README.md                     # This file
```

---

## Phase 1 Testing

```bash
# Run integration tests
python tests/test_phase1_integration.py

# Run unit tests (requires pytest)
pytest tests/test_event_bus.py -v
```

---

## License

Released under the MIT License.

---

**"Sometimes you gotta run before you can walk."** — Tony Stark
