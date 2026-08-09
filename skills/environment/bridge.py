"""Hardware Bridge: Home Assistant, MQTT, Serial, GPIO abstraction."""
import json
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from pathlib import Path

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class HardwareBridge(ABC):
    """Abstract hardware interface."""
    
    @abstractmethod
    def connect(self) -> bool:
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    @abstractmethod
    def send_command(self, device: str, command: str, params: dict = None) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_state(self, device: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def list_devices(self) -> list:
        pass


class HomeAssistantBridge(HardwareBridge):
    """Home Assistant REST API + WebSocket bridge."""
    
    def __init__(self, config: dict):
        self.config = config
        self.url = config.get("ha_url", "http://homeassistant.local:8123")
        self.token = config.get("ha_token") or ""
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        self.ws = None
        self.connected = False
        self.devices = {}
        self._state_cache = {}
    
    def connect(self) -> bool:
        if not REQUESTS_AVAILABLE:
            return False
        try:
            resp = requests.get(f"{self.url}/api/", headers=self.headers, timeout=5)
            if resp.status_code == 200:
                self.connected = True
                self._fetch_states()
                return True
        except Exception as e:
            print(f"HA connect failed: {e}")
        return False
    
    def disconnect(self):
        self.connected = False
    
    def _fetch_states(self):
        try:
            resp = requests.get(f"{self.url}/api/states", headers=self.headers, timeout=5)
            if resp.status_code == 200:
                for entity in resp.json():
                    self._state_cache[entity["entity_id"]] = entity
                    self.devices[entity["entity_id"]] = {
                        "name": entity.get("attributes", {}).get("friendly_name", entity["entity_id"]),
                        "domain": entity["entity_id"].split(".")[0],
                        "state": entity["state"]
                    }
        except Exception as e:
            print(f"HA state fetch failed: {e}")
    
    def send_command(self, device: str, command: str, params: dict = None) -> Dict[str, Any]:
        if not self.connected:
            return {"ok": False, "error": "Not connected to Home Assistant"}
        
        domain = device.split(".")[0]
        service_map = {
            "turn_on": "turn_on",
            "turn_off": "turn_off",
            "toggle": "toggle",
            "lock": "lock",
            "unlock": "unlock",
            "open": "open_cover",
            "close": "close_cover",
            "set_temperature": "set_temperature",
            "set_hvac_mode": "set_hvac_mode"
        }
        
        service = service_map.get(command, command)
        url = f"{self.url}/api/services/{domain}/{service}"
        
        data = {"entity_id": device}
        if params:
            data.update(params)
        
        try:
            resp = requests.post(url, headers=self.headers, json=data, timeout=10)
            if resp.status_code == 200:
                self._fetch_states()
                return {"ok": True, "message": f"{device} {command} executed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "Command failed"}
    
    def get_state(self, device: str) -> Dict[str, Any]:
        if device in self._state_cache:
            entity = self._state_cache[device]
            return {"ok": True, "state": entity["state"], "attributes": entity.get("attributes", {})}
        return {"ok": False, "error": "Device not found"}
    
    def list_devices(self) -> list:
        return list(self.devices.values())
    
    def get_all_states(self) -> Dict[str, Any]:
        self._fetch_states()
        return self._state_cache


class MQTTBridge(HardwareBridge):
    """MQTT device bridge for IoT sensors/actuators."""
    
    def __init__(self, config: dict):
        self.config = config
        self.host = config.get("mqtt_host", "localhost")
        self.port = config.get("mqtt_port", 1883)
        self.username = config.get("mqtt_username")
        self.password = config.get("mqtt_password")
        self.topic_prefix = config.get("topic_prefix", "kairon")
        self.client = None
        self.connected = False
        self.devices = {}
        self._message_handlers = {}
    
    def connect(self) -> bool:
        if not MQTT_AVAILABLE:
            return False
        try:
            self.client = mqtt.Client()
            if self.username:
                self.client.username_pw_set(self.username, self.password)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
            time.sleep(1)
            return self.connected
        except Exception as e:
            print(f"MQTT connect failed: {e}")
            return False
    
    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            client.subscribe(f"{self.topic_prefix}/+/state")
            print("MQTT connected")
        else:
            print(f"MQTT connect failed: {rc}")
    
    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        device_id = topic.split("/")[-2]
        if device_id in self.devices:
            self.devices[device_id]["state"] = payload
            if device_id in self._message_handlers:
                self._message_handlers[device_id](payload)
    
    def register_device(self, device_id: str, device_info: dict):
        self.devices[device_id] = device_info
        self.client.subscribe(f"{self.topic_prefix}/{device_id}/command")
    
    def send_command(self, device: str, command: str, params: dict = None) -> Dict[str, Any]:
        if not self.connected:
            return {"ok": False, "error": "MQTT not connected"}
        
        topic = f"{self.topic_prefix}/{device}/command"
        payload = json.dumps({"command": command, "params": params or {}})
        
        try:
            self.client.publish(topic, payload)
            return {"ok": True, "message": f"MQTT command sent to {device}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def get_state(self, device: str) -> Dict[str, Any]:
        if device in self.devices:
            return {"ok": True, "state": self.devices[device].get("state")}
        return {"ok": False, "error": "Device not found"}
    
    def list_devices(self) -> list:
        return list(self.devices.values())


class SerialBridge(HardwareBridge):
    """Serial/USB bridge for Arduino, ESP32, custom hardware."""
    
    def __init__(self, config: dict):
        self.config = config
        self.port = config.get("serial_port", "/dev/ttyUSB0")
        self.baudrate = config.get("baudrate", 115200)
        self.timeout = config.get("timeout", 1)
        self.ser = None
        self.connected = False
        self.devices = {}
        self._read_thread = None
        self._running = False
    
    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            return False
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Arduino reset
            self.connected = True
            self._running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            return True
        except Exception as e:
            print(f"Serial connect failed: {e}")
            return False
    
    def disconnect(self):
        self._running = False
        if self.ser:
            self.ser.close()
        self.connected = False
    
    def _read_loop(self):
        while self._running and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode().strip()
                if line:
                    self._parse_message(line)
            except Exception:
                pass
    
    def _parse_message(self, line: str):
        # Expected format: DEVICE_ID:STATE:VALUE
        parts = line.split(":")
        if len(parts) >= 3:
            device_id, state, value = parts[0], parts[1], ":".join(parts[2:])
            if device_id in self.devices:
                self.devices[device_id]["state"] = {state: value}
    
    def register_device(self, device_id: str, device_info: dict):
        self.devices[device_id] = device_info
    
    def send_command(self, device: str, command: str, params: dict = None) -> Dict[str, Any]:
        if not self.connected:
            return {"ok": False, "error": "Serial not connected"}
        
        try:
            cmd = f"{device}:{command}"
            if params:
                cmd += ":" + json.dumps(params)
            cmd += "\n"
            self.ser.write(cmd.encode())
            return {"ok": True, "message": f"Serial command sent to {device}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def get_state(self, device: str) -> Dict[str, Any]:
        if device in self.devices:
            return {"ok": True, "state": self.devices[device].get("state", {})}
        return {"ok": False, "error": "Device not found"}
    
    def list_devices(self) -> list:
        return list(self.devices.values())


class HardwareManager:
    """Manages all hardware bridges."""
    
    def __init__(self, config: dict):
        self.config = config
        self.bridges = {}
        self._load_bridges()
    
    def _load_bridges(self):
        # Home Assistant
        if self.config.get("home_assistant", {}).get("enabled"):
            self.bridges["home_assistant"] = HomeAssistantBridge(self.config["home_assistant"])
        
        # MQTT
        if self.config.get("mqtt", {}).get("enabled"):
            self.bridges["mqtt"] = MQTTBridge(self.config["mqtt"])
        
        # Serial
        if self.config.get("serial", {}).get("enabled"):
            self.bridges["serial"] = SerialBridge(self.config["serial"])
    
    def connect_all(self) -> Dict[str, bool]:
        results = {}
        for name, bridge in self.bridges.items():
            results[name] = bridge.connect()
        return results
    
    def disconnect_all(self):
        for bridge in self.bridges.values():
            bridge.disconnect()
    
    def get_bridge(self, name: str) -> Optional[HardwareBridge]:
        return self.bridges.get(name)
    
    def send_command(self, bridge_name: str, device: str, command: str, params: dict = None) -> Dict[str, Any]:
        bridge = self.bridges.get(bridge_name)
        if not bridge:
            return {"ok": False, "error": f"Bridge {bridge_name} not found"}
        return bridge.send_command(device, command, params)
    
    def get_state(self, bridge_name: str, device: str) -> Dict[str, Any]:
        bridge = self.bridges.get(bridge_name)
        if not bridge:
            return {"ok": False, "error": f"Bridge {bridge_name} not found"}
        return bridge.get_state(device)
    
    def list_all_devices(self) -> Dict[str, list]:
        return {name: bridge.list_devices() for name, bridge in self.bridges.items()}
    
    def get_all_states(self) -> Dict[str, Any]:
        states = {}
        for name, bridge in self.bridges.items():
            if hasattr(bridge, "get_all_states"):
                states[name] = bridge.get_all_states()
            else:
                states[name] = {d: bridge.get_state(d) for d in bridge.list_devices()}
        return states


def create_hardware_manager(config: dict) -> HardwareManager:
    return HardwareManager(config)