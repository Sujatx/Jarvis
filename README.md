# Jarvis

A personal assistant built the "AI memory vault" way: the **brain** is Claude Code itself
(configured by `CLAUDE.md`), the **memory** is an Obsidian vault, and a **voice line** + a
**WebGL brain-orb visualizer** give it a voice and a face.

```
launch.bat           # one-click: starts the server, the visualizer window, and the voice line
CLAUDE.md            # the brain: persona, rules, and a pointer to the vault memory
voice-line/          # mic -> speech-to-text -> claude -> speech, and the signal-bus writer
voice-visualizer/    # golden J.A.R.V.I.S. brain-orb (WebGL) that reacts to the voice line
```

Memory lives in the Obsidian vault at `%USERPROFILE%\Desktop\Second brain`
(`VAULT-INDEX.md`, `MEMORY.md`, `01 - Daily Notes/`). The brain is the only thing that writes it.

---

## Setup (once)

```powershell
pip install -r requirements.txt
```

You also need the Claude Code CLI on your PATH (`claude`) and Google Chrome (for the visualizer
window — it falls back to your default browser if Chrome isn't found).

Check everything is wired up:

```powershell
python voice-line\voice_line.py --check
```

---

## Run it

**1. Talk to the brain directly (no voice):**

```powershell
claude    # run inside this folder; CLAUDE.md + the vault load automatically
```

**2. Full voice + visuals — one click:**

Double-click **`launch.bat`** (in the repo root). It starts the visualizer server, opens the Jarvis
window, and launches the voice line (brain) using the repo's `.venv`. You'll watch it initialize
on screen ("JARVIS — Loading…"), then Jarvis greets you when ready.

Say "Hey Jarvis", speak your request, and watch the orb move through
listening → thinking → speaking while Jarvis replies — with live subtitles of what you said and
what he answers. The core and filaments breathe with the live voice level, and alert floods it red.

(Prefer press-Enter over the wake word? Add `--ptt` to the voice-line line inside `launch.bat`,
or run `python voice-line\voice_line.py --ptt` yourself.)

---

## The visualizer on its own

```powershell
python voice-visualizer\server.py --mock    # port 8778, scripted state loop
```

Then open `http://127.0.0.1:8778`. Useful URL hooks:

- `?mockstate=speaking` — simulate any state locally (idle/listening/thinking/speaking/alert)
- `?shot=speaking&t=1200` — render a state deterministically and freeze (for screenshots)
- press **F** for the FPS meter; any key skips the assemble-in intro

The scene is WebGL (`index.html`); it needs a browser with WebGL (any modern Chrome).

---

## The signal bus

The voice line writes, and the visualizer server reads (read-only), three files in
`%USERPROFILE%\voice-line\`:

- `.voice_state` — `idle` | `listening` | `thinking` | `speaking`
- `.voice_waveform` — `{"ts", "samples":[64]}`; a fresh waveform always reads as *speaking*
- `.voice_alert` — present only during an alert
