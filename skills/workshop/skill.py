"""Workshop skill: file, code, and project operations."""
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List


class Skill:
    name = "workshop"
    tier = "side_effect"
    watchable = False
    triggers = ["workshop", "open project", "create project", "run tests", "build", "git status", "code"]

    def __init__(self):
        self.vault = None

    def set_vault(self, vault):
        self.vault = vault

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        if parameters is None:
            parameters = {}
        raw_lower = raw.lower()
        
        if "git status" in raw_lower:
            return self._git_status()
        elif "run tests" in raw_lower:
            return self._run_tests()
        elif "build" in raw_lower:
            return self._build()
        elif "create project" in raw_lower or "new project" in raw_lower:
            return self._create_project(raw)
        elif "open project" in raw_lower:
            return self._open_project(raw)
        elif "code" in raw_lower:
            return self._open_editor(raw)
        
        return {"ok": True, "message": "Workshop ready, sir. What shall we build?"}

    def _git_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=os.getcwd())
            return {"ok": True, "message": result.stdout or result.stderr}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _run_tests(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["python", "-m", "pytest", "-v"], capture_output=True, text=True, cwd=os.getcwd())
            return {"ok": result.returncode == 0, "message": result.stdout or result.stderr}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _build(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["python", "-m", "build"], capture_output=True, text=True, cwd=os.getcwd())
            return {"ok": result.returncode == 0, "message": result.stdout or result.stderr}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _create_project(self, raw: str) -> Dict[str, Any]:
        # Extract project name
        name = raw.split("create project")[-1].strip() or raw.split("new project")[-1].strip()
        if not name:
            return {"ok": False, "error": "Project name required, sir."}
        
        proj_path = Path.cwd() / name
        proj_path.mkdir(exist_ok=True)
        (proj_path / "src").mkdir(exist_ok=True)
        (proj_path / "tests").mkdir(exist_ok=True)
        (proj_path / "README.md").write_text(f"# {name}\n\n")
        (proj_path / "requirements.txt").write_text("")
        
        if self.vault:
            self.vault.write_note("projects", name, f"# {name}\n\nCreated via workshop.")
        
        return {"ok": True, "message": f"Project '{name}' created at {proj_path}, sir."}

    def _open_project(self, raw: str) -> Dict[str, Any]:
        return {"ok": True, "message": "Use your editor to open the project, sir. I've noted the path."}

    def _open_editor(self, raw: str) -> Dict[str, Any]:
        return {"ok": True, "message": "Opening your editor... (configure EDITOR env var for automatic launch)"}

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)