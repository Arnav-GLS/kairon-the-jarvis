"""Memory: reads/writes the Obsidian vault — single source of truth."""
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class Memory:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_structure()

    def _ensure_structure(self):
        dirs = ["daily", "projects", "people", "tasks"]
        for d in dirs:
            (self.vault_path / d).mkdir(exist_ok=True)
        
        # Initialize daily log for today
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.vault_path / "daily" / f"{today}.md"
        if not daily_file.exists():
            daily_file.write_text(f"# {today}\n\n## Log\n\n")

    def orient(self) -> Dict[str, Any]:
        """Boot-time context load — what's outstanding, what's in the vault."""
        context = {
            "vault_path": str(self.vault_path),
            "today": datetime.now().strftime("%Y-%m-%d"),
            "outstanding_tasks": self._read_tasks(),
            "recent_logs": self._read_recent_logs(5),
            "projects": self._list_projects(),
        }
        self.log({"event": "orient", "context_keys": list(context.keys())})
        return context

    def log(self, entry: Dict[str, Any]):
        """Append structured log entry to today's daily file."""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.vault_path / "daily" / f"{today}.md"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"- [{timestamp}] {json.dumps(entry, ensure_ascii=False)}\n"
        
        with self._lock:
            with open(daily_file, "a", encoding="utf-8") as f:
                f.write(log_line)

    def write_note(self, category: str, filename: str, content: str):
        """Write a note to vault/category/filename.md"""
        category_path = self.vault_path / category
        category_path.mkdir(exist_ok=True)
        with self._lock:
            (category_path / f"{filename}.md").write_text(content, encoding="utf-8")

    def read_note(self, category: str, filename: str) -> Optional[str]:
        path = self.vault_path / category / f"{filename}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def append_note(self, category: str, filename: str, content: str):
        path = self.vault_path / category / f"{filename}.md"
        path.parent.mkdir(exist_ok=True)
        with self._lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n{content}")

    def _read_tasks(self) -> List[Dict]:
        tasks = []
        for f in (self.vault_path / "tasks").glob("*.json"):
            try:
                tasks.append(json.loads(f.read_text()))
            except:
                pass
        return tasks

    def _read_recent_logs(self, count: int) -> List[str]:
        logs = []
        daily_dir = self.vault_path / "daily"
        if daily_dir.exists():
            files = sorted(daily_dir.glob("*.md"), reverse=True)[:count]
            for f in files:
                logs.append(f.read_text())
        return logs

    def _list_projects(self) -> List[str]:
        return [f.stem for f in (self.vault_path / "projects").glob("*.md")]