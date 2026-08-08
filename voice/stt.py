"""STT: Whisper wrapper (local). Stub interface for now."""
import os
from typing import Optional


class STT:
    def __init__(self, model: str = "base"):
        self.model_name = model
        self.model = None

    def load(self):
        try:
            import whisper
            self.model = whisper.load_model(self.model_name)
        except ImportError:
            pass

    def transcribe(self, audio_path: str) -> Optional[str]:
        if not self.model:
            self.load()
        if not self.model:
            return None
        try:
            result = self.model.transcribe(audio_path)
            return result.get("text", "").strip()
        except Exception:
            return None

    def transcribe_bytes(self, audio_data: bytes) -> Optional[str]:
        if not self.model:
            self.load()
        if not self.model:
            return None
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name
            result = self.transcribe(temp_path)
            os.unlink(temp_path)
            return result
        except Exception:
            return None