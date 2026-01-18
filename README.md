# Jarvis — Automation Assistant (Windows)

While growing up I was amazed when I saw **Iron Man** and I’m damn sure you had too, and you know **Tony** was kind of a vibe-coder as well — he was the force behind everything. He had some great visions and **Jarvis** helped him achieve it.

**TONY STARK BUILT THIS IN A CAVE, WITH A BOX OF SCRAPS!**

Well, here I am building my own **Jarvis** from scratch, leveraging everything I can — because why not?


---

## System Overview

Jarvis provides:

* Offline wake‑word detection using Picovoice Porcupine
* Precision double‑clap pattern recognition
* Persistent background execution through a Windows system tray icon
* Automatic multi‑app launching on command
* Audio feedback for activation, detection, and errors
* Pause/resume controls
* Real‑time logging for analysis

The design prioritizes consistency: the system keeps listening unless paused deliberately.

---

## Requirements

* Windows 10 or Windows 11
* Python 3.10–3.12
* Microphone
* Porcupine Access Key
* Google Chrome
* Visual Studio Code

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/Sujatx/Jarvis.git
cd Jarvis
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file:

```
PORCUPINE_ACCESS_KEY=your_key_here
CHROME_PROFILE=Profile 1
```

### 4. Run Jarvis

```bash
python clap_launcher.py
```

The tray icon will appear, and the listener will begin running in the background.

---

## Usage

### Wake Word

Say:

```
jarvis
```

The system enters active mode.

### Action Trigger (Double Clap)

```
clap clap
```

This launches:

* Visual Studio Code (last session)
* Google Chrome → ChatGPT
* Google Chrome → Notion (Second Brain)

Actions are defined in:

```
launch_all_apps()
```

Modify freely.

---

## Troubleshooting

**Wake word not detected**

* Ensure microphone access is allowed for Python
* Validate Porcupine API key
* Reduce background noise

**Claps not detected**

* Adjust `clap_threshold`
* Use sharp claps rather than ambient taps

**Chrome or VS Code not launching**

* Confirm paths and profile names
* Make sure Chrome background mode doesn’t interfere

---

## Project Structure

```
Jarvis/
│
├── clap_launcher.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env                  (ignored)
│
├── icons/
│   ├── listening.png
│   ├── active.png
│   └── error.png
│
└── sounds/
    ├── wake.wav
    ├── clap.wav
    └── error.wav
```

---

## License

Released under the MIT License. Modification and redistribution are permitted with attribution.

---

Jarvis runs silently—until you speak. Then it listens only to you.
