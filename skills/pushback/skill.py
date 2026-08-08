"""Pushback skill: risk analysis and honest pushback — the spine."""
from pathlib import Path
from typing import Dict, Any


class Skill:
    name = "pushback"
    tier = "read"
    watchable = False
    triggers = ["pushback", "risk", "bad idea", "analyze risk", "should i", "is this safe"]

    def __init__(self):
        self.vault = None
        self.llm = None

    def set_vault(self, vault):
        self.vault = vault

    def set_llm(self, llm):
        self.llm = llm

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        # Extract the decision/question
        query = raw
        for trigger in self.triggers:
            query = query.replace(trigger, "").strip()
        query = query.strip()
        
        if not query:
            return {"ok": False, "error": "What decision would you like me to analyze, sir?"}
        
        # Use LLM for risk analysis
        if self.llm:
            analysis = self._analyze_risk(query)
            return {"ok": True, "message": analysis}
        
        # Fallback: basic heuristic
        return self._basic_analysis(query)

    def _analyze_risk(self, query: str) -> str:
        prompt = f"""You are Kairon. Analyze this decision for risks. Be direct, economical, British butler tone.

Decision: {query}

Provide:
1. Risk level (Low/Medium/High/Critical)
2. One clear concern (if any)
3. Recommendation: proceed / modify / abort
4. One line of dry wit if appropriate

Format as a brief report."""
        return self.llm.generate(prompt, max_tokens=400)

    def _basic_analysis(self, query: str) -> Dict[str, Any]:
        # Simple keyword-based risk detection
        high_risk = ["delete", "drop", "remove", "destroy", "wipe", "format", "shutdown", "production", "prod"]
        medium_risk = ["change", "modify", "update", "migrate", "refactor", "restart"]
        
        q_lower = query.lower()
        
        if any(w in q_lower for w in high_risk):
            level = "High"
            concern = "Destructive action detected. Irreversible without backup."
            rec = "abort"
        elif any(w in q_lower for w in medium_risk):
            level = "Medium"
            concern = "Reversible but potentially disruptive. Test first."
            rec = "modify"
        else:
            level = "Low"
            concern = "No obvious risks detected."
            rec = "proceed"
        
        lines = [
            f"Risk Analysis, sir:",
            f"  Decision: {query}",
            f"  Level: {level}",
            f"  Concern: {concern}",
            f"  Recommendation: {rec}"
        ]
        
        if level in ("High", "Critical"):
            lines.append("  Sir, that's a bad call. Proceed at your own peril.")
        
        return {"ok": True, "message": "\n".join(lines)}

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)