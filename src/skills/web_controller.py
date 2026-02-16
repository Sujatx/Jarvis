"""
Web Controller - Elite Digital Entity.
Brave-aware persistent session with robust state management.
"""

import asyncio
import os
import winreg
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.core.logging_config import get_logger

logger = get_logger(__name__)

def get_brave_path():
    """Locate the Brave executable on Windows."""
    paths = [
        os.path.join(os.environ.get("ProgramFiles", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe")
    ]
    for p in paths:
        if os.path.exists(p): return p
    return None

class WebController:
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.active = False
        self._lock = asyncio.Lock()

    async def start(self, headless=False):
        """Initialize browser with preference awareness."""
        async with self._lock:
            if self.active and self.browser:
                try:
                    await self.page.evaluate("1")
                    return
                except:
                    await self.close()

            logger.info("WebController: Launching Entity...")
            self.playwright = await async_playwright().start()
            
            # ELITE: Use Brave if available
            brave_path = get_brave_path()
            if brave_path:
                logger.info(f"WebController: Using Brave at {brave_path}")
                self.browser = await self.playwright.chromium.launch(executable_path=brave_path, headless=headless)
            else:
                logger.info("WebController: Brave not found, using system Chrome.")
                self.browser = await self.playwright.chromium.launch(channel="chrome", headless=headless)
            
            self.context = await self.browser.new_context(viewport={"width": 1280, "height": 720})
            self.page = await self.context.new_page()
            self.active = True

    async def get_interactive_html(self) -> str:
        if not self.active: await self.start()
        try:
            return await self.page.evaluate('''() => {
                const items = [];
                const all = document.querySelectorAll('button, a, input, [role="button"]');
                for (const el of all) {
                    if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                        items.push(`<${el.tagName} id="${el.id}" title="${el.title}">${el.innerText || el.value || el.placeholder || ''}</${el.tagName}>`);
                    }
                }
                return items.join('\\n').slice(0, 10000);
            }''')
        except: return ""

    async def navigate(self, url: str):
        if not self.active: await self.start()
        if not url.startswith("http"): url = f"https://{url}"
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._inject_visualizer()
            return f"Successfully navigated to {url}"
        except Exception as e:
            return f"Failed to navigate: {e}"

    async def click(self, selector: str):
        if not self.active or not selector: return "No target."
        try:
            await self._highlight(selector)
            await asyncio.sleep(0.5)
            await self.page.click(selector, timeout=5000)
            return f"Clicked {selector}"
        except Exception as e: return f"Click Failed: {e}"

    async def type_text(self, selector: str, text: str):
        if not self.active or not selector: return "No target."
        try:
            await self._highlight(selector)
            await self.page.fill(selector, "")
            await self.page.type(selector, text, delay=50)
            await self.page.press(selector, "Enter")
            return f"Typed {text}"
        except Exception as e: return f"Type Failed: {e}"

    async def _inject_visualizer(self):
        try:
            await self.page.add_style_tag(content="""
                @keyframes jarvis-pulse {
                    0% { box-shadow: 0 0 0 0 rgba(0, 229, 255, 0.7); }
                    70% { box-shadow: 0 0 0 10px rgba(0, 229, 255, 0); }
                    100% { box-shadow: 0 0 0 0 rgba(0, 229, 255, 0); }
                }
                .jarvis-highlight {
                    outline: 2px solid #00e5ff !important;
                    border-radius: 4px !important;
                    animation: jarvis-pulse 1.5s infinite !important;
                }
            """)
        except: pass

    async def _highlight(self, selector: str):
        try:
            await self.page.eval_on_selector(selector, "el => el.classList.add('jarvis-highlight')")
            asyncio.create_task(self._remove_highlight(selector))
        except: pass

    async def _remove_highlight(self, selector: str):
        await asyncio.sleep(1.5)
        try: await self.page.eval_on_selector(selector, "el => el.classList.remove('jarvis-highlight')")
        except: pass

    async def close(self):
        async with self._lock:
            if self.browser:
                try: await self.browser.close()
                except: pass
            if self.playwright:
                try: await self.playwright.stop()
                except: pass
            self.active = False
            self.browser = None
            self.page = None

WEB = WebController()
