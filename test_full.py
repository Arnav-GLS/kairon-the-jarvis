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

print('=== ORIENT ===')
r = orch.handle('orient')
print(r['result']['message'][:300])

print('=== SYSTEM ===')
r = orch.handle('system status')
print(r['result']['message'])

print('=== HOUSE ===')
r = orch.handle('house security')
print(r['result']['message'])

print('=== WAKE ===')
r = orch.handle("what's up buddy")
print(r['message'])

print('=== DESTRUCTIVE (after wake) ===')
r = orch.handle('shutdown system')
print(r)

print('=== PUSHBACK ===')
r = orch.handle('pushback should i delete prod db')
print(r['result']['message'][:200])

print('=== RECALL ===')
r = orch.handle('recall machine learning')
print(r['result']['message'][:200])

print('=== TASK QUEUE ===')
r = orch.handle('handle check disk space')
print('Task:', r['task_id'])

print('=== PROTOCOL ===')
r = orch.handle('run focus_mode')
print('Steps:', len(r['results']))

print('All systems go. Sir.')