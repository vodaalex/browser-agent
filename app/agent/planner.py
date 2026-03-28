from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from app.config import Settings, settings
from app.llm.prompts import PLANNER_SYSTEM_PROMPT
from app.log import logger

if TYPE_CHECKING:
    from app.llm.client import LLMClient


class TaskPlanner:

    def __init__(self, llm: LLMClient, cfg: Settings | None = None):
        self._llm = llm
        self._cfg = cfg or settings

    async def create_plan(self, task: str) -> list[str]:
        try:
            response = await self._llm.create_message(
                messages=[{"role": "user", "content": f"Task: {task}"}],
                system=PLANNER_SYSTEM_PROMPT,
                max_tokens=300,
                model_override=self._cfg.planner_model_name,
            )
            text = next(
                (b.text for b in response.content if b.type == "text"), "[]"
            )
            # Strip markdown code fences if present
            text = text.strip()
            m = re.search(r"\[.*\]", text, re.DOTALL)
            if m:
                text = m.group(0)
            plan = json.loads(text)
            if isinstance(plan, list):
                logger.info("Plan created: %d steps", len(plan))
                return plan
            return []
        except Exception as e:
            logger.warning("Planning failed: %s", e)
            return []

