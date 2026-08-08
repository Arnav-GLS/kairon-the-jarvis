"""Orchestrator: request loop — parse → route → tier check → act → log. JARVIS-grade."""
import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

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

    # JARVIS-style response templates
    ACKNOWLEDGMENTS = [
        "Right away, sir.",
        "Consider it done.",
        "On it, sir.",
        "Of course.",
        "Immediately."
    ]
    
    REFUSALS = [
        "I'm afraid I can't do that without authorization, sir.",
        "That requires your wake phrase, sir.",
        "Destructive actions need confirmation, sir.",
        "Not without the proper phrase, sir."
    ]
    
    EMERGENCY_RESPONSES = [
        "Emergency protocol engaged. Acting immediately.",
        "Overriding all safeties. Executing now.",
        "Danger detected. Taking action."
    ]

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
        self.startup_complete = False
        self.vault.orient()

    def _load_persona(self, path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    def startup(self) -> str:
        """JARVIS startup sequence."""
        self.startup_complete = True
        self.watch_loop.start()
        
        # Check systems
        env_skill = next((s for s in self.skills if s.name == "environment"), None)
        house_skill = next((s for s in self.skills if s.name == "house"), None)
        
        lines = ["Good evening, sir.", "Kairon systems coming online."]
        
        if env_skill:
            state = env_skill.check_state()
            if state and state.get("alerts"):
                lines.append(f"Note: {', '.join(state['alerts'])}")
            else:
                lines.append("All systems nominal.")
        
        if house_skill:
            status = house_skill.run("house security")
            if status.get("ok"):
                lines.append("House security: nominal.")
        
        lines.append("How may I assist you, sir?")
        return "\n".join(lines)

    def shutdown(self) -> str:
        """JARVIS shutdown sequence."""
        self.watch_loop.stop()
        lines = [
            "Shutting down, sir.",
            "Vault synchronized.",
            "Watch loop terminated.",
            "Good night, sir."
        ]
        return "\n".join(lines)

    def handle(self, raw_input: str, requester: str = "primary") -> Dict[str, Any]:
        if not raw_input or not raw_input.strip():
            return {"status": "empty", "message": "Sir?"}
        
        raw = raw_input.strip()
        
        # Emergency override
        if self._is_emergency(raw):
            return self._execute_emergency(raw, requester)
        
        # Wake phrase check
        if not self.session_unlocked and self._contains_wake_phrase(raw):
            self.session_unlocked = True
            return {
                "status": "unlocked", 
                "message": "Authorization confirmed. Destructive tier unlocked for this session, sir."
            }
        
        # Parse intent
        cmd = self._parse_natural(raw)
        
        if cmd["type"] == "protocol":
            return self._run_protocol(cmd["name"], cmd["args"], requester)
        if cmd["type"] == "task":
            return self.task_queue.handoff(cmd["description"], requester, self.skills)
        if cmd["type"] == "shutdown":
            return {"status": "shutdown", "message": self.shutdown()}
        if cmd["type"] == "status":
            return self._full_status()
        
        return self._route_skill(cmd, requester)

    def _parse_natural(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower().strip()
        
        # Protocol triggers
        protocol_match = re.match(r'^(?:run|execute|start)\s+(\w+)(?:\s+(.*))?$', raw_lower)
        if protocol_match:
            return {"type": "protocol", "name": protocol_match.group(1), "args": protocol_match.group(2) or ""}
        
        # Task handoff
        task_match = re.match(r'^(?:handle|do|take care of|deal with)\s+(.+)$', raw_lower)
        if task_match:
            return {"type": "task", "description": task_match.group(1).strip()}
        
        # Shutdown
        if any(w in raw_lower for w in ["shutdown", "power down", "go to sleep", "good night", "stand down"]):
            return {"type": "shutdown"}
        
        # Full status
        if any(w in raw_lower for w in ["full status", "complete status", "everything", "how are things"]):
            return {"type": "status"}
        
        # Direct skill routing
        return {"type": "skill", "raw": raw}

    def _route_skill(self, cmd: Dict[str, Any], requester: str) -> Dict[str, Any]:
        raw = cmd.get("raw", "")
        
        # Try exact skill matches first
        for skill in self.skills:
            if skill.matches(raw):
                tier = skill.tier
                if tier == "destructive" and not self._can_destructive(requester):
                    return {"status": "blocked", "reason": "wake_phrase_required", "message": self._refusal()}
                
                result = skill.run(raw)
                self.vault.log({"event": "skill_run", "skill": skill.name, "requester": requester, "input": raw})
                
                # Add acknowledgment for side-effect/destructive
                if tier in ("side_effect", "destructive") and result.get("ok"):
                    ack = self._acknowledgment()
                    if isinstance(result.get("message"), str):
                        result["message"] = f"{ack}\n{result['message']}"
                
                return {"status": "ok", "result": result}
        
        # Fallback to LLM with persona
        return self._llm_fallback(raw, requester)

    def _llm_fallback(self, raw: str, requester: str) -> Dict[str, Any]:
        prompt = f"{self.persona}\n\nUser: {raw}\nKairon:"
        response = self.llm.generate(prompt, max_tokens=500, temperature=0.2)
        self.vault.log({"event": "llm_fallback", "requester": requester, "input": raw, "response": response})
        return {"status": "ok", "result": {"response": response}}

    def _run_protocol(self, name: str, args: str, requester: str) -> Dict[str, Any]:
        proto = self.protocols.get(name)
        if not proto:
            return {"status": "unknown_protocol", "name": name, "message": f"Protocol '{name}' not found, sir. Available: {', '.join(self.protocols.list_protocols())}"}
        
        ack = self._acknowledgment()
        results = []
        for step in proto["steps"]:
            results.append(self.handle(step, requester))
        
        return {"status": "ok", "results": results, "message": f"{ack} Protocol '{name}' completed."}

    def _full_status(self) -> Dict[str, Any]:
        orient_result = self.handle("orient")
        env_result = self.handle("system status")
        house_result = self.handle("house security")
        tasks = self.task_queue.list_outstanding()
        
        lines = ["Full system status, sir:", "", orient_result.get("result", {}).get("message", ""), ""]
        lines.append(env_result.get("result", {}).get("message", ""))
        lines.append("")
        lines.append(house_result.get("result", {}).get("message", ""))
        
        if tasks:
            lines.append(f"\nOutstanding tasks: {len(tasks)}")
            for t in tasks[:5]:
                lines.append(f"  - {t['description']} ({t['status']})")
        else:
            lines.append("\nNo outstanding tasks.")
        
        return {"status": "ok", "result": {"message": "\n".join(lines)}}

    def _is_emergency(self, raw: str) -> bool:
        signals = ["emergency", "fire", "urgent", "danger", "911", "help me now", "code red", "mayday"]
        return any(s in raw.lower() for s in signals)

    def _execute_emergency(self, raw: str, requester: str) -> Dict[str, Any]:
        self.vault.log({"event": "emergency_override", "input": raw, "requester": requester})
        return {"status": "emergency_executed", "message": self._emergency_response(), "input": raw}

    def _contains_wake_phrase(self, raw: str) -> bool:
        wake_phrases = self.config.get("wake_phrases", ["what's up buddy", "daddy's home", "how's going on"])
        raw_lower = raw.lower()
        return any(wp.lower() in raw_lower for wp in wake_phrases)

    def _can_destructive(self, requester: str) -> bool:
        return self.session_unlocked and self.identity.is_primary(requester)

    def _acknowledgment(self) -> str:
        import random
        return random.choice(self.ACKNOWLEDGMENTS)

    def _refusal(self) -> str:
        import random
        return random.choice(self.REFUSALS)

    def _emergency_response(self) -> str:
        import random
        return random.choice(self.EMERGENCY_RESPONSES)


if __name__ == "__main__":
    base = Path(__file__).parent.parent
    orch = Orchestrator(
        vault_path=str(base / "vault"),
        skills_path=str(base / "skills"),
        persona_path=str(base / "persona.md"),
        config={"wake_phrases": ["what's up buddy", "daddy's home", "how's going on"], "llm": {"provider": "groq", "model": "llama3-70b-8192"}},
    )
    print(orch.startup())
    while True:
        try:
            user_input = input("kairon> ")
            if user_input.lower() in ("exit", "quit"):
                print(orch.shutdown())
                break
            result = orch.handle(user_input)
            import json
            print(json.dumps(result, indent=2))
        except KeyboardInterrupt:
            print("\n" + orch.shutdown())
            break