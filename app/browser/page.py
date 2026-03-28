import asyncio
import base64

from playwright.async_api import Page

from app.log import logger


class PageStateExtractor:

    def __init__(self, page: Page):
        self._page = page
        self._cached_elements: list = []
        self._cached_url: str = ""

    def invalidate_cache(self):
        self._cached_url = ""
        self._cached_elements = []

    async def screenshot(self) -> str:
        data = await self._page.screenshot(type="jpeg", quality=80, full_page=False)
        return base64.b64encode(data).decode("utf-8")

    async def get_page_state(self) -> dict:
        await self._auto_dismiss_popups()
        screenshot_b64 = await self.screenshot()
        current_url = self._page.url
        # Re-extract a11y tree only when URL changed
        if current_url != self._cached_url:
            self._cached_elements = await self._get_accessibility_tree()
            self._cached_url = current_url
        return {
            "screenshot": screenshot_b64,
            "elements": self._cached_elements,
            "url": current_url,
        }

    # ── Private helpers ──────────────────────────────────────────

    async def _auto_dismiss_popups(self):
        try:
            overlay = await self._page.query_selector(
                '[role="dialog"]:visible, .modal:visible, '
                '[class*="cookie"]:visible, [class*="consent"]:visible, '
                '[class*="popup"]:visible, [class*="overlay"]:visible'
            )
            if overlay and await overlay.is_visible():
                await self._page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
        except Exception:
            logger.debug("Popup dismiss failed (non-critical)")

    async def _get_accessibility_tree(self) -> list:
        elements: list[dict] = []
        try:
            handles = await self._page.query_selector_all(
                'button, a, input, select, textarea, [role="button"], '
                '[role="link"], [role="menuitem"], [role="tab"], '
                '[role="checkbox"], [role="radio"], [tabindex]'
            )
            for handle in handles[:40]:
                try:
                    el_info = await handle.evaluate("""el => {
                        const r = el.getBoundingClientRect();
                        if (r.x < -100 || r.y < -100 || r.width === 0 || r.height === 0)
                            return null;
                        const text = (
                            el.innerText ||
                            el.getAttribute('aria-label') ||
                            el.getAttribute('placeholder') || ''
                        ).slice(0, 40).trim();
                        if (!text) return null;
                        return {
                            tag: el.tagName.toLowerCase(),
                            text: text,
                            inputType: el.getAttribute('type') || '',
                            rect: {
                                x: Math.round(r.x),
                                y: Math.round(r.y),
                                w: Math.round(r.width),
                                h: Math.round(r.height)
                            }
                        };
                    }""")
                    if not el_info:
                        continue

                    el_data: dict = {
                        "type": el_info["tag"],
                        "text": el_info["text"],
                        "bbox": [
                            el_info["rect"]["x"],
                            el_info["rect"]["y"],
                            el_info["rect"]["w"],
                            el_info["rect"]["h"],
                        ],
                    }
                    if el_info["inputType"]:
                        el_data["input_type"] = el_info["inputType"]
                    elements.append(el_data)
                except Exception:
                    continue
        except Exception:
            logger.warning("Failed to extract accessibility tree")
        return elements

