from __future__ import annotations

import json

from app.config import Settings, settings
from app.log import logger


class ContextManager:

    def __init__(self, cfg: Settings | None = None):
        self._cfg = cfg or settings
        self.messages: list[dict] = []
        self._url_history: list[str] = []

    def reset(self):
        self.messages = []
        self._url_history = []

    # ── Initialisation ───────────────────────────────────────────

    def init_from_plan(self, task: str, plan: list[str]):
        if plan:
            plan_text = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(plan))
            self.messages = [
                {
                    "role": "user",
                    "content": (
                        f"Task: {task}\n\n"
                        f"Your plan:\n{plan_text}\n\n"
                        "Now execute this plan step by step."
                    ),
                }
            ]
        else:
            self.messages = [{"role": "user", "content": task}]

    # ── Append helpers ───────────────────────────────────────────

    def append_assistant(self, content):
        self.messages.append({"role": "assistant", "content": content})

    def append_tool_results(self, results: list[dict]):
        self.messages.append({"role": "user", "content": results})
        self.maybe_compress()

    def append_user_guidance(self, text: str):
        self.messages.append({"role": "user", "content": f"User guidance: {text}"})

    # ── State tracking & stuck detection ─────────────────────────

    def track_url(self, url: str):
        """Legacy alias — prefer track_state()."""
        self.track_state(url)

    def track_state(self, url: str, content_hash: str = ""):
        """Track page state combining URL and visible content hash."""
        state_key = f"{url}#{content_hash}"
        self._url_history.append(state_key)

    def is_stuck(self) -> bool:
        if len(self._url_history) >= 5:
            recent = self._url_history[-5:]
            if len(set(recent)) == 1 and "about:blank" not in recent[0]:
                self._url_history = []  # reset to avoid repeated trigger
                logger.info("Stuck detected: same state for 5+ observations")
                return True
        return False

    # ── Context compression ──────────────────────────────────────

    def maybe_compress(self):
        """Remove old screenshots when context grows too large."""
        context_size = sum(len(json.dumps(m, default=str)) for m in self.messages)
        if context_size < self._cfg.compress_threshold:
            return

        max_screenshots = self._cfg.max_screenshots_in_context
        screenshot_count = 0

        # Walk backwards to keep the most recent screenshots
        for msg in reversed(self.messages):
            if msg["role"] != "user":
                continue
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for i, block in enumerate(content):
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tr_content = block.get("content", "")
                if not isinstance(tr_content, list):
                    continue
                has_img = any(
                    isinstance(b, dict) and b.get("type") == "image"
                    for b in tr_content
                )
                if has_img:
                    screenshot_count += 1
                    if screenshot_count > max_screenshots:
                        text_blocks = [
                            b
                            for b in tr_content
                            if isinstance(b, dict) and b.get("type") == "text"
                        ]
                        content[i] = {
                            **block,
                            "content": text_blocks
                            + [{"type": "text", "text": "[screenshot removed]"}],
                        }

        # Truncate middle tool results when conversation is long
        if len(self.messages) > 12:
            preserved = self.messages[:2]   # task + plan always kept
            recent = self.messages[-10:]    # last 10 messages kept in full
            middle = []
            for msg in self.messages[2:-10]:
                if msg["role"] == "user":
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        new_content = []
                        for block in content:
                            if (
                                isinstance(block, dict)
                                and block.get("type") == "tool_result"
                            ):
                                raw = block.get("content", "")
                                if isinstance(raw, str) and len(raw) > 200:
                                    # JSON string result (get_elements etc.)
                                    raw = raw[:100] + "...[truncated]"
                                    new_content.append({**block, "content": raw})
                                elif isinstance(raw, list):
                                    # Multimodal list (get_page_state): extract URL, drop elements + screenshot
                                    url_text = ""
                                    for b in raw:
                                        if isinstance(b, dict) and b.get("type") == "text":
                                            try:
                                                d = json.loads(b["text"])
                                                url_text = d.get("url", "")
                                            except Exception:
                                                pass
                                    new_content.append({
                                        **block,
                                        "content": [{"type": "text", "text": json.dumps({"url": url_text, "elements": "[removed]"})}],
                                    })
                                else:
                                    new_content.append(block)
                            else:
                                new_content.append(block)
                        middle.append({**msg, "content": new_content})
                    else:
                        middle.append(msg)
                else:
                    middle.append(msg)
            self.messages = preserved + middle + recent

        logger.debug(
            "Context compressed: %d bytes, kept %d screenshots",
            context_size,
            min(screenshot_count, max_screenshots),
        )

