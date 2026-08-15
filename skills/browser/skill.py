"""Browser skill: Full browser automation with Playwright."""
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


class Skill:
    name = "browser"
    tier = "side_effect"
    watchable = False
    triggers = ["browser", "open", "navigate", "search", "click", "scroll", "screenshot", "tab", "close tab", "new tab", "go to", "visit"]

    def __init__(self):
        self.vault = None
        self.llm = None
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    def set_vault(self, vault):
        self.vault = vault

    def set_llm(self, llm):
        self.llm = llm

    def matches(self, raw: str) -> bool:
        raw_lower = raw.lower()
        return any(t.lower() in raw_lower for t in self.triggers)

    async def _ensure_browser(self):
        """Initialize browser if not already running."""
        if self.browser is not None and self.page is not None:
            return
        
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
        except ImportError:
            return {"ok": False, "error": "Playwright not installed. Run: pip install playwright && playwright install"}

    async def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def run(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        # Navigate / Open
        if any(kw in raw_lower for kw in ["open", "navigate", "go to", "visit"]):
            return self._handle_navigate(raw)
        
        # Search
        if "search" in raw_lower:
            return self._handle_search(raw)
        
        # Click
        if "click" in raw_lower:
            return self._handle_click(raw)
        
        # Scroll
        if "scroll" in raw_lower:
            return self._handle_scroll(raw)
        
        # Screenshot
        if "screenshot" in raw_lower or "capture" in raw_lower:
            return self._handle_screenshot(raw)
        
        # Tab management
        if "tab" in raw_lower:
            return self._handle_tab(raw)
        
        # Get content
        if any(kw in raw_lower for kw in ["read", "extract", "get content", "what's on"]):
            return self._handle_content(raw)
        
        return {"ok": False, "error": "Browser command not recognized. Try: open [url], search [query], click [element], scroll, screenshot, tab management"}

    def _handle_navigate(self, raw: str) -> Dict[str, Any]:
        # Extract URL
        import re
        url_match = re.search(r'(https?://\S+|www\.\S+)', raw)
        if not url_match:
            return {"ok": False, "error": "No URL found. Try: 'open https://example.com'"}
        
        url = url_match.group(1)
        if not url.startswith("http"):
            url = "https://" + url
        
        async def _navigate():
            await self._ensure_browser()
            await self.page.goto(url, wait_until="networkidle")
            return {"ok": True, "message": f"Navigated to {url}", "url": self.page.url}
        
        return self._run_async(_navigate())

    def _handle_search(self, raw: str) -> Dict[str, Any]:
        # Extract search query
        import re
        query_match = re.search(r'search\s+(?:for\s+)?(.+)', raw.lower())
        if not query_match:
            return {"ok": False, "error": "No search query found. Try: 'search for python tutorials'"}
        
        query = query_match.group(1).strip()
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        
        async def _search():
            await self._ensure_browser()
            await self.page.goto(search_url, wait_until="networkidle")
            return {"ok": True, "message": f"Searched for: {query}", "url": self.page.url}
        
        return self._run_async(_search())

    def _handle_click(self, raw: str) -> Dict[str, Any]:
        import re
        # Try to extract selector
        selector_match = re.search(r'click\s+(?:on\s+)?(.+)', raw.lower())
        if not selector_match:
            return {"ok": False, "error": "What should I click? Try: 'click button' or 'click .submit-button'"}
        
        selector = selector_match.group(1).strip()
        
        async def _click():
            await self._ensure_browser()
            await self.page.click(selector)
            return {"ok": True, "message": f"Clicked: {selector}"}
        
        return self._run_async(_click())

    def _handle_scroll(self, raw: str) -> Dict[str, Any]:
        import re
        direction = "down"
        if "up" in raw.lower():
            direction = "up"
        elif "top" in raw.lower():
            direction = "top"
        elif "bottom" in raw.lower():
            direction = "bottom"
        
        async def _scroll():
            await self._ensure_browser()
            if direction == "top":
                await self.page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            else:
                await self.page.evaluate(f"window.scrollBy(0, {'-500' if direction == 'up' else '500'})")
            return {"ok": True, "message": f"Scrolled {direction}"}
        
        return self._run_async(_scroll())

    def _handle_screenshot(self, raw: str) -> Dict[str, Any]:
        import re
        filename = "screenshot.png"
        match = re.search(r'(?:save\s+as\s+|as\s+)(\S+)', raw.lower())
        if match:
            filename = match.group(1)
            if not filename.endswith('.png'):
                filename += '.png'
        
        async def _screenshot():
            await self._ensure_browser()
            await self.page.screenshot(path=filename, full_page=True)
            return {"ok": True, "message": f"Screenshot saved to {filename}"}
        
        return self._run_async(_screenshot())

    def _handle_tab(self, raw: str) -> Dict[str, Any]:
        raw_lower = raw.lower()
        
        async def _tab():
            await self._ensure_browser()
            
            if "new" in raw_lower:
                new_page = await self.context.new_page()
                self.page = new_page
                return {"ok": True, "message": "New tab opened"}
            elif "close" in raw_lower:
                if len(self.context.pages) > 1:
                    await self.page.close()
                    self.page = self.context.pages[-1]
                    return {"ok": True, "message": "Tab closed"}
                else:
                    return {"ok": False, "error": "Cannot close last tab"}
            elif "next" in raw_lower:
                pages = self.context.pages
                current_idx = pages.index(self.page) if self.page in pages else 0
                next_idx = (current_idx + 1) % len(pages)
                self.page = pages[next_idx]
                return {"ok": True, "message": "Switched to next tab"}
            elif "previous" in raw_lower or "prev" in raw_lower:
                pages = self.context.pages
                current_idx = pages.index(self.page) if self.page in pages else 0
                prev_idx = (current_idx - 1) % len(pages)
                self.page = pages[prev_idx]
                return {"ok": True, "message": "Switched to previous tab"}
            elif "list" in raw_lower:
                tabs = [{"url": p.url, "title": await p.title()} for p in self.context.pages]
                return {"ok": True, "message": f"Open tabs: {len(tabs)}", "tabs": tabs}
            
            return {"ok": False, "error": "Tab command not recognized"}
        
        return self._run_async(_tab())

    def _handle_content(self, raw: str) -> Dict[str, Any]:
        async def _content():
            await self._ensure_browser()
            
            content = await self.page.content()
            title = await self.page.title()
            url = self.page.url
            
            # Also get text content
            text = await self.page.evaluate("document.body.innerText")
            
            return {
                "ok": True,
                "message": f"Page: {title}",
                "url": url,
                "title": title,
                "text_preview": text[:2000] + ("..." if len(text) > 2000 else "")
            }
        
        return self._run_async(_content())

    def can_handle(self, desc: str) -> bool:
        return self.matches(desc)