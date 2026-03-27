from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.planner import TaskPlanner


def _make_llm_response(text: str):
    response = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    return response


@pytest.fixture
def planner():
    llm = AsyncMock()
    return TaskPlanner(llm), llm


class TestCreatePlan:
    @pytest.mark.asyncio
    async def test_valid_plan(self, planner):
        tp, llm = planner
        llm.create_message.return_value = _make_llm_response(
            '["Step one", "Step two", "Step three"]'
        )
        plan = await tp.create_plan("Search for something")
        assert plan == ["Step one", "Step two", "Step three"]

    @pytest.mark.asyncio
    async def test_plan_with_markdown_fences(self, planner):
        tp, llm = planner
        llm.create_message.return_value = _make_llm_response(
            '```json\n["A", "B"]\n```'
        )
        plan = await tp.create_plan("Do something")
        assert plan == ["A", "B"]

    @pytest.mark.asyncio
    async def test_plan_returns_empty_on_bad_json(self, planner):
        tp, llm = planner
        llm.create_message.return_value = _make_llm_response("not valid json at all")
        plan = await tp.create_plan("Do something")
        assert plan == []

    @pytest.mark.asyncio
    async def test_plan_returns_empty_on_exception(self, planner):
        tp, llm = planner
        llm.create_message.side_effect = Exception("API down")
        plan = await tp.create_plan("Do something")
        assert plan == []

    @pytest.mark.asyncio
    async def test_plan_returns_empty_on_non_list(self, planner):
        tp, llm = planner
        llm.create_message.return_value = _make_llm_response('{"steps": ["a", "b"]}')
        plan = await tp.create_plan("Do something")
        assert plan == []


