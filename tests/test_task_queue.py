"""Tests for task_queue module."""
import sys
import tempfile
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.task_queue import TaskQueue
from core.memory import Memory


class MockSkill:
    def __init__(self, name, triggers, should_handle=True):
        self.name = name
        self.triggers = triggers
        self.should_handle = should_handle
    
    def matches(self, raw):
        return any(t in raw.lower() for t in self.triggers)
    
    def can_handle(self, desc):
        return self.should_handle and any(t in desc.lower() for t in self.triggers)
    
    def run(self, raw):
        return {"ok": True, "message": f"{self.name} executed"}


def test_task_handoff():
    """Test task handoff creates task and returns task_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        vault = Memory(vault_path)
        queue = TaskQueue(vault)
        
        skill = MockSkill("test_skill", ["test"])
        result = queue.handoff("test task", "primary", [skill])
        
        assert "task_id" in result
        assert result["status"] == "accepted"
        print("✓ test_task_handoff passed")


def test_task_execution():
    """Test task is executed and completed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        vault = Memory(vault_path)
        queue = TaskQueue(vault)
        
        skill = MockSkill("test_skill", ["test"])
        result = queue.handoff("test task", "primary", [skill])
        task_id = result["task_id"]
        
        # Wait for async execution
        time.sleep(0.5)
        
        task = queue.get(task_id)
        assert task is not None
        assert task["status"] == "done"
        assert task["result"]["ok"] == True
        print("✓ test_task_execution passed")


def test_task_blocked_no_skill():
    """Test task is blocked when no skill can handle it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        vault = Memory(vault_path)
        queue = TaskQueue(vault)
        
        # Skill that doesn't match
        skill = MockSkill("other_skill", ["other"])
        result = queue.handoff("test task", "primary", [skill])
        task_id = result["task_id"]
        
        time.sleep(0.5)
        
        task = queue.get(task_id)
        assert task["status"] == "blocked"
        assert task["blocked_reason"] == "no_skill_matched"
        print("✓ test_task_blocked_no_skill passed")


def test_task_list_outstanding():
    """Test listing outstanding tasks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        vault = Memory(vault_path)
        queue = TaskQueue(vault)
        
        # Skill that handles "task" in description
        skill = MockSkill("test_skill", ["task"])
        
        # Create multiple tasks
        queue.handoff("task 1", "primary", [skill])
        queue.handoff("task 2", "primary", [skill])
        time.sleep(0.5)
        
        outstanding = queue.list_outstanding()
        # Should be empty since tasks complete quickly
        assert len(outstanding) == 0
        
        # Test with blocking skill
        blocked_skill = MockSkill("blocked_skill", ["blocked"], should_handle=False)
        queue.handoff("blocked task", "primary", [blocked_skill])
        time.sleep(0.5)
        
        outstanding = queue.list_outstanding()
        assert len(outstanding) == 1
        assert outstanding[0]["status"] == "blocked"
        print("✓ test_task_list_outstanding passed")


if __name__ == "__main__":
    test_task_handoff()
    test_task_execution()
    test_task_blocked_no_skill()
    test_task_list_outstanding()
    print("\nAll task_queue tests passed!")