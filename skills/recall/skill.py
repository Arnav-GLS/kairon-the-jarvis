"""Recall skill: memory query from vault."""
import json
from pathlib import Path
from typing import Dict, Any, List


class Skill:
    name = "recall"
    tier = "read"
    watchable = False
    triggers = ["recall", "remember", "what did", "search memory", "find in vault"]

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
        
        # Extract search term
        term = raw
        for trigger in self.triggers:
            term = term.replace(trigger, "").strip()
        term = term.strip()
        
        if not term:
            return {"ok": False, "error": "What would you like me to search for, sir?"}
        
        results = []
        
        # Search daily logs
        for f in (self.vault.vault_path / "daily").glob("*.md"):
            content = f.read_text(encoding="utf-8")
            if term.lower() in content.lower():
                lines = [l.strip() for l in content.split("\n") if term.lower() in l.lower()]
                results.append({"source": f"daily/{f.stem}", "matches": lines[:3]})
        
        # Search projects
        for f in (self.vault.vault_path / "projects").glob("*.md"):
            content = f.read_text(encoding="utf-8")
            if term.lower() in content.lower():
                lines = [l.strip() for l in content.split("\n") if term.lower() in l.lower()]
                results.append({"source": f"projects/{f.stem}", "matches": lines[:3]})
        
        # Search people
        for f in (self.vault.vault_path / "people").glob("*.md"):
            content = f.read_text(encoding="utf-8")
            if term.lower() in content.lower():
                lines = [l.strip() for l in content.split("\n") if term.lower() in l.lower()]
                results.append({"source": f"people/{f.stem}", "matches": lines[:3]})
        
        if not results:
            return {"ok": True, "message": f"No matches for '{term}' in the vault, sir."}
        
        lines = [f"Found {len(results)} matches for '{term}', sir:"]
        for r in results[:10]:
            lines.append(f"\n**{r['source']}:**")
            for m in r['matches']:
                lines.append(f"  - {m}")
        
        return {"ok": True, "message": "\n".join(lines)}

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)