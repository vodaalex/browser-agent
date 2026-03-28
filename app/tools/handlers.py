"""Tool handler functions.

Each handler receives the browser manager and tool arguments,
and returns the result to be sent back to the LLM.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.log import logger

if TYPE_CHECKING:
    from app.browser.manager import BrowserManager


# ── Page observation ─────────────────────────────────────────────

async def handle_page_state(browser: BrowserManager, _args: dict) -> list:
    """Return screenshot + elements + URL as a multimodal content list."""
    state = await browser.page_state.get_page_state()
    # Persist dom_hash on extractor for executor to read during stuck tracking
    browser.page_state._last_dom_hash = state.get("dom_hash", "")
    return [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": state["screenshot"],
            },
        },
        {
            "type": "text",
            "text": json.dumps(
                {"url": state["url"], "elements": state["elements"]},
                ensure_ascii=False,
            ),
        },
    ]


# ── Browser actions ──────────────────────────────────────────────

async def handle_navigate(browser: BrowserManager, args: dict) -> str:
    result = await browser.actions.navigate(args["url"])
    return json.dumps(result)


async def handle_click(browser: BrowserManager, args: dict) -> str:
    result = await browser.actions.click(args["x"], args["y"])
    return json.dumps(result)


async def handle_type_text(browser: BrowserManager, args: dict) -> str:
    result = await browser.actions.type_text(args["text"])
    return json.dumps(result)


async def handle_press_key(browser: BrowserManager, args: dict) -> str:
    result = await browser.actions.press_key(args["key"])
    return json.dumps(result)


async def handle_scroll(browser: BrowserManager, args: dict) -> str:
    result = await browser.actions.scroll(args["x"], args["y"], args["delta_y"])
    return json.dumps(result)


async def handle_wait(browser: BrowserManager, args: dict) -> str:
    result = await browser.actions.wait(args["milliseconds"])
    return json.dumps(result)


async def handle_type_and_submit(browser: BrowserManager, args: dict) -> str:
    result = await browser.actions.type_and_submit(args["x"], args["y"], args["text"])
    return json.dumps(result)

