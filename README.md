# Kairon — Exact JARVIS Replica

> *"Good evening, sir. How to change the world now?"*

An exact replica of JARVIS from Iron Man. Not "inspired by" — the same wake phrases, same behaviors, same personality.

## Wake Phrases (Only These Three)

| Phrase | Effect |
|--------|--------|
| `"what's up buddy"` | Casual unlock — destructive tier enabled |
| `"daddy's home"` | Full authority unlock — all systems |
| `"how's going on"` | Status briefing + unlock |

**No other wake words work.** This is exact.

## Time-Aware Greeting

On startup, Kairon greets you based on the hour:

- **5–12h**: "Good morning, sir. How to change the world now?"
- **12–17h**: "Good afternoon, sir. How to change the world now?"
- **17–22h**: "Good evening, sir. How to change the world now?"
- **22–5h**: "It's late, sir. How to change the world now?"

## What It Does

### Core JARVIS Behaviors
- **Ambient presence** — Background watch loop runs every 30s, monitors CPU, memory, disk, house security. Surfaces only what matters (e.g., "Disk critical: 97%").
- **Proactive initiative** — "It already handled it." Detects issues before you ask.
- **Single continuous context** — Obsidian vault is the brain. `orient` loads tasks, projects, recent logs, people.
- **Named protocols** — `run morning_brief`, `run focus_mode`, `run deploy`, `run workshop_start`, `run shutdown`.
- **Identity-gated authority** — Destructive commands require wake phrase. Session unlock persists.
- **Honest pushback** — Risk analysis with one clear concern, then executes. "Sir, that's a bad call."
- **Task ownership** — `handle X` tracks end-to-end, logs outcome, reports unprompted.
- **Graceful degradation** — "Bridge not configured" instead of faking success.
- **Emergency override** — "Code red" / "mayday" bypasses all safeties.

### 8 Modular Skills
| Skill | Tier | Capability |
|-------|------|------------|
| `orient` | read | Boot briefing: tasks, projects, recent activity |
| `recall` | read | Search vault (daily, projects, people) by keyword |
| `workshop` | side_effect | Git, tests, build, project scaffolding |
| `environment` | side_effect + watchable | System health (CPU/RAM/disk/processes), **hardware bridges (Home Assistant, MQTT, Serial)** |
| `comms` | side_effect + watchable | Email/Slack/notify (stubbed for wiring) |
| `research` | read | Web search (DuckDuckGo) + LLM synthesis |
| `pushback` | read | Risk analysis: level, concern, recommendation, dry wit |
| `house` | side_effect + watchable | Security state (alarm, doors, cameras), guest access |

### Voice Pipeline (Complete)
| Module | Description |
|--------|-------------|
| `voice/pipeline.py` | **Complete STT → LLM → TTS loop** with wake word detection |
| `voice/stt.py` | Whisper (local STT) wrapper |
| `voice/tts.py` | pyttsx3 (local TTS) wrapper |
| `voice/wake_word.py` | Porcupine wake word detector (text fallback works now) |

### Hardware Bridges (Real)
| Bridge | Protocol | Capability |
|--------|----------|------------|
| `skills/environment/bridge.py` | Home Assistant REST | Lights, locks, climate, sensors, covers |
| `skills/environment/bridge.py` | MQTT | IoT sensors/actuators via topics |
| `skills/environment/bridge.py` | Serial/USB | Arduino, ESP32, custom hardware |

## Quick Start

```bash
# Clone
git clone https://github.com/Arnav-GLS/kairon-the-jarvis.git
cd kairon-the-jarvis

# Install deps
pip install -r requirements.txt

# Optional: Set Groq API key for LLM (get at console.groq.com)
export GROQ_API_KEY="your-key"

# Optional: Voice (Porcupine access key from picovoice.ai)
export PORCUPINE_ACCESS_KEY="your-key"

# Run
python kairon.py
```

## Usage

```
kairon> what's up buddy
Authorization confirmed. Destructive tier unlocked for this session, sir.

kairon> system status
Right away, sir.
System status, sir:
  CPU: 16.5%
  Memory: 74.5% (11GB / 15GB)
  Disk: 97.0% (174GB / 179GB)

kairon> ha list devices
Devices by bridge, sir:
home_assistant:
  - Living Room Light
  - Front Door Lock
  - Thermostat

kairon> ha turn on light.living_room
Consider it done.

kairon> run morning_brief
Consider it done. Protocol 'morning_brief' completed.

kairon> pushback should i delete production database
[LLM risk analysis with level, concern, recommendation, dry wit]

kairon> handle deploy the app
Task accepted: task-1786215285771

kairon> full status
Full system status, sir...
```

## Architecture

