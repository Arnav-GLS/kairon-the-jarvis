#!/usr/bin/env python3
"""Kairon — Exact JARVIS Replica. Entry point with voice & hardware."""
import sys
import os
import json
import threading
from pathlib import Path

# Add kairon to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import Orchestrator


def load_config():
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {
        "wake_phrases": ["what's up buddy", "daddy's home", "how's going on"],
        "llm": {"provider": "groq", "model": "llama3-70b-8192"},
        "watch_interval": 30,
        "whisper_model": "base",
        "tts_rate": 180,
        "home_assistant": {"enabled": False},
        "mqtt": {"enabled": False},
        "serial": {"enabled": False}
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
    try:
        from skills.environment.bridge import create_hardware_manager
        hw_manager = create_hardware_manager(config)
        hw_results = hw_manager.connect_all()
        
        for skill in orch.skills:
            if hasattr(skill, "set_hardware_manager"):
                skill.set_hardware_manager(hw_manager)
        
        print("Hardware bridges:", hw_results)
    except Exception as e:
        print(f"Hardware init: {e}")
        hw_manager = None
    
    # Initialize voice pipeline
    voice_pipeline = None
    try:
        from voice.pipeline import create_voice_pipeline
        voice_pipeline = create_voice_pipeline(orch, config)
        voice_pipeline.start()
        print("Voice pipeline initialized.")
    except Exception as e:
        print(f"Voice init: {e}")
    
    # Startup sequence
    print(orch.startup())
    
    # CLI loop (voice runs in background)
    print("\nKairon online. Sir.")
    print("Type 'exit' or 'quit' to stop. Voice runs in background.")
    print("Wake phrases: \"what's up buddy\", \"daddy's home\", \"how's going on\"")
    
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