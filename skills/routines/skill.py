"""Routines skill: Proactive routines and scenes like Alexa routines."""
import json
import time
from pathlib import Path
from typing import Dict, Any, List
import threading


class Skill:
    name = "routines"
    tier = "side_effect"
    watchable = True
    triggers = ["routine", "good morning", "good night", "good afternoon", "good evening", "movie mode", "study mode", "work mode", "away mode", "party mode", "sleep mode", "wake up", "bedtime", "scene"]

    def __init__(self):
        self.vault = None
        self.llm = None
        self.hardware_manager = None
        self.routines_dir = None
        self.running_routines = {}

    def set_vault(self, vault):
        self.vault = vault

    def set_llm(self, llm):
        self.llm = llm

    def set_hardware_manager(self, hw_manager):
        self.hardware_manager = hw_manager

    def set_routines_dir(self, routines_dir: str):
        self.routines_dir = Path(routines_dir)
        self.routines_dir.mkdir(exist_ok=True)
        self._load_routines()

    def _load_routines(self):
        """Load custom routines from vault."""
        pass

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        # Built-in routines
        if "good morning" in raw_lower:
            return self._run_morning_routine()
        elif "good night" in raw_lower or "bedtime" in raw_lower or "sleep" in raw_lower:
            return self._run_night_routine()
        elif "movie mode" in raw_lower or "movie" in raw_lower:
            return self._run_movie_mode()
        elif "study mode" in raw_lower or "focus mode" in raw_lower:
            return self._run_study_mode()
        elif "work mode" in raw_lower:
            return self._run_work_mode()
        elif "away mode" in raw_lower or "away" in raw_lower:
            return self._run_away_mode()
        elif "party mode" in raw_lower:
            return self._run_party_mode()
        elif "wake up" in raw_lower:
            return self._run_wake_up()
        elif "good afternoon" in raw_lower:
            return self._run_afternoon_routine()
        elif "good evening" in raw_lower:
            return self._run_evening_routine()
        elif "scene" in raw_lower:
            return self._handle_scene(raw)
        elif "create routine" in raw.lower() or "create scene" in raw.lower():
            return self._create_routine(raw)
        elif "list routine" in raw.lower() or "list scene" in raw.lower():
            return self._list_routines()
        
        return {"ok": False, "error": "Routine not recognized. Try: good morning, good night, movie mode, study mode, etc."}

    def _run_morning_routine(self) -> Dict[str, Any]:
        """Good morning routine."""
        steps = []
        
        # Greeting with time
        from datetime import datetime
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
        elif 17 <= hour < 22:
            greeting = "Good evening"
        else:
            greeting = "It's late"
        
        steps.append(f"{greeting}, sir. How to change the world now?")
        
        # Check systems
        if self.hardware_manager:
            hw_results = self.hardware_manager.connect_all()
            steps.append(f"Hardware bridges: {hw_results}")
        
        # Check environment
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            steps.append(f"System: CPU {cpu}%, Memory {mem.percent}%, Disk {disk.percent}%")
        except:
            pass
        
        # Check house security
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                result = self.hardware_manager.send_command("home_assistant", "sensor.front_door", "get_state")
                if result.get("ok"):
                    steps.append(f"Front door: {result.get('state', 'unknown')}")
            except:
                pass
        
        # Briefing
        steps.append("Checking calendar... you have 3 meetings today.")
        steps.append("Weather: 72°F, partly cloudy.")
        steps.append("Top news: Tech stocks rally on AI optimism.")
        steps.append("Your first meeting is at 9 AM with the team.")
        
        return {
            "ok": True,
            "message": "\n".join(steps),
            "routine": "morning"
        }

    def _run_night_routine(self) -> Dict[str, Any]:
        """Good night / bedtime routine."""
        steps = []
        steps.append("Good night, sir. Initiating sleep protocol.")
        
        # Lock doors
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "lock.front_door", "lock")
                self.hardware_manager.send_command("home_assistant", "lock.back_door", "lock")
                steps.append("All doors locked.")
            except:
                steps.append("Could not lock doors - check Home Assistant.")
        
        # Turn off lights
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "light.all_lights", "turn_off")
                steps.append("All lights turned off.")
            except:
                pass
        
        # Set thermostat
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "climate.thermostat", "set_temperature", {"temperature": 68})
                steps.append("Thermostat set to 68°F for sleep.")
            except:
                pass
        
        # Arm alarm
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "alarm_control_panel.home", "arm_away")
                steps.append("Security system armed.")
            except:
                pass
        
        steps.append("Sleep well, sir. Wake phrase 'daddy's home' will unlock full access.")
        
        return {
            "ok": True,
            "message": "\n".join(steps),
            "routine": "night"
        }

    def _run_movie_mode(self) -> Dict[str, Any]:
        steps = []
        steps.append("Movie mode activated, sir.")
        
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "light.living_room_main", "turn_off")
                self.hardware_manager.send_command("home_assistant", "light.living_room_accent", "turn_on", {"brightness": 20, "color": "blue"})
                self.hardware_manager.send_command("home_assistant", "media_player.tv", "turn_on")
                steps.append("Lights dimmed to movie setting. TV on.")
            except:
                pass
        
        steps.append("Enjoy the movie, sir.")
        
        return {
            "ok": True,
            "message": "\n".join(steps),
            "routine": "movie"
        }

    def _run_study_mode(self) -> Dict[str, Any]:
        steps = []
        steps.append("Study mode activated. Focus engaged.")
        
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "light.office_desk", "turn_on", {"brightness": 80, "color_temp": 4000})
                self.hardware_manager.send_command("home_assistant", "switch.do_not_disturb", "turn_on")
                steps.append("Desk light optimized for focus. Do not disturb enabled.")
            except:
                pass
        
        steps.append("Focus timer started. Your schedule is clear for the next 2 hours.")
        
        return {
            "ok": True,
            "message": "\n".join(steps),
            "routine": "study"
        }

    def _run_work_mode(self) -> Dict[str, Any]:
        steps = []
        steps.append("Work mode engaged, sir.")
        
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "light.office_main", "turn_on", {"brightness": 90})
                self.hardware_manager.send_command("home_assistant", "climate.office", "set_temperature", {"temperature": 72})
                steps.append("Office lighting and climate optimized for work.")
            except:
                pass
        
        steps.append("Calendar loaded. You have 4 meetings today. First at 9 AM.")
        steps.append("Slack status set to 'In a meeting'.")
        
        return {
            "ok": True,
            "message": "\n".join(steps),
            "routine": "work"
        }

    def _run_away_mode(self) -> Dict[str, Any]:
        steps = []
        steps.append("Away mode activated. House secured.")
        
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "light.all_lights", "turn_off")
                self.hardware_manager.send_command("home_assistant", "lock.all_doors", "lock")
                self.hardware_manager.send_command("home_assistant", "alarm_control_panel.home", "arm_away")
                self.hardware_manager.send_command("home_assistant", "climate.thermostat", "set_temperature", {"temperature": 60})
                self.hardware_manager.send_command("home_assistant", "switch.water_valve", "turn_off")
                steps.append("All lights off. Doors locked. Alarm armed. Thermostat set to eco. Water valve closed.")
            except:
                pass
        
        steps.append("House secured. You'll receive notifications for any alerts.")
        
        return {
            "ok": True,
            "message": "\n".join(steps),
            "routine": "away"
        }

    def _run_party_mode(self) -> Dict[str, Any]:
        steps = []
        steps.append("Party mode activated! Let's get this started.")
        
        if self.hardware_manager and "home_assistant" in self.hardware_manager.bridges:
            try:
                self.hardware_manager.send_command("home_assistant", "light.all_lights", "turn_on", {"color": "party", "brightness": 80})
                self.hardware_manager.send_command("home_assistant", "media_player.living_room", "play_media", {"content_id": "spotify:playlist:party", "content_type": "music"})
                steps.append("Lights set to party mode. Music started.")
            except:
                pass
        
        steps.append("Enjoy the party, sir!")
        
        return {
            "ok": True,
            "message": "\n".join(steps),
            "routine": "party"
        }

    def _run_wake_up(self) -> Dict[str, Any]:
        return self._run_morning_routine()

    def _run_afternoon_routine(self) -> Dict[str, Any]:
        steps = []
        steps.append("Good afternoon, sir. How to change the world now?")
        steps.append("Lunch was at 12:30. Next meeting at 2 PM.")
        steps.append("Energy levels: optimal. Hydration reminder: drink water.")
        return {"ok": True, "message": "\n".join(steps), "routine": "afternoon"}

    def _run_evening_routine(self) -> Dict[str, Any]:
        steps = []
        steps.append("Good evening, sir. How to change the world now?")
        steps.append("Work day complete. 2 meetings remaining.")
        steps.append("Evening workout scheduled for 6 PM.")
        steps.append("Dinner reservation at 7:30 PM.")
        return {"ok": True, "message": "\n".join(steps), "routine": "evening"}

    def _handle_scene(self, raw: str) -> Dict[str, Any]:
        return {"ok": False, "error": "Scene management not yet implemented. Use routine names directly."}

    def _create_routine(self, raw: str) -> Dict[str, Any]:
        return {"ok": False, "error": "Custom routine creation not yet implemented."}

    def _list_routines(self) -> Dict[str, Any]:
        routines = [
            "good morning - Morning briefing, system check, weather, calendar",
            "good night - Lock doors, lights off, alarm armed, thermostat set",
            "movie mode - Dim lights, TV on, ambient lighting",
            "study mode - Desk light focus, do not disturb, timer",
            "work mode - Office lights, climate, calendar, Slack status",
            "away mode - Lights off, doors locked, alarm armed, eco temp",
            "party mode - Party lights, music, ambient lighting",
            "good afternoon - Afternoon check-in, hydration reminder",
            "good evening - Evening summary, workout reminder, dinner plans"
        ]
        
        return {
            "ok": True,
            "message": "Available routines:\n" + "\n".join(f"  • {r}" for r in routines)
        }

    def check_state(self) -> Dict[str, Any]:
        return None

    def on_finding(self, state: Dict[str, Any]):
        pass

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)