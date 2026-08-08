"""Comms skill: email, messages, notifications."""
from pathlib import Path
from typing import Dict, Any


class Skill:
    name = "comms"
    tier = "side_effect"
    watchable = True
    triggers = ["email", "message", "send", "notify", "mail", "inbox", "slack", "teams"]

    def __init__(self):
        self.vault = None

    def set_vault(self, vault):
        self.vault = vault

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        if "send" in raw_lower and ("email" in raw_lower or "mail" in raw_lower):
            return self._send_email(raw)
        elif "inbox" in raw_lower:
            return self._check_inbox()
        elif "notify" in raw_lower:
            return self._notify(raw)
        
        return {"ok": True, "message": "Communications ready, sir. Email/Slack bridges need wiring in skills/comms/bridge.py"}

    def _send_email(self, raw: str) -> Dict[str, Any]:
        return {"ok": False, "error": "Email bridge not configured, sir. Add SMTP config to skills/comms/bridge.py"}

    def _check_inbox(self) -> Dict[str, Any]:
        return {"ok": False, "error": "IMAP bridge not configured, sir."}

    def _notify(self, raw: str) -> Dict[str, Any]:
        # Local notification
        msg = raw.replace("notify", "").replace("me", "").strip()
        return {"ok": True, "message": f"Notification queued: {msg}"}

    def check_state(self) -> Dict[str, Any]:
        """Watchable: check for new messages (stub)"""
        return None

    def on_finding(self, state: Dict[str, Any]):
        pass

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)