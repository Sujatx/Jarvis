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
*   **Configuration:** [Porcupine Access Key](https://picovoice.ai/console/) (Free tier available)

---

## Getting Started

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

---

## License

Released under the MIT License.

---
