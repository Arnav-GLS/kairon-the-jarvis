# Kairon — Exact JARVIS Replica

> *"Good evening, sir. Kairon systems coming online."*

An exact replica of JARVIS from Iron Man. Not "inspired by" — the same wake phrases, same behaviors, same personality.

## Wake Phrases (Only These Three)

| Phrase | Effect |
|--------|--------|
| `"what's up buddy"` | Casual unlock — destructive tier enabled |
| `"daddy's home"` | Full authority unlock — all systems |
| `"how's going on"` | Status briefing + unlock |

**No other wake words work.** This is exact.

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
| `environment` | side_effect + watchable | System health (CPU/RAM/disk/processes), smart home stubs |
| `comms` | side_effect + watchable | Email/Slack/notify (stubbed for wiring) |
| `research` | read | Web search (DuckDuckGo) + LLM synthesis |
| `pushback` | read | Risk analysis: level, concern, recommendation, dry wit |
| `house` | side_effect + watchable | Security state (alarm, doors, cameras), guest access |

### Voice Stubs (Ready for Wiring)
- `voice/stt.py` — Whisper (local STT)
- `voice/tts.py` — pyttsx3 (local TTS)
- `voice/wake_word.py` — Wake phrase detector

## Quick Start

```bash
# Clone
git clone https://github.com/Arnav-GLS/kairon-the-jarvis.git
cd kairon-the-jarvis

# Install deps
pip install -r requirements.txt

# Optional: Set Groq API key for LLM (get at console.groq.com)
export GROQ_API_KEY="your-key"

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
  CPU: 22.1%
  Memory: 64.9% (10GB / 15GB)
  Disk: 97.3% (175GB / 179GB)

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
├── kairon.py              # Entry point — CLI REPL
├── persona.md             # JARVIS personality rules
├── config.json            # Wake phrases, LLM config
├── requirements.txt
├── core/
│   ├── orchestrator.py    # Request loop + startup/shutdown
│   ├── watch_loop.py      # Ambient background thread
│   ├── protocols.py       # Named routine registry
│   ├── identity.py        # Wake phrases + authority gate
│   ├── task_queue.py      # End-to-end task ownership
│   ├── skill_loader.py    # Dynamic skill loading
│   ├── memory.py          # Obsidian vault read/write
│   └── llm.py             # Groq/Ollama/Claude driver
├── skills/
│   ├── orient/            # Boot context loading
│   ├── recall/            # Vault search
│   ├── workshop/          # Code/project ops
│   ├── environment/       # System + smart home
│   ├── comms/             # Email/message (stubs)
│   ├── research/          # Web search + synthesis
│   ├── pushback/          # Risk analysis (the spine)
│   └── house/             # Security/access control
├── voice/
│   ├── stt.py             # Whisper wrapper
│   ├── tts.py             # pyttsx3 wrapper
│   └── wake_word.py       # Phrase detector
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
  "startup_sequence": true,
  "shutdown_sequence": true
}
```

Set `GROQ_API_KEY` env var or add to config.

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
6. **Voice-ready** — Stubs wired, just add hardware.
7. **No fake success** — "Bridge not configured" is honest.

---

**Repo:** https://github.com/Arnav-GLS/kairon-the-jarvis  
**License:** MIT  
**Status:** Production-ready core. Voice hardware = your project.