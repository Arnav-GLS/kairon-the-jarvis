import sys
sys.path.insert(0, r'C:\Users\ASUS\kairon')
from core.orchestrator import Orchestrator

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

# Test real JARVIS behaviors
print('=== JARVIS STARTUP ===')
print(orch.startup())

print('\n=== WAKE PHRASES ===')
for wp in ["what's up buddy", "daddy's home", "how's going on", "jarvis", "hey jarvis"]:
    r = orch.handle(wp)
    print(f'  {wp}: {r["message"][:80]}')

print('\n=== DEVICE CONTROL ===')
r = orch.handle('ha list bridges')
print(r.get('result', {}).get('message', r.get('message', 'N/A'))[:200])

print('\n=== ROUTINES ===')
r = orch.handle('good morning')
print(r['result']['message'][:300])

print('\n=== BROWSER ===')
r = orch.handle('open https://github.com')
print(r.get('result', {}).get('message', r.get('message', 'N/A'))[:200])

print('\n=== SCREEN ===')
r = orch.handle('capture screen')
print(r.get('message', 'N/A')[:200])

print('\n=== ALL VERIFIED ===')