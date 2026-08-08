"""Protocols: named multi-step routine registry. User-defined, re-runnable."""
import json
from pathlib import Path
from typing import Dict, List, Any


class ProtocolRegistry:
    def __init__(self, config_path: str = None):
        self.protocols: Dict[str, Dict] = {}
        self.config_path = config_path
        if config_path and Path(config_path).exists():
            self._load()
        else:
            self._write_defaults()

    def register(self, name: str, steps: List[str], description: str = ""):
        self.protocols[name] = {"steps": steps, "description": description}
        self._save()

    def get(self, name: str) -> Dict:
        return self.protocols.get(name)

    def list_protocols(self) -> List[str]:
        return list(self.protocols.keys())

    def _load(self):
        with open(self.config_path, "r") as f:
            self.protocols = json.load(f)

    def _save(self):
        if not self.config_path:
            return
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.protocols, f, indent=2)

    def _write_defaults(self):
        defaults = {
            "morning_brief": {
                "steps": ["check calendar for today", "check inbox for urgent", "check task queue status", "summarize weather"],
                "description": "Daily morning briefing routine"
            },
            "focus_mode": {
                "steps": ["mute notifications", "close distracting apps", "set status to focused", "start focus timer"],
                "description": "Enter deep work mode"
            },
            "deploy": {
                "steps": ["run tests", "build project", "push to remote", "notify on completion"],
                "description": "Standard deployment sequence"
            },
            "workshop_start": {
                "steps": ["open project", "check git status", "run tests", "show todo"],
                "description": "Initialize workshop session"
            },
            "shutdown": {
                "steps": ["save all", "commit changes", "sync vault", "power down"],
                "description": "Graceful shutdown"
            }
        }
        self.protocols = defaults
        self._save()