"""Environment skill: system control and smart home interface."""
import psutil
import platform
from pathlib import Path
from typing import Dict, Any, List


class Skill:
    name = "environment"
    tier = "side_effect"
    watchable = True
    triggers = ["environment", "system", "cpu", "memory", "disk", "process", "shutdown", "restart", "lights", "temperature"]

    def __init__(self):
        self.vault = None

    def set_vault(self, vault):
        self.vault = vault

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        if "cpu" in raw_lower or "processor" in raw_lower:
            return self._cpu_info()
        elif "memory" in raw_lower or "ram" in raw_lower:
            return self._memory_info()
        elif "disk" in raw_lower or "storage" in raw_lower:
            return self._disk_info()
        elif "process" in raw_lower:
            return self._process_info()
        elif "shutdown" in raw_lower:
            return self._shutdown()
        elif "restart" in raw_lower:
            return self._restart()
        elif "lights" in raw_lower:
            return self._lights_control(raw)
        elif "temperature" in raw_lower or "temp" in raw_lower:
            return self._temperature()
        
        return self._system_summary()

    def _system_summary(self) -> Dict[str, Any]:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        lines = [
            f"System status, sir:",
            f"  CPU: {cpu}%",
            f"  Memory: {mem.percent}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)",
            f"  Disk: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)",
            f"  Platform: {platform.system()} {platform.release()}"
        ]
        return {"ok": True, "message": "\n".join(lines)}

    def _cpu_info(self) -> Dict[str, Any]:
        return {"ok": True, "message": f"CPU: {psutil.cpu_percent(interval=1)}% across {psutil.cpu_count()} cores, sir."}

    def _memory_info(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        return {"ok": True, "message": f"Memory: {mem.percent}% used ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB), sir."}

    def _disk_info(self) -> Dict[str, Any]:
        disk = psutil.disk_usage("/")
        return {"ok": True, "message": f"Disk: {disk.percent}% used ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB), sir."}

    def _process_info(self) -> Dict[str, Any]:
        procs = sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), key=lambda p: p.info['cpu_percent'], reverse=True)[:5]
        lines = ["Top processes, sir:"]
        for p in procs:
            lines.append(f"  {p.info['pid']}: {p.info['name']} ({p.info['cpu_percent']}%)")
        return {"ok": True, "message": "\n".join(lines)}

    def _shutdown(self) -> Dict[str, Any]:
        return {"ok": False, "error": "Shutdown requires wake word confirmation, sir."}

    def _restart(self) -> Dict[str, Any]:
        return {"ok": False, "error": "Restart requires wake word confirmation, sir."}

    def _lights_control(self, raw: str) -> Dict[str, Any]:
        return {"ok": True, "message": "Smart home bridge not configured, sir. Connect Philips Hue / Home Assistant in skills/environment/bridge.py"}

    def _temperature(self) -> Dict[str, Any]:
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                lines = ["Temperature sensors, sir:"]
                for name, entries in temps.items():
                    for entry in entries:
                        lines.append(f"  {name}: {entry.current}°C")
                return {"ok": True, "message": "\n".join(lines)}
        except:
            pass
        return {"ok": True, "message": "Temperature sensors unavailable, sir."}

    def check_state(self) -> Dict[str, Any]:
        """Watchable: check for high CPU/memory/disk"""
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        alerts = []
        if cpu > 90:
            alerts.append(f"CPU critical: {cpu}%")
        if mem.percent > 90:
            alerts.append(f"Memory critical: {mem.percent}%")
        if disk.percent > 90:
            alerts.append(f"Disk critical: {disk.percent}%")
        
        if alerts:
            return {"relevance": 0.9, "alerts": alerts}
        return None

    def on_finding(self, state: Dict[str, Any]):
        if self.vault:
            self.vault.log({"event": "environment_alert", "alerts": state.get("alerts", [])})

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)