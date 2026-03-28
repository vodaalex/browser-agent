import json
import pytest
import pytest_asyncio

from app.tools.dispatcher import ToolDispatcher


@pytest.fixture
def dispatcher(mock_browser):
    return ToolDispatcher(mock_browser)


class TestDescribe:
    def test_navigate(self):
        desc = ToolDispatcher.describe("navigate", {"url": "https://google.com/search?q=test"})
        assert "google.com" in desc

    def test_click(self):
        desc = ToolDispatcher.describe("click", {"x": 100, "y": 200})
        assert "100" in desc and "200" in desc

    def test_type_text_short(self):
        desc = ToolDispatcher.describe("type_text", {"text": "hello"})
        assert "hello" in desc

    def test_type_text_long(self):
        desc = ToolDispatcher.describe("type_text", {"text": "a" * 50})
        assert "…" in desc

    def test_scroll_down(self):
        desc = ToolDispatcher.describe("scroll", {"delta_y": 300})
        assert "down" in desc

    def test_scroll_up(self):
        desc = ToolDispatcher.describe("scroll", {"delta_y": -300})
        assert "up" in desc

    def test_unknown(self):
        desc = ToolDispatcher.describe("unknown_tool", {})
        assert desc == "unknown_tool"


class TestDispatch:
    @pytest.mark.asyncio
    async def test_navigate(self, dispatcher, mock_browser):
        result = await dispatcher.dispatch("navigate", {"url": "https://example.com"})
        parsed = json.loads(result)
        assert parsed["success"] is True
        mock_browser.actions.navigate.assert_awaited_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_click(self, dispatcher, mock_browser):
        result = await dispatcher.dispatch("click", {"x": 10, "y": 20})
        parsed = json.loads(result)
        assert parsed["success"] is True
        mock_browser.actions.click.assert_awaited_once_with(10, 20)

    @pytest.mark.asyncio
    async def test_unknown_tool(self, dispatcher):
        result = await dispatcher.dispatch("nonexistent", {})
        parsed = json.loads(result)
        assert "error" in parsed


