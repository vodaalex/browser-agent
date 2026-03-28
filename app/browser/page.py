import asyncio
import base64

from playwright.async_api import Page

from app.log import logger


class PageStateExtractor:

    def __init__(self, page: Page):
        self._page = page
        self._cached_elements: list = []
        self._cached_url: str = ""
        self._cached_dom_hash: str = ""
        self._last_dom_hash: str = ""
        self._call_count: int = 0

    def invalidate_cache(self):
        self._cached_url = ""
        self._cached_elements = []
        self._cached_dom_hash = ""

    async def screenshot(self) -> str:
        data = await self._page.screenshot(type="jpeg", quality=80, full_page=False)
        b64 = base64.b64encode(data).decode("utf-8")
        del data
        return b64

    async def get_elements(self) -> dict:
        self._call_count += 1
        if self._call_count % 10 == 0:
            try:
                await self._page.evaluate("() => { if (window.gc) window.gc(); }")
            except Exception:
                pass
        current_url = self._page.url
        dom_hash = await self._get_dom_hash()
        self._last_dom_hash = dom_hash
        if current_url != self._cached_url or dom_hash != self._cached_dom_hash:
            self._cached_elements = await self._get_accessibility_tree()
            self._cached_url = current_url
            self._cached_dom_hash = dom_hash
        return {
            "elements": self._cached_elements,
            "url": current_url,
            "dom_hash": dom_hash,
        }

    async def get_page_state(self) -> dict:
        self._call_count += 1
        # Periodically nudge JS GC to keep renderer memory stable
        if self._call_count % 10 == 0:
            try:
                await self._page.evaluate("() => { if (window.gc) window.gc(); }")
            except Exception:
                pass

        screenshot_b64 = await self.screenshot()
        current_url = self._page.url
        dom_hash = await self._get_dom_hash()
        self._last_dom_hash = dom_hash
        # Re-extract a11y tree when URL or DOM structure changed (modals, overlays)
        if current_url != self._cached_url or dom_hash != self._cached_dom_hash:
            self._cached_elements = await self._get_accessibility_tree()
            self._cached_url = current_url
            self._cached_dom_hash = dom_hash
        return {
            "screenshot": screenshot_b64,
            "elements": self._cached_elements,
            "url": current_url,
            "dom_hash": dom_hash,
        }


    async def _get_dom_hash(self) -> str:
        try:
            result = await self._page.evaluate("""() => {
                const headers = [...document.querySelectorAll('h1,h2,h3')]
                    .map(h => h.innerText.trim()).join('|').slice(0, 100);
                const dialogs = document.querySelectorAll(
                    '[role="dialog"]:not([hidden])'
                ).length;
                const clickable = [...document.querySelectorAll('*')]
                    .filter(el => {
                        if (el.offsetParent === null && el.tagName !== 'BODY') return false;
                        const rect = el.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) return false;
                        const ti = parseInt(el.getAttribute('tabindex') ?? '-1');
                        const role = el.getAttribute('role') || '';
                        return ti >= 0 || ['button','link','menuitem','tab',
                            'checkbox','radio','option'].includes(role);
                    }).length;
                return headers + '_d' + dialogs + '_c' + clickable;
            }""")
            return str(result)
        except Exception:
            return ""


    async def _get_accessibility_tree(self) -> list:
        elements: list[dict] = []
        try:
            results = await self._page.evaluate("""() => {
                const INTERACTIVE_ROLES = new Set([
                    'button','link','menuitem','tab','checkbox',
                    'radio','option','listitem','combobox','textbox',
                    'searchbox','spinbutton','slider','switch'
                ]);
                const vh = window.innerHeight;
                const vw = window.innerWidth;
                const modalElements = [];
                const regularElements = [];
                const allEls = [...document.querySelectorAll('*')].filter(el => {
                    if (el.offsetParent === null && el.tagName !== 'BODY') return false;
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return false;
                    const ti = parseInt(el.getAttribute('tabindex') ?? '-1');
                    if (ti >= 0) return true;
                    const role = (el.getAttribute('role') || '').toLowerCase();
                    if (INTERACTIVE_ROLES.has(role)) return true;
                    const tag = el.nodeName.toLowerCase();
                    return ['input','select','textarea'].includes(tag) &&
                           el.type !== 'hidden';
                });
                for (const el of allEls) {
                    const r = el.getBoundingClientRect();
                    if (r.x < -50 || r.y < -50 || r.y > vh + 50) continue;
                    if (r.x > vw + 50) continue;
                    if (r.width === 0 || r.height === 0) continue;
                    const text = (
                        el.innerText ||
                        el.getAttribute('aria-label') ||
                        el.getAttribute('placeholder') || ''
                    ).slice(0, 25).trim();
                    if (!text) continue;
                    const data = {
                        tag: el.tagName.toLowerCase(),
                        text: text,
                        inputType: el.getAttribute('type') || '',
                        x: Math.round(r.x),
                        y: Math.round(r.y),
                        w: Math.round(r.width),
                        h: Math.round(r.height),
                    };
                    // Check if element lives inside a modal / overlay
                    let parent = el.parentElement;
                    let inModal = false;
                    for (let i = 0; i < 8; i++) {
                        if (!parent) break;
                        const role = parent.getAttribute('role') || '';
                        const ps = window.getComputedStyle(parent);
                        const zi = parseInt(ps.zIndex) || 0;
                        if (role === 'dialog' || role === 'alertdialog' ||
                            (zi > 100 && ps.position === 'fixed') ||
                            (zi > 100 && ps.position === 'absolute')) {
                            inModal = true;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    if (inModal) {
                        modalElements.push(data);
                    } else {
                        regularElements.push(data);
                    }
                }
                // Modal elements first so they are never pushed out by background UI
                return [...modalElements, ...regularElements].slice(0, 25);
            }""")
            for el_info in results:
                el_data: dict = {
                    "type": el_info["tag"],
                    "text": el_info["text"],
                    "bbox": [el_info["x"], el_info["y"], el_info["w"], el_info["h"]],
                }
                if el_info["inputType"]:
                    el_data["input_type"] = el_info["inputType"]
                elements.append(el_data)
        except Exception:
            logger.warning("Failed to extract accessibility tree")
        return elements
