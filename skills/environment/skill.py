"""Environment skill: system control + hardware bridges (HA, MQTT, Serial)."""
import psutil
import platform
from pathlib import Path
from typing import Dict, Any, List


class Skill:
    name = "environment"
    tier = "side_effect"
    watchable = True
    triggers = ["environment", "system", "cpu", "memory", "disk", "process", "shutdown", "restart", "lights", "temperature", "ha ", "home assistant", "mqtt", "serial", "device", "bridge"]

    def __init__(self):
        self.vault = None
        self.hardware_manager = None

    def set_vault(self, vault):
        self.vault = vault

    def set_hardware_manager(self, hw_manager):
        self.hardware_manager = hw_manager

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        raw_lower = raw.lower()
        if parameters is None:
            parameters = {}
        
        # Hardware bridge commands
        if any(kw in raw_lower for kw in ["ha ", "home assistant", "mqtt", "serial", "bridge", "device"]):
            return self._handle_bridge_command(raw)
        
        # System commands
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
        elif "lights" in raw_lower or "light" in raw_lower:
            return self._lights_control(raw)
        elif "temperature" in raw_lower or "temp" in raw_lower:
            return self._temperature()
        
        return self._system_summary()

    def _handle_bridge_command(self, raw: str) -> Dict[str, Any]:
        if not self.hardware_manager:
            return {"ok": False, "error": "Hardware manager not initialized, sir."}
        
        raw_lower = raw.lower()
        
        # List bridges
        if "list" in raw_lower and "bridge" in raw_lower:
            bridges = list(self.hardware_manager.bridges.keys())
            return {"ok": True, "message": f"Available bridges: {', '.join(bridges) or 'none configured'}"}
        
        # Connect all
        if "connect" in raw_lower:
            results = self.hardware_manager.connect_all()
            return {"ok": True, "message": f"Bridge connections: {results}"}
        
        # List devices
        if "list" in raw_lower and "device" in raw_lower:
            all_devices = self.hardware_manager.list_all_devices()
            lines = ["Devices by bridge, sir:"]
            for bridge, devices in all_devices.items():
                lines.append(f"\n{bridge}:")
                for d in devices:
                    if isinstance(d, dict):
                        lines.append(f"  - {d.get('name', d.get('entity_id', 'unknown'))}")
                    else:
                        lines.append(f"  - {d}")
            return {"ok": True, "message": "\n".join(lines)}
        
        # Get all states
        if "state" in raw_lower or "status" in raw_lower:
            states = self.hardware_manager.get_all_states()
            lines = ["Device states, sir:"]
            for bridge, devices in states.items():
                lines.append(f"\n{bridge}:")
                for dev_id, state in devices.items():
                    if isinstance(state, dict) and "state" in state:
                        lines.append(f"  {dev_id}: {state['state']}")
                    else:
                        lines.append(f"  {dev_id}: {state}")
            return {"ok": True, "message": "\n".join(lines)}
        
        # Control device: "ha turn on light.living_room"
        parts = raw_lower.split()
        if len(parts) >= 3:
            bridge_name = parts[0]
            command = parts[1]
            device = parts[2]
            params = {}
            if len(parts) > 3:
                try:
                    import json
                    params = json.loads(" ".join(parts[3:]))
                except:
                    pass
            
            if bridge_name in self.hardware_manager.bridges:
                result = self.hardware_manager.send_command(bridge_name, device, command, params)
                return result
        
        return {"ok": False, "error": "Bridge command not recognized. Try: 'ha list devices', 'mqtt connect', 'ha turn on light.living_room'"}

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
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            # Try to control lights via HA
            raw_lower = raw.lower()
            if "on" in raw_lower:
                return self.hardware_manager.send_command("home_assistant", "light.all_lights", "turn_on")
            elif "off" in raw_lower:
                return self.hardware_manager.send_command("home_assistant", "light.all_lights", "turn_off")
        return {"ok": True, "message": "Home Assistant bridge not configured, sir. Configure in config.json"}

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
        """Watchable: check for high CPU/memory/disk + hardware states"""
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
        
        # Check hardware bridges for alerts
        if self.hardware_manager:
            for name, bridge in self.hardware_manager.bridges.items():
                if hasattr(bridge, "get_all_states"):
                    try:
                        states = bridge.get_all_states()
                        for dev_id, state in states.items():
                            if isinstance(state, dict):
                                s = state.get("state", "").lower()
                                if s in ("unavailable", "offline", "error", "fault"):
                                    alerts.append(f"{name} device {dev_id}: {s}")
                    except:
                        pass
        
        if alerts:
            return {"relevance": 0.9, "alerts": alerts}
        return None

    def on_finding(self, state: Dict[str, Any]):
        if self.vault:
            self.vault.log({"event": "environment_alert", "alerts": state.get("alerts", [])})

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)