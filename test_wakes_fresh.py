import sys
sys.path.insert(0, r'C:\Users\ASUS\kairon')
from core.orchestrator import Orchestrator

wake_phrases = ["what's up buddy", "daddy's home", "how's going on", "jarvis", "hey jarvis"]

for wp in ["what's up buddy", "daddy's home", "how's going on", "jarvis", "hey jarvis"]:
    orch = Orchestrator(
        vault_path=r'C:\Users\ASUS\kairon\vault',
        skills_path=r'C:\Users\ASUS\kairon\skills',
        persona_path=r'C:\Users\ASUS\kairon\persona.md',
        config={'wake_phrases': ["what's up buddy", "daddy's home", "how's going on", "jarvis", "hey jarvis"], 'llm': {'provider': 'groq', 'model': 'llama3-70b-8192'}},
    )

    for skill in orch.skills:
        if hasattr(skill, 'set_vault'):
            skill.set_vault(orch.vault)
        if hasattr(skill, 'set_llm'):
            skill.set_llm(orch.llm)

    r = orch.handle(wp)
    print(f'  {wp}: {r}')