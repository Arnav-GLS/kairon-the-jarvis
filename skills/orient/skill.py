"""Orient skill: boot-time context loading from vault."""
import json
from pathlib import Path
from typing import Dict, Any, List


class Skill:
    name = "orient"
    tier = "read"
    watchable = False
    triggers = ["orient", "status", "what's up", "brief me", "morning brief"]

    def __init__(self):
        self.vault = None

    def set_vault(self, vault):
        self.vault = vault

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        if not self.vault:
            return {"ok": False, "error": "vault not initialized"}
        
        context = self.vault.orient()
        
        # Format a brief response
        lines = ["Good morning, sir. Here's the current state:"]
        
        if context.get("outstanding_tasks"):
            lines.append(f"\n**Outstanding Tasks ({len(context['outstanding_tasks'])}):**")
            for task in context["outstanding_tasks"][:5]:
                lines.append(f"  - {task.get('description', 'Unknown')} ({task.get('status', 'unknown')})")
        else:
            lines.append("\nNo outstanding tasks, sir.")
        
        if context.get("projects"):
            lines.append(f"\n**Active Projects ({len(context['projects'])})):**")
            for proj in context["projects"][:5]:
                lines.append(f"  - {proj}")
        
        recent_logs = context.get("recent_logs", [])
        if recent_logs:
            lines.append(f"\n**Recent Activity ({len(recent_logs)} days):**")
            for log in recent_logs[:3]:
                lines.append(f"  - {log[:200]}...")
        
        return {"ok": True, "message": "\n".join(lines)}

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)