"""TaskQueue: owns handed-off tasks end-to-end. Tracks state, follows up, reports unprompted."""
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional


class TaskQueue:
    def __init__(self, vault):
        self.vault = vault
        self.tasks: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread = None

    def handoff(self, description: str, requester: str, skills) -> Dict[str, Any]:
        task_id = f"task-{int(time.time() * 1000)}"
        task = {
            "id": task_id,
            "description": description,
            "requester": requester,
            "status": "in_progress",
            "created": datetime.utcnow().isoformat(),
            "updates": [],
            "result": None,
            "blocked_reason": None,
        }
        with self._lock:
            self.tasks[task_id] = task
        self.vault.log({"event": "task_handoff", "task_id": task_id, "description": description, "requester": requester})
        threading.Thread(target=self._execute, args=(task_id, skills), daemon=True).start()
        return {"status": "accepted", "task_id": task_id}

    def _execute(self, task_id: str, skills):
        task = self.tasks.get(task_id)
        if not task:
            return
        try:
            for skill in skills:
                if hasattr(skill, "can_handle") and skill.can_handle(task["description"]):
                    result = skill.run(task["description"])
                    task["result"] = result
                    task["status"] = "done" if result.get("ok") else "blocked"
                    if not result.get("ok"):
                        task["blocked_reason"] = result.get("error", "unknown")
                    break
            else:
                task["status"] = "blocked"
                task["blocked_reason"] = "no_skill_matched"
        except Exception as e:
            task["status"] = "failed"
            task["blocked_reason"] = str(e)
        finally:
            task["completed"] = datetime.utcnow().isoformat()
            self.vault.log({
                "event": "task_complete",
                "task_id": task_id,
                "status": task["status"],
                "result": task["result"],
            })

    def get(self, task_id: str) -> Optional[Dict]:
        return self.tasks.get(task_id)

    def list_outstanding(self) -> List[Dict]:
        return [t for t in self.tasks.values() if t["status"] in ("in_progress", "blocked")]

    def list_all(self) -> List[Dict]:
        return list(self.tasks.values())