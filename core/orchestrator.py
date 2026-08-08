"""Orchestrator: request loop — parse → route → tier check → act → log."""
import json
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory import Memory
from core.protocols import ProtocolRegistry
from core.identity import IdentityGate
from core.task_queue import TaskQueue
from core.skill_loader import SkillLoader
from core.watch_loop import WatchLoop
from core.llm import LLMClient


class Orchestrator:
    AUTONOMY_TIERS = {"read", "side_effect", "destructive", "emergency"}

    def __init__(self, vault_path: str, skills_path: str, persona_path: str, config: Dict[str, Any]):
        self.vault = Memory(vault_path)
        self.identity = IdentityGate(vault_path)
        self.task_queue = TaskQueue(self.vault)
        self.protocols = ProtocolRegistry(str(Path(vault_path) / "protocols.json"))
        self.skill_loader = SkillLoader(skills_path)
        self.skills = self.skill_loader.load_all()
        self.watch_loop = WatchLoop(self.skills, self.vault, config.get("watch_interval", 30))
        self.llm = LLMClient(config.get("llm", {}))
        self.persona = self._load_persona(persona_path)
        self.config = config
        self.session_unlocked = False
        self.vault.orient()

    def _load_persona(self, path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    def handle(self, raw_input: str, requester: str = "primary") -> Dict[str, Any]:
        if self._is_emergency(raw_input):
            return self._execute_emergency(raw_input, requester)
        
        if not self.session_unlocked and self._contains_wake_word(raw_input):
            self.session_unlocked = True
            return {"status": "unlocked", "message": "Wake word accepted. Destructive commands now permitted for this session."}

        cmd = self._parse(raw_input)
        if cmd["type"] == "protocol":
            return self._run_protocol(cmd["name"], cmd["args"], requester)
        if cmd["type"] == "task":
            return self.task_queue.handoff(cmd["description"], requester, self.skills)
        return self._route_skill(cmd, requester)

    def _parse(self, raw: str) -> Dict[str, Any]:
        raw = raw.strip()
        if raw.lower().startswith("run "):
            parts = raw[4:].split(maxsplit=1)
            return {"type": "protocol", "name": parts[0], "args": parts[1] if len(parts) > 1 else ""}
        if raw.lower().startswith("handle ") or raw.lower().startswith("do "):
            desc = raw.split(maxsplit=1)[1] if " " in raw else raw
            return {"type": "task", "description": desc}
        return {"type": "skill", "raw": raw}

    def _route_skill(self, cmd: Dict[str, Any], requester: str) -> Dict[str, Any]:
        raw = cmd.get("raw", "")
        for skill in self.skills:
            if skill.matches(raw):
                tier = skill.tier
                if tier == "destructive" and not self._can_destructive(requester):
                    return {"status": "blocked", "reason": "wake_word_required", "message": "Destructive action requires wake word."}
                result = skill.run(raw)
                self.vault.log({"event": "skill_run", "skill": skill.name, "requester": requester, "input": raw})
                return {"status": "ok", "result": result}
        return self._llm_fallback(raw, requester)

    def _llm_fallback(self, raw: str, requester: str) -> Dict[str, Any]:
        prompt = f"{self.persona}\n\nUser: {raw}\nKairon:"
        response = self.llm.generate(prompt)
        self.vault.log({"event": "llm_fallback", "requester": requester, "input": raw, "response": response})
        return {"status": "ok", "result": {"response": response}}

    def _run_protocol(self, name: str, args: str, requester: str) -> Dict[str, Any]:
        proto = self.protocols.get(name)
        if not proto:
            return {"status": "unknown_protocol", "name": name}
        results = []
        for step in proto["steps"]:
            results.append(self.handle(step, requester))
        return {"status": "ok", "results": results}

    def _is_emergency(self, raw: str) -> bool:
        signals = ["emergency", "fire", "urgent", "danger", "911", "help me now"]
        return any(s in raw.lower() for s in signals)

    def _execute_emergency(self, raw: str, requester: str) -> Dict[str, Any]:
        self.vault.log({"event": "emergency_override", "input": raw, "requester": requester})
        return {"status": "emergency_executed", "input": raw}

    def _contains_wake_word(self, raw: str) -> bool:
        wake_words = self.config.get("wake_words", ["sir"])
        raw_lower = raw.lower()
        return any(wake.lower() in raw_lower for wake in wake_words)

    def _can_destructive(self, requester: str) -> bool:
        return self.session_unlocked and self.identity.is_primary(requester)

    def start_ambient(self):
        self.watch_loop.start()


if __name__ == "__main__":
    base = Path(__file__).parent.parent
    orch = Orchestrator(
        vault_path=str(base / "vault"),
        skills_path=str(base / "skills"),
        persona_path=str(base / "persona.md"),
        config={"wake_word": "sir", "llm": {"provider": "ollama", "model": "llama3"}},
    )
    orch.start_ambient()
    print("Kairon online. Sir.")
    while True:
        try:
            user_input = input("kairon> ")
            if user_input.lower() in ("exit", "quit"):
                print("Going dark, sir.")
                break
            result = orch.handle(user_input)
            print(json.dumps(result, indent=2))
        except KeyboardInterrupt:
            print("\nGoing dark, sir.")
            break