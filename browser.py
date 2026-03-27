import asyncio
import base64
import os
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None

    async def start(self):
        headless = os.getenv("HEADLESS", "false").lower() == "true"
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-timer-throttling",
            ],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.page = await self.context.new_page()
        await self.page.goto("about:blank")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def screenshot(self) -> str:
        data = await self.page.screenshot(
            type="jpeg",
            quality=60,
            full_page=False,
        )
        return base64.b64encode(data).decode("utf-8")

    async def get_page_state(self) -> dict:
        await self._auto_dismiss_popups()
        screenshot_b64 = await self.screenshot()
        elements = await self._get_accessibility_tree()
        return {
            "screenshot": screenshot_b64,
            "elements": elements,
            "url": self.page.url,
        }

    async def _auto_dismiss_popups(self):
        """Try to dismiss obvious overlays and cookie banners."""
        try:
            overlay = await self.page.query_selector(
                '[role="dialog"]:visible, .modal:visible, '
                '[class*="cookie"]:visible, [class*="consent"]:visible, '
                '[class*="popup"]:visible, [class*="overlay"]:visible'
            )
            if overlay and await overlay.is_visible():
                await self.page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
        except Exception:
            pass

    async def _get_accessibility_tree(self) -> list:
        elements = []
        try:
            handles = await self.page.query_selector_all(
                'button, a, input, select, textarea, [role="button"], '
                '[role="link"], [role="menuitem"], [role="tab"], '
                '[role="checkbox"], [role="radio"], [tabindex]'
            )
            for handle in handles[:25]:
                try:
                    bbox = await handle.bounding_box()
                    if not bbox:
                        continue
                    if bbox["x"] < -100 or bbox["y"] < -100:
                        continue
                    tag = await handle.evaluate("el => el.tagName.toLowerCase()")
                    text = ""
                    try:
                        text = await handle.inner_text()
                    except Exception:
                        pass
                    aria = await handle.get_attribute("aria-label") or ""
                    placeholder = await handle.get_attribute("placeholder") or ""
                    input_type = await handle.get_attribute("type") or ""
                    label = (text or aria or placeholder)[:40].strip()
                    # Skip elements with no useful label
                    if not label:
                        continue
                    el_data: dict = {
                        "type": tag,
                        "text": label,
                        "bbox": [
                            round(bbox["x"]),
                            round(bbox["y"]),
                            round(bbox["width"]),
                            round(bbox["height"]),
                        ],
                    }
                    if input_type:
                        el_data["input_type"] = input_type
                    elements.append(el_data)
                except Exception:
                    continue
        except Exception:
            pass
        return elements

    async def wait_for_stable(self):
        """Wait for page network to settle after navigation."""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass  # Timeout is fine — continue

    async def navigate(self, url: str) -> dict:
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await self.wait_for_stable()
            return {"success": True, "url": self.page.url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def click(self, x: int, y: int) -> dict:
        try:
            await self.page.mouse.click(x, y)
            await asyncio.sleep(0.7)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def type_text(self, text: str) -> dict:
        try:
            await self.page.keyboard.type(text, delay=30)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def press_key(self, key: str) -> dict:
        try:
            await self.page.keyboard.press(key)
            await asyncio.sleep(0.5)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scroll(self, x: int, y: int, delta_y: int) -> dict:
        try:
            await self.page.mouse.move(x, y)
            await self.page.mouse.wheel(delta_x=0, delta_y=delta_y)
            await asyncio.sleep(0.4)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def wait(self, milliseconds: int) -> dict:
        ms = min(max(milliseconds, 100), 5000)
        await asyncio.sleep(ms / 1000)
        return {"success": True}
