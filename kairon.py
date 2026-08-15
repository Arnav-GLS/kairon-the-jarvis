#!/usr/bin/env python3
"""Kairon — Exact JARVIS Replica + Alexa capabilities. Entry point with voice, hardware, browser, screen."""
import sys
import os
import json
import threading
import logging
from pathlib import Path

# Add kairon to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import Orchestrator


def load_config():
    """Load config with explicit warnings for missing/malformed files."""
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"config.json is malformed: {e}. Fix or delete to use defaults.")
    else:
        print("⚠ config.json not found — using defaults. Copy config.example.json to config.json and fill in your keys.")
        return {
            "wake_phrases": ["what's up buddy", "daddy's home", "how's going on", "jarvis", "hey jarvis"],
            "llm": {"provider": "groq", "model": "llama3-70b-8192"},
            "watch_interval": 30,
            "session_timeout": 300,
            "whisper_model": "base",
            "tts_rate": 180,
            "home_assistant": {"enabled": False},
            "mqtt": {"enabled": False},
            "serial": {"enabled": False},
            "browser": {"enabled": True, "headless": False},
            "screen": {"enabled": True},
            "camera": {"enabled": False},
            "alexa_skills": {"enabled": True, "skills_dir": "alexa_skills"}
        }


def main():
    base = Path(__file__).parent
    config = load_config()
    
    orch = Orchestrator(
        vault_path=str(base / "vault"),
        skills_path=str(base / "skills"),
        persona_path=str(base / "persona.md"),
        config=config,
    )
    
    # Inject vault and LLM into skills
    for skill in orch.skills:
        if hasattr(skill, "set_vault"):
            skill.set_vault(orch.vault)
        if hasattr(skill, "set_llm"):
            skill.set_llm(orch.llm)
    
    # Initialize hardware manager
    hw_manager = None
    try:
        from skills.environment.bridge import create_hardware_manager
        hw_manager = create_hardware_manager(config)
        hw_results = hw_manager.connect_all()
        
        for skill in orch.skills:
            if hasattr(skill, "set_hardware_manager"):
                skill.set_hardware_manager(hw_manager)
        
        orch.vault.log({"event": "hardware_init", "results": hw_results})
        print("Hardware bridges:", hw_results)
    except Exception as e:
        hw_manager = None
        orch.vault.log({"event": "hardware_init_failed", "error": str(e)})
        print(f"Hardware init failed: {e}")
    
    # Initialize Alexa skill manager
    alexa_manager = None
    try:
        # Find alexa skill manager
        alexa_skill = next((s for s in orch.skills if s.name == "alexa_skill_manager"), None)
        if alexa_skill:
            alexa_skill.set_skills_dir(str(Path(__file__).parent / "alexa_skills"))
            alexa_manager = alexa_skill
            orch.vault.log({"event": "alexa_skill_manager_init", "status": "started"})
            print("Alexa Skill Manager initialized.")
    except Exception as e:
        orch.vault.log({"event": "alexa_skill_manager_init_failed", "error": str(e)})
        print(f"Alexa Skill Manager init failed: {e}")
    
    # Initialize routines skill
    routines_skill = None
    try:
        routines_skill = next((s for s in orch.skills if s.name == "routines"), None)
        if routines_skill:
            routines_skill.set_hardware_manager(hw_manager)
            routines_skill.set_routines_dir(str(Path(__file__).parent / "routines"))
            orch.vault.log({"event": "routines_init", "status": "started"})
            print("Routines engine initialized.")
    except Exception as e:
        orch.vault.log({"event": "routines_init_failed", "error": str(e)})
        print(f"Routines init failed: {e}")
    
    # Initialize browser skill
    browser_skill = None
    try:
        browser_skill = next((s for s in orch.skills if s.name == "browser"), None)
        if browser_skill:
            orch.vault.log({"event": "browser_init", "status": "started"})
            print("Browser automation initialized.")
    except Exception as e:
        orch.vault.log({"event": "browser_init_failed", "error": str(e)})
        print(f"Browser init failed: {e}")
    
    # Initialize screen skill
    screen_skill = None
    try:
        screen_skill = next((s for s in orch.skills if s.name == "screen"), None)
        if screen_skill:
            orch.vault.log({"event": "screen_init", "status": "started"})
            print("Screen awareness initialized.")
    except Exception as e:
        orch.vault.log({"event": "screen_init_failed", "error": str(e)})
        print(f"Screen init failed: {e}")
    
    # Initialize voice pipeline
    voice_pipeline = None
    try:
        from voice.pipeline import create_voice_pipeline
        voice_pipeline = create_voice_pipeline(orch, config)
        voice_pipeline.start()
        orch.vault.log({"event": "voice_init", "status": "started"})
        print("Voice pipeline initialized.")
    except Exception as e:
        orch.vault.log({"event": "voice_init_failed", "error": str(e)})
        print(f"Voice init failed: {e}")
    
    # Startup sequence
    print(orch.startup())
    
    # CLI loop (voice runs in background)
    print("\nKairon online. Sir.")
    print("Type 'exit' or 'quit' to stop. Voice runs in background.")
    print("Wake phrases: \"what's up buddy\", \"daddy's home\", \"how's going on\", \"jarvis\", \"hey jarvis\"")
    
    while True:
        try:
            user_input = input("kairon> ")
            if user_input.lower() in ("exit", "quit"):
                if hw_manager:
                    hw_manager.disconnect_all()
                if voice_pipeline:
                    voice_pipeline.stop()
                print(orch.shutdown())
                break
            
            # Also feed to voice pipeline for unified processing
            if voice_pipeline:
                voice_pipeline.text_command(user_input)
            
            result = orch.handle(user_input)
            print(json.dumps(result, indent=2))
        except KeyboardInterrupt:
            if hw_manager:
                hw_manager.disconnect_all()
            if voice_pipeline:
                voice_pipeline.stop()
            print("\n" + orch.shutdown())
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()