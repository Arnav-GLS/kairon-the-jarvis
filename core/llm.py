"""LLMClient: pluggable model driver (Groq API, Ollama local, Claude API as fallback)."""
import json
import os
from typing import Dict, Any, Optional


class LLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "groq")
        self.model = config.get("model", "llama3-70b-8192")
        self.base_url = config.get("base_url", "https://api.groq.com/openai/v1")
        self.api_key = config.get("api_key") or os.getenv("GROQ_API_KEY")
        self.timeout = config.get("timeout", 30)

    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.3) -> str:
        if self.provider == "groq":
            return self._generate_groq(prompt, max_tokens, temperature)
        elif self.provider == "ollama":
            return self._generate_ollama(prompt, max_tokens, temperature)
        elif self.provider == "claude":
            return self._generate_claude(prompt, max_tokens, temperature)
        else:
            return f"[LLM not configured for provider: {self.provider}]"

    def _generate_groq(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not self.api_key:
            return "[Groq API key not configured. Set GROQ_API_KEY env var or config.]"
        try:
            import urllib.request
            url = f"{self.base_url}/chat/completions"
            data = json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }).encode()
            
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            })
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode())
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"[Groq error: {e}]"

    def _generate_ollama(self, prompt: str, max_tokens: int, temperature: float) -> str:
        try:
            import urllib.request
            url = f"{self.base_url}/api/generate"
            data = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": temperature}
            }).encode()
            
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode())
                return result.get("response", "").strip()
        except Exception as e:
            return f"[Ollama error: {e}]"

    def _generate_claude(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not self.api_key:
            return "[Claude API key not configured]"
        try:
            import urllib.request
            url = "https://api.anthropic.com/v1/messages"
            data = json.dumps({
                "model": self.model or "claude-3-5-sonnet-20241022",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }).encode()
            
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            })
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode())
                return result.get("content", [{}])[0].get("text", "").strip()
        except Exception as e:
            return f"[Claude error: {e}]"