"""SkillLoader: scans /skills, validates manifests, dynamic imports."""
import json
import importlib.util
from pathlib import Path
from typing import List, Dict, Any


class SkillLoader:
    def __init__(self, skills_path: str):
        self.skills_path = Path(skills_path)
        self.schema = self._load_schema()

    def load_all(self) -> List[Any]:
        skills = []
        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            skill = self._load_skill(skill_dir)
            if skill:
                skills.append(skill)
        return skills

    def _load_skill(self, skill_dir: Path) -> Any:
        manifest_path = skill_dir / "SKILL.md"
        if not manifest_path.exists():
            return None
        
        manifest = self._parse_manifest(manifest_path)
        if not self._validate(manifest):
            return None
        
        # Look for Python module
        py_file = skill_dir / "skill.py"
        if py_file.exists():
            return self._load_python_skill(py_file, manifest)
        
        # Fallback: create skill from manifest only
        return self._create_skill_from_manifest(manifest)

    def _load_python_skill(self, py_file: Path, manifest: Dict) -> Any:
        spec = importlib.util.spec_from_file_location(manifest["name"], py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Expect a Skill class
        if hasattr(module, "Skill"):
            skill_instance = module.Skill()
            skill_instance.name = manifest["name"]
            skill_instance.tier = manifest.get("tier", "read")
            skill_instance.watchable = manifest.get("watchable", False)
            skill_instance.triggers = manifest.get("triggers", [])
            return skill_instance
        
        return self._create_skill_from_manifest(manifest)

    def _create_skill_from_manifest(self, manifest: Dict) -> Any:
        class DynamicSkill:
            def __init__(self, m):
                self.name = m["name"]
                self.tier = m.get("tier", "read")
                self.watchable = m.get("watchable", False)
                self.triggers = m.get("triggers", [])
            
            def matches(self, raw: str) -> bool:
                raw_lower = raw.lower()
                return any(t.lower() in raw_lower for t in self.triggers)
            
            def run(self, raw: str) -> Dict[str, Any]:
                return {"ok": True, "message": f"Skill {self.name} executed: {raw}"}
            
            def can_handle(self, desc: str) -> bool:
                return self.matches(desc)
        
        return DynamicSkill(manifest)

    def _parse_manifest(self, path: Path) -> Dict:
        content = path.read_text()
        manifest = {}
        
        # Parse the SKILL.md format:
        # ## skill_name
        # ### field_name
        # value
        # ### field_name
        # value
        import re
        
        # Find all ### field_name sections
        pattern = r'###\s+(\w+)\n(.*?)(?=\n### |\n## |\Z)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for field_name, value in matches:
            field_name = field_name.strip().lower().replace(" ", "_")
            value = value.strip()
            
            # Parse triggers as JSON array if it looks like one
            if field_name == "triggers":
                try:
                    import ast
                    value = ast.literal_eval(value)
                except:
                    value = [v.strip() for v in value.split(",")]
            elif field_name == "watchable":
                value = value.lower() in ("true", "yes", "1")
            
            manifest[field_name] = value
        
        return manifest

    def _validate(self, manifest: Dict) -> bool:
        required = ["name", "tier"]
        return all(k in manifest for k in required)

    def _load_schema(self) -> Dict:
        schema_path = self.skills_path / "_manifest.schema.json"
        if schema_path.exists():
            return json.loads(schema_path.read_text())
        return {}