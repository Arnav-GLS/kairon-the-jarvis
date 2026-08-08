"""TTS: pyttsx3 wrapper (local). Stub interface for now."""
import threading
import queue
from typing import Optional


class TTS:
    def __init__(self, voice: str = None, rate: int = 180):
        self.voice_id = voice
        self.rate = rate
        self.engine = None
        self._queue = queue.Queue()
        self._worker = None

    def init(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.rate)
            if self.voice_id:
                voices = self.engine.getProperty('voices')
                for v in voices:
                    if self.voice_id.lower() in v.id.lower():
                        self.engine.setProperty('voice', v.id)
                        break
        except ImportError:
            pass

    def speak(self, text: str, blocking: bool = False):
        if not self.engine:
            self.init()
        if not self.engine:
            return
        
        if blocking:
            self.engine.say(text)
            self.engine.runAndWait()
        else:
            self._queue.put(text)
            if not self._worker or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run_worker, daemon=True)
                self._worker.start()

    def _run_worker(self):
        while not self._queue.empty():
            try:
                text = self._queue.get_nowait()
                self.engine.say(text)
                self.engine.runAndWait()
            except queue.Empty:
                break

    def stop(self):
        if self.engine:
            self.engine.stop()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break