"""Wake word detector. Text-based for CLI, hooks for voice later."""
import threading
import time
from typing import Optional, Callable


class WakeWordDetector:
    def __init__(self, wake_word: str = "sir", on_wake: Callable = None):
        self.wake_word = wake_word.lower()
        self.on_wake = on_wake
        self.listening = False
        self._thread = None

    def start(self):
        if self.listening:
            return
        self.listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.listening = False

    def _listen_loop(self):
        """For CLI: just a placeholder. Voice implementation would go here."""
        # In voice mode, this would continuously listen to microphone
        # and trigger on_wake when wake word detected
        pass

    def check_text(self, text: str) -> bool:
        """Check if wake word is in text input."""
        return self.wake_word in text.lower()

    def check_audio(self, audio_data: bytes) -> bool:
        """Placeholder for audio wake word detection."""
        return False