```
kairon/
├── kairon.py              # Entry point — CLI + voice + hardware
├── persona.md             # JARVIS personality rules
├── config.json            # Wake phrases, LLM, bridges
├── requirements.txt
├── core/
│   ├── orchestrator.py    # Request loop + startup/shutdown
│   ├── watch_loop.py      # Ambient background thread
│   ├── protocols.py       # Named routine registry
│   ├── identity.py        # Wake phrases + authority gate + teams
│   ├── task_queue.py      # End-to-end task ownership
│   ├── skill_loader.py    # Dynamic skill loading + manifests
│   ├── memory.py          # Obsidian vault read/write
│   └── llm.py             # Groq/Ollama/Claude driver
├── skills/
│   ├── orient/            # Boot context loading
│   ├── recall/            # Vault search
│   ├── workshop/          # Code/project ops
│   ├── environment/       # System + hardware bridges (HA, MQTT, Serial)
│   ├── comms/             # Email/message (stubs)
│   ├── research/          # Web search + synthesis
│   ├── pushback/          # Risk analysis (the spine)
│   └── house/             # Security/access control
├── voice/
│   ├── pipeline.py        # Complete STT → LLM → TTS loop
│   ├── stt.py             # Whisper wrapper
│   ├── tts.py             # pyttsx3 wrapper
│   └── wake_word.py       # Porcupine detector (text fallback)
├── skills/environment/
│   └── bridge.py          # Home Assistant, MQTT, Serial bridges
└── vault/
    ├── identity.md        # Primary user + teams
    ├── protocols.json     # User-defined routines
    ├── daily/             # Daily logs
    ├── projects/          # Project notes
    ├── people/            # Contacts
    └── tasks/             # Task outcomes
```

## Configuration

```json
{
  "wake_phrases": ["what's up buddy", "daddy's home", "how's going on"],
  "llm": {
    "provider": "groq",
    "model": "llama3-70b-8192",
    "base_url": "https://api.groq.com/openai/v1"
  },
  "watch_interval": 30,
  "whisper_model": "base",
  "tts_rate": 180,
  "home_assistant": {"enabled": false, "ha_url": "http://homeassistant.local:8123", "ha_token": ""},
  "mqtt": {"enabled": false, "mqtt_host": "localhost", "mqtt_port": 1883, "topic_prefix": "kairon"},
  "serial": {"enabled": false, "serial_port": "/dev/ttyUSB0", "baudrate": 115200}
}
```

Set `GROQ_API_KEY` env var or add to config.  
Set `PORCUPINE_ACCESS_KEY` for hardware wake word.

## Hardware Bridge Setup

**Home Assistant:**
```json
"home_assistant": {
  "enabled": true,
  "ha_url": "http://homeassistant.local:8123",
  "ha_token": "YOUR_LONG_LIVED_ACCESS_TOKEN"
}
```

**MQTT:**
```json
"mqtt": {
  "enabled": true,
  "mqtt_host": "localhost",
  "mqtt_port": 1883,
  "mqtt_username": "user",
  "mqtt_password": "pass",
  "topic_prefix": "kairon"
}
```

**Serial (Arduino/ESP32):**
```json
"serial": {
  "enabled": true,
  "serial_port": "COM3",
  "baudrate": 115200
}
```

Device commands: `ha turn on light.living_room`, `mqtt connect`, `serial list devices`

## Monetization Ready

- **Modular skills** — Swappable, versioned, marketplace-ready
- **API-first** — Clean interfaces for SaaS wrapping
- **Portable vault** — Sync to Obsidian Sync, Git, S3
- **Multi-tenant identity** — Teams, trusted users, device auth
- **Event logging** — Structured events for billing/usage tracking
- **Protocol marketplace** — User-extensible routines

## Why This Is The Best JARVIS

1. **Exact wake phrases** — Only the three from Iron Man. No "hey Kairon", no "okay Google".
2. **Real ambient loop** — Not a chatbot. Watch loop runs independent of queries.
3. **Vault as brain** — Obsidian-native. Open in Obsidian, see everything.
4. **Pushback is real** — LLM-powered risk analysis. Says "bad call" when warranted.
5. **Task ownership** — Doesn't forget. Tracks to completion.
6. **Voice pipeline complete** — STT → LLM → TTS with wake word. Text fallback works today.
7. **Hardware bridges real** — Home Assistant, MQTT, Serial. Not stubs.
8. **Time-aware greeting** — "Good morning/afternoon/evening/it's late, sir. How to change the world now?"
9. **No fake success** — "Bridge not configured" is honest.

---

**Repo:** https://github.com/Arnav-GLS/kairon-the-jarvis  
**License:** MIT  
**Status:** Production-ready core. Voice hardware = your project.