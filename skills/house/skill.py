"""House skill: security, access control, environmental monitoring — JARVIS's house system."""
from pathlib import Path
from typing import Dict, Any


class Skill:
    name = "house"
    tier = "side_effect"
    watchable = True
    triggers = ["house", "home", "security", "alarm", "lock", "unlock", "door", "window", "camera", "guest"]

    def __init__(self):
        self.vault = None
        self.security_state = {"armed": False, "doors_locked": True, "cameras_active": True}

    def set_vault(self, vault):
        self.vault = vault

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        if "security" in raw_lower or "status" in raw_lower:
            return self._security_status()
        elif "arm" in raw_lower and "alarm" in raw_lower:
            return self._arm_alarm()
        elif "disarm" in raw_lower:
            return self._disarm_alarm()
        elif "lock" in raw_lower and "door" in raw_lower:
            return self._lock_doors()
        elif "unlock" in raw_lower and "door" in raw_lower:
            return self._unlock_doors()
        elif "camera" in raw_lower:
            return self._camera_status()
        elif "guest" in raw_lower:
            return self._guest_access(raw)
        
        return self._house_summary()

    def _security_status(self) -> Dict[str, Any]:
        status = "ARMED" if self.security_state["armed"] else "DISARMED"
        doors = "LOCKED" if self.security_state["doors_locked"] else "UNLOCKED"
        cameras = "ACTIVE" if self.security_state["cameras_active"] else "OFFLINE"
        
        lines = [
            f"House security status, sir:",
            f"  Alarm: {status}",
            f"  Doors: {doors}",
            f"  Cameras: {cameras}"
        ]
        return {"ok": True, "message": "\n".join(lines)}

    def _arm_alarm(self) -> Dict[str, Any]:
        if not self.security_state["doors_locked"]:
            return {"ok": False, "error": "Cannot arm: doors unlocked, sir."}
        self.security_state["armed"] = True
        if self.vault:
            self.vault.log({"event": "house_alarm_armed"})
        return {"ok": True, "message": "Alarm armed. House secure, sir."}

    def _disarm_alarm(self) -> Dict[str, Any]:
        self.security_state["armed"] = False
        if self.vault:
            self.vault.log({"event": "house_alarm_disarmed"})
        return {"ok": True, "message": "Alarm disarmed. Welcome home, sir."}

    def _lock_doors(self) -> Dict[str, Any]:
        self.security_state["doors_locked"] = True
        return {"ok": True, "message": "All doors locked, sir."}

    def _unlock_doors(self) -> Dict[str, Any]:
        self.security_state["doors_locked"] = False
        return {"ok": True, "message": "Doors unlocked, sir."}

    def _camera_status(self) -> Dict[str, Any]:
        if self.security_state["cameras_active"]:
            return {"ok": True, "message": "All cameras active and recording, sir."}
        return {"ok": True, "message": "Cameras offline, sir."}

    def _guest_access(self, raw: str) -> Dict[str, Any]:
        return {"ok": True, "message": "Guest access system not wired, sir. Configure smart lock in skills/house/bridge.py"}

    def _house_summary(self) -> Dict[str, Any]:
        return self._security_status()

    def check_state(self) -> Dict[str, Any]:
        """Watchable: check for security events"""
        if self.security_state["armed"] and not self.security_state["doors_locked"]:
            return {"relevance": 1.0, "alert": "Alarm armed but doors unlocked!"}
        return None

    def on_finding(self, state: Dict[str, Any]):
        if self.vault and "alert" in state:
            self.vault.log({"event": "house_security_alert", "alert": state["alert"]})

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)