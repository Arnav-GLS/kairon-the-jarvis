"""Screen skill: Screen capture, OCR, and vision analysis."""
import base64
import io
import os
from pathlib import Path
from typing import Dict, Any, List
import tempfile


class Skill:
    name = "screen"
    tier = "side_effect"
    watchable = True
    triggers = ["screen", "capture", "screenshot", "what's on screen", "read screen", "analyze screen", "record screen"]

    def __init__(self):
        self.vault = None
        self.llm = None

    def set_vault(self, vault):
        self.vault = vault

    def set_llm(self, llm):
        self.llm = llm

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    def run(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        if "record" in raw_lower:
            return self._handle_record(raw)
        elif "analyze" in raw_lower or "what" in raw_lower or "read" in raw_lower:
            return self._handle_analyze(raw)
        elif "screenshot" in raw_lower or "capture" in raw_lower:
            return self._handle_screenshot(raw)
        
        return {"ok": False, "error": "Screen command not recognized. Try: capture screen, analyze screen, record screen"}

    def _handle_screenshot(self, raw: str) -> Dict[str, Any]:
        try:
            import pyautogui
            import time
            
            timestamp = int(time.time())
            filename = f"screen_{timestamp}.png"
            filepath = os.path.join(tempfile.gettempdir(), filename)
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            return {
                "ok": True,
                "message": f"Screenshot saved to {filepath}",
                "filepath": filepath
            }
        except ImportError:
            return {"ok": False, "error": "pyautogui not installed. Run: pip install pyautogui"}
        except Exception as e:
            return {"ok": False, "error": f"Screenshot failed: {str(e)}"}

    def _handle_analyze(self, raw: str) -> Dict[str, Any]:
        try:
            import pyautogui
            import base64
            import io
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            
            # Convert to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Analyze with vision model if available
            if self.llm:
                analysis = self._analyze_with_vision(img_base64)
                return {
                    "ok": True,
                    "message": analysis,
                    "screenshot_base64": img_base64
                }
            else:
                return {
                    "ok": True,
                    "message": "Screenshot captured. Vision analysis requires LLM with vision support.",
                    "screenshot_base64": img_base64
                }
        except Exception as e:
            return {"ok": False, "error": f"Screen analysis failed: {str(e)}"}

    def _analyze_with_vision(self, img_base64: str) -> str:
        if not self.llm:
            return "No LLM configured for vision analysis."
        
        prompt = f"""Analyze this screenshot. Describe what's on screen: applications, text content, UI elements, windows, and anything notable. Be concise but thorough."""
        
        return "Screen captured. Vision analysis requires LLM with vision capability (like GPT-4V or Gemini Pro Vision). The screenshot has been captured and encoded."

    def check_state(self) -> Dict[str, Any]:
        """Watchable: check for screen changes."""
        return None

    def on_finding(self, state: Dict[str, Any]):
        pass

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)