"""Voice Pipeline: Complete STT → LLM → TTS loop with wake word detection."""
import threading
import queue
import time
import os
from typing import Optional, Callable
from pathlib import Path

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


class VoicePipeline:
    """Complete voice interface: wake word → STT → LLM → TTS"""
    
    def __init__(self, orchestrator, config: dict):
        self.orchestrator = orchestrator
        self.config = config
        self.running = False
        self._thread = None
        self._audio_queue = queue.Queue()
        self._tts_queue = queue.Queue()
        
        # Wake words
        self.wake_phrases = config.get("wake_phrases", ["what's up buddy", "daddy's home", "how's going on"])
        
        # Components
        self.stt = None
        self.tts = None
        self.porcupine = None
        self.audio_stream = None
        
        # State
        self.listening = False
        self.session_unlocked = False
        
    def initialize(self) -> bool:
        """Initialize all voice components."""
        success = True
        
        # STT
        if WHISPER_AVAILABLE:
            try:
                model_size = self.config.get("whisper_model", "base")
                print(f"Loading Whisper {model_size}...")
                self.stt = whisper.load_model(model_size)
                print("Whisper loaded.")
            except Exception as e:
                print(f"Whisper init failed: {e}")
                success = False
        else:
            print("Whisper not installed. pip install openai-whisper")
            success = False
        
        # TTS
        if PYTTSX3_AVAILABLE:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty('rate', self.config.get("tts_rate", 180))
                voice_id = self.config.get("tts_voice")
                if voice_id:
                    voices = self.tts.getProperty('voices')
                    for v in voices:
                        if voice_id.lower() in v.id.lower():
                            self.tts.setProperty('voice', v.id)
                            break
                print("TTS initialized.")
            except Exception as e:
                print(f"TTS init failed: {e}")
                success = False
        else:
            print("pyttsx3 not installed.")
            success = False
        
        # Wake word (Porcupine)
        if PORCUPINE_AVAILABLE and PYAUDIO_AVAILABLE:
            try:
                access_key = os.getenv("PORCUPINE_ACCESS_KEY") or self.config.get("porcupine_access_key")
                if access_key:
                    # Custom wake words would need .ppn files
                    # For now, use built-in "hey google" as proxy
                    self.porcupine = pvporcupine.create(
                        access_key=access_key,
                        keywords=["hey google"]  # placeholder
                    )
                    print("Porcupine wake word loaded.")
                else:
                    print("Porcupine access key not set. Using text-based wake detection.")
            except Exception as e:
                print(f"Porcupine init failed: {e}")
        else:
            print("Porcupine/pyaudio not installed. Using text-based wake detection.")
        
        return success
    
    def start(self):
        """Start the voice pipeline."""
        if self.running:
            return
        
        if not self.initialize():
            print("Voice pipeline initialization incomplete. Falling back to text mode.")
        
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        # Start TTS worker
        self._tts_worker = threading.Thread(target=self._tts_loop, daemon=True)
        self._tts_worker.start()
        
        print("Voice pipeline started.")
    
    def stop(self):
        self.running = False
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.porcupine:
            self.porcupine.delete()
    
    def _run_loop(self):
        """Main voice loop: listen → wake → STT → LLM → TTS"""
        if not PYAUDIO_AVAILABLE:
            print("PyAudio not available. Voice loop cannot run.")
            return
        
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            
            self.audio_stream = pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=512
            )
            
            print("Listening for wake phrase...")
            
            while self.running:
                try:
                    # Read audio
                    audio_data = self.audio_stream.read(512, exception_on_overflow=False)
                    
                    # Porcupine wake word detection
                    if self.porcupine:
                        import struct
                        pcm = struct.unpack_from("h" * 512, audio_data)
                        keyword_index = self.porcupine.process(pcm)
                        if keyword_index >= 0:
                            self._on_wake_detected()
                            continue
                    
                    # Queue for STT (when session unlocked or wake detected)
                    if self.session_unlocked or self.listening:
                        self._audio_queue.put(audio_data)
                        
                except Exception as e:
                    print(f"Audio loop error: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"Voice loop failed: {e}")
    
    def _on_wake_detected(self):
        """Wake phrase detected."""
        print("Wake phrase detected!")
        self.session_unlocked = True
        self.listening = True
        self.speak("Yes, sir?")
    
    def process_audio_queue(self):
        """Process queued audio through STT."""
        if not self.stt:
            return
        
        audio_buffer = []
        silence_threshold = 0.5  # seconds
        last_audio_time = time.time()
        
        while self.running:
            try:
                audio_chunk = self._audio_queue.get(timeout=0.1)
                audio_buffer.append(audio_chunk)
                last_audio_time = time.time()
            except queue.Empty:
                pass
            
            # Check for silence (end of utterance)
            if audio_buffer and (time.time() - last_audio_time) > silence_threshold:
                self._process_utterance(audio_buffer)
                audio_buffer = []
    
    def _process_utterance(self, audio_chunks):
        """Convert audio chunks to text and process."""
        if not self.stt or not audio_chunks:
            return
        
        try:
            import numpy as np
            audio_data = b"".join(audio_chunks)
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe
            result = self.stt.transcribe(audio_np, fp16=False)
            text = result.get("text", "").strip()
            
            if text:
                print(f"Heard: {text}")
                self._process_command(text)
                
        except Exception as e:
            print(f"STT error: {e}")
    
    def _process_command(self, text: str):
        """Process recognized text through orchestrator."""
        # Check wake phrases in text (fallback)
        text_lower = text.lower()
        for phrase in self.wake_phrases:
            if phrase in text_lower:
                self.session_unlocked = True
                break
        
        # Send to orchestrator
        result = self.orchestrator.handle(text)
        
        # Speak response
        if result.get("result", {}).get("message"):
            self.speak(result["result"]["message"])
        elif result.get("result", {}).get("response"):
            self.speak(result["result"]["response"])
        elif result.get("message"):
            self.speak(result["message"])
    
    def speak(self, text: str):
        """Queue text for TTS."""
        if self.tts:
            self._tts_queue.put(text)
    
    def _tts_loop(self):
        """TTS worker thread."""
        while self.running:
            try:
                text = self._tts_queue.get(timeout=0.1)
                if text:
                    print(f"Speaking: {text[:50]}...")
                    self.tts.say(text)
                    self.tts.runAndWait()
            except queue.Empty:
                pass
            except Exception as e:
                print(f"TTS error: {e}")
    
    def text_command(self, text: str):
        """Process text command directly (for CLI integration)."""
        self._process_command(text)


def create_voice_pipeline(orchestrator, config: dict) -> VoicePipeline:
    """Factory function."""
    return VoicePipeline(orchestrator, config)