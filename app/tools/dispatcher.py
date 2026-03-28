"""Tool dispatcher — maps tool names to handlers with descriptions."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Callable, Awaitable
from urllib.parse import urlparse

from app.log import logger
from app.tools import handlers

if TYPE_CHECKING:
    from app.browser.manager import BrowserManager

# Type alias for a handler coroutine
Handler = Callable[["BrowserManager", dict], Awaitable[list | str]]


class ToolDispatcher:
    """Registry-based tool dispatcher.

    Adding a new tool:
      1. Add JSON schema in ``definitions.py``
      2. Add handler in ``handlers.py``
      3. Register it in ``_build_registry()``
    """

    def __init__(self, browser: BrowserManager):
        self._browser = browser
        self._registry: dict[str, Handler] = self._build_registry()

    # ── Public API ───────────────────────────────────────────────

    async def dispatch(self, name: str, args: dict, *, step: int = 0) -> list | str:
        """Execute a tool by name and return its result."""
        handler = self._registry.get(name)
        if handler is None:
            logger.warning("Unknown tool requested: %s", name)
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            result = await handler(self._browser, args)
            return result
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return json.dumps({"error": str(e)})

    def invalidate_cache(self):
        """Invalidate the page-state cache (URL-based cache in PageStateExtractor)."""
        try:
            self._browser.page_state.invalidate_cache()
        except Exception:
            pass

    @property
    def current_url(self) -> str:
        """Current browser URL (empty string if unavailable)."""
        try:
            return self._browser.page.url
        except Exception:
            return ""

    @property
    def page_changes_on(self) -> frozenset[str]:
        """Tools that trigger action_result events (non-observation tools)."""
        return frozenset({"navigate", "click", "type_text", "press_key", "scroll", "wait"})

    # ── Action descriptions (human-readable) ─────────────────────

    @staticmethod
    def describe(tool: str, args: dict) -> str:
        """Return a short human-readable description of a tool call."""
        if tool == "navigate":
            url = args.get("url", "")
            try:
                domain = urlparse(url).netloc or url[:40]
            except Exception:
                domain = url[:40]
            return f"Navigating to {domain}"
        elif tool == "click":
            return f"Clicking at ({args.get('x', 0)}, {args.get('y', 0)})"
        elif tool == "type_text":
            text = args.get("text", "")
            preview = text[:25] + "…" if len(text) > 25 else text
            return f'Typing "{preview}"'
        elif tool in ("get_page_state", "screenshot"):
            return "Analyzing page state"
        elif tool == "wait":
            return f"Waiting {args.get('milliseconds', 0)}ms"
        elif tool == "scroll":
            delta = args.get("delta_y", 0)
            direction = "down" if delta > 0 else "up"
            return f"Scrolling {direction}"
        elif tool == "press_key":
            return f"Pressing {args.get('key', '')}"
        elif tool == "ask_user":
            q = args.get("question", "")
            return f"Asking: {q[:40]}…" if len(q) > 40 else f"Asking: {q}"
        elif tool == "task_complete":
            return "Completing task"
        return tool

    # ── Private ──────────────────────────────────────────────────

    def _build_registry(self) -> dict[str, Handler]:
        return {
            "get_page_state": handlers.handle_page_state,
            "screenshot": handlers.handle_page_state,
            "navigate": handlers.handle_navigate,
            "click": handlers.handle_click,
            "type_text": handlers.handle_type_text,
            "press_key": handlers.handle_press_key,
            "scroll": handlers.handle_scroll,
            "wait": handlers.handle_wait,
        }
