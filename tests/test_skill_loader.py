"""Tests for skill_loader module."""
import sys
import tempfile
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.skill_loader import SkillLoader


def test_load_valid_skill():
    """Test loading a valid skill with proper manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = os.path.join(tmpdir, "test_skill")
        os.makedirs(skill_dir)
        
        # Create valid SKILL.md
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("""## test_skill

### name
test_skill

### tier
read

### watchable
false

### triggers
["test", "hello"]

### description
A test skill
""")
        
        # Create skill.py
        with open(os.path.join(skill_dir, "skill.py"), "w") as f:
            f.write("""
class Skill:
    name = "test_skill"
    tier = "read"
    watchable = False
    triggers = ["test", "hello"]
    
    def matches(self, raw):
        return any(t in raw.lower() for t in self.triggers)
    
    def run(self, raw):
        return {"ok": True, "message": "test"}
    
    def can_handle(self, desc):
        return self.matches(desc)
""")
        
        loader = SkillLoader(tmpdir)
        skills = loader.load_all()
        
        assert len(skills) == 1
        assert skills[0].name == "test_skill"
        print("✓ test_load_valid_skill passed")


def test_skip_malformed_manifest():
    """Test that skills with malformed manifests are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = os.path.join(tmpdir, "bad_skill")
        os.makedirs(skill_dir)
        
        # Missing required fields
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("""## bad_skill

### description
A bad skill
""")
        
        loader = SkillLoader(tmpdir)
        skills = loader.load_all()
        
        assert len(skills) == 0
        print("✓ test_skip_malformed_manifest passed")


def test_skip_missing_skill_py():
    """Test fallback to dynamic skill when skill.py missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = os.path.join(tmpdir, "no_py_skill")
        os.makedirs(skill_dir)
        
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("""## no_py_skill

### name
no_py_skill

### tier
side_effect

### watchable
true

### triggers
["trigger1"]

### description
Skill without Python file
""")
        
        loader = SkillLoader(tmpdir)
        skills = loader.load_all()
        
        assert len(skills) == 1
        assert skills[0].name == "no_py_skill"
        print("✓ test_skip_missing_skill_py passed")


if __name__ == "__main__":
    test_load_valid_skill()
    test_skip_malformed_manifest()
    test_skip_missing_skill_py()
    print("\nAll skill_loader tests passed!")