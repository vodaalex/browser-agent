from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_browser():
    browser = AsyncMock()

    # Mock page_state.get_page_state
    browser.page_state.get_page_state.return_value = {
        "screenshot": "base64data==",
        "elements": [
            {"type": "button", "text": "Submit", "bbox": [100, 200, 80, 30]},
        ],
        "url": "https://example.com",
    }

    # Mock actions
    browser.actions.navigate.return_value = {"success": True, "url": "https://example.com"}
    browser.actions.click.return_value = {"success": True}
    browser.actions.type_text.return_value = {"success": True}
    browser.actions.press_key.return_value = {"success": True}
    browser.actions.scroll.return_value = {"success": True}
    browser.actions.wait.return_value = {"success": True}

    return browser


@pytest.fixture
def mock_llm_response():
    """Factory fixture for building mock LLM responses."""

    def _make(text: str = "", tool_calls: list | None = None, stop_reason: str = "end_turn"):
        response = MagicMock()
        content = []

        if text:
            text_block = MagicMock()
            text_block.type = "text"
            text_block.text = text
            content.append(text_block)

        if tool_calls:
            for tc in tool_calls:
                block = MagicMock()
                block.type = "tool_use"
                block.id = tc.get("id", "tool_123")
                block.name = tc["name"]
                block.input = tc.get("input", {})
                content.append(block)

        response.content = content
        response.stop_reason = stop_reason
        return response

    return _make

