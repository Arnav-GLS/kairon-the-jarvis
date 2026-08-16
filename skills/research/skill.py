"""Research skill: web search and synthesis."""
import urllib.request
import urllib.parse
import json
from pathlib import Path
from typing import Dict, Any, List


class Skill:
    name = "research"
    tier = "read"
    watchable = False
    triggers = ["research", "search", "look up", "find", "web search", "summarize"]

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

    def run(self, raw: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        if parameters is None:
            parameters = {}
        raw_lower = raw.lower()
        
        # Extract query
        query = raw
        for trigger in self.triggers:
            query = query.replace(trigger, "").strip()
        query = query.strip()
        
        if not query:
            return {"ok": False, "error": "Research topic required, sir."}
        
        # Try DuckDuckGo HTML scrape
        results = self._search_duckduckgo(query)
        
        if not results:
            return {"ok": False, "error": "Search returned no results, sir."}
        
        # Synthesize with LLM if available
        if self.llm:
            summary = self._synthesize(query, results)
            return {"ok": True, "message": summary, "sources": [r["url"] for r in results[:5]]}
        
        # Fallback: just list results
        lines = [f"Search results for '{query}', sir:"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"  {i}. {r['title']} - {r['url']}")
        
        return {"ok": True, "message": "\n".join(lines), "sources": [r["url"] for r in results[:5]]}

    def _search_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8")
            
            results = []
            # Simple HTML parsing for result links
            import re
            for match in re.finditer(r'class="result__url">([^<]+)</a>.*?class="result__snippet">([^<]+)</a>', html, re.DOTALL):
                url_part = match.group(1).strip()
                snippet = match.group(2).strip()
                if url_part.startswith("//"):
                    url_part = "https:" + url_part
                results.append({"title": snippet[:100], "url": url_part, "snippet": snippet})
            
            return results[:10]
        except Exception as e:
            return []

    def _synthesize(self, query: str, results: List[Dict]) -> str:
        if not self.llm:
            return ""
        
        context = "\n".join([f"{r['title']}: {r['snippet']}" for r in results[:5]])
        prompt = f"Summarize the following search results for '{query}' in 3-4 sentences:\n\n{context}"
        return self.llm.generate(prompt, max_tokens=300)

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)