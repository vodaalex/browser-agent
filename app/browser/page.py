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
        data = await self._page.screenshot(type="jpeg", quality=60, full_page=False)
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
            logger.warning("Failed to extract accessibility tree")
        return elements

