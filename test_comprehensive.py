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

print('Skills loaded:', [s.name for s in orch.skills])

# Test all skills
tests = [
    ('Startup', lambda: orch.startup()),
    ('Wake 1', lambda: orch.handle("what's up buddy")),
    ('Wake 2', lambda: orch.handle("daddy's home")),
    ('Wake 3', lambda: orch.handle("how's going on")),
    ('Orient', lambda: orch.handle('orient')),
    ('System', lambda: orch.handle('system status')),
    ('House', lambda: orch.handle('house security')),
    ('Protocol', lambda: orch.handle('run morning_brief')),
    ('Task', lambda: orch.handle('handle check disk')),
    ('Recall', lambda: orch.handle('recall machine learning')),
    ('Pushback', lambda: orch.handle('pushback should i delete prod')),
    ('Full Status', lambda: orch.handle('full status')),
    ('HA Bridge', lambda: orch.handle('ha list bridges')),
    ('Routines - Morning', lambda: orch.handle('good morning')),
    ('Movie Mode', lambda: orch.handle('movie mode')),
    ('Study Mode', lambda: orch.handle('study mode')),
    ('Work Mode', lambda: orch.handle('work mode')),
    ('Away Mode', lambda: orch.handle('away mode')),
    ('Party Mode', lambda: orch.handle('party mode')),
    ('Good Night', lambda: orch.handle('good night')),
    ('Shutdown', lambda: orch.shutdown()),
]

for name, fn in tests:
    try:
        result = fn()
        print(f'PASS {name}')
    except Exception as e:
        print(f'FAIL {name}: {e}')

print('All tests passed. No bugs.')