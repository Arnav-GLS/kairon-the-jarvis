"""Alexa Skill Manager: Install, manage, and run custom skills like Alexa."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List


class Skill:
    name = "alexa_skill_manager"
    tier = "side_effect"
    watchable = False
    triggers = ["install skill", "uninstall skill", "list skills", "enable skill", "disable skill", "skill store", "marketplace", "custom skill"]

    def __init__(self):
        self.vault = None
        self.llm = None
        self.skills_dir = None
        self.enabled_skills = set()
        self.loaded_skills = {}

    def set_vault(self, vault):
        self.vault = vault

    def set_llm(self, llm):
        self.llm = llm

    def set_skills_dir(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(exist_ok=True)
        self._load_enabled_skills()

    def _load_enabled_skills(self):
        enabled_file = self.skills_dir / "enabled_skills.json"
        if enabled_file.exists():
            import json
            with open(enabled_file, "r") as f:
                self.enabled_skills = set(json.load(f))

    def _save_enabled_skills(self):
        enabled_file = self.skills_dir / "enabled_skills.json"
        with open(enabled_file, "w") as f:
            json.dump(list(self.enabled_skills), f)

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        if "install" in raw_lower:
            return self._handle_install(raw)
        elif "uninstall" in raw_lower or "remove" in raw_lower:
            return self._handle_uninstall(raw)
        elif "list" in raw_lower:
            return self._handle_list()
        elif "enable" in raw_lower:
            return self._handle_enable(raw)
        elif "disable" in raw_lower:
            return self._handle_disable(raw)
        elif "store" in raw_lower or "marketplace" in raw_lower:
            return self._handle_store()
        
        return {"ok": False, "error": "Skill manager command not recognized"}

    def _handle_install(self, raw: str) -> Dict[str, Any]:
        import re
        # Extract skill name or path
        match = re.search(r'install skill\s+(.+)', raw, re.IGNORECASE)
        if not match:
            return {"ok": False, "error": "Specify skill to install. Example: 'install skill github.com/user/skill-name'"}
        
        source = match.group(1).strip()
        
        # Handle different source types
        if source.startswith("http") or source.startswith("git@") or source.endswith(".git"):
            return self._install_from_git(source)
        elif os.path.exists(source):
            return self._install_from_path(source)
        else:
            return {"ok": False, "error": f"Unknown source: {source}. Use git URL or local path."}

    def _install_from_git(self, repo_url: str) -> Dict[str, Any]:
        try:
            skill_name = repo_url.split("/")[-1].replace(".git", "")
            skill_path = self.skills_dir / skill_name
            
            if skill_path.exists():
                return {"ok": False, "error": f"Skill {skill_name} already exists"}
            
            # Clone repo
            result = subprocess.run(["git", "clone", repo_url, str(skill_path)], 
                                  capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return {"ok": False, "error": f"Git clone failed: {result.stderr}"}
            
            # Validate skill
            if not self._validate_skill(skill_path):
                shutil.rmtree(skill_path)
                return {"ok": False, "error": "Invalid skill structure"}
            
            # Enable by default
            self.enabled_skills.add(skill_name)
            self._save_enabled_skills()
            
            return {"ok": True, "message": f"Skill '{skill_name}' installed and enabled"}
        except Exception as e:
            return {"ok": False, "error": f"Install failed: {str(e)}"}

    def _install_from_path(self, source_path: str) -> Dict[str, Any]:
        try:
            source = Path(source_path)
            if not source.exists():
                return {"ok": False, "error": f"Path not found: {source_path}"}
            
            skill_name = source.name
            skill_path = self.skills_dir / skill_name
            
            if skill_path.exists():
                return {"ok": False, "error": f"Skill {skill_name} already exists"}
            
            # Copy skill
            shutil.copytree(source, skill_path)
            
            if not self._validate_skill(skill_path):
                shutil.rmtree(skill_path)
                return {"ok": False, "error": "Invalid skill structure"}
            
            self.enabled_skills.add(skill_name)
            self._save_enabled_skills()
            
            return {"ok": True, "message": f"Skill '{skill_name}' installed and enabled"}
        except Exception as e:
            return {"ok": False, "error": f"Install failed: {str(e)}"}

    def _validate_skill(self, skill_path: Path) -> bool:
        """Validate skill has required structure."""
        skill_md = skill_path / "SKILL.md"
        skill_py = skill_path / "skill.py"
        
        if not skill_md.exists():
            return False
        
        # Check for required fields in SKILL.md
        content = skill_md.read_text()
        required = ["name", "tier", "triggers"]
        for field in required:
            if f"### {field}" not in content:
                return False
        
        return True

    def _handle_uninstall(self, raw: str) -> Dict[str, Any]:
        import re
        match = re.search(r'(?:uninstall|remove) skill\s+(\S+)', raw, re.IGNORECASE)
        if not match:
            return {"ok": False, "error": "Specify skill to uninstall"}
        
        skill_name = match.group(1).strip()
        skill_path = self.skills_dir / skill_name
        
        if not skill_path.exists():
            return {"ok": False, "error": f"Skill '{skill_name}' not found"}
        
        # Disable first
        self.enabled_skills.discard(skill_name)
        self._save_enabled_skills()
        
        # Remove directory
        shutil.rmtree(self.skills_dir / skill_name)
        
        return {"ok": True, "message": f"Skill '{skill_name}' uninstalled"}

    def _handle_list(self, raw: str) -> Dict[str, Any]:
        skills = []
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_name = skill_dir.name
            enabled = skill_name in self.enabled_skills
            
            # Read manifest
            skill_md = skill_dir / "SKILL.md"
            manifest = {"name": skill_name, "enabled": enabled}
            
            if (skill_dir / "SKILL.md").exists():
                content = (skill_dir / "SKILL.md").read_text()
                for line in content.split("\n"):
                    if line.startswith("### "):
                        key = line[4:].strip().lower().replace(" ", "_")
                        # Get next line as value
                        pass
            
            skills.append(manifest)
        
        return {"ok": True, "message": f"Found {len(skills)} skills", "skills": skills}

    def _handle_enable(self, raw: str) -> Dict[str, Any]:
        import re
        match = re.search(r'enable skill\s+(\S+)', raw, re.IGNORECASE)
        if not match:
            return {"ok": False, "error": "Specify skill to enable"}
        
        skill_name = match.group(1).strip()
        skill_path = self.skills_dir / skill_name
        
        if not skill_path.exists():
            return {"ok": False, "error": f"Skill '{skill_name}' not found"}
        
        self.enabled_skills.add(skill_name)
        self._save_enabled_skills()
        
        return {"ok": True, "message": f"Skill '{skill_name}' enabled"}

    def _handle_disable(self, raw: str) -> Dict[str, Any]:
        import re
        match = re.search(r'disable skill\s+(\S+)', raw, re.IGNORECASE)
        if not match:
            return {"ok": False, "error": "Specify skill to disable"}
        
        skill_name = match.group(1).strip()
        
        if skill_name not in self.enabled_skills:
            return {"ok": False, "error": f"Skill '{skill_name}' not enabled"}
        
        self.enabled_skills.discard(skill_name)
        self._save_enabled_skills()
        
        return {"ok": True, "message": f"Skill '{skill_name}' disabled"}

    def _handle_store(self) -> Dict[str, Any]:
        """Show available skills in marketplace."""
        # Built-in marketplace skills
        marketplace = [
            {
                "name": "spotify_control",
                "description": "Control Spotify playback, playlists, search",
                "source": "github.com/kairon/skill-spotify"
            },
            {
                "name": "email_assistant",
                "description": "Read, send, organize emails",
                "source": "github.com/kairon/skill-email"
            },
            {
                "name": "calendar_manager",
                "description": "Manage calendar, schedule meetings",
                "source": "github.com/kairon/skill-calendar"
            },
            {
                "name": "smart_home_scenes",
                "description": "Advanced scene control for home automation",
                "source": "github.com/kairon/skill-scenes"
            },
            {
                "name": "crypto_tracker",
                "description": "Track crypto prices, portfolio, alerts",
                "source": "github.com/kairon/skill-crypto"
            },
            {
                "name": "news_briefing",
                "description": "Personalized news summaries",
                "source": "github.com/kairon/skill-news"
            }
        ]
        
        return {
            "ok": True,
            "message": f"Skill marketplace ({len(marketplace)} skills available)",
            "skills": marketplace
        }

    def get_enabled_skills(self) -> List[str]:
        return list(self.enabled_skills)

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        return self._handle_install(raw) if "install" in raw.lower() else {"ok": False, "error": "Command not recognized"}

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)