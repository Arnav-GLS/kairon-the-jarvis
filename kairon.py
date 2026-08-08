#!/usr/bin/env python3
"""Kairon — JARVIS replica. Entry point."""
import sys
import os
from pathlib import Path

# Add kairon to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import Orchestrator


def load_config():
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        import json
        return json.loads(config_path.read_text())
    return {
        "wake_word": "sir",
        "llm": {"provider": "ollama", "model": "llama3"},
        "watch_interval": 30
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
    
    orch.start_ambient()
    
    print("Kairon online. Sir.")
    print("Type 'exit' or 'quit' to stop.")
    
    while True:
        try:
            user_input = input("kairon> ")
            if user_input.lower() in ("exit", "quit"):
                print("Going dark, sir.")
                break
            result = orch.handle(user_input)
            import json
            print(json.dumps(result, indent=2))
        except KeyboardInterrupt:
            print("\nGoing dark, sir.")
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()