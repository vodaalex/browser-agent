from __future__ import annotations

import asyncio
import json
from typing import Callable, Awaitable

import anthropic

from app.config import settings
from app.log import logger
from app.llm.client import LLMClient
from app.llm.prompts import SYSTEM_PROMPT
from app.tools.definitions import TOOL_DEFINITIONS
from app.tools.dispatcher import ToolDispatcher
from app.agent.planner import TaskPlanner
from app.agent.context import ContextManager
from app.browser.manager import BrowserManager


class AgentExecutor:

    def __init__(
        self,
        browser: BrowserManager,
        send_event: Callable[[dict], Awaitable[None]],
        wait_for_user: Callable[[], Awaitable[str]],
    ):
        self.send_event = send_event
        self.wait_for_user = wait_for_user

        # Composed components
        self.llm = LLMClient()
        self.planner = TaskPlanner(self.llm)
        self.context = ContextManager()
        self.dispatcher = ToolDispatcher(browser)

        self._running = False
        self._step = 0

    # ── Public API ───────────────────────────────────────────────

    async def run(self, task: str):
        """Execute a browser task end-to-end."""
        self._running = True
        self._step = 0
        self.context.reset()
        self.dispatcher.invalidate_cache()

        # ── Hierarchical planning ────────────────────────────────
        plan = await self.planner.create_plan(task)

        if plan:
            await self.send_event({"type": "plan", "steps": plan})

        self.context.init_from_plan(task, plan)
        await self.send_event({"type": "thought", "content": f"Starting task: {task}"})

        try:
            while self._running:
                self._step += 1
                await self.send_event({"type": "step", "step": self._step})

                # ── Max steps guard ──────────────────────────────
                if self._step > settings.max_steps:
                    await self.send_event({
                        "type": "ask_user",
                        "question": (
                            f"I've taken {settings.max_steps} steps. "
                            "Should I continue or stop? (reply 'continue' or 'stop')"
                        ),
                    })
                    answer = await self.wait_for_user()
                    if any(w in answer.lower() for w in ("stop", "нет", "no", "quit")):
                        break
                    self._step = 0  # reset counter, keep going

                # ── Main LLM call ────────────────────────────────
                response = await self.llm.create_message(
                    messages=self.context.messages,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                )

                self.context.append_assistant(response.content)

                # Emit any text thoughts
                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        await self.send_event({"type": "thought", "content": block.text})

                if response.stop_reason == "end_turn":
                    await self.send_event({"type": "complete", "report": "Task finished."})
                    break

                if response.stop_reason != "tool_use":
                    break

                # ── Process tool calls ───────────────────────────
                tool_results = []
                stop_after = False

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input

                    # task_complete has no action item — only the final complete event
                    if tool_name != "task_complete":
                        action_event: dict = {
                            "type": "action",
                            "tool": tool_name,
                            "description": ToolDispatcher.describe(tool_name, tool_input),
                            "args": tool_input,
                        }
                        # Attach current URL for page-observation actions
                        if tool_name in ("get_page_state", "screenshot"):
                            action_event["url"] = self.dispatcher.current_url
                        await self.send_event(action_event)

                    # ── task_complete ─────────────────────────────
                    if tool_name == "task_complete":
                        report = tool_input.get("report", "Task completed.")
                        await self.send_event({"type": "complete", "report": report})
                        tool_results.append(
                            self._make_tool_result(block.id, {"success": True})
                        )
                        stop_after = True
                        break

                    # ── ask_user ──────────────────────────────────
                    if tool_name == "ask_user":
                        question = tool_input.get("question", "")
                        await self.send_event({"type": "ask_user", "question": question})
                        answer = await self.wait_for_user()
                        tool_results.append(
                            self._make_tool_result(block.id, {"answer": answer})
                        )
                        continue

                    # ── Browser tools ────────────────────────────
                    result_content = await self.dispatcher.dispatch(
                        tool_name, tool_input, step=self._step,
                    )

                    # Track URL from page-state observations
                    if tool_name in ("get_page_state", "screenshot"):
                        self._track_url_from_result(result_content)

                    # Send action_result event for non-observation tools
                    if tool_name in self.dispatcher.page_changes_on:
                        await self._emit_action_result(tool_name, result_content)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_content,
                    })

                if tool_results:
                    self.context.append_tool_results(tool_results)

                # ── Stuck detection ──────────────────────────────
                if self.context.is_stuck():
                    await self.send_event({
                        "type": "thought",
                        "content": "Detected: same page for 4+ observations. Asking for guidance.",
                    })
                    await self.send_event({
                        "type": "ask_user",
                        "question": "I seem to be stuck on the same page. Can you help me proceed?",
                    })
                    answer = await self.wait_for_user()
                    self.context.append_user_guidance(answer)

                if stop_after:
                    break

        except asyncio.CancelledError:
            logger.info("Agent task cancelled")
        except anthropic.APIError as e:
            logger.error("Anthropic API error: %s", e.message)
            await self.send_event({"type": "error", "message": f"API error: {e.message}"})
        except Exception as e:
            logger.error("Agent error: %s", e, exc_info=True)
            await self.send_event({"type": "error", "message": str(e)})
        finally:
            self._running = False

    # ── Private helpers ──────────────────────────────────────────

    @staticmethod
    def _make_tool_result(tool_use_id: str, data: dict) -> dict:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": json.dumps(data),
        }

    def _track_url_from_result(self, result_content):
        """Extract URL from a page-state result and record it."""
        if isinstance(result_content, list):
            for item in result_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    try:
                        data = json.loads(item["text"])
                        if "url" in data:
                            self.context.track_url(data["url"])
                    except (json.JSONDecodeError, KeyError):
                        pass

    async def _emit_action_result(self, tool_name: str, result_content):
        is_error = False
        detail = ""
        if isinstance(result_content, str):
            try:
                parsed = json.loads(result_content)
                is_error = "error" in parsed
                detail = (
                    str(parsed.get("error", ""))[:60]
                    if is_error
                    else parsed.get("url", "")
                )
            except Exception:
                pass
        await self.send_event({
            "type": "action_result",
            "tool": tool_name,
            "result": "error" if is_error else "success",
            "detail": detail,
        })

