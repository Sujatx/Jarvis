# Jarvis — AI Automation Assistant (Windows)

While growing up I was amazed when I saw **Iron Man** and I'm damn sure you had too, and you know **Tony** was kind of a vibe-coder as well — he was the force behind everything. He had some great visions and **Jarvis** helped him achieve it.

**TONY STARK BUILT THIS IN A CAVE, WITH A BOX OF SCRAPS!**

Well, here I am building my own **Jarvis** from scratch, leveraging everything I can — because why not?

---

---

## Core System

Jarvis is an event-driven assistant for Windows that bridges the gap between natural language and system control. It is built on a modular architecture that prioritizes privacy, reliability, and security.

### How it Works:

*   **Event-Driven Core:** All components communicate via an asynchronous `EventBus`. This decoupled design ensures that perception (voice/text), cognition (LLM/Logic), and execution (Tools) remain independent and highly responsive.
*   **Offline-First Intelligence:** Common system intents (opening apps, checking time, help) are handled locally using pattern matching. This provides zero-latency responses and ensures core functionality works without an internet connection.
*   **Secure Execution Pipeline:** Every system action is routed through a validation layer. Commands are checked against a strict registry and sanitized by a `SecurityManager` to prevent harmful access.
*   **LLM Tool-Calling:** For complex requests, Jarvis uses an LLM to interpret intent and generate structured tool calls. This allows for flexible, natural language control of your workspace.
*   **Modular Plugin Architecture:** System capabilities are implemented as standalone tools. New functionality can be added by simply dropping a new tool plugin into the system.
*   **Privacy-First Perception:** Audio processing and wake-word detection happen locally. The microphone is only gated open when the system is actively listening for a command.

---

---

## Essential Assets

To keep the repository lightweight, large ML models and assets are not tracked. You must download/configure these manually:

1.  **TTS Voice Model**: Download the [Northern English Male (Medium)](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx) Piper model and place it in `resources/voices/`.
2.  **API Configuration**: Create a `.env` file in the root directory with the following:
    ```env
    PORCUPINE_ACCESS_KEY=your_key_here
    GEMINI_API_KEY=your_key_here
    ```
    *   Get a **Porcupine** key from [Picovoice Console](https://console.picovoice.ai/).
    *   Get a **Gemini** key from [Google AI Studio](https://aistudio.google.com/).

---

---

## Quick Start

### Development Setup
```bash
# Bootstrap the environment
.\bootstrap.ps1

# Run Jarvis
python jarvis.py
```

### Usage
- Ensure your assets are in place (see section above).
- Toggle **Voice Mode** in the dashboard to enable hands-free interaction.

---

## Project Structure

```
Jarvis/
├── jarvis.py                     # Main orchestrator
├── src/                          # Source modules
│   ├── core/                     # Messaging, Security, and Memory
│   ├── cognitive/                # Reasoning and Intent Routing
│   ├── tools/                    # Modular System Tools (Plugins)
│   ├── perception/               # Audio and Speech Processing
│   └── execution/                # Plan Validation and Execution
├── config/                       # System and Intent configuration
└── resources/                    # Icons, Sounds, and Voice Models
```

---

---

## License

Released under the MIT License.

---

**"Sometimes you gotta run before you can walk."** — Tony Stark
