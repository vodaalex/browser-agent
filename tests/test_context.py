import json
import pytest

from app.agent.context import ContextManager
from app.config import Settings


@pytest.fixture
def ctx():
    cfg = Settings(
        anthropic_api_key="test",
        compress_threshold=500,       # low threshold for testing
        max_screenshots_in_context=1,
    )
    return ContextManager(cfg)


class TestInitFromPlan:
    def test_with_plan(self, ctx: ContextManager):
        ctx.init_from_plan("Go to google", ["Open browser", "Search"])
        assert len(ctx.messages) == 1
        assert "Your plan:" in ctx.messages[0]["content"]
        assert "1. Open browser" in ctx.messages[0]["content"]

    def test_without_plan(self, ctx: ContextManager):
        ctx.init_from_plan("Go to google", [])
        assert ctx.messages == [{"role": "user", "content": "Go to google"}]


class TestStuckDetection:
    def test_not_stuck_when_few_urls(self, ctx: ContextManager):
        ctx.track_state("https://a.com")
        ctx.track_state("https://a.com")
        assert ctx.is_stuck() is False

    def test_stuck_after_5_same(self, ctx: ContextManager):
        for _ in range(5):
            ctx.track_state("https://a.com")
        assert ctx.is_stuck() is True

    def test_not_stuck_with_different_urls(self, ctx: ContextManager):
        ctx.track_state("https://a.com")
        ctx.track_state("https://b.com")
        ctx.track_state("https://a.com")
        ctx.track_state("https://c.com")
        assert ctx.is_stuck() is False

    def test_about_blank_never_stuck(self, ctx: ContextManager):
        for _ in range(6):
            ctx.track_state("about:blank")
        assert ctx.is_stuck() is False

    def test_stuck_resets_history(self, ctx: ContextManager):
        for _ in range(5):
            ctx.track_state("https://a.com")
        assert ctx.is_stuck() is True
        # After stuck, history is reset — should not trigger again immediately
        assert ctx.is_stuck() is False

    def test_content_hash_differentiates_same_url(self, ctx: ContextManager):
        # Same URL but different DOM state should not be stuck
        for i in range(5):
            ctx.track_state("https://a.com", f"hash_{i}")
        assert ctx.is_stuck() is False

    def test_same_url_and_hash_triggers_stuck(self, ctx: ContextManager):
        for _ in range(5):
            ctx.track_state("https://a.com", "same_hash")
        assert ctx.is_stuck() is True


class TestCompression:
    def test_removes_old_screenshots(self, ctx: ContextManager):
        # Build 3 tool results with images (exceeds threshold of 500 bytes)
        for i in range(3):
            ctx.messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": f"t{i}",
                        "content": [
                            {"type": "image", "source": {"data": "x" * 200}},
                            {"type": "text", "text": json.dumps({"url": "https://example.com"})},
                        ],
                    }
                ],
            })

        ctx.maybe_compress()

        # The most recent screenshot should be kept; older ones replaced
        removed_count = 0
        for msg in ctx.messages:
            if msg["role"] != "user" or not isinstance(msg["content"], list):
                continue
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    inner = block.get("content", [])
                    if any(
                        isinstance(b, dict) and b.get("text") == "[screenshot removed]"
                        for b in inner
                    ):
                        removed_count += 1

        assert removed_count >= 2  # at least 2 of 3 should be removed

