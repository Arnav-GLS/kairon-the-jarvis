"""Identity: authority gating. Wake phrases unlock destructive tier. Verifies who is asking. Multi-tenant ready."""
import json
from pathlib import Path
from typing import Dict, Set, List


class IdentityGate:
    WAKE_PHRASES = ["what's up buddy", "daddy's home", "how's going on"]
    
    def __init__(self, vault_path: str):
        self.primary = {"name": "sir", "device_id": None, "voiceprint": None}
        self.trusted: Set[str] = set()
        self.teams: Dict[str, List[str]] = {}  # team_name -> [members]
        self.config_path = str(Path(vault_path) / "identity.md")
        self._load()

    def is_primary(self, requester: str) -> bool:
        if requester == "primary":
            return True
        return requester == self.primary.get("name")

    def is_trusted(self, requester: str) -> bool:
        return requester in self.trusted

    def is_team_member(self, requester: str, team: str) -> bool:
        return requester in self.teams.get(team, [])

    def can(self, requester: str, action_tier: str, team: str = None) -> bool:
        if action_tier == "read":
            return True
        if action_tier == "side_effect":
            return self.is_trusted(requester) or self.is_primary(requester) or (team and self.is_team_member(requester, team))
        if action_tier == "destructive":
            return self.is_primary(requester)
        return False

    def add_trusted(self, name: str):
        self.trusted.add(name)
        self._save()

    def set_primary(self, name: str, device_id: str = None, voiceprint: str = None):
        self.primary = {"name": name, "device_id": device_id, "voiceprint": voiceprint}
        self._save()

    def add_team(self, team_name: str, members: List[str]):
        self.teams[team_name] = members
        self._save()

    def verify_wake_phrase(self, phrase: str) -> bool:
        phrase_lower = phrase.lower().strip()
        return any(wp.lower() in phrase_lower for wp in self.WAKE_PHRASES)

    def get_wake_phrases(self) -> List[str]:
        return self.WAKE_PHRASES.copy()

    def _load(self):
        p = Path(self.config_path)
        if p.exists():
            content = p.read_text()
            for line in content.split("\n"):
                if line.startswith("primary:"):
                    self.primary["name"] = line.split(":", 1)[1].strip()
                elif line.startswith("trusted:"):
                    self.trusted = set([x.strip() for x in line.split(":", 1)[1].split(",") if x.strip()])
                elif line.startswith("teams:"):
                    try:
                        self.teams = json.loads(line.split(":", 1)[1].strip())
                    except:
                        pass

    def _save(self):
        p = Path(self.config_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        content = f"""# Identity Configuration

primary: {self.primary['name']}
device_id: {self.primary['device_id'] or ''}
voiceprint: {self.primary['voiceprint'] or ''}
trusted: {', '.join(self.trusted)}
teams: {json.dumps(self.teams)}
"""
        p.write_text(content)