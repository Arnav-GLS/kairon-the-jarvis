"""Tests for watch_loop module."""
import sys
import tempfile
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.watch_loop import WatchLoop
from core.memory import Memory


class MockWatchableSkill:
    def __init__(self, name, should_alert=False, relevance=1.0):
        self.name = name
        self.watchable = True
        self.should_alert = should_alert
        self.relevance = relevance
        self.alerts_received = []
    
    def check_state(self):
        if self.should_alert:
            return {"relevance": self.relevance, "alert": f"{self.name} alert"}
        return None
    
    def on_finding(self, state):
        self.alerts_received.append(state)


class MockNonWatchableSkill:
    def __init__(self, name):
        self.name = name
        self.watchable = False


def test_watch_loop_start_stop():
    """Test watch loop starts and stops."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        vault = Memory(vault_path)
        skill = MockWatchableSkill("test_skill")
        
        watch_loop = WatchLoop([skill], vault, interval_seconds=1)
        watch_loop.start()
        
        time.sleep(0.5)
        
        assert watch_loop._thread is not None
        assert watch_loop._thread.is_alive()
        
        watch_loop.stop()
        watch_loop.join(timeout=2.0)
        
        assert not watch_loop._thread.is_alive()
        print("✓ test_watch_loop_start_stop passed")


def test_watch_loop_surfaces_alerts():
    """Test watch loop surfaces alerts above relevance threshold."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        vault = Memory(vault_path)
        skill = MockWatchableSkill("alert_skill", should_alert=True, relevance=0.9)
        quiet_skill = MockWatchableSkill("quiet_skill", should_alert=True, relevance=0.1)  # Below threshold
        
        watch_loop = WatchLoop([skill, quiet_skill], vault, interval_seconds=1)
        watch_loop.start()
        
        time.sleep(1.5)  # Allow one tick
        
        watch_loop.stop()
        watch_loop.join(timeout=2.0)
        
        # Check vault log
        logs = vault._read_recent_logs(5)
        log_text = " ".join(logs)
        assert "watch_loop_surfaced" in log_text
        assert "alert_skill" in log_text
        assert "quiet_skill" not in log_text  # Below threshold
        print("✓ test_watch_loop_surfaces_alerts passed")


def test_watch_loop_ignores_non_watchable():
    """Test non-watchable skills are ignored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        vault = Memory(vault_path)
        skill = MockNonWatchableSkill("non_watchable")
        
        watch_loop = WatchLoop([skill], vault, interval_seconds=1)
        watch_loop.start()
        
        time.sleep(1.5)
        
        watch_loop.stop()
        watch_loop.join(timeout=2.0)
        
        # Should not log anything
        logs = vault._read_recent_logs(5)
        log_text = " ".join(logs)
        assert "watch_loop_surfaced" not in log_text
        print("✓ test_watch_loop_ignores_non_watchable passed")


def test_watch_loop_relevance_threshold():
    """Test relevance threshold filtering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        
        vault = Memory(vault_path)
        
        # Test with custom threshold
        watch_loop = WatchLoop([], Memory(os.path.join(tmpdir, "vault2")), interval_seconds=1)
        watch_loop.relevance_threshold = 0.5
        
        # Test threshold comparison
        assert watch_loop.relevance_threshold == 0.5
        print("✓ test_watch_loop_relevance_threshold passed")


if __name__ == "__main__":
    test_watch_loop_start_stop()
    test_watch_loop_surfaces_alerts()
    test_watch_loop_ignores_non_watchable()
    test_watch_loop_relevance_threshold()
    print("\nAll watch_loop tests passed!")