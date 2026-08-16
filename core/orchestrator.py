"""Orchestrator: request loop — parse → route → tier check → act → log. JARVIS-grade."""
import json
import sys
import re
import time
import threading
import difflib
from datetime import datetime
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
        self.session_unlock_time = 0
        self.session_timeout = config.get("session_timeout", 300)  # 5 minutes default
        self.startup_complete = False
        self._vault_lock = threading.Lock()
        self.vault.orient()

    def _load_persona(self, path: str) -> str:
        with open(path, "r") as f:
            return f.read()

    def startup(self) -> str:
        """JARVIS startup sequence with time-aware greeting."""
        self.startup_complete = True
        self.watch_loop.start()
        
        # Time-aware greeting
        from datetime import datetime
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
        elif 17 <= hour < 22:
            greeting = "Good evening"
        else:
            greeting = "It's late"
        
        # Check systems
        env_skill = next((s for s in self.skills if s.name == "environment"), None)
        house_skill = next((s for s in self.skills if s.name == "house"), None)
        
        lines = [f"{greeting}, sir. How to change the world now?"]
        
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
        
        return "\n".join(lines)

    def shutdown(self) -> str:
        """JARVIS shutdown sequence."""
        self.watch_loop.stop()
        # Wait for watch loop thread to finish (max 2 seconds)
        if self.watch_loop._thread and self.watch_loop._thread.is_alive():
            self.watch_loop._thread.join(timeout=2.0)
        
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
        if self.session_unlocked and (time.time() - self.session_unlock_time) > self.session_timeout:
            self.session_unlocked = False
            self.session_unlock_time = 0
        
        if not self.session_unlocked and self._contains_wake_phrase(raw):
            self.session_unlocked = True
            self.session_unlock_time = time.time()
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
        
        # Use LLM to classify intent and route to appropriate skill
        intent = self._classify_intent(raw)
        
        if intent.get("action") == "skill":
            skill_name = intent.get("skill")
            skill = next((s for s in self.skills if s.name == skill_name), None)
            
            if skill:
                tier = skill.tier
                if tier == "destructive" and not self._can_destructive(requester):
                    return {"status": "blocked", "reason": "wake_phrase_required", "message": self._refusal()}
                
                # Pass extracted parameters to skill
                result = skill.run(raw, intent.get("parameters", {}))
                self.vault.log({"event": "skill_run", "skill": skill.name, "requester": requester, "input": raw, "intent": intent})
                
                if tier in ("side_effect", "destructive") and result.get("ok"):
                    ack = self._acknowledgment()
                    if isinstance(result.get("message"), str):
                        result["message"] = f"{self._acknowledgment()}\n{result['message']}"
                
                return {"status": "ok", "result": result, "intent": intent}
        
        # Fallback to LLM with persona for conversation
        return self._llm_fallback(raw, requester)

    def _llm_fallback(self, raw: str, requester: str) -> Dict[str, Any]:
        prompt = f"{self.persona}\n\nUser: {raw}\nKairon:"
        response = self.llm.generate(prompt, max_tokens=500, temperature=0.2)
        self.vault.log({"event": "llm_fallback", "requester": requester, "input": raw, "response": response})
        return {"status": "ok", "result": {"response": response}}

    def _classify_intent(self, raw: str) -> Dict[str, Any]:
        """Use LLM to classify user intent and extract parameters."""
        # Build skill descriptions for the LLM
        skill_descriptions = []
        for skill in self.skills:
            triggers_str = ", ".join(skill.triggers[:5])
            skill_descriptions.append(
                f"- {skill.name} (tier: {skill.tier}, watchable: {skill.watchable}): "
                f"Triggers: {triggers_str}. Description: {getattr(skill, 'description', 'No description')}"
            )
        
        skills_text = "\n".join(skill_descriptions)
        
        prompt = f"""You are Kairon's intent classifier. Analyze the user's request and determine which skill should handle it.

Available skills:
{skills_text}

User request: "{raw}"

Respond with JSON only:
{{
  "action": "skill|conversation|protocol|task",
  "skill": "skill_name_or_null",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "parameters": {{"key": "value"}}
}}

Rules:
- If user wants to control devices, use "environment" or "house"
- If user wants to search web, use "research"
- If user wants to control browser, use "browser"
- If user wants screen analysis, use "screen"
- If user wants to run a routine, use "routines"
- If user wants to control hardware bridges, use "environment"
- If user wants to install/manage skills, use "alexa_skill_manager"
- If user wants to manage tasks, use "task"
- If user wants to run a protocol, use "protocol"
- If user wants to search memory, use "recall"
- If user wants to run code/workshop, use "workshop"
- If it's just conversation, use "conversation" with skill=null
- Extract relevant parameters from the request

Respond with ONLY the JSON."""
        
        try:
            response = self.llm.generate(prompt, max_tokens=500, temperature=0.1)
            # Parse JSON response
            import json
            response_text = response.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            intent = json.loads(response_text)
            if "action" not in intent:
                intent["action"] = "conversation"
            if "skill" not in intent:
                intent["skill"] = None
            if "parameters" not in intent:
                intent["parameters"] = {}
            return intent
        except Exception as e:
            self.vault.log({"event": "intent_classification_failed", "error": str(e), "raw": raw})
            return self._fallback_classify(raw)
    
    def _fallback_classify(self, raw: str) -> Dict[str, Any]:
        """Fallback keyword-based classification if LLM fails."""
        raw_lower = raw.lower()
        
        skill_keywords = {
            "environment": ["system", "cpu", "memory", "disk", "process", "temperature", "ha ", "home assistant", "mqtt", "serial", "bridge", "device", "bridge", "lights", "fan", "ac"],
            "house": ["house", "home", "security", "alarm", "lock", "unlock", "door", "window", "camera", "guest"],
            "browser": ["browser", "open", "navigate", "search", "click", "scroll", "screenshot", "tab", "go to", "visit"],
            "screen": ["screen", "capture", "screenshot", "what's on screen", "read screen", "analyze screen"],
            "routines": ["routine", "good morning", "good night", "movie mode", "study mode", "work mode", "away mode", "party mode"],
            "research": ["research", "search", "look up", "find", "web search", "summarize"],
            "recall": ["recall", "remember", "what did", "search memory", "find in vault"],
            "pushback": ["pushback", "risk", "bad idea", "analyze risk", "should i", "is this safe"],
            "house": ["house", "home", "security", "alarm", "lock", "unlock", "door", "window", "camera"],
            "workshop": ["workshop", "git", "build", "test", "code", "project"],
            "recall": ["recall", "remember", "search memory"],
            "alexa_skill_manager": ["install skill", "uninstall skill", "list skills", "enable skill", "disable skill"],
            "routines": ["routine", "good morning", "good night", "movie mode", "study mode", "work mode", "away mode", "party mode"],
        }
        
        for skill_name, keywords in skill_keywords.items():
            if any(kw in raw.lower() for kw in keywords):
                return {
                    "action": "skill",
                    "skill": skill_name,
                    "confidence": 0.6,
                    "reasoning": f"Keyword match for {skill_name}",
                    "parameters": {}
                }
        
        return {
            "action": "conversation",
            "skill": None,
            "confidence": 0.5,
            "reasoning": "No skill match, falling back to conversation",
            "parameters": {}
        }

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
        
        # Exact match first (fast path)
        for wp in wake_phrases:
            if wp.lower() in raw_lower:
                return True
        
        # Fuzzy match for STT tolerance (edit distance / similarity)
        for wp in wake_phrases:
            ratio = difflib.SequenceMatcher(None, wp.lower(), raw_lower).ratio()
            if ratio >= 0.75:  # 75% similarity threshold
                return True
        
        return False

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