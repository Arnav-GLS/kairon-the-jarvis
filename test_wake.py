import sys
sys.path.insert(0, r'C:\Users\ASUS\kairon')
from core.orchestrator import Orchestrator

orch = Orchestrator(
    vault_path=r'C:\Users\ASUS\kairon\vault',
    skills_path=r'C:\Users\ASUS\kairon\skills',
    persona_path=r'C:\Users\ASUS\kairon\persona.md',
    config={'wake_words': ["what's up buddy", "daddy's home", "how's going on"], 'llm': {'provider': 'groq', 'model': 'llama3-70b-8192'}},
)

for skill in orch.skills:
    if hasattr(skill, 'set_vault'):
        skill.set_vault(orch.vault)
    if hasattr(skill, 'set_llm'):
        skill.set_llm(orch.llm)

orch.start_ambient()

# Test wake phrases
tests = [
    "what's up buddy",
    "daddy's home",
    "how's going on",
    'sir',
]

for t in tests:
    result = orch.handle(t)
    print(f'>> {t}')
    import json
    print(json.dumps(result, indent=2))
    print()