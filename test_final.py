import sys
sys.path.insert(0, r'C:\Users\ASUS\kairon')
from core.orchestrator import Orchestrator

orch = Orchestrator(
    vault_path=r'C:\Users\ASUS\kairon\vault',
    skills_path=r'C:\Users\ASUS\kairon\skills',
    persona_path=r'C:\Users\ASUS\kairon\persona.md',
    config={'wake_phrases': ["what's up buddy", "daddy's home", "how's going on"], 'llm': {'provider': 'groq', 'model': 'llama3-70b-8192'}},
)

for skill in orch.skills:
    if hasattr(skill, 'set_vault'):
        skill.set_vault(orch.vault)
    if hasattr(skill, 'set_llm'):
        skill.set_llm(orch.llm)

print(orch.startup())
print()
r = orch.handle("what's up buddy")
print('Wake:', r['message'])
r = orch.handle('system status')
print('System:', r['result']['message'][:100])
r = orch.handle('ha list bridges')
print('HA:', r.get('result', {}).get('message', r.get('message', 'N/A')))
r = orch.handle('full status')
print('Full status:', r['result']['message'][:200])
print('All good.')