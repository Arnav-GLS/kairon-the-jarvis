"""WatchLoop: ambient background thread. Runs on interval, checks skills' watchable state, surfaces only what clears relevance bar."""
import threading
import time
from typing import List, Dict, Any


class WatchLoop:
    def __init__(self, skills: List, vault, interval_seconds: int = 30):
        self.skills = skills
        self.vault = vault
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread = None
        self.relevance_threshold = 0.5

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                self.vault.log({"event": "watch_loop_error", "error": str(e)})
            self._stop.wait(self.interval)

    def _tick(self):
        findings = []
        for skill in self.skills:
            if hasattr(skill, "watchable") and skill.watchable:
                state = skill.check_state()
                if state and state.get("relevance", 0) >= self.relevance_threshold:
                    findings.append({"skill": skill.name, "state": state})
        if findings:
            self.vault.log({"event": "watch_loop_surfaced", "findings": findings})
            self._surface(findings)

    def _surface(self, findings: List[Dict[str, Any]]):
        for f in findings:
            skill = next((s for s in self.skills if s.name == f["skill"]), None)
            if skill and hasattr(skill, "on_finding"):
                skill.on_finding(f["state"])