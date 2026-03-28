import asyncio

from playwright.async_api import Page

from app.log import logger


class BrowserActions:

    def __init__(self, page: Page, on_page_change=None):
        self._page = page
        self._on_page_change = on_page_change  # called after actions that change the page

    def _notify_page_change(self):
        if self._on_page_change:
            self._on_page_change()

    async def navigate(self, url: str) -> dict:
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await self._wait_for_stable()
            self._notify_page_change()
            return {"success": True, "url": self._page.url}
        except Exception as e:
            logger.warning("Navigate failed: %s", e)
            return {"success": False, "error": str(e)}

    async def click(self, x: int, y: int) -> dict:
        try:
            await self._page.mouse.click(x, y)
            await asyncio.sleep(1.0)
            self._notify_page_change()
            return {
                "success": True,
                "url": self._page.url,
                "hint": "Call get_page_state() to see what changed",
            }
        except Exception as e:
            logger.warning("Click failed: %s", e)
            return {"success": False, "error": str(e)}

    async def type_text(self, text: str) -> dict:
        try:
            await self._page.keyboard.type(text, delay=15)
            return {"success": True}
        except Exception as e:
            logger.warning("Type failed: %s", e)
            return {"success": False, "error": str(e)}

    async def press_key(self, key: str) -> dict:
        try:
            await self._page.keyboard.press(key)
            await asyncio.sleep(0.3)
            return {"success": True}
        except Exception as e:
            logger.warning("Press key failed: %s", e)
            return {"success": False, "error": str(e)}

    async def scroll(self, x: int, y: int, delta_y: int) -> dict:
        try:
            await self._page.mouse.move(x, y)
            await self._page.mouse.wheel(delta_x=0, delta_y=delta_y)
            await asyncio.sleep(0.3)
            self._notify_page_change()
            return {"success": True}
        except Exception as e:
            logger.warning("Scroll failed: %s", e)
            return {"success": False, "error": str(e)}

    async def wait(self, milliseconds: int) -> dict:
        ms = min(max(milliseconds, 100), 3_000)
        await asyncio.sleep(ms / 1000)
        return {"success": True}

    async def type_and_submit(self, x: int, y: int, text: str) -> dict:
        try:
            await self._page.mouse.click(x, y)
            await asyncio.sleep(0.3)
            await self._page.keyboard.type(text, delay=15)
            await self._page.keyboard.press("Enter")
            await self._wait_for_stable()
            self._notify_page_change()
            return {"success": True, "url": self._page.url, "typed": text}
        except Exception as e:
            logger.warning("type_and_submit failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── Private ──────────────────────────────────────────────────

    async def _wait_for_stable(self):
        try:
            await self._page.wait_for_load_state("networkidle", timeout=2_500)
        except Exception:
            await asyncio.sleep(0.8)



